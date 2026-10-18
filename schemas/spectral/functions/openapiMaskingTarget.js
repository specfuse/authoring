"use strict";

// specfuse-xprotection-masking-target — `x-protection.masking` fits its target.
//
// Mirrors generator 0.19.0 (FEAT-2026-0227). Every check reads one property
// schema, so the kit can report it at lint time instead of leaving it to
// `validate`. Measured against the jar, one property per case:
//
//   MASKING_REVEAL_SHAPE (ERROR)
//     `reveal` beside `first` / `last`             the two shapes are exclusive
//     `reveal` naming year, month AND day          masks nothing; the shape
//                                                  guard's `maxItems: 2` also
//                                                  rejects it
//   MASKING_NON_STRING (ERROR)
//     `reveal` on anything but `type: string, format: date`
//     `first` / `last` on a non-string, or on a `date` / `date-time` / `time`
//     string — a character window over a date is not a date
//   PROTECTION_HASHED_MASKING_MUTEX (ERROR)
//     any `masking` beside `atRest: hashed`        a digest has nothing to reveal
//
// Clean on the jar, and clean here: `reveal: []`, `reveal: [month, day]` on a
// date, a window on a plain string, and an encrypted date with no `masking`
// (the generator masks it as `reveal: []`).
//
// A property whose `type` cannot be read here (a bare `$ref` to a value
// object, an `allOf`) is skipped: the value-object case is the generator's
// MASKING_NON_STRING, and guessing would flag specs the jar accepts.
//
// Given: $.components.schemas[*].properties[*] with x-protection.masking.

const DATE_FORMATS = new Set(["date", "date-time", "time"]);

function isObj(v) {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

module.exports = function openapiMaskingTarget(prop, _opts, context) {
  if (!isObj(prop) || !isObj(prop["x-protection"])) return;
  const protection = prop["x-protection"];
  const masking = protection.masking;
  if (!isObj(masking)) return;

  const at = (context && Array.isArray(context.path) ? context.path : []).concat([
    "x-protection",
    "masking",
  ]);
  const results = [];
  const hasReveal = Object.prototype.hasOwnProperty.call(masking, "reveal");
  const hasWindow = "first" in masking || "last" in masking;
  const atRest = typeof protection.atRest === "string" ? protection.atRest.toLowerCase() : undefined;

  if (atRest === "hashed") {
    results.push({
      message:
        "x-protection.masking beside atRest: hashed. A digest is never read back, so there is " +
        "nothing to mask (PROTECTION_HASHED_MASKING_MUTEX).",
      path: at,
    });
  }

  if (hasReveal && hasWindow) {
    results.push({
      message:
        "x-protection.masking declares `reveal` together with `first` / `last`. They are two " +
        "shapes: `reveal` for a `format: date`, the window for a plain string (MASKING_REVEAL_SHAPE).",
      path: at,
    });
  }

  if (typeof prop.type !== "string") return results;
  const fmt = typeof prop.format === "string" ? prop.format : undefined;

  if (hasReveal && !(prop.type === "string" && fmt === "date")) {
    results.push({
      message:
        "x-protection.masking.reveal applies only to `type: string, format: date`. " +
        "`date-time` and `time` cannot be masked (MASKING_NON_STRING).",
      path: at.concat(["reveal"]),
    });
  }

  // With `reveal` beside it, the window is already MASKING_REVEAL_SHAPE; the
  // jar does not report it a second time.
  if (hasWindow && !hasReveal && (prop.type !== "string" || DATE_FORMATS.has(fmt))) {
    results.push({
      message:
        "x-protection.masking `first` / `last` applies only to a plain string. A character " +
        "window over a date is not a date — use `reveal` on a `format: date` (MASKING_NON_STRING).",
      path: at,
    });
  }

  return results;
};
