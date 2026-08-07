"use strict";

// specfuse-async-snapshot-guardrails
//
// AsyncAPI_Handbook.md §2.3 promises three snapshot guardrails. Two of them
// compare the snapshot against its SOURCE ENTITY, which lives in the OpenAPI
// document — a different spec, not reachable when Spectral is linting the
// AsyncAPI surface. Those two stay generator-side (see compatibility.md):
//
//   - a snapshot field whose source entity property carries
//     `x-classification: [pii|sensitive]` must be acknowledged
//   - a snapshot field must exist on the source entity
//
// What IS decidable from the AsyncAPI document alone is implemented here, and
// it is not nothing: it enforces the *shape and honesty* of the two override
// mechanisms, which were previously unenforced in any ruleset. An override
// that can be written malformed, or that can name a field the snapshot does
// not have, is an override that silently does nothing — the failure mode this
// guardrail exists to prevent.
//
//   1. Snapshot size. More than MAX_SCALAR_FIELDS scalar properties warns,
//      unless the snapshot declares `x-snapshot-size-acknowledged: true`.
//
//   2. `x-snapshot-pii-acknowledged` shape. Each entry must be
//      `propertyName: justification`, the justification a string of at least
//      MIN_JUSTIFICATION_CHARS characters. A bare list, or a too-short
//      string, is rejected — the handbook is explicit that a bare list is not
//      an acknowledgement.
//
//   3. Acknowledgement targets. An acknowledged property must actually exist
//      on the snapshot. A typo'd or stale entry looks like a considered
//      privacy decision while covering nothing.
//
//   4. `x-snapshot-size-acknowledged` must be boolean `true` if present.
//
// Given: a snapshot object (see the rule's `given` in specfuse-asyncapi.yaml).

const MAX_SCALAR_FIELDS = 25;
const MIN_JUSTIFICATION_CHARS = 20;
const PII_ACK = "x-snapshot-pii-acknowledged";
const SIZE_ACK = "x-snapshot-size-acknowledged";

const SCALAR_TYPES = new Set(["string", "number", "integer", "boolean"]);

function isScalar(prop) {
  if (!prop || typeof prop !== "object") return false;
  // A $ref to a standalone enum resolves to a string schema; after resolution
  // it looks scalar, which is correct — it occupies one field on the wire.
  if (typeof prop.type === "string") return SCALAR_TYPES.has(prop.type);
  return false;
}

module.exports = function asyncSnapshotGuardrails(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;

  const properties = targetVal.properties;
  if (!properties || typeof properties !== "object") return;

  const basePath = context && Array.isArray(context.path) ? context.path : [];
  const results = [];

  // ---- 1. Size ------------------------------------------------------------
  const scalarCount = Object.values(properties).filter(isScalar).length;
  const sizeAck = targetVal[SIZE_ACK];

  if (scalarCount > MAX_SCALAR_FIELDS && sizeAck !== true) {
    results.push({
      message:
        `Snapshot has ${scalarCount} scalar fields (max ${MAX_SCALAR_FIELDS}). A snapshot this wide ` +
        `couples consumers to most of the entity. Narrow it, or acknowledge deliberately with ` +
        `'${SIZE_ACK}: true'.`,
      path: [...basePath, "properties"],
    });
  }

  // ---- 4. Size-acknowledgement shape --------------------------------------
  if (sizeAck !== undefined && sizeAck !== true) {
    results.push({
      message: `'${SIZE_ACK}' must be the boolean true, or be omitted entirely.`,
      path: [...basePath, SIZE_ACK],
    });
  }

  // ---- 2 & 3. PII acknowledgement shape and targets ------------------------
  const piiAck = targetVal[PII_ACK];
  if (piiAck !== undefined) {
    if (Array.isArray(piiAck) || typeof piiAck !== "object" || piiAck === null) {
      results.push({
        message:
          `'${PII_ACK}' must be a map of propertyName to justification. A bare list is not an ` +
          `acknowledgement — the justification is the point. See Vendor_Extensions.md §11.2.`,
        path: [...basePath, PII_ACK],
      });
    } else {
      for (const [propName, justification] of Object.entries(piiAck)) {
        const at = [...basePath, PII_ACK, propName];

        if (typeof justification !== "string") {
          results.push({
            message:
              `'${PII_ACK}.${propName}' must be a justification string of at least ` +
              `${MIN_JUSTIFICATION_CHARS} characters.`,
            path: at,
          });
        } else if (justification.trim().length < MIN_JUSTIFICATION_CHARS) {
          results.push({
            message:
              `'${PII_ACK}.${propName}' is ${justification.trim().length} characters; at least ` +
              `${MIN_JUSTIFICATION_CHARS} are required. State why this classified field has to cross ` +
              `the event boundary, so the decision is reviewable.`,
            path: at,
          });
        }

        if (!Object.prototype.hasOwnProperty.call(properties, propName)) {
          results.push({
            message:
              `'${PII_ACK}.${propName}' acknowledges a property this snapshot does not have. A stale ` +
              `or misspelled entry reads as a considered privacy decision while covering nothing.`,
            path: at,
          });
        }
      }
    }
  }

  return results;
};
