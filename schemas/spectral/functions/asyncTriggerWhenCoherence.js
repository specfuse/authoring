"use strict";

// specfuse-async-trigger-when-coherence
//
// Validates the joint contract for x-trigger-when across all event messages:
//
//   1. State-transition events (action verb is anything other than
//      *Created/*Updated/*Deleted) MUST declare x-trigger-when.
//   2. *Created / *Updated / *Deleted events MUST NOT declare x-trigger-when.
//   3. When x-trigger-when is present, its value must be a non-empty string and
//      pass a syntactic check (only allowed tokens; balanced parens). Full
//      semantic checks (unknown fields, type errors, invalid enum literals)
//      are generator-side.
//
// Given: $.channels[*].messages[*]

const ALLOWED_TOKEN_PATTERN =
  // Tokens permitted in a predicate, in order: Before/After dotted path,
  // operators, boolean composers, parens, primitive/enum literals, null,
  // numeric literal, string literal in single quotes, or whitespace.
  /^(\s+|Before(?:\.[A-Za-z][A-Za-z0-9]*)+|After(?:\.[A-Za-z][A-Za-z0-9]*)+|==|!=|<=|>=|<|>|&&|\|\||\(|\)|null|true|false|-?\d+(?:\.\d+)?|'[^']*')+$/;

function isCudSuffix(action) {
  return action.endsWith("Created") || action.endsWith("Updated") || action.endsWith("Deleted");
}

function balancedParens(s) {
  let depth = 0;
  for (const ch of s) {
    if (ch === "(") depth++;
    else if (ch === ")") depth--;
    if (depth < 0) return false;
  }
  return depth === 0;
}

function syntacticIssues(predicate, messageName) {
  if (typeof predicate !== "string" || predicate.trim() === "") {
    return [`x-trigger-when on ${messageName} must be a non-empty string predicate.`];
  }
  if (!balancedParens(predicate)) {
    return [`x-trigger-when on ${messageName} has unbalanced parentheses.`];
  }
  if (!ALLOWED_TOKEN_PATTERN.test(predicate)) {
    return [
      `x-trigger-when on ${messageName} contains tokens outside the allowed grammar (Before/After paths, comparison operators, &&, ||, parens, null, primitive literals, single-quoted strings). Function calls, time arithmetic, and repository lookups are forbidden — see AsyncAPI Handbook §2.5.1.`,
    ];
  }
  return [];
}

module.exports = function asyncTriggerWhenCoherence(targetVal, _opts, _context) {
  if (!targetVal || typeof targetVal !== "object") return;
  if (targetVal["x-message-category"] !== "event") return;

  const xLabel = targetVal["x-label"];
  const action = xLabel && typeof xLabel.action === "string" ? xLabel.action : null;
  if (!action) return;

  const messageName = targetVal.name || "<unnamed>";
  const triggerWhen = targetVal["x-trigger-when"];
  const hasTrigger = triggerWhen !== undefined && triggerWhen !== null;
  const isCud = isCudSuffix(action);

  const results = [];

  if (isCud && hasTrigger) {
    results.push({
      message: `Message ${messageName} has a *${action.match(/(Created|Updated|Deleted)$/)[1]} suffix — x-trigger-when is forbidden on *Created/*Updated/*Deleted events. Remove it; auto-emission for these action classes is unconditional.`,
    });
  }
  if (!isCud && !hasTrigger) {
    results.push({
      message: `Message ${messageName} is a state-transition event (action '${action}' is not *Created/*Updated/*Deleted) and is missing required x-trigger-when. Declare a boolean predicate over (Before, After) — see AsyncAPI Handbook §2.5.`,
    });
  }
  if (hasTrigger) {
    syntacticIssues(triggerWhen, messageName).forEach((message) => {
      results.push({ message });
    });
  }

  return results.length ? results : undefined;
};
