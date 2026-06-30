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
//     tenantId        : uuid
//
//   Optional (presence not enforced; if present, format/type checked):
//     causationId     : uuid
//     traceparent     : string
//     aggregateVersion: integer
//     userId          : uuid
//
// The rule discriminates "this is the auditableEvent trait" by checking that
// the header schema includes `eventId` (no other trait in the system has
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
  tenantId:         { required: true,  type: "string",  format: "uuid" },
  // optional but typed when present
  causationId:      { required: false, type: "string",  format: "uuid" },
  traceparent:      { required: false, type: "string"                  },
  aggregateVersion: { required: false, type: "integer"                 },
  userId:           { required: false, type: "string",  format: "uuid" },
};

const FORBIDDEN_LEGACY_FIELDS = ["messageType", "timestamp"];

module.exports = function asyncAuditableEventEnvelopeShape(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;
  const headers = targetVal.headers;
  if (!headers || typeof headers !== "object") return;
  const props = headers.properties;
  if (!props || typeof props !== "object") return;

  // Discriminator: only the auditableEvent trait carries `eventId`.
  if (!Object.prototype.hasOwnProperty.call(props, "eventId")) return;

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
      if (!Object.prototype.hasOwnProperty.call(props, name)) {
        results.push({
          message: `auditableEvent envelope (on message ${messageName}) is missing required property '${name}'. The canonical envelope from AsyncAPI Handbook §0.8 must be preserved.`,
        });
      } else if (!required.includes(name)) {
        results.push({
          message: `auditableEvent envelope property '${name}' (on message ${messageName}) must be listed in the trait's headers.required array.`,
        });
      }
    }
  }

  // 2. Type/format conformance for any field that IS present
  for (const [name, spec] of Object.entries(ENVELOPE_FIELDS)) {
    const def = props[name];
    if (!def || typeof def !== "object") continue;
    if (def.type !== spec.type) {
      results.push({
        message: `auditableEvent envelope property '${name}' (on message ${messageName}) has type '${def.type}'; canonical contract requires '${spec.type}'.`,
      });
    }
    if (spec.format && def.format !== spec.format) {
      results.push({
        message: `auditableEvent envelope property '${name}' (on message ${messageName}) has format '${def.format ?? "(none)"}'; canonical contract requires format '${spec.format}'.`,
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
