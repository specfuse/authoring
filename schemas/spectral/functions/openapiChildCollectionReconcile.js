"use strict";

// specfuse-child-collection-reconcile-id
//
// A child collection inside a PATCH body is reconciled by identity: an element
// carrying a known `id` updates that child in place, an element with no `id` is
// a create, and a tracked child absent from the array is deleted. That contract
// is unimplementable if the element DTO has no identity property — and the only
// available fallback, delete-every-child-then-re-add, recreates rows with new
// PKs on every PATCH, breaking `x-references` FKs from other aggregates, audit
// trails, and concurrency tokens.
//
// So: an `Update*` DTO used as an ARRAY ELEMENT inside another `Update*` DTO
// must expose an optional `id`.
//
// Scope is deliberately narrow. Most `Update*` DTOs are the body of a PATCH
// addressed by URL, where identity lives in the path — requiring `id` on all of
// them would be a false-positive storm. Only the array-element-inside-Update
// shape is flagged.
//
// Two failure modes are reported:
//   - the element DTO has no `id` property at all
//   - it has one, but lists it in `required` (which forbids the create leg,
//     since an element with no `id` is how a create is expressed)
//
// Runs unresolved: the rule keys off `items.$ref` naming an `Update*` schema,
// and resolution would inline the target and erase the name.
//
// See handbooks/API_Handbook.md §1.5.1.
//
// Given: $.components.schemas

const UPDATE_DTO = /^Update[A-Z]/;
const REF_TO_SCHEMA = /^#\/components\/schemas\/([A-Za-z0-9_.-]+)$/;

module.exports = function openapiChildCollectionReconcile(targetVal, _opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;

  const basePath = context && Array.isArray(context.path) ? context.path : [];
  const results = [];

  for (const [parentName, parentSchema] of Object.entries(targetVal)) {
    if (!UPDATE_DTO.test(parentName)) continue;
    if (!parentSchema || typeof parentSchema !== "object") continue;

    const properties = parentSchema.properties;
    if (!properties || typeof properties !== "object") continue;

    for (const [propName, prop] of Object.entries(properties)) {
      if (!prop || typeof prop !== "object") continue;
      if (prop.type !== "array") continue;

      const items = prop.items;
      if (!items || typeof items !== "object" || typeof items.$ref !== "string") continue;

      const match = REF_TO_SCHEMA.exec(items.$ref);
      if (!match) continue;

      const childName = match[1];
      if (!UPDATE_DTO.test(childName)) continue;

      const childSchema = targetVal[childName];
      if (!childSchema || typeof childSchema !== "object") continue;

      const childProps =
        childSchema.properties && typeof childSchema.properties === "object"
          ? childSchema.properties
          : {};
      const childRequired = Array.isArray(childSchema.required) ? childSchema.required : [];
      const path = [...basePath, parentName, "properties", propName];

      if (!Object.prototype.hasOwnProperty.call(childProps, "id")) {
        results.push({
          message:
            `Child collection reconcile requires an optional 'id' on ${childName} — add it. ` +
            `'${parentName}.${propName}' is reconciled by identity, and without 'id' the server cannot ` +
            `tell an update from a create. Delete-then-add is not an acceptable fallback: it recreates ` +
            `rows with new primary keys on every PATCH, breaking x-references FKs, audit trails, and ` +
            `concurrency tokens. See API_Handbook.md §1.5.1.`,
          path,
        });
        continue;
      }

      if (childRequired.includes("id")) {
        results.push({
          message:
            `'id' on ${childName} must be optional, not required. An element with no 'id' is how a ` +
            `create is expressed inside '${parentName}.${propName}'; requiring it forbids the create leg ` +
            `of the reconcile. See API_Handbook.md §1.5.1.`,
          path: [...basePath, childName, "required"],
        });
      }
    }
  }

  return results;
};
