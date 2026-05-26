"use strict";

// asyncapi-subscription-filter-entity-cap
//
// For every x-subscription.filter string, count the number of
// `LIKE '<Entity>.` patterns (where <Entity> is a PascalCase identifier).
// If > 10, fail. A subscription filter with more than 10 entity patterns
// signals a worker that is doing too much — split it. This also defends
// against approaching ASB's 2048-char filter-size limit.
//
// Given: $.operations[*].x-subscription.filter

const MAX_ENTITY_PATTERNS = 10;
const ENTITY_LIKE_PATTERN = /LIKE\s+'([A-Z][A-Za-z0-9]*)\./g;

module.exports = function asyncSubscriptionFilterEntityCap(targetVal, _opts, context) {
  if (typeof targetVal !== "string" || targetVal.length === 0) return;

  const matches = targetVal.match(ENTITY_LIKE_PATTERN);
  const count = matches ? matches.length : 0;
  if (count <= MAX_ENTITY_PATTERNS) return;

  // Path shape: ['operations', operationId, 'x-subscription', 'filter']
  const path = context && Array.isArray(context.path) ? context.path : [];
  const operationId = path.length >= 2 ? path[1] : "<unknown>";

  return [
    {
      message: `Subscription filter on operation ${operationId} covers ${count} entity patterns (max ${MAX_ENTITY_PATTERNS}). Consider splitting this worker.`,
    },
  ];
};
