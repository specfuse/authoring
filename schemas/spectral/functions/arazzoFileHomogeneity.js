"use strict";

// arazzoFileHomogeneity
//
// Checks that all workflows in a file share the same category -- either all
// recipes (have x-recipe) or all scenarios (no x-recipe). Mixed files are
// a validator error.
//
// When x-recipe is at the document root, all workflows inherit that category
// and the file is homogeneous by definition.
//
// Handbook: Section 3.3
// Given: $

module.exports = function arazzoFileHomogeneity(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;

  const workflows = Array.isArray(targetVal.workflows) ? targetVal.workflows : [];
  if (workflows.length <= 1) return;

  // If x-recipe is at document root, all workflows share the recipe category
  if (targetVal["x-recipe"]) return;

  // Check per-workflow x-recipe
  const recipeWorkflows = [];
  const scenarioWorkflows = [];

  workflows.forEach((wf, idx) => {
    const name = (wf && wf.workflowId) || "workflows[" + idx + "]";
    if (wf && wf["x-recipe"]) {
      recipeWorkflows.push(name);
    } else {
      scenarioWorkflows.push(name);
    }
  });

  if (recipeWorkflows.length > 0 && scenarioWorkflows.length > 0) {
    return [{
      message: "All workflows in a file must be the same category. Found " + recipeWorkflows.length + " recipe(s) [" + recipeWorkflows.join(", ") + "] and " + scenarioWorkflows.length + " scenario(s) [" + scenarioWorkflows.join(", ") + "]. Split into separate files.",
      path: ["workflows"],
    }];
  }
};
