"use strict";

// specfuse-async-first-appearance-uses-created
//
// Heuristic: state-transition events whose x-trigger-when references no
// Before.* fields are very likely first-appearance events disguised as state
// transitions. The first-appearance rule (AsyncAPI Handbook §2.6) requires
// these to use the *Created suffix and capture the manner of creation as a
// snapshot field (e.g., creationSource: 'generated' | 'manual').
//
// We detect:
//   - x-trigger-when present (so the message is in the state-transition class)
//   - x-trigger-when references no Before.* tokens
//   - action verb is not *Created (we don't fire on legit *Created without trigger)
//
// False-positive scenario: a transition predicate that genuinely depends only
// on After fields (e.g., "After.publishedAt != null"). The author can suppress
// the warning by adding `x-first-appearance-acknowledged: false` to the
// message — declaring "I have considered this and it is genuinely a state
// transition, not a first appearance."
//
// Given: $.channels[*].messages[*]

module.exports = function asyncFirstAppearanceCreated(targetVal, _opts, _context) {
  if (!targetVal || typeof targetVal !== "object") return;
  if (targetVal["x-message-category"] !== "event") return;

  const xLabel = targetVal["x-label"];
  const action = xLabel && typeof xLabel.action === "string" ? xLabel.action : null;
  if (!action) return;

  // Skip if already *Created/*Updated/*Deleted
  if (
    action.endsWith("Created") ||
    action.endsWith("Updated") ||
    action.endsWith("Deleted")
  ) {
    return;
  }

  const triggerWhen = targetVal["x-trigger-when"];
  if (typeof triggerWhen !== "string" || triggerWhen.trim() === "") return;

  // Author opt-out
  if (targetVal["x-first-appearance-acknowledged"] === false) return;

  const referencesBefore = /\bBefore\./.test(triggerWhen);
  if (referencesBefore) return;

  const messageName = targetVal.name || "<unnamed>";
  const entity = (xLabel.entity || "Entity").trim();

  return [
    {
      message: `Message ${messageName} (action '${action}') uses a state-transition suffix but its x-trigger-when references no Before.* fields. This is likely a first-appearance event in disguise. First-appearance events must use the *Created suffix (e.g., '${entity}.Created') and capture the manner of creation as a snapshot field (e.g., creationSource: 'generated' | 'manual'). See AsyncAPI Handbook §2.6. If this really is a state transition, add x-first-appearance-acknowledged: false to suppress this rule.`,
    },
  ];
};
