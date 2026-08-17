"use strict";

// specfuse-read-model-* — the shape a `Read{Entity}` replica schema must carry.
//
// A `Read{Entity}` is the fourth member of the `New*` / `Update*` / `Basic*`
// derived-model family, and it is the one that is NOT a wire shape. It declares
// exactly what slice of `{Entity}` a foreign service may keep as a persisted
// read-only replica. Every check here defends that distinction.
//
// Do not read "read model" as either of the two things that phrase already
// means in Specfuse: `x-operation.category: query` (a read-side operation) and
// `Basic*` (a lightweight response projection). `Read{Entity}` is a STORE
// shape. `Basic*` was deliberately not reused for it, because `Basic*` carries
// expandable refs and lives in the Api layer — reusing it would weld a
// consuming service's database table to another team's response DTO.
//
// Checks (selected by functionOptions.check, one rule id each):
//
//   primaryKey    no `id` and no `{Source}Id`. A replica row with no key has
//                 nothing for an inbox handler to upsert on.
//   nested        a property embedding another entity or a `Basic*`. That
//                 re-welds the cross-service edge the replica exists to cut.
//                 Remediation is to flatten to the FK. Enum- and value-object-
//                 typed properties are fine and never trip this.
//   wireType      used as a request body, a response, or a projection embed.
//   sourceDelete  the source entity leaves `x-entity.delete` undeclared (absent
//                 resolves to `hard` by fallback, which is not a fact a replica
//                 can be built on), or declares `soft` while the replica omits
//                 the deletion-state property — in which case every holding
//                 service serves rows the owner considers gone.
//
// See handbooks/Vendor_Extensions.md §14.
//
// Given: $.components.schemas
// Runs with `resolved: false` against the BUNDLED document: the nested and
// wire-type checks key on `$ref` NAMES, which resolution erases, and the
// schema-name lookups need bundled `components.schemas` keys.

const READ_PREFIX = "Read";
const BASIC_PREFIX = "Basic";
const DELETED_AT = "deletedat"; // compared lowercased

// `#/components/schemas/Foo` and `./Foo.yaml` both name `Foo`. The second form
// matters because an editor lints the unbundled file the author is typing in.
function refName(ref) {
  if (typeof ref !== "string" || ref.length === 0) return null;
  const last = ref.split("/").pop();
  if (!last) return null;
  return last.replace(/\.(ya?ml|json)$/i, "").replace(/^.*#/, "") || null;
}

// The one schema a property embeds, however it is spelled: a direct `$ref`, the
// `allOf: [{ $ref }]` wrapper a scalar projection uses, or an array's `items`.
function embedTarget(prop) {
  if (!prop || typeof prop !== "object") return null;
  if (prop.$ref) return refName(prop.$ref);
  if (Array.isArray(prop.allOf)) {
    for (const member of prop.allOf) {
      if (member && typeof member === "object" && member.$ref) return refName(member.$ref);
    }
  }
  if (prop.items && typeof prop.items === "object" && prop.items.$ref) {
    return refName(prop.items.$ref);
  }
  return null;
}

function readModels(schemas) {
  const out = [];
  for (const [name, schema] of Object.entries(schemas)) {
    if (!name.startsWith(READ_PREFIX)) continue;
    if (!schema || typeof schema !== "object") continue;
    const source = name.slice(READ_PREFIX.length);
    // `Read` followed by a lowercase letter is an ordinary schema name
    // (`Readme`, `Readiness`), not a replica declaration.
    if (!/^[A-Z]/.test(source)) continue;
    out.push({ name, schema, source });
  }
  return out;
}

function propertyNames(schema) {
  const props = schema.properties;
  if (!props || typeof props !== "object") return [];
  return Object.keys(props);
}

function hasNamed(names, wanted) {
  const target = wanted.toLowerCase();
  return names.some((n) => n.toLowerCase() === target);
}

function checkPrimaryKey(schemas, basePath) {
  const results = [];
  for (const { name, schema, source } of readModels(schemas)) {
    const names = propertyNames(schema);
    const entityKey = source + "Id";
    if (hasNamed(names, "id") || hasNamed(names, entityKey)) continue;
    results.push({
      message:
        `'${name}' does not carry '${source}'s primary key ('id' or '${entityKey}'). ` +
        `A replica with no key has nothing for an inbox handler to upsert on.`,
      path: [...basePath, name],
    });
  }
  return results;
}

function checkNested(schemas, basePath) {
  const results = [];
  const entities = new Set(
    Object.entries(schemas)
      .filter(([, s]) => s && typeof s === "object" && s["x-entity"])
      .map(([n]) => n),
  );

  for (const { name, schema } of readModels(schemas)) {
    const props = schema.properties;
    if (!props || typeof props !== "object") continue;

    for (const [propName, prop] of Object.entries(props)) {
      const target = embedTarget(prop);
      if (!target) continue;

      const isEntity = entities.has(target);
      const isBasic =
        target.startsWith(BASIC_PREFIX) &&
        /^[A-Z]/.test(target.slice(BASIC_PREFIX.length) || "");
      if (!isEntity && !isBasic) continue; // enum / value object / scalar ref

      results.push({
        message:
          `'${name}.${propName}' embeds '${target}', ${
            isEntity ? "an entity" : "a Basic* response projection"
          }. A replica is a flat store shape — flatten this to the foreign key ` +
          `(e.g. '${propName}Id'). Enum- and value-object-typed properties are fine.`,
        path: [...basePath, name, "properties", propName],
      });
    }
  }
  return results;
}

// Every schema name reachable from a request body, a response, or a projection
// embed — i.e. every name that is on the wire.
function collectWireNames(doc) {
  const wire = new Map(); // name -> short description of where it was seen
  const paths = (doc && doc.paths) || {};

  const noteContent = (content, where) => {
    if (!content || typeof content !== "object") return;
    for (const media of Object.values(content)) {
      const target = media && typeof media === "object" ? embedTarget(media.schema) : null;
      if (target && !wire.has(target)) wire.set(target, where);
    }
  };

  for (const [route, item] of Object.entries(paths)) {
    if (!item || typeof item !== "object") continue;
    for (const [method, op] of Object.entries(item)) {
      if (!op || typeof op !== "object") continue;
      if (op.requestBody && typeof op.requestBody === "object") {
        noteContent(op.requestBody.content, `the request body of ${method.toUpperCase()} ${route}`);
      }
      if (op.responses && typeof op.responses === "object") {
        for (const [status, response] of Object.entries(op.responses)) {
          if (!response || typeof response !== "object") continue;
          noteContent(response.content, `the ${status} response of ${method.toUpperCase()} ${route}`);
        }
      }
    }
  }

  // Projection embeds: a property marked `x-expand-of` or `x-projection` is a
  // read-convenience field on a wire shape, so whatever it embeds is on the
  // wire too.
  const schemas = (doc && doc.components && doc.components.schemas) || {};
  for (const [owner, schema] of Object.entries(schemas)) {
    const props = schema && typeof schema === "object" ? schema.properties : null;
    if (!props || typeof props !== "object") continue;
    for (const [propName, prop] of Object.entries(props)) {
      if (!prop || typeof prop !== "object") continue;
      const isProjection =
        Object.prototype.hasOwnProperty.call(prop, "x-expand-of") || prop["x-projection"] === true;
      if (!isProjection) continue;
      const target = embedTarget(prop);
      if (target && !wire.has(target)) {
        wire.set(target, `the projection embed '${owner}.${propName}'`);
      }
    }
  }

  return wire;
}

function checkWireType(schemas, doc, basePath) {
  const wire = collectWireNames(doc);
  if (wire.size === 0) return [];

  const results = [];
  for (const { name } of readModels(schemas)) {
    const where = wire.get(name);
    if (!where) continue;
    results.push({
      message:
        `'${name}' appears in ${where}. A Read{Entity} is a store shape, not a wire shape — ` +
        `putting it on the wire welds a consuming service's replica table to this API's ` +
        `payloads. Use the entity or its 'Basic' projection there.`,
      path: [...basePath, name],
    });
  }
  return results;
}

function deleteModeOf(entitySchema) {
  const entity = entitySchema && entitySchema["x-entity"];
  if (!entity || typeof entity !== "object") return undefined;
  const declared = entity.delete;
  if (typeof declared === "string") return declared;
  if (declared && typeof declared === "object" && typeof declared.mode === "string") {
    return declared.mode;
  }
  return undefined;
}

function checkSourceDelete(schemas, basePath) {
  const results = [];
  for (const { name, schema, source } of readModels(schemas)) {
    const sourceSchema = schemas[source];
    // No source entity in this document: the pairing rules report that; there
    // is no delete semantics to read either way.
    if (!sourceSchema || typeof sourceSchema !== "object" || !sourceSchema["x-entity"]) continue;

    const mode = deleteModeOf(sourceSchema);
    if (mode === undefined) {
      results.push({
        message:
          `'${source}' has a replica '${name}' but leaves \`x-entity.delete\` undeclared. ` +
          `Absent resolves to \`hard\` by fallback, and a replica's removal semantics derive ` +
          `from that value — silence is not a fact a replica can be built on.`,
        path: [...basePath, source, "x-entity"],
      });
      continue;
    }

    // A malformed value is `specfuse-xentity-shape`'s to report; nothing more
    // to say about the replica when the mode did not parse.
    if (mode !== "soft") continue;

    if (hasNamed(propertyNames(schema), DELETED_AT)) continue;
    results.push({
      message:
        `'${source}' declares \`x-entity.delete: soft\` but its replica '${name}' has no ` +
        `\`deletedAt\` property. Soft removal is a field change — without it the replica can ` +
        `never represent an archived row, and every holding service serves data the owner ` +
        `considers gone.`,
      path: [...basePath, name],
    });
  }
  return results;
}

module.exports = function openapiReadModelShape(targetVal, opts, context) {
  if (!targetVal || typeof targetVal !== "object" || Array.isArray(targetVal)) return;

  const check = opts && opts.check;
  const doc = context && context.document ? context.document.data : undefined;
  const basePath =
    context && Array.isArray(context.path) ? context.path : ["components", "schemas"];

  switch (check) {
    case "primaryKey":
      return checkPrimaryKey(targetVal, basePath);
    case "nested":
      return checkNested(targetVal, basePath);
    case "wireType":
      return checkWireType(targetVal, doc, basePath);
    case "sourceDelete":
      return checkSourceDelete(targetVal, basePath);
    default:
      return;
  }
};
