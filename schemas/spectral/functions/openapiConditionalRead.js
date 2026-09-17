"use strict";

// specfuse-conditional-read — `If-None-Match` + `304 Not Modified` declared as a pair.
//
// Mirrors generator 0.12.0's ConditionalReadDeclarationValidationRule, which
// reports every one of these at ERROR. The kit runs them at `warn`: the jar
// already fails the bundle, so Spectral severity only decides who tells you
// first.
//
//   check: pair    (per operation, GET/HEAD or not)
//     CONDITIONAL_READ_NOT_MODIFIED_ON_UNSAFE_METHOD      304 + If-None-Match on a non-GET/HEAD
//     CONDITIONAL_READ_NOT_MODIFIED_WITHOUT_IF_NONE_MATCH  GET/HEAD declares 304, accepts no If-None-Match
//     CONDITIONAL_READ_IF_NONE_MATCH_WITHOUT_NOT_MODIFIED  GET/HEAD accepts If-None-Match, declares no 304
//
//   check: shape   (only on a conditional read: GET/HEAD + If-None-Match + 304)
//     CONDITIONAL_READ_NOT_MODIFIED_WITH_BODY              the 304 declares content
//     CONDITIONAL_READ_ENTITY_TAG_UNDECLARED               no 2xx response declares an ETag header
//     (kit only) a 412 on a conditional read               a stale If-None-Match is a 200, never a failure
//
// Matching follows the jar, not the obvious reading:
//   * header names compare case-insensitively (`if-none-match` counts);
//   * path-level parameters count as well as operation-level ones;
//   * only the literal response key "304" counts — `3XX` does not;
//   * any 2xx response carrying an `ETag` header satisfies the ETag check.
// A rule that only read operation-level, exactly-cased parameters would flag
// specs the generator accepts, and that is the rule a consumer switches off.
//
// The 412 check has no generator counterpart. It encodes API_Handbook.md's
// "do not" rule: the two preconditions do not mix on one operation.
//
// See handbooks/API_Handbook.md "Conditional GET" and compatibility.md.
//
// Given: $.paths (resolved, so $ref'd parameters and responses are visible).

const METHODS = ["get", "put", "post", "delete", "patch", "options", "head", "trace"];
const SAFE = new Set(["get", "head"]);

function isObj(v) {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

function acceptsIfNoneMatch(pathItem, op) {
  const params = []
    .concat(Array.isArray(pathItem.parameters) ? pathItem.parameters : [])
    .concat(Array.isArray(op.parameters) ? op.parameters : []);
  return params.some(
    (p) =>
      isObj(p) &&
      typeof p.name === "string" &&
      typeof p.in === "string" &&
      p.in.toLowerCase() === "header" &&
      p.name.toLowerCase() === "if-none-match"
  );
}

function declaresEntityTag(responses) {
  return Object.entries(responses).some(
    ([code, resp]) =>
      String(code).startsWith("2") &&
      isObj(resp) &&
      isObj(resp.headers) &&
      Object.keys(resp.headers).some((h) => h.toLowerCase() === "etag")
  );
}

function label(op, method, path) {
  const id = typeof op.operationId === "string" ? `'${op.operationId}' ` : "";
  return `Operation ${id}(${method.toUpperCase()} ${path})`;
}

module.exports = function openapiConditionalRead(targetVal, opts, context) {
  if (!isObj(targetVal)) return;
  const check = opts && opts.check;
  const base = context && Array.isArray(context.path) ? context.path : ["paths"];
  const results = [];

  for (const [path, pathItem] of Object.entries(targetVal)) {
    if (!isObj(pathItem)) continue;
    for (const method of METHODS) {
      const op = pathItem[method];
      if (!isObj(op)) continue;
      const responses = isObj(op.responses) ? op.responses : {};
      const inm = acceptsIfNoneMatch(pathItem, op);
      const notModified = Object.prototype.hasOwnProperty.call(responses, "304");
      const safe = SAFE.has(method);
      const at = base.concat([path, method]);
      const name = label(op, method, path);

      if (check === "pair") {
        if (!safe) {
          if (inm && notModified) {
            results.push({
              message: `${name} declares 304 and accepts If-None-Match, but a 304 can only answer GET or HEAD. A write that wants a precondition wants If-Match and 412.`,
              path: at,
            });
          }
        } else if (notModified && !inm) {
          results.push({
            message: `${name} declares 304 Not Modified but accepts no If-None-Match header. Nothing a client sends can reach the 304.`,
            path: at.concat(["responses", "304"]),
          });
        } else if (inm && !notModified) {
          results.push({
            message: `${name} accepts If-None-Match but declares no 304 Not Modified. The header has nowhere to land.`,
            path: at,
          });
        }
        continue;
      }

      if (check === "shape" && safe && inm && notModified) {
        const nm = responses["304"];
        if (isObj(nm) && isObj(nm.content) && Object.keys(nm.content).length > 0) {
          results.push({
            message: `${name} declares content on its 304. A 304 Not Modified carries no body.`,
            path: at.concat(["responses", "304", "content"]),
          });
        }
        if (!declaresEntityTag(responses)) {
          results.push({
            message: `${name} is a conditional read but no 2xx response declares an ETag header. A client can only send If-None-Match with a tag it was given.`,
            path: at.concat(["responses"]),
          });
        }
        if (Object.prototype.hasOwnProperty.call(responses, "412")) {
          results.push({
            message: `${name} is a conditional read and declares 412. A stale If-None-Match is a 200 with the current representation, never a failure; 412 belongs to If-Match on writes.`,
            path: at.concat(["responses", "412"]),
          });
        }
      }
    }
  }
  return results;
};
