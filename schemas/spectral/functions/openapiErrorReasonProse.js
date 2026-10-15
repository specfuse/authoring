"use strict";

// specfuse-error-rule-name-in-code — prose names a rule in `code`, which
// carries the HTTP status.
//
// Since authoring#159 (compatibility.md §54) the kit's `Error` carries the
// HTTP status in an integer `code` and the snake_case rule name in `reason`.
// A description that says `error.code = template_in_use` passes `validate` and
// `generate` and still sends every client that reads it to branch on a field
// that never holds that value. Response examples are covered elsewhere:
// `spectral:oas` example validation rejects a string `code`. Nothing checks prose.
//
// Gate: the rule speaks only when `components.schemas.Error.properties.code`
// is typed `integer`. A project still on the old shape (string `code` = rule
// name) is described correctly by that prose, and flagging it would
// push the migration through a lint warning instead of §54's note.
//
// Targets: every `description` and `summary` string in the document, at any
// depth. Operations, responses, parameters, schemas and `x-*` blocks all carry
// prose a client reads.
//
// Matches (the key may be written `code`, `error.code`, `errors[0].code`,
// quoted or in backticks, so the match starts at `code` itself):
//   code = foo_bar     code == 'foo_bar'     code: foo_bar     "code": "foo_bar"
// The value must contain an underscore. That is what separates a rule name
// (`template_in_use`, `slot_already_booked`) from prose such as `code: integer`
// or `code = status`, and a rule that fires on those is a rule a consumer
// switches off. A single-word rule name is not caught; the trade is deliberate.
// `\b` before `code` keeps `status_code` and `reason_code` out.
//
// Given: $ (resolved, so a multi-file bundle's `Error` and descriptions are
// visible; Spectral maps each finding back to its source file and drops the
// duplicates a shared `$ref` produces).

const RULE_IN_CODE =
  /\bcode[`"']?\s*(?:===?|:|=)\s*[`"']?([a-z][a-z0-9]*_[a-z0-9_]*)\b/g;

function isObj(v) {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

function codeIsInteger(doc) {
  const error =
    isObj(doc.components) && isObj(doc.components.schemas) ? doc.components.schemas.Error : undefined;
  if (!isObj(error) || !isObj(error.properties)) return false;
  const code = error.properties.code;
  if (!isObj(code)) return false;
  const t = code.type;
  return t === "integer" || (Array.isArray(t) && t.includes("integer"));
}

function walk(node, path, out, seen) {
  if (node === null || typeof node !== "object" || seen.has(node)) return;
  seen.add(node);
  const entries = Array.isArray(node) ? node.map((v, i) => [i, v]) : Object.entries(node);
  for (const [key, value] of entries) {
    if ((key === "description" || key === "summary") && typeof value === "string") {
      const names = [];
      for (const m of value.matchAll(RULE_IN_CODE)) names.push(m[1]);
      if (names.length > 0) out.push({ path: path.concat([key]), names });
    } else {
      walk(value, path.concat([key]), out, seen);
    }
  }
  seen.delete(node);
}

module.exports = function openapiErrorReasonProse(targetVal) {
  if (!isObj(targetVal) || !codeIsInteger(targetVal)) return;
  const found = [];
  walk(targetVal, [], found, new Set());
  return found.map(({ path, names }) => {
    const first = names[0];
    return {
      message:
        `Prose names the rule ${names.map((n) => `'${n}'`).join(", ")} in \`code\`, but Error.code is the HTTP status. ` +
        `Name the rule in \`reason\` (error.reason = ${first}). API Handbook §11.`,
      path,
    };
  });
};
