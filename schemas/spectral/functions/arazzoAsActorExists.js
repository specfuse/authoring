"use strict";

// arazzoAsActorExists
//
// Verifies that x-as on a step references an actor key declared in the
// document's x-actors map. The $ prefix is stripped before lookup.
// For example, x-as: $manager resolves to x-actors.manager.
//
// Handbook: Section 5.1
// Given: $.workflows[*].steps[*]

module.exports = function arazzoAsActorExists(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;

  const xAs = targetVal["x-as"];
  if (typeof xAs !== "string") return;

  // Strip $ prefix: "$requester" -> "requester"
  const actorKey = xAs.startsWith("$") ? xAs.substring(1) : xAs;

  // Get x-actors from document root
  const doc = context && context.document ? context.document.data : undefined;
  if (!doc) return;

  const actors = doc["x-actors"];
  if (!actors || typeof actors !== "object") {
    return [{
      message: "Step uses 'x-as: " + xAs + "' but no x-actors map is declared at document root. Add x-actors with a '" + actorKey + "' entry.",
      path: [...context.path, "x-as"],
    }];
  }

  if (!(actorKey in actors)) {
    const available = Object.keys(actors).map(k => "$" + k).join(", ");
    return [{
      message: "Step uses 'x-as: " + xAs + "' but '" + actorKey + "' is not declared in x-actors. Available actors: " + (available || "(none)") + ".",
      path: [...context.path, "x-as"],
    }];
  }
};
