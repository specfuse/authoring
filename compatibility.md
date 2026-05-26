# Kit ↔ Generator Compatibility

This file tracks which Specfuse generator commits are known compatible with each kit version. Breaking changes to vendor extensions require coordinated releases on both sides — the generator implements the contract that the kit defines.

## Current

| Kit version | Generator commit | Notes |
|---|---|---|
| `v0.1` (incubating) | `0a812e46` (`Bug #457: Add x-test-seed operation extension`) | Initial bootstrap. Kit content not yet populated; pin reflects the generator state at the moment of kit creation. |
| `v0.2` (incubating, current) | *pending generator alignment — see follow-ups below* | Phases 1–6 of the kit-extraction effort: handbooks, samples, claude-assets, project-init template, and bundled `examples/hello-orders/` lifted and generalized from RestoManager. No generator-contract grammar changed; outstanding items are naming/style alignments that the generator will adopt incrementally. |

## How to update this matrix

Bump the kit version on every change to:
- Handbook content that changes a generator-contract rule (new `x-*` extension, naming convention change, validation rule)
- Sample YAML structure (templates the generator consumes)
- Spectral schemas in `schemas/`

Pair the kit bump with the generator commit that implements the corresponding parser/validator change, and add a row above.

Workflow assets (`claude-assets/`, `templates/project-init/init.sh`) do not require generator-side coordination and do not need a matrix bump.

---

## Outstanding generator-side follow-ups

These are alignment items the kit declared canonical during Phases 2–6 but that the generator has not yet picked up. None block kit usage today (the kit is internally consistent), but each one should land on the generator to remove drift between the two sides.

The kit accepts both forms in its prose (notes the alias where one exists), so the generator can adopt these incrementally without breaking any existing project. Mark each item done by linking the generator commit that implements it.

### 1. Spectral rule prefix `rm-*` → `specfuse-*`

**Status:** kit canonical (Phase 2, 4 commits)

The kit renamed all Spectral rule identifiers from the legacy `rm-*` prefix (inherited from RestoManager) to `specfuse-*` to match the kit's neutral identity. Rules touched:

| Legacy name | Kit canonical name |
|---|---|
| `rm-validate-only-on-writes` | `specfuse-validate-only-on-writes` |
| `rm-change-description-headers` | `specfuse-change-description-headers` |
| `rm-batch-operation-structure` | `specfuse-batch-operation-structure` |
| `rm-conflict-response-details` | `specfuse-conflict-response-details` |
| `rm-idempotency-key-support` | `specfuse-idempotency-key-support` |
| `rm-async-snapshot-version-coexistence` | `specfuse-async-snapshot-version-coexistence` |
| `rm-async-trigger-when-coherence` | `specfuse-async-trigger-when-coherence` |
| `rm-async-worker-inbox-dedup-coherence` | `specfuse-async-worker-inbox-dedup-coherence` |
| `rm-async-subscription-name-mismatch` | `specfuse-async-subscription-name-mismatch` |
| `rm-async-event-name-action-class` | `specfuse-async-event-name-action-class` |
| `rm-async-first-appearance-uses-created` | `specfuse-async-first-appearance-uses-created` |
| `rm-arazzo-*` (all Arazzo Spectral rules) | `specfuse-arazzo-*` |

**Generator action:** rename the rule identifiers in the generator's bundled Spectral ruleset. The rule logic is unchanged; only the identifier strings differ. Suggest accepting both forms for one transitional release, then deprecating `rm-*`.

**Severity:** additive — non-breaking if both forms are accepted during transition. Breaking if only the new form is accepted.

### 2. Vendor extension naming canonicalization

**Status:** kit canonical (Phase 2, commits `c59a3d5` and `337b164`)

Two extensions exist in the generator under both kebab-case and camelCase names. The kit standardizes on kebab-case:

| Generator alias (legacy) | Kit canonical |
|---|---|
| `x-valueObject` | `x-value-object` |
| `x-enumCase` | `x-enum-case` |

The kit's handbook (`handbooks/Vendor_Extensions.md` §1.2 and §1.4) documents both forms with inline naming notes, declaring the kebab-case form as canonical going forward.

**Generator action:** continue accepting both forms; document the kebab-case form as the preferred spelling in `ExtensionConstants.java`. New extensions added after this point should use kebab-case only.

**Severity:** additive — both forms work today.

### 3. Vendor extensions documentation source-of-truth

**Status:** kit canonical (Phase 2, commit `c59a3d5`)

The generator currently ships `docs/VENDOR-EXTENSIONS.md` as a 45-line summary. The kit's `handbooks/Vendor_Extensions.md` is the full, authoritative reference and explicitly designates itself as canonical (top-of-file banner).

**Generator action:** replace `generator/docs/VENDOR-EXTENSIONS.md` with a pointer to the kit's `handbooks/Vendor_Extensions.md`. Keep a short stub that lists the extensions the generator currently parses, with a link to the kit handbook for full semantics.

**Severity:** documentation-only — non-breaking.

### 4. Authorization extension names `x-required-roles` / `x-required-scopes`

**Status:** kit canonical (Phase 2 and Phase 3, commit `d813853`)

The kit's samples and handbooks consistently use `x-roles` and `x-scopes` (the shorter form, matching the generator's `ExtensionConstants` documentation). The RM endpoint-samples used the longer `x-required-roles` / `x-required-scopes` form. The kit aligned on the short form during the endpoint-samples generalization (documented in the commit message).

**Generator action:** confirm `ExtensionConstants` accepts `x-roles` / `x-scopes` as canonical. If the longer alias is also accepted, document the canonical short form and mark the longer one as legacy.

**Severity:** additive — short form is already canonical; this is a documentation/alias cleanup.

### 5. OpenTelemetry attribute prefix

**Status:** kit canonical (Phase 2, commit `569a89b`)

The kit's AsyncAPI handbook §4.5.8 (telemetry dimension tagging) declares the unprefixed `event.entity` / `event.action` attributes as canonical, with a note that projects may apply a project-specific prefix (e.g., `{project}.event.entity`) via generator configuration. The legacy `resto.event.*` prefix is removed.

**Generator action:** emit telemetry attributes as `event.entity` / `event.action` by default. Read a `telemetryAttributePrefix` field from the project config (or environment) to apply a per-project prefix when set.

**Severity:** breaking for any observability dashboards that filtered on `resto.event.*`. Coordinated with telemetry consumers before flip.

### 6. Spec path versioning baseline

**Status:** kit canonical (commit `7cea428`)

Projects bootstrapped from `templates/project-init/` start at `api/specs/v1/`. The RM project used `api/specs/v3/` for legacy reasons (it had migrated through v1 and v2 internally). Fresh projects from the kit do not inherit that history.

**Generator action:** ensure the generator's spec-discovery logic does not assume any specific major version. The project's generator config (`{project}-project.json`) declares the spec paths explicitly; the generator should read them rather than glob for a hardcoded directory name.

**Severity:** additive — the generator already reads paths from the project config; this entry just notes the kit's chosen baseline.

### 7. Single-shared-topic alignment in event channel samples

**Status:** kit canonical (Phase 3, commit `6d1a7c9`)

The kit's AsyncAPI handbook §1.5 and §3.2 declare a single shared event topic (`{project}.events`) as the v2.1 architectural baseline, with a documented sharding escape hatch (handbook §3.2). The RM `message-samples.yaml` showed a per-aggregate event-topic address (`restomanager.scheduling.staffing-plan.events`) that predated this decision. The kit's `samples/message-samples.yaml` aligns with the handbook (`{project}.events` as the canonical channel address).

**Generator action:** verify that the generator's channel-derivation logic supports both the single-shared-topic case (default) and the sharded case (escape hatch). The `messages:` map completeness invariant on the shared channel must be enforced by the bundled Spectral rule `asyncapi-channel-message-completeness`.

**Severity:** additive — the single-topic case is a simplification of the channel topology, not a breaking change to the message contract.

### 8. Project file format and location

**Status:** kit canonical (Phases 2 and 5, commits `0fa6742` and `910521e`)

The kit clarified the project file convention during Phase 2 review:

- The **generator project file** is **JSON-only**, lives at the project root, and is named `{project-name}-project.json`. This file declares spec paths, generator output language/directory per code-group (Workers / Backend / Frontend), and any other generator-driven configuration.
- The kit explicitly does **not** require a `.specfuse/project.yaml` overlay — that was a phantom convention introduced during early kit drafting and was removed across all 10 handbook references in commit `0fa6742`. Projects that want a separate authoring-side overlay (e.g., a domain-list file consumed only by Spectral and Claude agents) may add one in any format the project chooses; the kit does not prescribe it.

**Generator action:** confirm that the generator reads project configuration only from the `{project-name}-project.json` file at the project root. Do not look for `.specfuse/project.yaml` or any other path.

**Severity:** no change required if the generator already follows this; documentation alignment otherwise.

### 9. `Authenticated` role as recommended convention

**Status:** kit canonical (Phase 2, multiple commits)

The kit handbooks document `Authenticated` as a **recommended convention** for pre-business-role flows (signup, invitation acceptance, magic-link redemption) where the caller has a valid auth token but no business role yet. It is not a kit-required value — every project defines its own closed role enum in `common/enums.yaml`, and `Authenticated` is one suggested entry.

**Generator action:** do not hardcode `Authenticated` in any generator validation or template logic. The role enum is project-defined; the generator reads it from `common/enums.yaml#/Role` (or wherever the project declares it).

**Severity:** additive — clarifies an existing pattern.

### 10. Tenant routing field name

**Status:** kit canonical (Phases 2–3, throughout)

The kit collapsed the RM-specific two-level tenant model (`companyId` + `restaurantId`) into a single `tenantId` envelope ApplicationProperty for routing. Projects with a multi-level tenancy hierarchy define their own scoping fields in addition to `tenantId` — but `tenantId` is the canonical top-level tenant scope across handbooks and samples.

**Generator action:** confirm that the envelope/header-stamping logic reads `tenantId` from the snapshot or operation parameters and stamps it as an ApplicationProperty. Project-specific narrower scopes (e.g., `customerId`, `siteId`) are stamped through `x-envelope-promote` declarations on snapshot fields, not through hardcoded generator logic.

**Severity:** non-breaking for projects that already use `tenantId`; coordination required for projects that need to migrate from a different field name.

---

## Surfaced bugs (kit-side, fixed during Phase 6 verification)

| Bug | Fixed in | Description |
|---|---|---|
| `openapi.yaml.template` YAML syntax error | commit `690db55` | Line 50 had `PreconditionRequiredError:{ $ref:` with no whitespace before `{`. YAML inline-flow requires a space after `:`. Would have produced an unparseable `openapi.yaml` in every project bootstrapped from the template. Caught by the Phase 6 agent while concretizing the template into `examples/hello-orders/`. |
| `openapi.yaml.template` missing path-param refs | commit `690db55` | The template defined `tenantId`/`customerId` in `common/parameters/path.yaml.template` but did not reference them from `components.parameters` in the OpenAPI root. Added refs so bootstrapped projects see the pattern. |

These are kit-internal fixes and do not require generator coordination.

---

## Outstanding kit-side work

These are gaps in the kit itself, separate from the generator-side follow-ups above. Each represents an enforcement promise the handbooks make that has no implementation today.

### Three handbook-referenced Spectral rules with no implementation

Surfaced during the schemas import (commits `78abc31`..`b146efa`) when verifying that every rule name mentioned in the handbooks resolves to a real Spectral rule in `schemas/spectral/`. The source RestoManager Spectral ruleset never implemented these three — the handbooks reference them as if they exist, but the enforcement code was aspirational.

| Rule ID | Referenced in | What it should enforce |
|---|---|---|
| `specfuse-async-snapshot-version-coexistence` | `handbooks/Vendor_Extensions.md §12.2`, `handbooks/AsyncAPI_Handbook.md §2.3` | Deprecated event messages with a `replacedBy` pointing at a different version must `$ref` a versioned snapshot file (`*V{N}.yaml`); orphan versioned snapshot files with no deprecated referrer must be removed. |
| `specfuse-async-subscription-name-mismatch` | `handbooks/Vendor_Extensions.md §12.3`, `handbooks/AsyncAPI_Handbook.md §4.3` | `x-subscription.name` must equal the operation file stem (e.g., file `on-order-submitted.yaml` → name `on-order-submitted`). Free-form kebab-case naming is no longer permitted. |
| `specfuse-batch-operation-structure` | `handbooks/API_Handbook.md §16` (AI Integration Spectral rules) | Validates batch operation schemas (the `/{resources}:batch` POST pattern with `operations[]` array containing `oneOf` create/update/delete shapes). |

**Action:** author the three rules as new entries in `schemas/spectral/specfuse-{openapi,asyncapi}.yaml`. Two are AsyncAPI rules (snapshot-version-coexistence, subscription-name-mismatch); one is an OpenAPI rule (batch-operation-structure). Each will likely need a custom function under `schemas/spectral/functions/` since the logic involves cross-file resolution (snapshot $refs) or file-name vs declared-name comparison (operation file stem).

**Severity:** the handbooks make these promises today; until the rules ship, the promises are unenforced. New projects bootstrapped from the kit can violate these contracts and not know it. Worth landing before Phase 7 (smoke test of an imminent second project).

### `x-action-class` and `x-trigger-mode` non-introduction

The handbooks document `x-action-class` and `x-trigger-mode` as "not introduced" extensions whose semantics are inferred from message-name suffix (`*Created`/`*Updated`/`*Deleted`/state-transition) and payload `context` field presence respectively. The kit does not currently enforce that these extensions are NOT used — a project author could declare `x-action-class: stateTransition` on a message and the kit's rules would silently allow it.

**Action:** add a single rule (`specfuse-async-non-introduced-extensions-forbidden`) that flags any use of `x-action-class`, `x-trigger-mode`, `x-pii`, `x-sensitive`, `x-deprecated`, `x-tags`, or `x-category` as a hard error pointing at the handbook section that explains why the extension isn't introduced. Pure structural check — no custom function needed.

**Severity:** low — the kit's authoring path (Claude Code agents from `/design-*` commands) doesn't generate these extensions, so the gap is theoretical for kit-conformant projects. Adding the rule closes the gap for projects that author by hand.
