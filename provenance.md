# Provenance — reference generator PRs and bug history

This file tracks the originating bug reports and shipped PRs in the **reference
generator implementation** for each vendor extension and behavioral rule
introduced by this kit.

The reference generator is a private implementation maintained by the kit
authors. External consumers of the kit do **not** need access to it — the
handbooks (`handbooks/API_Handbook.md`, `handbooks/Vendor_Extensions.md`)
contain the full authoring contract and the bug summaries that motivated each
rule. This file exists for the kit maintainers' own audit trail and for any
future generator implementer who wants to see the original symptom that drove
a design decision.

PR/issue numbers below refer to the reference generator repo and are not
expected to resolve as public links.

## Vendor extensions

| Extension          | Handbook §                  | Symptom that motivated it                                                                                                | Bug | Shipped in |
|--------------------|-----------------------------|--------------------------------------------------------------------------------------------------------------------------|-----|------------|
| `x-test-seed-value`| API §10.5 / VendorExt §7.4  | Happy-path test 404s on non-`*Id` string path params whose backend transforms the value before lookup (hash/slug/normalize). | #395 | #400 |
| `x-membership-gated`| API §10.6 / VendorExt §7.5 | Privileged role passes `[RoleRequired]` but 403s in tests because the seed fixture has no membership row for it.         | #401 | #404 |
| `x-self-scoped`    | API §10.7 / VendorExt §7.6  | Happy-path test 404s on `/me/*` endpoints when the role exercised has no per-principal runtime row in the seed fixture.  | #405 | #406 |
| `x-test-seed`      | API §10.8 / VendorExt §7.7  | Multiple happy-path tests on the same `*Id` path param need mutually-exclusive entity-state preconditions; one shared seed row cannot satisfy all. | #457 | #459 |

## Other generator references

| Topic | Handbook § | PR / Issue |
|-------|------------|------------|
| DTO-local `x-sample` override for enum-sentinel-first traps in request DTOs | API §10.3 | PR #389 |
| C# fake emits a non-existent enum case when `x-sample` literal is misspelled | API §10.3 checklist | Issue #390 |
| Automatic path-based privileged-role strip for `/me/*` endpoints           | API §10.7 (referenced) | #396 |

## How to update

When a new vendor extension or generator-driven authoring rule is introduced:
1. Add a row to the appropriate table above with the symptom summary and PR/issue numbers.
2. In the handbook section that documents the rule, write a one-line symptom summary in prose (no PR numbers) and link to this file.
