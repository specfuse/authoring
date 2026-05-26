"use strict";

// arazzoRecipeScenarioExclusion
//
// Validates that recipe workflows do not coexist with scenario-only extensions.
// When x-recipe is present (at document root or workflow level), the following
// must not appear:
//   - x-actors (recipes use implicit $system actor)
//   - x-mcp (recipes are not MCP tools)
//   - x-setup (recipes compose via extends, not $setup)
//   - x-ui on steps (UI hints are for scenarios only)
//
// Handbook: Section 3.3, 4.6, 4.8, 7.4, 13 Do NOT #6, #8, #18
// Given: $

const SCENARIO_ONLY_FIELDS = ["x-actors", "x-mcp", "x-setup"];

const FIELD_REASONS = {
  "x-actors": "Recipes execute as the implicit $system actor (mapped to Admin).",
  "x-mcp": "Recipes are infrastructure, not user-facing MCP tools.",
  "x-setup": "Recipes compose via 'extends', not $setup. Only scenarios reference recipes via $setup.",
};

module.exports = function arazzoRecipeScenarioExclusion(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;

  const hasRootRecipe = !!targetVal["x-recipe"];
  const workflows = Array.isArray(targetVal.workflows) ? targetVal.workflows : [];
  const results = [];

  // Check document-root-level recipe
  if (hasRootRecipe) {
    for (const field of SCENARIO_ONLY_FIELDS) {
      if (targetVal[field]) {
        results.push({
          message: "Recipe file must not declare '" + field + "'. " + FIELD_REASONS[field],
          path: [field],
        });
      }
    }

    // Check all steps in all workflows for x-ui
    workflows.forEach((wf, wfIdx) => {
      const steps = Array.isArray(wf.steps) ? wf.steps : [];
      steps.forEach((step, stepIdx) => {
        if (step && step["x-ui"]) {
          const stepName = step.stepId || "steps[" + stepIdx + "]";
          results.push({
            message: "Recipe step '" + stepName + "' must not have 'x-ui'. UI automation hints are for scenario workflows only.",
            path: ["workflows", wfIdx, "steps", stepIdx, "x-ui"],
          });
        }
      });
    });
  }

  // Also check per-workflow x-recipe (for files where x-recipe is at workflow level)
  workflows.forEach((wf, wfIdx) => {
    if (!wf || !wf["x-recipe"]) return;

    for (const field of SCENARIO_ONLY_FIELDS) {
      if (wf[field]) {
        const wfName = wf.workflowId || "workflows[" + wfIdx + "]";
        results.push({
          message: "Recipe workflow '" + wfName + "' must not declare '" + field + "'. " + FIELD_REASONS[field],
          path: ["workflows", wfIdx, field],
        });
      }
    }

    const steps = Array.isArray(wf.steps) ? wf.steps : [];
    steps.forEach((step, stepIdx) => {
      if (step && step["x-ui"]) {
        const stepName = step.stepId || "steps[" + stepIdx + "]";
        const wfName = wf.workflowId || "workflows[" + wfIdx + "]";
        results.push({
          message: "Recipe step '" + stepName + "' in workflow '" + wfName + "' must not have 'x-ui'.",
          path: ["workflows", wfIdx, "steps", stepIdx, "x-ui"],
        });
      }
    });
  });

  return results.length > 0 ? results : undefined;
};
