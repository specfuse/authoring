"use strict";

// specfuse-auth-scopes-* — the `x-scopes` grammar and its registry cross-checks.
//
// GRAMMAR
//
//     <domain>[.<Entity>].<operation>
//
//     domain      kebab-case, a member of info.x-domains
//     Entity      PascalCase, a schema carrying x-entity, OPTIONAL
//     operation   read | write | delete | all
//
//     order.read                domain-level
//     order.Order.read          entity-level
//     work-orders.WorkOrder.write
//
// PARSE FROM THE RIGHT, AND COUNT SEGMENTS — DO NOT DISCRIMINATE ON CASE.
//
// The last segment is always the operation, drawn from a closed four-member
// set. Two segments is domain-level; three is entity-level. That resolves the
// two forms without a registry lookup and, more importantly, without depending
// on the casing of the middle segment.
//
// The casing convention is still enforced (a kebab domain and a PascalCase
// entity make a scope self-describing — each segment says which registry it
// came from), but it is a lint rule rather than the parser's discriminator.
// Some identity providers normalise scope case at introspection; where that
// happens `order.Order.read` and `order.order.read` collapse into one string,
// and a parser keyed on case would resolve the collapsed form differently from
// the authored one. Segment counting survives it.
//
// See handbooks/Vendor_Extensions.md §3.2.
//
// Given: $.paths
// `resolved: false` — the entity lookup reads `x-entity.domain` off the
// schema as authored.

const OPERATIONS = ["read", "write", "delete", "all"];
const METHODS = ["get", "put", "post", "delete", "patch", "options", "head", "trace"];

const KEBAB = /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/;
const PASCAL = /^[A-Z][A-Za-z0-9]*$/;

function domainRegistry(doc) {
  const declared = doc && doc.info ? doc.info["x-domains"] : undefined;
  if (Array.isArray(declared)) {
    return new Set(declared.filter((d) => typeof d === "string"));
  }
  if (declared && typeof declared === "object") {
    return new Set(Object.keys(declared));
  }
  return null; // absent registry: membership is unanswerable, not violated
}

// entity name -> declared x-entity.domain (or null when the entity declares none)
function entityDomains(doc) {
  const schemas = (doc && doc.components && doc.components.schemas) || {};
  const out = new Map();
  for (const [name, schema] of Object.entries(schemas)) {
    if (!schema || typeof schema !== "object") continue;
    const entity = schema["x-entity"];
    if (!entity || typeof entity !== "object") continue;
    out.set(name, typeof entity.domain === "string" ? entity.domain : null);
  }
  return out;
}

// Every (operation, scope) pair in the document, with the path to the scope.
function* scopeEntries(paths, basePath) {
  if (!paths || typeof paths !== "object") return;
  for (const [route, item] of Object.entries(paths)) {
    if (!item || typeof item !== "object") continue;
    for (const method of METHODS) {
      const op = item[method];
      if (!op || typeof op !== "object") continue;
      const scopes = op["x-scopes"];
      if (!Array.isArray(scopes)) continue;
      // A plain loop, not forEach: `yield` cannot cross an arrow-function
      // boundary.
      for (let index = 0; index < scopes.length; index += 1) {
        const scope = scopes[index];
        if (typeof scope !== "string") continue;
        yield {
          scope,
          route,
          method,
          scopes,
          path: [...basePath, route, method, "x-scopes", index],
        };
      }
    }
  }
}

function parse(scope) {
  const segments = scope.split(".");
  if (segments.length < 2 || segments.length > 3) return null;
  const operation = segments[segments.length - 1];
  if (!OPERATIONS.includes(operation)) return null;
  return {
    domain: segments[0],
    entity: segments.length === 3 ? segments[1] : null,
    operation,
    segments,
  };
}

function checkShape(paths, basePath) {
  const results = [];
  for (const entry of scopeEntries(paths, basePath)) {
    const { scope, path } = entry;
    const segments = scope.split(".");

    if (segments.length < 2 || segments.length > 3) {
      results.push({
        message:
          `Scope '${scope}' has ${segments.length} segment(s). The grammar is ` +
          `'<domain>.<operation>' or '<domain>.<Entity>.<operation>'.`,
        path,
      });
      continue;
    }

    const operation = segments[segments.length - 1];
    if (!OPERATIONS.includes(operation)) {
      results.push({
        message:
          `Scope '${scope}' ends in '${operation}', which is not an operation. ` +
          `The last segment must be one of: ${OPERATIONS.join(", ")}.`,
        path,
      });
      continue;
    }

    const domain = segments[0];
    if (!KEBAB.test(domain)) {
      results.push({
        message:
          `Scope '${scope}' has a domain segment '${domain}' that is not kebab-case. ` +
          `Domains are kebab-case everywhere in Specfuse — this is the same value as ` +
          `x-entity.domain and a key of info.x-domains.`,
        path,
      });
      continue;
    }
    // A domain named for an operation makes the segment count the only thing
    // separating `read.write` from a two-segment scope on a domain called
    // 'read'. Cheap to forbid, and no project loses anything by it.
    if (OPERATIONS.includes(domain)) {
      results.push({
        message:
          `Scope '${scope}' uses '${domain}' as its domain, which is an operation keyword. ` +
          `Rename the domain — a domain named for an operation makes the scope ambiguous to read.`,
        path,
      });
      continue;
    }

    if (segments.length === 3 && !PASCAL.test(segments[1])) {
      results.push({
        message:
          `Scope '${scope}' has an entity segment '${segments[1]}' that is not PascalCase. ` +
          `The entity segment is a schema name and must match it exactly.`,
        path,
      });
    }
  }
  return results;
}

function checkRegistry(paths, doc, basePath) {
  const domains = domainRegistry(doc);
  const entities = entityDomains(doc);
  const results = [];

  for (const entry of scopeEntries(paths, basePath)) {
    const parsed = parse(entry.scope);
    // Malformed scopes are `specfuse-auth-scopes-shape`'s to report; reporting
    // them a second time here says nothing new. That extends to the casing
    // rules: a domain that is not kebab-case is never going to be a registry
    // member, and saying so is a second finding on one mistake — the author
    // fixes the casing and the "unregistered" line disappears with it.
    if (!parsed) continue;
    if (!KEBAB.test(parsed.domain) || OPERATIONS.includes(parsed.domain)) continue;

    // An absent or empty x-domains is a different (already reported) gap.
    // Flagging every scope as unregistered would bury it.
    if (domains && domains.size > 0 && !domains.has(parsed.domain)) {
      results.push({
        message:
          `Scope '${entry.scope}' names domain '${parsed.domain}', which is not a member of ` +
          `info.x-domains. A scope cannot grant access to a domain the project has not declared.`,
        path: entry.path,
      });
      continue;
    }

    // Same rule for the entity segment: shape owns the casing finding.
    if (!parsed.entity || !PASCAL.test(parsed.entity)) continue;

    if (!entities.has(parsed.entity)) {
      results.push({
        message:
          `Scope '${entry.scope}' names entity '${parsed.entity}', which is not an x-entity ` +
          `schema in this spec.`,
        path: entry.path,
      });
      continue;
    }

    const owner = entities.get(parsed.entity);
    if (owner && owner !== parsed.domain) {
      results.push({
        message:
          `Scope '${entry.scope}' places '${parsed.entity}' in domain '${parsed.domain}', but ` +
          `'${parsed.entity}' declares x-entity.domain '${owner}'. This is the drift that turns ` +
          `a scope list into decoration — the entity moved and the scope did not.`,
        path: entry.path,
      });
    }
  }
  return results;
}

function checkAllUsage(paths, basePath) {
  const results = [];
  const seen = new Set(); // one finding per operation, not per scope

  for (const entry of scopeEntries(paths, basePath)) {
    const parsed = parse(entry.scope);
    if (!parsed || parsed.operation !== "all") continue;

    const key = `${entry.method} ${entry.route}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const prefix = parsed.entity
      ? `${parsed.domain}.${parsed.entity}`
      : parsed.domain;

    // Redundancy first — it is the sharper finding of the two.
    const redundant = entry.scopes.filter(
      (s) =>
        typeof s === "string" &&
        s !== entry.scope &&
        OPERATIONS.some((op) => op !== "all" && s === `${prefix}.${op}`),
    );

    if (redundant.length > 0) {
      results.push({
        message:
          `Operation declares '${entry.scope}' alongside ${redundant
            .map((s) => `'${s}'`)
            .join(", ")}. '${prefix}.all' already covers read, write and delete — the narrower ` +
          `entries grant nothing extra, and a later attempt to narrow this operation will ` +
          `silently fail to narrow it.`,
        path: entry.path,
      });
      continue;
    }

    results.push({
      message:
        `Operation requires '${entry.scope}'. An operation performs one action, so requiring ` +
        `'all' demands delete rights to read — declare the operation's actual action ` +
        `('${prefix}.read', '${prefix}.write' or '${prefix}.delete'). 'all' is a scope worth ` +
        `granting a client, not one worth requiring at an endpoint.`,
      path: entry.path,
    });
  }
  return results;
}

module.exports = function openapiScopeGrammar(targetVal, opts, context) {
  if (!targetVal || typeof targetVal !== "object") return;

  const check = opts && opts.check;
  const doc = context && context.document ? context.document.data : undefined;
  const basePath = context && Array.isArray(context.path) ? context.path : ["paths"];

  switch (check) {
    case "shape":
      return checkShape(targetVal, basePath);
    case "registry":
      return checkRegistry(targetVal, doc, basePath);
    case "allUsage":
      return checkAllUsage(targetVal, basePath);
    default:
      return;
  }
};

module.exports.OPERATIONS = OPERATIONS;
