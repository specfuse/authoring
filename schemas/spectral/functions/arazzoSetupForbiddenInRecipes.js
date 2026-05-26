"use strict";

// arazzoSetupForbiddenInRecipes
//
// Scans all expression strings in the document for $setup references when any
// workflow has x-recipe. Recipes must not reference $setup -- they compose via
// extends, and $setup is only valid in scenario workflows.
//
// Skips metadata fields (info, sourceDescriptions, x-doc, description, summary)
// that contain human-readable text, not runtime expressions.
//
// Handbook: Section 7.4, 8.2, 13 Do NOT #8
// Given: $

const SETUP_PATTERN = /\$setup\b/;

function scanForSetup(obj, path, results) {
  if (typeof obj === "string") {
    if (SETUP_PATTERN.test(obj)) {
      results.push({
        message: "Recipe files must not reference '$setup'. Recipes compose via 'extends', not $setup. Found '" + obj + "'.",
        path: path,
      });
    }
    return;
  }
  if (Array.isArray(obj)) {
    for (let i = 0; i < obj.length; i++) {
      scanForSetup(obj[i], [...path, i], results);
    }
    return;
  }
  if (obj && typeof obj === "object") {
    for (const key of Object.keys(obj)) {
      // Skip top-level metadata that cannot contain runtime expressions
      if (path.length === 0 && (key === "arazzo" || key === "info" || key === "sourceDescriptions")) {
        continue;
      }
      // Skip human-readable text fields at any level
      if (key === "x-doc" || key === "description" || key === "summary") {
        continue;
      }
      scanForSetup(obj[key], [...path, key], results);
    }
  }
}

module.exports = function arazzoSetupForbiddenInRecipes(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;

  // Check if this is a recipe file
  const hasRootRecipe = !!targetVal["x-recipe"];
  if (!hasRootRecipe) {
    const workflows = Array.isArray(targetVal.workflows) ? targetVal.workflows : [];
    const hasWorkflowRecipe = workflows.some(wf => wf && wf["x-recipe"]);
    if (!hasWorkflowRecipe) return;
  }

  const results = [];
  scanForSetup(targetVal, [], results);
  return results.length > 0 ? results : undefined;
};
