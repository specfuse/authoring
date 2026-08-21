"use strict";

// specfuse-classification-* — the `x-classification` checks that need to see the
// property's siblings (its `description`, its other classification members) or
// the property's name, neither of which a plain schema rule can reach.
//
// `x-classification` marks an entity property's sensitivity class and drives
// encryption at rest, snapshot PII acknowledgement, audit logging and AI read
// shaping. See handbooks/Vendor_Extensions.md §1.5.
//
// WHY THESE LIVE IN THE KIT RATHER THAN THE GENERATOR
//
// The generator's own PiiClassificationValidationRule says it outright: "The
// classification value itself isn't validated here — that's a structural
// concern handled by Spectral. We only enforce presence." That delegation has
// been in the jar since #516 and the kit had never picked it up, so the closed
// value set, the `exposed` contradiction and the `exposed` justification were
// documented as rules and enforced by nothing.
//
// Checks (selected by functionOptions.check, one rule id each):
//
//   exposedContradiction  `exposed` alongside `sensitive` or `encrypted`.
//                         `exposed` asserts safe-to-return; the other two
//                         demand masking or ciphertext. A property claiming
//                         both has no readable meaning, and the reading a
//                         consumer picks decides whether a secret is served.
//   exposedDescription    `exposed` with no `description`. The value is a
//                         reviewed override of SENSITIVE_FIELD_IN_RESPONSE, and
//                         a review with no recorded reasoning is not reviewable
//                         by the next person.
//   piiRequired           a property strongly indicative of PII carrying no
//                         `x-classification` at all. MIRRORS THE JAR EXACTLY —
//                         see the note on PII_NAMES below.
//
// Given: $.components.schemas[?(@ && @["x-entity"])]
// Entity schemas only, matching the generator: `New*` / `Update*` / `Basic*`
// project the same fields and would double-flag every PII property.

// The nine-value set. Widened from four in authoring #76 — see the note on
// specfuse-classification-values for why this is safe against the pinned jar
// (0.5.8 has no opinion on any of these tokens; it does not reject them).
const CLASSES = [
  "pii",
  "sensitive",
  "confidential",
  "exposed",
  "financial",
  "credential",
  "cardholder",
  "sad",
  "encrypted",
];

// The classes that CONTRADICT `exposed`. Not simply "everything sensitive":
// `pii` is deliberately absent, because a person's own email returned to that
// person is both PII and legitimately exposed, and the rule has always allowed
// it. `confidential` and `financial` follow that precedent — an invoice total
// shown to the customer who owes it is exactly that pairing.
//
// `credential`, `cardholder` and `sad` do not have an owner-visible reading.
// A credential, a PAN or PCI Sensitive Authentication Data marked
// safe-to-return is a defect in every context, and `sad` may not be retained
// after authorisation at all.
//
// Widening the value set without widening this one would have opened a hole
// that did not exist before #76: `[cardholder, exposed]` would lint clean,
// which is precisely the "one consumer masks it, another serves it" ambiguity
// this check exists to catch.
const MASKING_CLASSES = [
  "sensitive",
  "encrypted",
  "credential",
  "cardholder",
  "sad",
];

// OpenAPI string-formats that always denote PII.
const PII_FORMATS = new Set(["email", "tel"]);

// Exact, case-insensitive property names that always denote PII.
//
// THIS LIST IS COPIED FROM THE JAR AND MUST NOT BE "IMPROVED" HERE.
// `PiiClassificationValidationRule.PII_PROPERTY_NAMES` is deliberately narrow —
// a broader heuristic ("anything containing 'email'") flags the `emails` array
// on an Inbox schema. Widening it kit-side would fail lint on specs that
// generate fine, which is the one direction a kit rule must never take
// (compatibility.md §18). Narrowing it silently drops coverage the jar has.
// When the jar's list changes, change this one in the same commit.
const PII_NAMES = new Set([
  "firstname",
  "lastname",
  "fullname",
  "middlename",
  "preferredname",
  "emailprimary",
  "emailsecondary",
  "phoneprimary",
  "phonesecondary",
  "linkedinurl",
  "personalurl",
  "addressline1",
  "addressline2",
  "dateofbirth",
  "birthdate",
  "dob",
  "sin",
  "ssn",
  "ipaddress",
]);

function classesOf(prop) {
  if (!prop || typeof prop !== "object") return null;
  const raw = prop["x-classification"];
  if (raw === undefined || raw === null) return null;
  // The shape itself is `specfuse-classification-values`' to report; here a
  // non-array is simply nothing to reason about.
  if (!Array.isArray(raw)) return [];
  return raw.filter((v) => typeof v === "string").map((v) => v.toLowerCase());
}

function entityProperties(schema) {
  const props = schema && typeof schema === "object" ? schema.properties : null;
  return props && typeof props === "object" ? Object.entries(props) : [];
}

function checkExposedContradiction(schema, basePath) {
  const results = [];
  for (const [name, prop] of entityProperties(schema)) {
    const classes = classesOf(prop);
    if (!classes || !classes.includes("exposed")) continue;

    const conflicting = MASKING_CLASSES.filter((c) => classes.includes(c));
    if (conflicting.length === 0) continue;

    results.push({
      message:
        `'${name}' declares x-classification 'exposed' alongside ` +
        `${conflicting.map((c) => `'${c}'`).join(" and ")}. 'exposed' asserts the value is safe ` +
        `to return as authored; ${conflicting.join("/")} demands masking or ciphertext. Pick the ` +
        `one that is true — if the field really is safe, it is not sensitive.`,
      path: [...basePath, "properties", name, "x-classification"],
    });
  }
  return results;
}

function checkExposedDescription(schema, basePath) {
  const results = [];
  for (const [name, prop] of entityProperties(schema)) {
    const classes = classesOf(prop);
    if (!classes || !classes.includes("exposed")) continue;

    const description = prop.description;
    if (typeof description === "string" && description.trim().length > 0) continue;

    results.push({
      message:
        `'${name}' declares x-classification 'exposed' with no description. 'exposed' is a ` +
        `reviewed override of SENSITIVE_FIELD_IN_RESPONSE on a secret-shaped name — record why ` +
        `returning this value is safe, or the next reader has only the assertion.`,
      path: [...basePath, "properties", name],
    });
  }
  return results;
}

function piiReason(name, prop) {
  if (!prop || typeof prop !== "object") return null;

  // Format triggers apply to strings, matching the jar.
  const isStringish = prop.type === "string" || prop.type === undefined;
  if (isStringish && typeof prop.format === "string" && PII_FORMATS.has(prop.format)) {
    return `format: ${prop.format}`;
  }
  if (PII_NAMES.has(name.toLowerCase())) {
    return `property name '${name}'`;
  }
  return null;
}

function checkPiiRequired(schema, basePath) {
  const results = [];
  for (const [name, prop] of entityProperties(schema)) {
    const reason = piiReason(name, prop);
    if (!reason) continue;

    // Presence only, exactly as the jar checks it: any non-empty
    // classification satisfies this rule. Whether the chosen value is the
    // right one is a different question, and the other rules in this group
    // cover the parts of it that are decidable from the spec.
    const classes = classesOf(prop);
    if (classes && classes.length > 0) continue;

    results.push({
      message:
        `'${name}' is PII (${reason}) but carries no x-classification. The marker is what drives ` +
        `snapshot acknowledgement, audit-log masking and AI read exclusion — without it the ` +
        `property is treated as unclassified everywhere downstream.`,
      path: [...basePath, "properties", name],
    });
  }
  return results;
}

module.exports = function openapiClassification(targetVal, opts, context) {
  if (!targetVal || typeof targetVal !== "object" || Array.isArray(targetVal)) return;

  const check = opts && opts.check;
  const basePath = context && Array.isArray(context.path) ? context.path : [];

  switch (check) {
    case "exposedContradiction":
      return checkExposedContradiction(targetVal, basePath);
    case "exposedDescription":
      return checkExposedDescription(targetVal, basePath);
    case "piiRequired":
      return checkPiiRequired(targetVal, basePath);
    default:
      return;
  }
};

module.exports.CLASSES = CLASSES;
