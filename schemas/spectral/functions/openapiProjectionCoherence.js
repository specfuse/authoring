"use strict";

// specfuse-projection-coherence
//
// Validates the read-only projection markers on a main resource's properties.
// Both checks need sibling context — the twin property, or the schema's
// `required` array — so they cannot be expressed as a property-level rule.
//
// x-expand-of: <twin>   scalar projection. The named twin MUST be a sibling
//                       property, and MUST be either a `format: uuid` FK or a
//                       `type: string` natural key. Anything else means the
//                       projection has no identifier to expand. The twin's
//                       `required` status is not part of the check — see the
//                       note at the branch.
//
// x-projection: true    collection projection. MUST be an array of $ref, and
//                       MUST NOT appear in the schema's `required` array — a
//                       projection is a convenience the server may decline to
//                       populate, so a client cannot depend on it.
//
// See handbooks/Vendor_Extensions.md §1.9 and API_Handbook.md §9.5.
//
// Given: $.components.schemas[?(@ && @["x-entity"])]

module.exports = function openapiProjectionCoherence(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;

  const properties = targetVal.properties;
  if (!properties || typeof properties !== "object") return;

  const required = Array.isArray(targetVal.required) ? targetVal.required : [];
  const basePath = context && Array.isArray(context.path) ? context.path : [];
  const results = [];

  for (const [name, prop] of Object.entries(properties)) {
    if (!prop || typeof prop !== "object") continue;

    // ---- x-expand-of ----------------------------------------------------
    if (Object.prototype.hasOwnProperty.call(prop, "x-expand-of")) {
      const twinName = prop["x-expand-of"];
      const path = [...basePath, "properties", name, "x-expand-of"];

      if (typeof twinName !== "string" || twinName.length === 0) {
        results.push({
          message: `x-expand-of on '${name}' must name a sibling property.`,
          path,
        });
      } else if (!Object.prototype.hasOwnProperty.call(properties, twinName)) {
        results.push({
          message:
            `x-expand-of on '${name}' names '${twinName}', which is not a property of this schema. ` +
            `A scalar projection must expand an identifier that exists alongside it.`,
          path,
        });
      } else {
        // The twin must be an identifier. It need NOT be `required`: an
        // optional FK models a genuinely optional relationship, and the
        // projection is `readOnly` and itself forbidden from `required`
        // (below) precisely because the server may decline to populate it.
        // Demanding that the twin be required would contradict that, and it
        // would do so asymmetrically — the uuid branch never checked. Both
        // twin kinds are accepted optional or required.
        const twin = properties[twinName] || {};
        const isUuidFk = twin.format === "uuid";
        const isNaturalKey = twin.type === "string";

        if (!isUuidFk && !isNaturalKey) {
          results.push({
            message:
              `x-expand-of on '${name}' names '${twinName}', which is neither a 'format: uuid' FK ` +
              `nor a 'type: string' natural key. A projection needs an identifier to expand.`,
            path,
          });
        }
      }
    }

    // ---- x-projection ---------------------------------------------------
    if (Object.prototype.hasOwnProperty.call(prop, "x-projection")) {
      const path = [...basePath, "properties", name, "x-projection"];

      if (prop["x-projection"] !== true) {
        results.push({
          message: `x-projection on '${name}' must be the boolean true, or be omitted entirely.`,
          path,
        });
        continue;
      }

      const items = prop.items;
      const isRefArray =
        prop.type === "array" &&
        items &&
        typeof items === "object" &&
        typeof items.$ref === "string";

      if (!isRefArray) {
        results.push({
          message:
            `x-projection on '${name}' must mark an array whose items are a $ref. ` +
            `A collection projection references another entity's shape; it does not define one inline.`,
          path,
        });
      }

      if (required.includes(name)) {
        results.push({
          message:
            `Projection '${name}' must not be required. A projection is a read convenience the server ` +
            `may decline to populate, so a client cannot depend on its presence.`,
          path: [...basePath, "required"],
        });
      }
    }
  }

  return results;
};
