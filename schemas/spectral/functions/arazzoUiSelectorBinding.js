"use strict";

// arazzoUiSelectorBinding
//
// Verifies that each x-ui.selectors[].for value matches an x-ui.actions[].id
// in the same step. Dangling selector references are an error -- they indicate
// a renamed or removed action that the selector still points to.
//
// Handbook: Section 5.3 (binding rule)
// Given: $.workflows[*].steps[*]

module.exports = function arazzoUiSelectorBinding(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;

  const xUi = targetVal["x-ui"];
  if (!xUi || typeof xUi !== "object") return;

  const actions = Array.isArray(xUi.actions) ? xUi.actions : [];
  const selectors = Array.isArray(xUi.selectors) ? xUi.selectors : [];

  if (selectors.length === 0) return;

  const actionIds = new Set(
    actions.map(a => a && a.id).filter(Boolean)
  );

  const results = [];
  selectors.forEach((sel, idx) => {
    const forVal = sel && sel["for"];
    if (typeof forVal !== "string") return;
    if (!actionIds.has(forVal)) {
      const available = [...actionIds].join(", ");
      results.push({
        message: "Selector 'for: " + forVal + "' does not match any actions[].id in this step. Available action ids: " + (available || "(none)") + ". Either fix the reference or remove the dangling selector.",
        path: [...context.path, "x-ui", "selectors", idx, "for"],
      });
    }
  });

  return results.length > 0 ? results : undefined;
};
