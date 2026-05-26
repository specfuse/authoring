"use strict";

// specfuse-async-worker-inbox-dedup-coherence
//
// Validates the joint contract for x-worker.idempotent × x-worker.inboxDedup ×
// applied operation traits per AsyncAPI Handbook §4.6:
//
//   idempotent | inboxDedup | required delivery guarantee | verdict
//   -----------|------------|-----------------------------|---------
//   true       | true       | atLeastOnce                 | OK (default)
//   true       | false      | atLeastOnce                 | OK (opt-out)
//   false      | false      | atMostOnce                  | OK (best-effort)
//   false      | true       | (any)                       | INCOHERENT
//
// Plus: idempotent: false WITHOUT atMostOnce delivery is INCOHERENT under
// at-least-once semantics (the producer's retry budget would re-deliver,
// and the handler can't safely re-process).
//
// Trait identification: AsyncAPI 3 inlines trait $refs at bundle time, so the
// operation's `traits[i]` ends up as the trait object itself (not a {name,...}
// reference). Each trait in async-common/operation-traits/common.yaml carries
// `x-delivery.guarantee` ('atLeastOnce' | 'atMostOnce'). We inspect that field
// directly. If the trait was authored without x-delivery (legacy / custom),
// we treat its guarantee as unknown and fall back to the default rule (which
// requires atMostOnce when idempotent: false).
//
// Given: $.operations[*]

function deliveryGuarantees(operation) {
  const traits = operation && operation.traits;
  if (!Array.isArray(traits)) return [];
  const guarantees = [];
  for (const trait of traits) {
    if (!trait || typeof trait !== "object") continue;
    const delivery = trait["x-delivery"];
    if (delivery && typeof delivery === "object" && typeof delivery.guarantee === "string") {
      guarantees.push(delivery.guarantee);
    }
  }
  return guarantees;
}

module.exports = function asyncInboxDedupCoherence(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;

  const worker = targetVal["x-worker"];
  if (!worker || typeof worker !== "object") return; // emit-* operations: no x-worker — skip

  // Defaults: both true
  const idempotent = worker.idempotent !== false;
  const inboxDedup = worker.inboxDedup !== false;

  const operationKey =
    Array.isArray(context.path) && context.path.length >= 2 ? context.path[1] : "<unknown>";
  const guarantees = deliveryGuarantees(targetVal);
  const hasAtMostOnce = guarantees.includes("atMostOnce");
  const hasAtLeastOnce = guarantees.includes("atLeastOnce");

  const results = [];

  // Incoherent: idempotent=false but inboxDedup=true
  if (!idempotent && inboxDedup) {
    results.push({
      message: `Operation ${operationKey}: x-worker.idempotent=false combined with x-worker.inboxDedup=true is incoherent. Inbox dedup without idempotency guarantees nothing useful (a non-idempotent handler claims the inbox row, fails midway with a partial side effect, then on retry the claim already exists and the handler skips — silent half-effect). Either set idempotent: true (and prove the handler is safe to retry) or set inboxDedup: false with atMostOnce delivery (fireAndForget trait).`,
    });
  }

  // Incoherent: idempotent=false without atMostOnce delivery
  if (!idempotent && !hasAtMostOnce) {
    results.push({
      message: `Operation ${operationKey}: x-worker.idempotent=false requires atMostOnce delivery (apply the fireAndForget trait via traits: [{ $ref: '../../../async-common/operation-traits/common.yaml#/fireAndForget' }]) — or set idempotent: true.`,
    });
  }

  // Incoherent: idempotent=false with both atMostOnce AND atLeastOnce stamped
  if (!idempotent && hasAtMostOnce && hasAtLeastOnce) {
    results.push({
      message: `Operation ${operationKey}: x-worker.idempotent=false combined with both atMostOnce and atLeastOnce delivery traits is incoherent. Pick one delivery guarantee.`,
    });
  }

  return results.length ? results : undefined;
};
