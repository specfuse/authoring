"use strict";

// specfuse-services-* — the four checks over `info.x-services` that need to see
// more than the registry entry they are standing on.
//
// `info.x-services` declares which service owns which domain, and — via the
// optional `holds` key — which entities a service keeps a read-only replica of.
// The registry lives in the spec rather than in `project.json` because a
// project file is per-generation-run and legitimately exists once per service
// repository, so a registry there can never see two services at once and can
// never detect a domain claimed twice. That check is the reason the extension
// exists, and it is `duplicateOwner` below.
//
// Checks (selected by functionOptions.check, one rule id each so the ratchet
// can count them separately):
//
//   duplicateOwner       a domain claimed by more than one service. Names every
//                        claimant, because the fix is a choice between them.
//   unregisteredDomain   a claimed domain that is not a member of
//                        `info.x-domains`. Skipped entirely when the domain
//                        registry is absent — the two registries degrade
//                        independently, and an absent `x-domains` is a
//                        different (already reported) gap.
//   holds                `holds: [X]` where X is not an entity in the spec, or
//                        where no `ReadX` schema exists to generate from.
//   unheld               a `Read{Entity}` schema no service holds — authored
//                        and unused.
//
// The last two are the two halves of one declaration. The OWNER of an entity
// authors `Read{Entity}` saying what slice may be replicated at all; the HOLDER
// declares `holds: [Entity]` saying that it keeps a copy. Neither implies the
// other, so both directions are checked. See handbooks/Vendor_Extensions.md §14.
//
// Given: $.info["x-services"]
// Runs against the BUNDLED document with `resolved: false` — the schema-name
// lookups key on `components.schemas` keys, which only exist once bundled, and
// the `Read*` scan must see `$ref` strings rather than inlined targets.

const READ_PREFIX = "Read";

function serviceEntries(registry) {
  if (!registry || typeof registry !== "object" || Array.isArray(registry)) return [];
  return Object.entries(registry).filter(
    ([, meta]) => meta && typeof meta === "object" && !Array.isArray(meta),
  );
}

function stringList(value) {
  return Array.isArray(value) ? value.filter((v) => typeof v === "string" && v.length > 0) : [];
}

function schemasOf(doc) {
  const components = doc && doc.components;
  const schemas = components && components.schemas;
  return schemas && typeof schemas === "object" ? schemas : {};
}

function entityNames(schemas) {
  return new Set(
    Object.entries(schemas)
      .filter(([, schema]) => schema && typeof schema === "object" && schema["x-entity"])
      .map(([name]) => name),
  );
}

function checkDuplicateOwner(registry, basePath) {
  const claimants = new Map(); // domain -> [service, ...]
  for (const [service, meta] of serviceEntries(registry)) {
    for (const domain of stringList(meta.domains)) {
      if (!claimants.has(domain)) claimants.set(domain, []);
      claimants.get(domain).push(service);
    }
  }

  const results = [];
  for (const [domain, services] of claimants) {
    if (services.length < 2) continue;
    results.push({
      message:
        `Domain '${domain}' is claimed by ${services.length} services (${services.join(", ")}). ` +
        `A domain has exactly one owner — every other service reaches it through a declared ` +
        `replica, not by co-owning it.`,
      // Anchor on the first claimant: the fix is to drop the domain from all
      // but one entry, and any of them is an equally valid place to start.
      path: [...basePath, services[0], "domains"],
    });
  }
  return results;
}

function checkUnregisteredDomain(registry, doc, basePath) {
  const info = (doc && doc.info) || {};
  const declared = info["x-domains"];

  // Absent or empty domain registry: skip. Membership is unanswerable, and
  // reporting every claimed domain as unregistered would bury the one finding
  // that matters (the missing registry) under noise.
  let known;
  if (Array.isArray(declared)) {
    known = new Set(declared.filter((d) => typeof d === "string"));
  } else if (declared && typeof declared === "object") {
    known = new Set(Object.keys(declared));
  } else {
    return [];
  }
  if (known.size === 0) return [];

  const results = [];
  for (const [service, meta] of serviceEntries(registry)) {
    stringList(meta.domains).forEach((domain, index) => {
      if (known.has(domain)) return;
      results.push({
        message:
          `Service '${service}' claims domain '${domain}', which is not a member of ` +
          `info.x-domains. A service cannot own a domain the project has not declared.`,
        path: [...basePath, service, "domains", index],
      });
    });
  }
  return results;
}

function checkHolds(registry, doc, basePath) {
  const schemas = schemasOf(doc);
  const entities = entityNames(schemas);
  const results = [];

  for (const [service, meta] of serviceEntries(registry)) {
    stringList(meta.holds).forEach((held, index) => {
      const path = [...basePath, service, "holds", index];

      if (!entities.has(held)) {
        results.push({
          message:
            `Service '${service}' holds '${held}', which is not an entity in this spec. ` +
            `A replica needs a source entity to replicate.`,
          path,
        });
        return;
      }

      const readName = READ_PREFIX + held;
      if (!Object.prototype.hasOwnProperty.call(schemas, readName)) {
        results.push({
          message:
            `Service '${service}' holds '${held}' but no '${readName}' schema exists, so there is ` +
            `nothing to generate. \`holds\` and \`${readName}\` are two halves of one ` +
            `declaration: ${held}'s OWNER authors '${readName}' declaring what slice may be ` +
            `replicated, and '${service}' declares that it keeps a copy.`,
          path,
        });
      }
    });
  }
  return results;
}

function checkUnheld(registry, doc) {
  const schemas = schemasOf(doc);
  const held = new Set();
  for (const [, meta] of serviceEntries(registry)) {
    for (const entity of stringList(meta.holds)) held.add(entity);
  }

  const results = [];
  for (const name of Object.keys(schemas)) {
    if (!name.startsWith(READ_PREFIX)) continue;
    const source = name.slice(READ_PREFIX.length);
    // `Read` followed by a lowercase letter is an ordinary schema name
    // (`Readme`, `Readiness`), not a replica declaration.
    if (!/^[A-Z]/.test(source)) continue;
    if (held.has(source)) continue;

    results.push({
      message:
        `'${name}' declares a replicable slice of '${source}', but no service declares ` +
        `\`holds: [${source}]\`. It is authored and unused — either a service is missing the ` +
        `\`holds\` half of the declaration, or the schema should be removed.`,
      // Anchored on the schema, not on the registry: the registry is where the
      // rule is *given*, but one path per unheld replica is what keeps Spectral
      // from collapsing every finding in this check into a single line.
      path: ["components", "schemas", name],
    });
  }
  return results;
}

module.exports = function openapiServiceRegistry(targetVal, opts, context) {
  // A registry that is not a mapping expresses no ownership at all; that shape
  // failure is `specfuse-services-registry-shape`'s to report, and every check
  // here would otherwise report it a second time in a less useful form.
  if (!targetVal || typeof targetVal !== "object" || Array.isArray(targetVal)) return;

  const check = opts && opts.check;
  const doc = context && context.document ? context.document.data : undefined;
  const basePath = context && Array.isArray(context.path) ? context.path : ["info", "x-services"];

  switch (check) {
    case "duplicateOwner":
      return checkDuplicateOwner(targetVal, basePath);
    case "unregisteredDomain":
      return checkUnregisteredDomain(targetVal, doc, basePath);
    case "holds":
      return checkHolds(targetVal, doc, basePath);
    case "unheld":
      return checkUnheld(targetVal, doc);
    default:
      return;
  }
};
