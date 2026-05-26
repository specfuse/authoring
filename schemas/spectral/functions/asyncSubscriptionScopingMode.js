"use strict";

// specfuse-async-subscription-scoping-mode
//
// Validates x-subscription scoping per the three-mode model in AsyncAPI Handbook §4.3:
//
//   1. Authoring `filter` is FORBIDDEN. Filters are derived from `messages:` by
//      default. Use `requiredHeaders` for header-equality scoping or
//      `filterOverride` for forward-compat / unusual SQL.
//   2. `requiredHeaders` and `filterOverride` are MUTUALLY EXCLUSIVE.
//   3. Each key in `requiredHeaders` must reference a known envelope
//      ApplicationProperty. The kit's canonical baseline is `tenantId` and
//      `userId`; projects extend KNOWN_HEADERS via overlay when they
//      promote additional fields via x-envelope-promote (handbook §4.2).
//   4. When `filterOverride` is present, the operation's `description` must
//      include a justification (heuristic: ≥40 chars).
//
// Given: $.operations[*]

const KNOWN_HEADERS = new Set([
  // Universal envelope properties stamped by the producer pipeline
  // per AsyncAPI Handbook §0.8 (auditableEvent envelope shape).
  "tenantId",
  "userId",
  // Per-entity scoped headers populated via x-envelope-promote on snapshot
  // fields (handbook §4.2). The `channel` example here matches the
  // NotificationJob.* events pattern from samples/message-samples.yaml §5c.
  // Projects with their own x-envelope-promote declarations should extend
  // this set in their project Spectral overlay.
  "channel",
]);

module.exports = function asyncSubscriptionScopingMode(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;
  const subscription = targetVal["x-subscription"];
  if (!subscription || typeof subscription !== "object") return;

  const operationKey =
    Array.isArray(context.path) && context.path.length >= 2 ? context.path[1] : "<unknown>";
  const results = [];

  // Rule 1: forbid authored `filter`
  if (Object.prototype.hasOwnProperty.call(subscription, "filter")) {
    results.push({
      message: `Operation ${operationKey}: x-subscription.filter is forbidden. Filters are derived from 'messages:' by default. Use x-subscription.requiredHeaders for declarative header-equality scoping or x-subscription.filterOverride for forward-compat patterns. See AsyncAPI Handbook §4.3.`,
    });
  }

  // Rule 2: mutual exclusion
  const hasRequiredHeaders =
    subscription.requiredHeaders &&
    typeof subscription.requiredHeaders === "object" &&
    Object.keys(subscription.requiredHeaders).length > 0;
  const hasFilterOverride =
    typeof subscription.filterOverride === "string" && subscription.filterOverride.trim().length > 0;
  if (hasRequiredHeaders && hasFilterOverride) {
    results.push({
      message: `Operation ${operationKey}: x-subscription.requiredHeaders and x-subscription.filterOverride are mutually exclusive. Pick one mode.`,
    });
  }

  // Rule 3: known headers
  if (hasRequiredHeaders) {
    for (const key of Object.keys(subscription.requiredHeaders)) {
      if (!KNOWN_HEADERS.has(key)) {
        results.push({
          message: `Operation ${operationKey}: x-subscription.requiredHeaders.${key} is not a known envelope ApplicationProperty. Kit baseline: ${[...KNOWN_HEADERS].join(", ")}. To add a new scoped header, declare x-envelope-promote: true on the snapshot field that publishes it (handbook §4.2), then extend KNOWN_HEADERS in your project Spectral overlay.`,
        });
      }
    }
  }

  // Rule 4: filterOverride needs justification
  if (hasFilterOverride) {
    const description = targetVal.description;
    if (typeof description !== "string" || description.trim().length < 40) {
      results.push({
        message: `Operation ${operationKey}: x-subscription.filterOverride is used but the operation's description is missing or too short (<40 chars). Justify why derivation isn't sufficient — see AsyncAPI Handbook §4.3.`,
      });
    }
  }

  return results.length ? results : undefined;
};
