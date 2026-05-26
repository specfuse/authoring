"use strict";

// specfuse-async-context-coherence
//
// Joint contract for the optional `context` payload property on event messages:
//
//   1. context is allowed ONLY on state-transition events
//      (i.e., action verb is anything other than *Created / *Updated / *Deleted).
//   2. When context is present, x-trigger-mode MUST be 'explicit'.
//   3. When context is present, the message's `description` MUST be at least
//      40 characters (heuristic for "real justification, not a one-liner").
//      The handbook requires the description to justify why the metadata is
//      transient; we can't enforce semantic content from Spectral, but we can
//      enforce that an effortful description exists.
//
// Given: $.channels[*].messages[*]

function isCudSuffix(action) {
  return action.endsWith("Created") || action.endsWith("Updated") || action.endsWith("Deleted");
}

function payloadHasContext(message) {
  const payload = message && message.payload;
  if (!payload || typeof payload !== "object") return false;
  const props = payload.properties;
  if (!props || typeof props !== "object") return false;
  return Object.prototype.hasOwnProperty.call(props, "context");
}

module.exports = function asyncContextCoherence(targetVal, _opts, _context) {
  if (!targetVal || typeof targetVal !== "object") return;
  if (targetVal["x-message-category"] !== "event") return;
  if (!payloadHasContext(targetVal)) return;

  const xLabel = targetVal["x-label"];
  const action = xLabel && typeof xLabel.action === "string" ? xLabel.action : null;
  if (!action) return;

  const messageName = targetVal.name || "<unnamed>";
  const results = [];

  if (isCudSuffix(action)) {
    results.push({
      message: `Message ${messageName} declares payload.context but its action '${action}' is *Created/*Updated/*Deleted — Context is allowed only on state-transition events. Remove the context property or rename the event.`,
    });
  }

  const triggerMode = targetVal["x-trigger-mode"];
  if (triggerMode !== "explicit") {
    results.push({
      message: `Message ${messageName} declares payload.context but is missing x-trigger-mode: explicit. Context-bearing events must be emitted via an explicit service method — the auto-trigger-when path cannot populate transient metadata. See AsyncAPI Handbook §2.7.`,
    });
  }

  const description = targetVal.description;
  if (typeof description !== "string" || description.trim().length < 40) {
    results.push({
      message: `Message ${messageName} declares payload.context but its description is missing or too short (<40 chars). Justify why the metadata is transient and cannot live on the entity — see AsyncAPI Handbook §2.7.`,
    });
  }

  return results.length ? results : undefined;
};
