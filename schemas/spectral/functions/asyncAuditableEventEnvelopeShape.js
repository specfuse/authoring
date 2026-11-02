"use strict";

// specfuse-async-auditable-event-envelope-shape
//
// Enforces that every event message's auditableEvent trait (post-bundle
// inlined into traits[i].headers) carries the canonical envelope from
// AsyncAPI Handbook §0.8:
//
//   Required (presence + format/type checked):
//     eventId         : uuid
//     correlationId   : uuid
//     aggregateId     : uuid
//     aggregateType   : string
//     eventVersion    : integer
//     producedAt      : date-time
//
//   Optional (presence not enforced; if present, format/type checked):
//     tenant          : uuid
//     causationId     : uuid
//     traceparent     : string
//     aggregateVersion: integer
//     userId          : uuid
//
// Each role above resolves the way the generator's envelope binding does: the
// header marked `x-envelope: <role>`, else the unmarked header with the role's
// canonical name. The tenant's canonical name comes from the project's
// `tenancy` block, which Spectral cannot read, so an unmarked tenant is only
// recognised as `tenantId`.
//
// The tenant is optional here because only the generator knows which aggregates
// are under the tenant: a global event must not require it
// (ASYNC_TENANT_HEADER_ON_GLOBAL_EVENT), and a scoped event must bind it
// (ASYNC_ENVELOPE_HEADER_MISSING). A trait cannot be judged on its own.
//
// The rule discriminates "this is the auditableEvent trait" by checking that
// the header schema binds the `eventId` role (no other trait in the system has
// that field). Drift in the trait file (legacy `messageType`, `timestamp`,
// or removal of any required field) fires this rule.
//
// Projects with a multi-level tenancy hierarchy may add narrower scoping
// fields (e.g., `siteId`, `regionId`) via `x-envelope-promote` declarations
// on the snapshot — this rule only enforces the canonical baseline shape.
//
// Given: $.channels[*].messages[*].traits[*]

const ENVELOPE_FIELDS = {
  // required per AsyncAPI Handbook §0.8
  eventId:          { required: true,  type: "string",  format: "uuid" },
  correlationId:    { required: true,  type: "string",  format: "uuid" },
  aggregateId:      { required: true,  type: "string",  format: "uuid" },
  aggregateType:    { required: true,  type: "string"                  },
  eventVersion:     { required: true,  type: "integer"                 },
  producedAt:       { required: true,  type: "string",  format: "date-time" },
  // optional but typed when present
  tenant:           { required: false, type: "string",  format: "uuid", canonicalName: "tenantId" },
  causationId:      { required: false, type: "string",  format: "uuid" },
  traceparent:      { required: false, type: "string"                  },
  aggregateVersion: { required: false, type: "integer"                 },
  userId:           { required: false, type: "string",  format: "uuid" },
};

const FORBIDDEN_LEGACY_FIELDS = ["messageType", "timestamp"];

function headerBoundTo(props, role, spec) {
  const names = Object.keys(props);
  const marked = names.find((name) => props[name] && props[name]["x-envelope"] === role);
  if (marked) return marked;
  const canonical = spec.canonicalName || role;
  return names.find((name) => name === canonical && !(props[name] && props[name]["x-envelope"]));
}

module.exports = function asyncAuditableEventEnvelopeShape(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;
  const headers = targetVal.headers;
  if (!headers || typeof headers !== "object") return;
  const props = headers.properties;
  if (!props || typeof props !== "object") return;

  // Discriminator: only the auditableEvent trait binds `eventId`.
  if (!headerBoundTo(props, "eventId", ENVELOPE_FIELDS.eventId)) return;

  const required = Array.isArray(headers.required) ? headers.required : [];
  const path = Array.isArray(context.path) ? context.path : [];
  const messageName =
    path.length >= 4 && path[3]
      ? `${path[1]}.${path[3]}`
      : "<unknown>";

  const results = [];

  // 1. Required-field presence (both in `required:` array and in `properties`)
  for (const [name, spec] of Object.entries(ENVELOPE_FIELDS)) {
    if (spec.required) {
      const header = headerBoundTo(props, name, spec);
      if (!header) {
        results.push({
          message: `auditableEvent envelope (on message ${messageName}) is missing required property '${name}'. The canonical envelope from AsyncAPI Handbook §0.8 must be preserved.`,
        });
      } else if (!required.includes(header)) {
        results.push({
          message: `auditableEvent envelope property '${header}' (on message ${messageName}) must be listed in the trait's headers.required array.`,
        });
      }
    }
  }

  // 2. Type/format conformance for any field that IS present
  for (const [name, spec] of Object.entries(ENVELOPE_FIELDS)) {
    const header = headerBoundTo(props, name, spec);
    const def = header && props[header];
    if (!def || typeof def !== "object") continue;
    if (def.type !== spec.type) {
      results.push({
        message: `auditableEvent envelope property '${header}' (on message ${messageName}) has type '${def.type}'; canonical contract requires '${spec.type}'.`,
      });
    }
    if (spec.format && def.format !== spec.format) {
      results.push({
        message: `auditableEvent envelope property '${header}' (on message ${messageName}) has format '${def.format ?? "(none)"}'; canonical contract requires format '${spec.format}'.`,
      });
    }
  }

  // 3. Forbidden legacy fields
  for (const legacy of FORBIDDEN_LEGACY_FIELDS) {
    if (Object.prototype.hasOwnProperty.call(props, legacy)) {
      results.push({
        message: `auditableEvent envelope (on message ${messageName}) carries legacy field '${legacy}'. Drop it — see AsyncAPI Handbook §0.8 for the canonical envelope. (messageType is removed; timestamp → producedAt.)`,
      });
    }
  }

  return results.length ? results : undefined;
};
