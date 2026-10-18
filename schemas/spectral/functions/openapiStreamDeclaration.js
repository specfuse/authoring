"use strict";

// specfuse-xstream-declaration — a streamed response is declared the one way
// the generator serves.
//
// Mirrors generator 0.19.0 (FEAT-2026-0228). `x-stream: {}` on a response
// Media Type Object makes `schema` describe ONE item of the stream. Measured
// against the jar, one operation per case:
//
//   STREAM_UNKNOWN_MEDIA_TYPE     media type other than text/event-stream or
//                                 application/jsonl
//   STREAM_UNKNOWN_OPTION         value is not an object, or carries a key
//                                 (`x-stream: true`, `x-stream: { event: … }`)
//   STREAM_NON_SUCCESS_RESPONSE   declared outside 2xx
//   STREAM_MIXED_CONTENT          the response has another media type beside it
//   STREAM_ITEM_NOT_OBJECT        `schema` absent, or typed as something other
//                                 than an object
//   STREAM_ITEM_IS_ENTITY         the item is an `x-entity`
//
// All ERROR on the jar. Not mirrored: STREAM_ITEM_SHARED_WITH_JSON_BODY, which
// needs every request and response body in the document; `validate` reports
// it. A correct declaration draws STREAM_NOT_YET_GENERATED (WARNING) from the
// generator and nothing from this rule.
//
// An item with no readable `type` (an `allOf`) is not reported as non-object;
// the generator resolves it and this rule would only guess.
//
// Given: $.paths (resolved, so a $ref'd item schema's x-entity is visible).

const METHODS = ["get", "put", "post", "delete", "patch", "options", "head", "trace"];
const STREAM_MEDIA = new Set(["text/event-stream", "application/jsonl"]);

function isObj(v) {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

module.exports = function openapiStreamDeclaration(paths, _opts, context) {
  if (!isObj(paths)) return;
  const base = context && Array.isArray(context.path) ? context.path : [];
  const results = [];

  for (const [route, pathItem] of Object.entries(paths)) {
    if (!isObj(pathItem)) continue;
    for (const method of METHODS) {
      const op = pathItem[method];
      if (!isObj(op) || !isObj(op.responses)) continue;
      for (const [code, resp] of Object.entries(op.responses)) {
        if (!isObj(resp) || !isObj(resp.content)) continue;
        const mediaTypes = Object.keys(resp.content);
        for (const mt of mediaTypes) {
          const media = resp.content[mt];
          if (!isObj(media) || !Object.prototype.hasOwnProperty.call(media, "x-stream")) continue;
          const at = base.concat([route, method, "responses", code, "content", mt]);
          const where = `${method.toUpperCase()} ${route} ${code} ${mt}`;
          const marker = media["x-stream"];

          if (!STREAM_MEDIA.has(mt.toLowerCase())) {
            results.push({
              message: `${where}: x-stream is only valid under text/event-stream or application/jsonl (STREAM_UNKNOWN_MEDIA_TYPE).`,
              path: at,
            });
          }
          if (!isObj(marker) || Object.keys(marker).length > 0) {
            results.push({
              message: `${where}: x-stream must be exactly {}. No options exist yet (STREAM_UNKNOWN_OPTION).`,
              path: at.concat(["x-stream"]),
            });
          }
          if (!/^2/.test(String(code))) {
            results.push({
              message: `${where}: x-stream is only valid on a 2xx response (STREAM_NON_SUCCESS_RESPONSE).`,
              path: at,
            });
          }
          if (mediaTypes.length > 1) {
            results.push({
              message: `${where}: a streamed response declares no other media type; found ${mediaTypes
                .filter((m) => m !== mt)
                .join(", ")} (STREAM_MIXED_CONTENT).`,
              path: at,
            });
          }
          const item = media.schema;
          if (!isObj(item) || (typeof item.type === "string" && item.type !== "object")) {
            results.push({
              message: `${where}: x-stream needs a schema that is ONE object item of the stream (STREAM_ITEM_NOT_OBJECT).`,
              path: at,
            });
          } else if (isObj(item["x-entity"])) {
            results.push({
              message: `${where}: a stream item is a read model, never an x-entity. Define a dedicated item schema (STREAM_ITEM_IS_ENTITY).`,
              path: at.concat(["schema"]),
            });
          }
        }
      }
    }
  }
  return results;
};
