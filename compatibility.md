# Kit ↔ Generator Compatibility

This file tracks which Specfuse generator commits are known compatible with each kit version. Breaking changes to vendor extensions require coordinated releases on both sides — the generator implements the contract that the kit defines.

## Current

| Kit version | Generator commit | Notes |
|---|---|---|
| `v0.1` (incubating) | `0a812e46` (`Bug #457: Add x-test-seed operation extension`) | Initial bootstrap. Kit content not yet populated; pin reflects the generator state at the moment of kit creation. |
| `v0.2` (incubating) | *pending generator alignment — see follow-ups below* | Phases 1–6 of the kit-extraction effort: handbooks, samples, claude-assets, project-init template, and bundled `examples/hello-orders/` lifted and generalized from the source project. No generator-contract grammar changed; outstanding items are naming/style alignments that the generator will adopt incrementally. |
| `v0.3` (incubating) | generator rules `#617`/`#622`/`#623` (trigger-mode/method-name), `#520`/`#523` (aiAccess Tier 0) | Open-source packaging (`specfuse-authoring` PyPi CLI, Apache-2.0) + handbook alignment to latest source contract: (1) `x-trigger-mode` flipped from forbidden/inferred to **required `explicit`** on context-bearing transitions, plus new `x-method-name` (Vendor §12.2, AsyncAPI Do-NOT #18) — enforcement already present in kit Spectral (`specfuse-async-context-coherence`, `specfuse-async-subscription-trigger-mode-values`); `x-method-name` is generator-enforced (`MISSING_METHOD_NAME`). (2) `aiAccess` now **required on every `x-entity`**; empty `operations: []` + `reason` is the canonical Tier 0 form; absence is validator WARN `ENTITY_AIACCESS_MISSING` (Vendor §1.1.1, API entity-metadata). |
| `v0.3.1` (incubating) | generator **`0.1.0`** — `Specfuse/generator-dist` release `v0.1.0`, asset `specfuse-generator-0.1.0.jar`, sha256 `35dad9af…59838` | First real generator pin. `generator.lock` now points at a published, checksum-verified jar (was `PENDING`); `specfuse authoring generate` resolves, verifies, and runs it. No contract grammar change from v0.3 — packaging/pin only. |
| `v0.3.4` (incubating) | generator **`0.2.0`** — `Specfuse/generator-dist` release `v0.2.0`, asset `specfuse-generator-0.2.0.jar`, sha256 `09d2697b…a89e24f` | Re-pin to generator 0.2.0. No contract grammar change from v0.3 — the generator bump carries Dart `Update*`-DTO fixes only (#696: hand-rolled `fromJson` coerces `double` via `num`, and the test-support builder seeds `double` defaults as double literals so `Function.apply` no longer throws `int is not a subtype of double`). Pin/packaging only. |
| `v0.4.0` (incubating) | generator **`0.4.0`** — `Specfuse/generator-dist` release `v0.4.0`, asset `specfuse-generator-0.4.0.jar`, sha256 `6c9c38e5…248a9b` | **Breaking contract change** (generator FEAT-2026-0053); kit bumped to `0.4.0` to match. Supersedes the never-published `0.3.5` re-pin. `x-entity.domain` becomes a **required** sub-field of every `x-entity`, validated fail-closed against `info.x-domains` (`ENTITY_DOMAIN_REQUIRED`, `ENTITY_DOMAIN_UNREGISTERED` — both ERROR); this makes the kit's already-documented domain-registry contract (`Vendor_Extensions.md §1.1`, `API_Handbook.md §0.1`) actually enforced. Adds a per-group `domains: {include\|exclude}` artifact-group filter (project.json), and source-tree drift-policing rules on `validate-source`: `ENTITY_DOMAIN_FOLDER_MISMATCH` (ERROR), `DOMAIN_FOLDER_UNREGISTERED` (ERROR), `MESSAGE_ENTITY_DOMAIN_MISMATCH` (WARNING), plus the `DOMAIN_REGISTRY_FOLDER_MISSING` dead-registry-entry warning (#658 both directions). **Migration required:** existing specs must backfill `x-entity.domain` and declare `info.x-domains` before regenerating (a bare `x-entity` now fails `ENTITY_DOMAIN_REQUIRED`); the per-group `domains: {include\|exclude}` filter itself is opt-in. |
| `v0.5.0` (incubating) | generator **`0.5.0`** — `Specfuse/generator-dist` release `v0.5.0`, asset `specfuse-generator-0.5.0.jar`, sha256 `c96ece89…331449` | **Additive contract change** (9 merges since 0.4.1; several change generated C# output — regen deliberately). Two new vendor extensions plus a leak guard: (1) `x-internal-only` (NEW property extension, #729) — property is persisted on the domain entity + EF column but excluded from every DTO and builder. (2) `x-classification: [exposed]` (NEW closed-set value) — reviewed "safe to expose despite secret-shaped name" escape hatch; documented in `Vendor_Extensions.md §1.5`. (3) `SENSITIVE_FIELD_IN_RESPONSE` (NEW validation rule, #734/#737) — ERROR when a string entity property whose name ends `hash`/`secret`/`salt`/`password` is emitted into a response without `writeOnly`, `x-internal-only`, or `x-classification: [encrypted\|exposed]` (temporal formats structurally excluded; deterministic); plus new `INTERNAL_ONLY_*` guards. (4) `writeOnly` response-scoping (#728) — `writeOnly` properties dropped from response DTOs, kept in request DTOs (`*Request`/`New*`/`Update*`). Also tri-state `Optional<List<T>>` for nullable list-of-VO `Update*` fields (#723), C# nested-VO JSON converter case-insensitivity (#722), Python paginated repos emit `ORDER BY` (#724). **Spec-author action:** a specs repo must add `exposed` to its `x-classification` vocabulary before marking fields with it, and backfill `x-internal-only`/response-scoping where the new leak guard now errors. No migration for existing specs that don't hit the secret-shaped heuristic. |
| `v0.5.1` (incubating) | generator **`0.5.1`** — `Specfuse/generator-dist` release `v0.5.1`, asset `specfuse-generator-0.5.1.jar`, sha256 `cdabf119…b6c8fc8` | **Additive contract change** (4 features since 0.5.0). (1) `info.x-roles` (NEW optional OpenAPI registry, #741/FEAT-2026-0056) — single source of truth for the valid-role set; both OpenAPI operation `x-roles` and Arazzo `x-actors.role` validate membership against it, replacing the hardcoded `ActorRole` enum. Permissive fallback when absent (skip membership + one warning), so specs and generator ship in any order. (2) `REQUEST_UNFAKEABLE_CONSTRAINT_NO_EXAMPLE` (NEW validation rule, #762 → promoted to **ERROR** with a precision guard, #765) — errors when a request-body string property has a regex `pattern` the generator's fake-data placeholder cannot satisfy, or an unsupported `format`, and no `example`/`x-sample`; fires only when the would-be placeholder genuinely fails the constraint (no false positives). (3) Generated-C#-test fixes (#760 S1/S3): fake-data honors `minLength`/`maximum`; Arazzo scenario tests emit `IClassFixture<>` wiring for injected recipe fixtures. **Spec-author action:** add an `example` (or `x-sample`) to any request-body property whose `pattern`/unsupported-`format` a generic `"Test <name>"` placeholder can't satisfy, or `validate` now fails (`REQUEST_UNFAKEABLE_CONSTRAINT_NO_EXAMPLE`); declaring `info.x-roles` is optional but recommended. #760 S2 (the 403s) was consumer-side, no generator change. |

| `v0.5.4` (incubating) | generator **`0.5.4`** — `Specfuse/generator-dist` release `v0.5.4`, asset `specfuse-generator-0.5.4.jar`, sha256 `86abba28…497eff` | **Consolidated re-pin from 0.5.1** (the kit skipped generator 0.5.2/0.5.3; this row covers 0.5.2 → 0.5.4). **⚠ BREAKING contract changes:** (1) **Explicit relationships only** (FEAT-2026-0049, #820/#822) — implicit `{Entity}Id` → `belongsTo` inference is **retired**; an undeclared `{Entity}Id` is now a **non-owning reference**, not an inferred parent. `RELATIONSHIP_SYMMETRY` is a hard **ERROR**: a half-declared `hasMany`/`hasOne` with no reciprocal `belongsTo` (or vice versa) fails `validate` (a `belongsTo` targeting a declared tenancy root is exempt, #822). **Migration:** declare every ownership edge symmetrically, or drop the stray side. (2) **Operation-category invariants** (FEAT-2026-0067, #824) — `QUERY_MUST_BE_GET` and `COORDINATION_NOT_GET` are NEW **ERRORS** (a `query` op must be GET; a `coordination` op must not be GET), and the `Admin`/`Discovery`/`Reference` operation categories are **removed** — an unknown `x-operation.category` is now a hard error. **⊕ Additive:** (3) `DDD_NESTED_LIST_RELATIONSHIP` (NEW rule, #826) — a parent-scoped list GET whose response child declares no relationship to the path aggregate is flagged at `validate` (the codegen path also fails with a coded `OPERATION_LIST_UNRESOLVED_RELATIONSHIP` instead of an NPE). (4) **QuerySpecification threading** for GET application lists (FEAT-2026-0067) — a `query`/`resource`/`coordination` GET list that resolves to a single domain entity now threads `QuerySpecification<Entity>` through the controller and gains a `QuerySpecification` parameter on the `I{Area}ApplicationService` method. **Consumer action:** hand-written `ApplicationService` impls must add the new parameter. (5) `OPERATION_NON_AGGREGATE_ENTITY_GET` (NEW warning, #834) — nudges a non-aggregate GET resolving to an aggregate-backed entity toward `category: aggregate`; an **absent** category is treated as the aggregate default and is not warned. (6) 0.5.3 (#791): non-paginated list endpoints stop silently truncating to 25 rows; 0.5.2: FEAT-2026-0060 Gate 1 DTO-driven eager-load `Includes`. C#-codegen-only fixes (no spec action): nullable owning-parent-FK child-create (#825), optional FK-reference create-fakes emit `null` not a random Guid (#767 nullable half; the required-FK half is tracked in #767), tri-state `Optional<List<T>>` nullability (#788). **Spec-author action:** (a) migrate to explicit symmetric relationships (FEAT-2026-0049); (b) ensure `query` ops are GET and `coordination` ops are non-GET, and stop using admin/discovery/reference categories; (c) declare a relationship for any parent-scoped list, or flatten it. |

| `v0.5.5` (incubating) | generator **`0.5.4`** (pin unchanged) | **Kit-only release — no generator coordination required.** Consolidates the ruleset fixes and two contract additions landed from consumer reports #12–#15, #19 and #20 (PRs #21–#23). **(1) Null-crash fixes (#14).** Any null in a linted document aborted the entire Spectral run, emitted zero findings and exited 2 — which any wrapper inspecting only the report reads as a clean pass. Root cause is upstream: `spectral:oas` ships `duplicated-entry-in-enum` with an unguarded recursive-descent filter. It is now disabled and replaced by the null-safe `specfuse-no-duplicate-enum-entries`, and 26 of the kit's own filter expressions gained the `@ &&` guard they were missing. New `scripts/spectral-lint.sh` fails on a crash or an empty report, not only on reported findings. **(2) `x-entity.mutability` (NEW optional sub-field, #13)** — `mutable` | `immutable` | `appendOnly`, default `mutable`. `specfuse-main-resource-has-updatedAt` now exempts entities declaring a non-mutable write policy instead of demanding an `updatedAt` that would permanently equal `createdAt` on audit-trail, ledger and append-only entities. Validated against the closed set by `specfuse-xentity-shape`, so the exemption cannot be taken silently. Runtime enforcement is generator-side — follow-up #12. **(3) Relationship classification and projection markers (NEW, #19)** — `x-references` (non-owning association FK; `none` for an opaque uuid, requiring a justifying description), `x-fk-for` (owning FK under a name that is not `{Entity}Id`, bound to a declared `belongsTo`), and `x-expand-of` / `x-projection` (read-only scalar and collection projections). Supplies the vocabulary that became necessary when implicit `{Entity}Id` → `belongsTo` inference was retired in `0.5.4`. **Convention shift:** the former "`belongsTo` wins, `x-references` degrades to a hint" precedence is removed — declaring both for the same target is an error. `API_Handbook.md` §9.5 also states that a nested `/{parents}/{parentId}/{children}` route requires the child to `belongsTo <Parent>`. Graph-level validators remain generator-side — follow-up #13. **(4) PATCH child-collection reconcile (#20)** — a collection property present in an `Update{Resource}` body is the **complete desired set**; there is no merge mode. Child-entity collections reconcile by identity: known `id` updates in place with the PK preserved, no `id` creates, unknown `id` is `404`, and an omitted child is **permanently hard-deleted**. `Update{Child}` DTOs used as array elements must expose an optional `id` (`specfuse-child-collection-reconcile-id`, WARN). Runtime behaviour and the fail-closed generation guard are follow-up #14. **(5) Documentation** — `$ref` resolution sensitivity and the resolved-vs-unresolved audit (#12); the per-rule baseline ratchet for adopting the ruleset against pre-existing specs (#15); the value-object-invariant vs entity-business-rule boundary for `validationRules` (#13); and the requirement that an extension-shape change updates `schemas/spectral/` in the same PR. **Spec-author action:** none required — every change is additive or a fix. Classify FK-shaped uuid properties and mark read-only embeds to adopt (3); add the optional `id` to child Update DTOs and correct any upsert-only prose to adopt (4). Projects that forked the kit rulesets should re-apply the null guards and the `duplicated-entry-in-enum` replacement, since a forked copy keeps the crash. |

| `v0.5.6` (incubating) | generator **`0.5.4`** (pin unchanged) | **Kit-only release — delivery. Nothing the kit shipped after `init` had any way of reaching an existing project.** **(1) `specfuse authoring upgrade <project>`** (with `--dry-run`), replacing the blind `refresh` (kept as a deprecated alias). Mirrors the scaffold overlay in `specfuse/loop`: a `.specfuse/authoring/VERSION` stamp that refuses a downgrade, a sha256 `.scaffold-manifest` ownership record, clobber warnings that distinguish a locally-modified kit file from a project-authored one, and a manifest-scoped prune that removes only what the kit provably wrote. Projects predating the overlay are adopted on first run (`kit unversioned -> …`). Project content — `api/`, `CLAUDE.md`, the project file, `.gitignore` — is seeded once at `init` and never touched again. **(2) The `scripts/` tooling the plugin skills invoke.** 23 script paths were referenced across the skills and **none existed in the kit** — `/preview` called `./scripts/serve-docs.sh`, `/bundle` called `./scripts/bundle-spec.sh`, and the design skills called validators that were never shipped. 17 scripts now ship and land at `<project>/scripts/`: nine validators, bundling, the two preview servers, and the docs generation. The Spectral validators lint against the rulesets the overlay delivers into `.specfuse/authoring/schemas/spectral/` rather than a project-local copy that drifts, and `generate-scenario-docs.sh` drives the generator through `specfuse authoring generate` instead of a bundled jar. **(3) Content the kit shipped but never delivered:** the Spectral `schemas` themselves (projects were told to lint against rulesets they never received), `ai-access-policy-template.md` (the README told users to copy a file that reached no project), and the two ideation backlog templates referenced by `ideation-capture`. `init` now writes the same overlay set as `upgrade` rather than keeping its own list — the drift between the two is how this content went undelivered. **(4) Two defects in the `project-init` template**, fixed in `examples/hello-orders/` when Spectral entered CI but not in the template it derives from, so every bootstrapped project began with five errors: `Role` enums lacked `x-enum-case: PascalCase`, and `asyncapi.yaml` carried a root `tags` key that is invalid in AsyncAPI 3.0. CI now lints a freshly scaffolded project with the scripts that project ships, closing the gap that let this survive. **Spec-author action:** run `specfuse authoring upgrade <project>` to receive the scripts, schemas and templates. Edits to shipped kit files do not survive an upgrade — the warning names them — so send improvements upstream. Existing projects should re-apply the two template fixes to their own `enums.yaml` and `asyncapi.yaml`, which `upgrade` does not touch because they are project content. `bundle-async-spec.sh` needs PyYAML (`pip install PyYAML`); every script reports what it is missing. |

| `v0.5.7` (incubating) | generator **`0.5.5`** — `Specfuse/generator-dist` release `v0.5.5`, asset `specfuse-generator-0.5.5.jar`, sha256 `e9b02532…c52d6` | **Generator re-pin + a missing script.** (1) **Re-pin to generator 0.5.5** (was 0.5.4). No kit-side contract change: no vendor extension, naming convention or validation rule moves in this bump, so no spec-author migration. The published release notes do not enumerate the generator-side changes, and the generator source tags were not available to diff — this row records the pin, not a changelog. (2) **`validate-generator.sh` shipped.** `validate-specs.sh` runs nine layers and the ninth calls `validate-generator.sh`, which the `0.5.6` script port missed — so the aggregate validator every project runs before a commit died on its last step. It drives the generator through `specfuse authoring validate-source` / `validate` rather than a bundled jar, discovers `<name>-project.json`, and follows the project's spec version. CI now asserts that every inter-script reference in `scripts/` resolves, which is the check that would have caught this: the `0.5.6` verification ran each validator individually but never the aggregate that composes them. **Spec-author action:** `specfuse authoring upgrade <project>` to receive the missing script. |

| `v0.5.8` (incubating) | generator **`0.5.5`** (pin unchanged) | **Kit-only release — the scaffolded project now passes generator validation (authoring #30).** Two defects, both from the same cause: nothing had ever run the generator against the template. **(1) The project file was a different shape than the generator accepts.** Of its top-level keys the generator recognised only `name` and `description`; `specs`, `bundle`, `Backend`, `Frontend`, `Workers` and `$schema` were all rejected, so `validate` and `generate` failed on the project file of every bootstrapped project. `handbooks/Project_File.md` documented the correct shape all along — the template and `examples/hello-orders/` diverged from it. Both now use `openApiSpecifications` / `asyncSpecifications` / `arazzoSpecifications` / `asyncSourceRoot` / `stateDir` / `groups`. The template ships `groups: []` rather than the previous `"language": "TODO"` placeholders, which fail validation outright (`Language 'TODO' is not registered in the LanguageRegistry`); fill it in from `Project_File.md` §14. **(2) The 412 response carried an inline schema**, which the generator rejects (`INLINE_RESPONSE_SCHEMA`) because an unnamed response shape cannot become a typed DTO. Extracted to a named `PreconditionFailedBody` in both the template and the example. A freshly scaffolded project now validates at **0 generator errors**. **Spec-author action:** `specfuse authoring upgrade <project>` does **not** fix this — the project file and `common/responses/` are project content, not kit-owned. Existing projects must re-apply both changes by hand; see the `0.5.8` template as the reference. |

| `v0.5.9` (incubating) | generator **`0.5.5`** (pin unchanged) | **Kit-only release — four consumer-reported defects, all found by pointing a tool at something it had never been pointed at.** **(1) `examples/hello-orders/` had six generator errors (#33).** `Customer` and `Order` declared `belongsTo: [Tenant]` and every route is scoped by `/v1/tenants/{tenantId}`, but no schema carried `x-entity` for it — the example demonstrated multi-tenancy with the tenancy root absent. Added as an aggregate with no `belongsTo`, a `tenant` domain, and a Tier 0 `aiAccess` block. Two required state-machine enums also had no default (`CustomerStatus` → `active`, `OrderStatus` → `draft`). **(2) `Vendor_Extensions.md` §4.6 was wrong about `x-default`** — it advised preferring the standard `default`, but on an enum the generator errors (`ENUM_MISSING_X_DEFAULT`) unless **both** are present with the same value. Following the handbook produced an error. Corrected, with `REQUIRED_ENUM_MISSING_DEFAULT` and the note that the default belongs on the enum schema, not beside the `$ref` (OpenAPI 3.0 drops `$ref` siblings). **(3) `validate-openapi-generator.sh` fed `asyncapi.yaml` to openapi-generator (#38).** It globbed `*.yaml` at the spec root, where the documented layout puts both roots — so the layer could never pass in any project with async specs, and `validate-specs.sh` aggregates it. OpenAPI documents are now identified by a top-level `openapi:` key. Also fixes an unparenthesised `-o` that let `-maxdepth 1` apply to only the first term. **(4) `specfuse-xentity-shape` rejected three documented keys (#36)** — `valueObjects`, `cascadeDelete` and `children`, so any spec following the handbook failed lint at error severity. The generator read a key its own linter rejected. The closed allow-list stays: it is what turns a typo into an error, and the fixture asserts both directions. **(5) Snapshot guardrails did not exist (#37).** `AsyncAPI_Handbook.md` §2.3 described three as Spectral-enforced; none were implemented, and `x-classification` appeared in no ruleset at all. New `specfuse-async-snapshot-guardrails` enforces the size limit and the shape and honesty of both overrides — a bare list, a justification under 20 characters, or an acknowledgement naming a property the snapshot lacks are all rejected. The two checks that compare a snapshot to its source entity stay generator-side (follow-up #15); the entity is in the OpenAPI document. **Spec-author action:** `specfuse authoring upgrade <project>` for the script fix; pair every enum `default` with a matching `x-default`. Nothing else changes meaning. Note the snapshot privacy gate is still only partly automatic — a classified field with no acknowledgement at all passes kit lint. |
| `v0.6.0` (incubating) | generator **`0.5.5`** (pin unchanged) | **Kit release — a new vendor key, and the kit moves onto the suite's single command.** *Minor, not patch: this release adds to the contract vocabulary (`x-entity.delete`) rather than only fixing what 0.5 shipped, and changes the documented command surface.* The Specfuse suite is now driven through one `specfuse` command, and this kit is `specfuse authoring …` (umbrella `0.11.0`). The umbrella hard-depends on every component, so `pipx install specfuse` / `uv tool install specfuse` brings the kit with no extras and no `--include-deps`, and `pipx upgrade specfuse` re-resolves it — an umbrella floor bump is no longer what delivers a kit release. **(1) Every command reference migrated** across the README, `docs/`, the `generate` skill, the `project-init` template and the scripts the kit ships: `specfuse-authoring <verb>` is now `specfuse authoring <verb>`. **(2) `--help` and `--version` print the name actually invoked** — `specfuse authoring` under the umbrella (and for `python -m`), the flat name when the deprecated script is called directly. **(3) The scaffolded `validate-generator.sh` and `generate-scenario-docs.sh` resolve the CLI at run time**: `specfuse authoring` when the suite CLI is installed, the flat `specfuse-authoring` otherwise, with `SPECFUSE_AUTHORING` overriding both. **Spec-author action:** none required — the flat `specfuse-authoring` command keeps working as a deprecated alias until `1.0.0`, when it is removed in a coordinated release train across all three components. Run `specfuse authoring upgrade <project>` to pick up the migrated scripts and `CLAUDE.md` wording; install the suite with `pipx install specfuse` rather than the standalone package, and do not run both installs (they provide the same flat command name and fight over it — `specfuse doctor` reports which one owns it).**(4) New vendor key `x-entity.delete`** (generator FEAT-2026-0080 gate 1). Shorthand `hard` | `soft`, or `{ mode, retention }` with `retention` = `none` or an ISO-8601 duration; absent resolves to `hard`, the pre-FEAT-2026-0080 generator behaviour, so no existing entity changes meaning. It replaces an inference — the generator's delete template branched on whether a linked AsyncAPI message carried `x-trigger-when`, letting an operation description promise retention while the service destroyed the row. The kit enforces the closed value sets, the long-form sub-keys and the retention format (`specfuse-xentity-shape`, fixtures in both directions); the eight coherence rules are generator-side and validation-only in gate 1. `API_Handbook.md` no longer states soft delete as a fact — it is a convention that `delete: soft` makes true of an entity — and its examples filter on `deletedAt` rather than a `status: deleted` member. **Spec-author action for this part:** audit DELETE operations against the generator's `DELETE_SEMANTICS_UNDECLARED` warning; an entity documented as soft-deleting with no declaration is hard-deleting today. See follow-up §16 for the two gaps gate 1 leaves open.**(5) A drift guard for the closed extension guards.** `check-extension-vocabulary.py` (shipped into `scripts/`, wired into `validate-spectral.sh`) compares every Spectral rule that closes a vendor extension with `additionalProperties: false` against the key constants in the pinned generator jar, and fails when the generator knows a key the ruleset rejects — the direction that blocks adoption. One-way by design: keys a ruleset accepts but the jar never mentions are informational, since the generator reaches some keys through indirect constants. With no cached jar it skips loudly and exits 0; CI passes `--require-jar`. Guards are discovered structurally, so `x-entity`, `x-value-object`, the async and Arazzo rulesets and any project-local `<token>-*-shape` rule are all covered without a list to maintain. See follow-up §17. |

| `v0.7.0` (incubating, current) | generator **`0.5.5`** (pin unchanged; re-pin when the FEAT-2026-0088 jar publishes) | **Kit release — `x-entity.concurrency` enters the kit's vocabulary** (authoring #47, generator FEAT-2026-0078 / FEAT-2026-0088). *Minor, not patch: it adds to the contract vocabulary.* **(1) The key was missing from `specfuse-xentity-shape` entirely**, and that guard is `additionalProperties: false` — so **every** authored form failed lint at error severity, not only the scalar shorthand a consumer report described. The hand-patch that unblocked FEAT-2026-0078 rollout (recorded in follow-up §17) was applied in a consumer's ruleset, never upstream, so the kit still rejected the key it had documented the drift lesson about. **(2) The key is now accepted and shape-checked.** `optimistic` \| `none` as a scalar, or `{ mode, reason }`. **Required with no default** — absent means *undeclared*, a third state the generator's census counts separately from a declared `none`, so no `default:` is set in the guard. `reason` is left an open string deliberately: the vocabulary is generator-owned and not frozen until FEAT-2026-0091, and closing a set the kit does not own is precisely how `domain`, `concurrency` and `delete` each blocked their own adoption. **(3) Both `none` forms pass lint, and a new WARNING asks for the justification.** `specfuse-xentity-concurrency-unprotected-needs-reason` fires on the bare `concurrency: none` and on `{ mode: none }` with no `reason`. Rejecting the scalar outright was the alternative and was declined: the generator accepts it, and a closed guard that rejects what generates fine blocks the adoption rather than the bad spec. The warning fires unconditionally, including on entities with no unsafe write — the write surface is not visible from inside the `x-entity` block, and the precise "`none` **and** an unsafe write" check is generator-side. **(4) Handbook framing corrected.** `API_Handbook.md` §"Concurrency Control" scoped ETags to *"safe autonomous operations by AI agents"*; an approval workflow where an employee cancels a request while a manager approves it is two writers with no AI anywhere. Treating the AI-reachable set as the answer under-protects everything else, so the handbook now frames it as a floor. `Vendor_Extensions.md` §1.1 documents the key, the recommended `reason` vocabulary including `not-assessed`, and why `mutability` cannot supply it. **Spec-author action:** declare `concurrency` on every entity. Start from the AI-writable set, then add approval workflows, shared rosters and anything else reachable by two callers. Where the analysis has not been done, declare `{ mode: none, reason: not-assessed }` rather than claiming a justification that is not true — it is the honest state and it is queryable; it is also the value expected to be refused when the key hardens to ERROR. See follow-up §18. |

## How to update this matrix

Bump the kit version on every change to:
- Handbook content that changes a generator-contract rule (new `x-*` extension, naming convention change, validation rule)
- Sample YAML structure (templates the generator consumes)
- Spectral schemas in `schemas/`

Pair the kit bump with the generator commit that implements the corresponding parser/validator change, and add a row above.

Claude assets (the `specfuse-authoring` plugin in the `specfuse/specfuse` marketplace) and the `specfuse-authoring` CLI do not require generator-side coordination and do not need a matrix bump.

---

## Outstanding generator-side follow-ups

These are alignment items the kit declared canonical during Phases 2–6 but that the generator has not yet picked up. None block kit usage today (the kit is internally consistent), but each one should land on the generator to remove drift between the two sides.

The kit accepts both forms in its prose (notes the alias where one exists), so the generator can adopt these incrementally without breaking any existing project. Mark each item done by linking the generator commit that implements it.

### 1. Spectral rule prefix `rm-*` → `specfuse-*`

**Status:** kit canonical (Phase 2, 4 commits)

The kit renamed all Spectral rule identifiers from the legacy `rm-*` prefix (inherited from the source project) to `specfuse-*` to match the kit's neutral identity. Rules touched:

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

The kit's samples and handbooks consistently use `x-roles` and `x-scopes` (the shorter form, matching the generator's `ExtensionConstants` documentation). The source project's endpoint-samples used the longer `x-required-roles` / `x-required-scopes` form. The kit aligned on the short form during the endpoint-samples generalization (documented in the commit message).

**Generator action:** confirm `ExtensionConstants` accepts `x-roles` / `x-scopes` as canonical. If the longer alias is also accepted, document the canonical short form and mark the longer one as legacy.

**Severity:** additive — short form is already canonical; this is a documentation/alias cleanup.

### 5. OpenTelemetry attribute prefix

**Status:** kit canonical (Phase 2, commit `569a89b`)

The kit's AsyncAPI handbook §4.5.8 (telemetry dimension tagging) declares the unprefixed `event.entity` / `event.action` attributes as canonical, with a note that projects may apply a project-specific prefix (e.g., `{project}.event.entity`) via generator configuration. The legacy source-project-specific prefix (`<project>.event.*`) is removed.

**Generator action:** emit telemetry attributes as `event.entity` / `event.action` by default. Read a `telemetryAttributePrefix` field from the project config (or environment) to apply a per-project prefix when set.

**Severity:** breaking for any observability dashboards that filtered on the legacy `<project>.event.*` attributes. Coordinated with telemetry consumers before flip.

### 6. Spec path versioning baseline

**Status:** kit canonical (commit `7cea428`)

Projects bootstrapped from `templates/project-init/` start at `api/specs/v1/`. The source project used `api/specs/v3/` for legacy reasons (it had migrated through v1 and v2 internally). Fresh projects from the kit do not inherit that history.

**Generator action:** ensure the generator's spec-discovery logic does not assume any specific major version. The project's generator config (`{project}-project.json`) declares the spec paths explicitly; the generator should read them rather than glob for a hardcoded directory name.

**Severity:** additive — the generator already reads paths from the project config; this entry just notes the kit's chosen baseline.

### 7. Single-shared-topic alignment in event channel samples

**Status:** kit canonical (Phase 3, commit `6d1a7c9`)

The kit's AsyncAPI handbook §1.5 and §3.2 declare a single shared event topic (`{project}.events`) as the v2.1 architectural baseline, with a documented sharding escape hatch (handbook §3.2). The source project's `message-samples.yaml` showed a per-aggregate event-topic address (`{project}.{domain}.{aggregate}.events`) that predated this decision. The kit's `samples/message-samples.yaml` aligns with the handbook (`{project}.events` as the canonical channel address).

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

The kit collapsed the source project's two-level tenant model (a parent-org id plus a per-site id) into a single `tenantId` envelope ApplicationProperty for routing. Projects with a multi-level tenancy hierarchy define their own scoping fields in addition to `tenantId` — but `tenantId` is the canonical top-level tenant scope across handbooks and samples.

**Generator action:** confirm that the envelope/header-stamping logic reads `tenantId` from the snapshot or operation parameters and stamps it as an ApplicationProperty. Project-specific narrower scopes (e.g., `customerId`, `siteId`) are stamped through `x-envelope-promote` declarations on snapshot fields, not through hardcoded generator logic.

**Severity:** non-breaking for projects that already use `tenantId`; coordination required for projects that need to migrate from a different field name.

### 11. Write/change-detection semantics (kit `v0.5.4`, authoring #16 + #11)

**Status:** kit canonical (handbook contract added in authoring PR #16, prompted by consumer report #11)

Three write/emit rules are now normative in the handbooks but govern generator **runtime behavior**, not an authorable surface — so there is no Spectral rule to lint them and generator conformance is unverified:

- **No-op writes are inert** (`API_Handbook.md` §Concurrency Control → No-Op Writes): a write leaving every tracked field unchanged returns `200` + current representation, unchanged ETag, no `updatedAt` bump, no row, no event. Critical because `*Created`/`*Updated`/`*Deleted` are forbidden from declaring `x-trigger-when`, so a `Before == After` event has no subscriber-side filter — suppression must be producer-side.
- **Change detection diffs the tracked entity, never the snapshot** (`AsyncAPI_Handbook.md` §2.3): diff `EntityEntry.OriginalValues`/`CurrentValues` before `SaveChangesAsync`. A snapshot-level diff reports "identical" for a write mutating only a snapshot-omitted field and, combined with no-op suppression, silently swallows a real persisted change.
- **Scalar-array properties compare as sets** (`AsyncAPI_Handbook.md` §2.3): reordering is not a change; sequence-significant data declares an explicit ordering property.

**Generator action:** confirm the emitted persistence/emit path (a) detects no-op writes and suppresses `updatedAt`/ETag/row/event, (b) diffs tracked-entity values rather than the serialized snapshot, and (c) compares scalar arrays order-insensitively.

**Open conformance gap (#11):** the consumer also observed **owned value objects absent from event snapshots** in practice, though `AsyncAPI_Handbook.md:402-406` requires them (serialized via the same converter as on the entity). That is a generator non-conformance bug, not an authoring gap — awaiting a repro (entity shape, snapshot YAML, observed payload) to file against the generator.

**Severity:** additive to the contract; generator behavior may already be conformant on (a)–(c). The owned-VO omission, if reproduced, is a silent-data-loss bug on the event stream.

### 12. `x-entity.mutability` write-policy enforcement (kit `v0.5.5`, authoring #13)

**Status:** kit canonical (extension introduced in the ruleset and `Vendor_Extensions.md` §1.1); generator-side runtime enforcement not implemented.

`x-entity.mutability` (`mutable` | `immutable` | `appendOnly`, default `mutable`) declares the write policy for an entity's rows after insert. The kit consumes it **only** as a lint exemption: `specfuse-main-resource-has-updatedAt` no longer demands `updatedAt` on an entity whose rows never change, because such a column permanently equals `createdAt` and asserts something untrue.

The value is validated against the closed set by `specfuse-xentity-shape`, so the exemption cannot be taken silently — but nothing today prevents an update to a row on an entity declared `immutable`.

**Generator action:** decide whether the declared write policy should constrain generated persistence and HTTP surface — e.g. suppress `Update`/`PATCH` handlers for `immutable` entities, reject in-place updates at the repository layer, or omit the `updatedAt` column entirely rather than leaving it perpetually equal to `createdAt`. Until then the property is a **declared and lint-checked intent, not an enforced guarantee**, and `Vendor_Extensions.md` says so explicitly.

**Severity:** additive and backward-compatible — an absent `mutability` means `mutable`, which is the pre-existing behaviour, so no existing spec changes meaning. The exemption's value does not depend on generator enforcement: it removes a rule that was previously forcing authors to write fields contradicting their own entities' stated semantics.

### 13. Relationship classification and projection markers (kit `v0.5.5`, authoring #19)

**Status:** kit canonical (extensions documented in `Vendor_Extensions.md` §1.7–1.9 and `API_Handbook.md` §9.5; shape rules shipped in `schemas/spectral/specfuse-openapi.yaml`). Graph-level validation is generator-side and not implemented in the kit.

Four property-level markers make relationship intent explicit now that implicit `{Entity}Id` → `belongsTo` inference is retired (follow-up: kit `0.5.4`):

- **`x-references: <Entity>`** — non-owning association FK. `OnDelete NoAction`, no aggregate membership, nullability follows `required`.
- **`x-references: none`** — opaque uuid that is not a foreign key; requires a justifying `description`.
- **`x-fk-for: <Entity>`** — owning FK under a name that is not `{Entity}Id`, bound to a declared `belongsTo` (composition and Cascade preserved).
- **`x-expand-of: <twin>`** / **`x-projection: true`** — read-only scalar and collection projections, excluded from persistence.

**Convention shift:** the former "`belongsTo` wins, `x-references` degrades to a hint" precedence is **removed**. `x-references` is association-only; declaring it alongside a `belongsTo` for the same target is an error.

**What the kit enforces:** marker value shape, marker exclusivity on a property, the `x-references: none` justification, projection coherence within a schema (`x-expand-of` names an existing sibling identifier; `x-projection` marks a non-required array of `$ref`), and that neither projection marker appears on a `New*`/`Update*` derivative.

**Generator action — validators the kit cannot express.** Each needs the resolved entity graph or route table, which Spectral does not have when linting a single document:

| Validator | Why it is generator-side |
|---|---|
| `DDD_UNCLASSIFIED_ENTITY_RELATIONSHIP` | Deciding that a uuid property *should* have been classified requires knowing which entity names exist |
| `DDD_DUAL_RELATIONSHIP_DECLARATION` | `x-references: <T>` co-occurring with `belongsTo: <T>` spans the property and the `x-entity` block, resolved per target |
| `DDD_INVALID_FK_FOR` | `x-fk-for` must name a target present in the same entity's `belongsTo` — needs cardinality-keyword resolution (`allOf`/`oneOf`/nested) |
| `DDD_UNMARKED_PROJECTION_EMBED` | Recognising that an embed projects *another entity's* data requires the graph |
| `DDD_EXPAND_OF_NAV_MISMATCH` | The twin must resolve to the same entity the projection references |
| `OPERATION_PARENT_NOT_OWNER` | Nested `POST`/`GET /{parents}/{parentId}/{children}` requires the child to `belongsTo <Parent>` — joins the route table to the entity graph |
| `DDD_UNJUSTIFIED_OPAQUE_REFERENCE` | Kit checks a description exists; judging whether it justifies anything does not automate |

`DDD_REQUIRED_PROJECTION_EMBED`, `DDD_INVALID_PROJECTION_COLLECTION` and `DDD_INVALID_EXPAND_OF` are covered kit-side by `specfuse-projection-coherence`; the generator should keep its own copies as defence in depth, not as the only enforcement.

**Severity:** additive. No existing spec changes meaning — an unmarked uuid property was already unclassified after `0.5.4`, and these markers give authors the vocabulary to fix that. Generator-implementation follow-ups for polymorphic and self-referential `x-fk-for` are tracked outside this repo.

### 14. PATCH child-collection reconcile semantics (kit `v0.5.5`, authoring #20)

**Status:** kit canonical (contract in `API_Handbook.md` §1.5.1). Governs generator **runtime behaviour**; the kit lints only the DTO shape the contract depends on.

A collection property present in an `Update{Resource}` body is the **complete desired set** — there is no merge mode. Value-object and scalar arrays are replaced wholesale; child-entity collections reconcile by identity:

| Incoming element | Behaviour |
|---|---|
| Known `id` | Update in place, PK preserved (so `x-references` FKs from other aggregates stay valid) |
| No `id` | Create, validated as a create — a violating element fails the whole PATCH with `400` |
| Unknown `id` | `404`, never a silent create-with-client-id |
| Tracked child absent | **Permanent hard delete** — reconciled children are aggregate-internal state, so a project-wide soft-delete convention for top-level resources does not apply |

Accidental-deletion risk is fenced by the already-mandatory `If-Match` (forcing read-modify-write) and `?validateOnly=true`.

**What the kit enforces:** `specfuse-child-collection-reconcile-id` (WARN) — an `Update*` DTO used as an array element inside another `Update*` DTO must expose an **optional** `id`. The rule fires only on that shape; a blunt "every `Update*` DTO needs `id`" rule would be a false-positive storm, since most `Update*` DTOs are the body of a PATCH addressed by URL.

**Generator action:**

1. Implement the reconcile table above, including **hard** delete for omitted children and create-leg validation for elements without `id`.
2. **Fail closed** at generation time when an element DTO has no identity property. Delete-then-add is not an acceptable fallback — it recreates rows with new PKs on every PATCH, breaking `x-references` FKs, audit trails, and concurrency tokens. The kit's WARN is the authoring-time half of the same rule; generation raising a `ConfigurationException` is the half that prevents destructive output.
3. Match the kit's rule scope so the two do not disagree about which DTOs are in scope.

**Rejected alternatives** (recorded so the contract does not drift back): upsert-only / absent-means-untouched forks the semantics inside one PATCH body, is inexpressible in OpenAPI, and requires child `DELETE` route coverage to remove anything; `_delete`-style deletion markers violate the property naming rules, pollute every child DTO, and carry no OpenAPI expressibility.

**Severity:** the contract is a clarification of what PATCH already meant, but consumer-facing **descriptions** must now state that omitted children are permanently removed. Prose that documents upsert-only semantics contradicts the server and is worse than no prose.

### 15. Snapshot-to-entity guardrails (kit `v0.5.9`, authoring #37)

**Status:** kit enforces the within-document half (`specfuse-async-snapshot-guardrails`); the two cross-spec checks are generator-side and not implemented.

`AsyncAPI_Handbook.md` §2.3 promises three snapshot guardrails. Two of them compare a snapshot against its **source entity**, which lives in the OpenAPI document — not reachable while Spectral is linting the AsyncAPI surface, and not reconstructable from it:

| Guardrail | Where it can live |
|---|---|
| Snapshot has > 25 scalar fields (warn, `x-snapshot-size-acknowledged` override) | **kit** — decidable from the snapshot alone |
| `x-snapshot-pii-acknowledged` well-formed, justification ≥ 20 chars, and naming a property the snapshot actually has | **kit** — decidable from the snapshot alone |
| Snapshot field whose source entity property carries `x-classification: [pii \| sensitive]` must be acknowledged (**error**) | **generator** — needs the entity |
| Snapshot field name must exist on the source entity (**error**) | **generator** — needs the entity |

**Generator action:** implement the two entity-comparing rules. Until then the privacy gate the handbook describes is only partly automatic: the kit guarantees an acknowledgement is *well-formed and on-target*, not that every classified field *has* one. A snapshot can still carry a `pii` field with no acknowledgement and pass lint.

**Why not solve it kit-side:** a Spectral function could walk the filesystem from the document's directory to find `../models/<Entity>.yaml`, but it would silently do nothing when linting a bundle (where the paths are gone) — and a privacy control that silently does nothing is the failure this guardrail exists to prevent. Better an honest gap than a rule that looks like enforcement.

**Severity:** the missing half is an unenforced **error**-severity promise in the handbooks. Consumers should not read a green AsyncAPI lint as evidence that snapshot PII has been reviewed.

### 16. `x-entity.delete` semantics (kit-side shape; generator FEAT-2026-0080 gate 1)

**Status:** kit accepts and shape-checks the key (`specfuse-xentity-shape`, `Vendor_Extensions.md` §1.1, `API_Handbook.md` §"Deletion Policy"). The eight coherence rules are generator-side; gate 1 is validation-only and emits no generated-code change.

`x-entity.delete` (`hard` | `soft`, or `{ mode, retention }`; default `hard`) declares what a `DELETE` does to the entity's own row. It replaces an inference that was invisible from the spec: the generator's delete template branched on whether a linked AsyncAPI message carried `x-trigger-when` — a message-shaped signal deciding a persistence-shaped question. An operation description could promise retention while the generated service destroyed the row, with nothing in the contract disagreeing.

**What the kit enforces:** the closed value sets, the long-form sub-keys, and that `retention` is `none` or an ISO-8601 duration with at least one component. Pinned by `schemas/spectral/fixtures/xentity-shape-keys.yaml` (`ShorthandDelete`, `BadDeleteMode`, `BadRetention`, `DeleteUnknownKey`).

**What the generator enforces (gate 1):** `DELETE_SOFT_REQUIRES_DELETED_AT`, `DELETE_SOFT_DELETED_AT_SHAPE`, `DELETE_HARD_DECLARES_DELETED_AT`, `DELETE_AUDIT_REQUIRES_SOFT`, `DELETE_RETENTION_REQUIRES_SOFT`, `DELETE_RETENTION_INVALID` (ERROR); `DELETE_SEMANTICS_UNDECLARED`, `DELETE_SOFT_STATUS_ENUM_OVERLAP` (WARNING). Stamping, the column, and read filtering are gate 2. `retention` stays declared-but-not-enforced until the cleanup worker (`FEAT-2026-0081`).

**Two overlaps the generator should reconcile before gate 2:**

1. **`cascadeDelete` already exists** and already takes `soft` | `hard`. It scopes the entity's *children*; `delete` scopes the entity's *own row*. The kit now documents the distinction, but nothing checks that a `cascadeDelete: soft` parent names children that themselves declare `delete: soft` — a cascade whose targets hard-delete is a coherent-looking declaration with the opposite effect. There is no gate-1 rule for it.
2. **The default is inverted relative to the handbook.** `API_Handbook.md` states soft delete as the project-wide convention; the vocabulary defaults to `hard`. That is the right default for backward compatibility — no existing entity changes meaning — but it means a project following the handbook has been hard-deleting everywhere it did not accidentally trip the `x-trigger-when` branch. `DELETE_SEMANTICS_UNDECLARED` is the detector for that, which is exactly why its WARNING severity is temporary.

**Severity:** additive and backward-compatible as a vocabulary. As a *finding*, the gap it exposes is not: an entity documented as soft-deleting, with no declaration, is hard-deleting today. Projects should audit their DELETE operations against `DELETE_SEMANTICS_UNDECLARED` before treating the warning as migration bookkeeping.

---

---

## Surfaced bugs (kit-side, fixed during Phase 6 verification)

| Bug | Fixed in | Description |
|---|---|---|
| `openapi.yaml.template` YAML syntax error | commit `690db55` | Line 50 had `PreconditionRequiredError:{ $ref:` with no whitespace before `{`. YAML inline-flow requires a space after `:`. Would have produced an unparseable `openapi.yaml` in every project bootstrapped from the template. Caught by the Phase 6 agent while concretizing the template into `examples/hello-orders/`. |
| `openapi.yaml.template` missing path-param refs | commit `690db55` | The template defined `tenantId`/`customerId` in `common/parameters/path.yaml.template` but did not reference them from `components.parameters` in the OpenAPI root. Added refs so bootstrapped projects see the pattern. |

These are kit-internal fixes and do not require generator coordination.

## Surfaced bugs (kit-side, fixed from consumer reports)

| Bug | Reported | Fix | Description |
|---|---|---|---|
| Any null aborts the whole Spectral run | authoring #14 | `duplicated-entry-in-enum: off` + `specfuse-no-duplicate-enum-entries` | The upstream `spectral:oas` rule filters with `$..[?(@property !== 'properties' && @.enum && …)]` — recursive descent with no `@ &&` guard. Any null in the document (property-level `example: null`, a meaningful `effectiveTo: null` in an example payload, a null schema node) throws `Cannot read properties of null (reading 'enum')`, aborting the run with **zero findings emitted**. A wrapper that only inspects the report reads that as a clean pass. Reproduced against Spectral CLI 6.16.2 / nimma 0.7.2 with a twelve-line OpenAPI document. The kit disables the upstream rule and ships a null-safe replacement that keeps the coverage. |
| 26 kit filter expressions crashed on null nodes | authoring #14 | `@ &&` guard added to every dereferencing filter | The same bug class in the kit's own rules, needing only a different null placement: a null schema node under `components.schemas` threw `Cannot read properties of null (reading 'x-enum-case')`. Filters that only test `@property` never dereference `@` and were left alone. |
| Spectral CI could not distinguish a crash from a pass | authoring #14 | `scripts/spectral-lint.sh` | Every CI invocation now goes through a wrapper that fails on exit `>= 2` and on an empty report, not only on reported findings. |
| `updatedAt` demanded on entities whose rows never change | authoring #13 | `x-entity.mutability` + rule exemption | `specfuse-main-resource-has-updatedAt` fired unconditionally on every `x-entity`, so audit-trail, ledger and append-only entities were told to add a field that would permanently equal `createdAt`. Treating those findings as mechanical spec defects produces fields contradicting their own entities' documented semantics. See follow-up #12 above. |

Both #14 fixes are pinned by fixtures under `schemas/spectral/fixtures/`, asserted in CI in **both** directions — that the run survives the nulls *and* that the replacement rule still fires. A rule that stops crashing by never running is indistinguishable from a fixed one if only the error count is checked.

### 17. Generator releases should declare their extension-surface delta

**Status:** asked of the generator; the kit now detects the drift rather than waiting to be told.

Every vendor extension the kit closes with `additionalProperties: false` is a schema over a vocabulary the generator owns. When the generator adds a key, a closed guard does not degrade to a missed warning — the first spec that declares the key fails lint with an `additionalProperties` error naming the spec, so the feature cannot be adopted at all. Three keys on `x-entity` reached that state: `domain` (shipped across 78 entities in a consumer repo, undetected for months), `concurrency` (FEAT-2026-0078, rollout blocked until a hand-patch), and `delete` (FEAT-2026-0080, which would have hit the same wall — its plan did not mention the ruleset). FEAT-2026-0071 even listed the consumer ruleset as an out-of-scope item, so the coupling was known and still went unhandled.

**The ask:** a generator feature that adds, renames, or reshapes a vendor-extension key should name the affected surface in its release as a **machine-readable field** — extension, keys, and value constraint — not as prose inside a plan document. Consumers cannot react to something they are not told about; today they learn by lint failure, in the wrong repo, pointing at the wrong file.

**What the kit does in the meantime** (kit `v0.6.0`): `check-extension-vocabulary.py` reads the generator's own key constants out of the pinned jar's class files and fails when a closed guard rejects a key the generator knows. It is wired into `validate-spectral.sh` ahead of the lint in every scaffolded project, and into `bump-generator-pin` as a gate at pin time — the moment the vocabulary changes and the last moment the fix is cheap. This makes the kit's detection independent of the ask above; the ask still stands, because detection at pin time is later than declaration at release time, and a declared surface is also what a consumer's own ruleset needs.

### 18. `x-entity.concurrency` (kit-side shape; generator FEAT-2026-0078 / FEAT-2026-0088)

**Status:** kit accepts and shape-checks the key (`specfuse-xentity-shape`, `Vendor_Extensions.md` §1.1, `API_Handbook.md` §"Concurrency Control"), and warns on an unjustified `none`. The required-key and required-`reason` checks are generator-side; FEAT-2026-0088 gate 1 is WARNING, and FEAT-2026-0091 hardens it to ERROR.

`x-entity.concurrency` (`optimistic` | `none`, or `{ mode, reason }`) declares whether writes to the entity's rows are protected against lost updates. **Required with no default** — an absent key means *undeclared*, which the generator counts separately from a declared `none`. That third state is the reason the key exists, and it is why the kit's guard sets no `default:`.

**What the kit enforces:** the closed value sets and the object form's sub-keys, plus `specfuse-xentity-concurrency-unprotected-needs-reason` (WARNING) on the bare `concurrency: none` and on `{ mode: none }` with no `reason`. Pinned by `schemas/spectral/fixtures/xentity-shape-keys.yaml` in both directions (`ConcurrencyUnprotected` clean; `BadConcurrencyMode` / `ConcurrencyUnknownKey` flagged by the shape guard; `BareConcurrencyNone` / `UnprotectedNoReason` flagged by the reason rule and *not* by the shape guard).

**Three things the generator still owns:**

1. **The `reason` vocabulary is not frozen.** The kit accepts any non-empty string. A closed set is the right end state — the alternative is 80 near-identical sentences that cannot be audited in aggregate — and the consumer census that motivated it (86 entities) supports the collapse: administrative reference data ~23, append-only ~4, owner-only ~2. **The set must include a `not-assessed` member.** In that same census ~15 entities were genuinely contended and simply not analysed yet, which is a *status*, not a justification; a vocabulary of justifications cannot express it, and forcing those into `rare-write` or an `other` escape hatch manufactures exactly the false claims the vocabulary exists to make auditable. Proposed: `append-only | single-writer | reference-data | rare-write | not-assessed | other`, with `other` carrying free text and `not-assessed` the value FEAT-2026-0091 must refuse to promote past. The kit tightens its guard to whatever set the jar ships.
2. **The required-`reason` condition needs the path surface.** `reason` is owed when the entity declares `none` *and* exposes a `PUT`/`PATCH`/`DELETE`. The second half is not visible from inside the `x-entity` block, so the kit's warning is unconditional and the precise check stays generator-side.
3. **Do not plan to derive it from `mutability`.** `appendOnly` looks like it could supply `reason: append-only` automatically. In the same census `mutability` was declared on 10 of 86 entities — an optional key with a permissive default is too sparse to source a required one.

**Severity:** additive as a vocabulary. As a *finding*, it is not: a spec with no `concurrency` anywhere is not a protected spec, it is an unmeasured one, and the entities most likely to be missed are the human-vs-human contended ones (approval workflows, shared rosters) that an AI-safety framing does not surface.

---

## Outstanding kit-side work

These are gaps in the kit itself, separate from the generator-side follow-ups above. Each represents an enforcement promise the handbooks make that has no implementation today.

### Wire Spectral into CI against the bundled example — DONE (all three surfaces)

`.github/workflows/example-regen.yml` lints `examples/hello-orders/` against all three kit rulesets, failing the job on any `error`-severity finding. The example passes at **zero `specfuse-*` errors** on OpenAPI, AsyncAPI, and Arazzo.

Getting there required:
- **OpenAPI** — a redocly **bundle step** (linting the unbundled root produced ~22 `oas3-schema` artifacts; operation-level `$ref` is illegal until resolved). AsyncAPI and Arazzo need no bundling — Spectral resolves their `$ref`s directly.
- **9 example fixes** — `x-enum-case: PascalCase` on `Role`; `404` on four `{…Id}` ops; `x-sample` `value:`→`format:` on three fields; an extracted shared `common/schemas/PaginationLinks.yaml`; `validateOnly` on `place-order`; `updatedAt` on `OrderLine`; **moved root `tags` under `info.tags`** in `asyncapi.yaml` (root `tags` is invalid in AsyncAPI 3.0).
- **Rule fixes** in `specfuse-openapi.yaml` — `specfuse-no-inline-objects` and `-no-inline-enums` had a malformed `properties[*][?(…)]` JSONPath (one level too deep, mislabeled locations) and ran against the resolved doc, so any properly `$ref`'d enum/object was inlined-then-falsely-flagged. Fixed the path and set `resolved: false`. The near-duplicate `specfuse-no-embedded-objects` was **merged into** `specfuse-no-inline-objects` (deduped).

### Three handbook-referenced Spectral rules with no implementation

Surfaced during the schemas import (commits `78abc31`..`b146efa`) when verifying that every rule name mentioned in the handbooks resolves to a real Spectral rule in `schemas/spectral/`. The source project's Spectral ruleset never implemented these three — the handbooks reference them as if they exist, but the enforcement code was aspirational.

| Rule ID | Referenced in | What it should enforce |
|---|---|---|
| `specfuse-async-snapshot-version-coexistence` | `handbooks/Vendor_Extensions.md §12.2`, `handbooks/AsyncAPI_Handbook.md §2.3` | Deprecated event messages with a `replacedBy` pointing at a different version must `$ref` a versioned snapshot file (`*V{N}.yaml`); orphan versioned snapshot files with no deprecated referrer must be removed. |
| `specfuse-async-subscription-name-mismatch` | `handbooks/Vendor_Extensions.md §12.3`, `handbooks/AsyncAPI_Handbook.md §4.3` | `x-subscription.name` must equal the operation file stem (e.g., file `on-order-submitted.yaml` → name `on-order-submitted`). Free-form kebab-case naming is no longer permitted. |
| `specfuse-batch-operation-structure` | `handbooks/API_Handbook.md §16` (AI Integration Spectral rules) | Validates batch operation schemas (the `/{resources}:batch` POST pattern with `operations[]` array containing `oneOf` create/update/delete shapes). |

**Action:** author the three rules as new entries in `schemas/spectral/specfuse-{openapi,asyncapi}.yaml`. Two are AsyncAPI rules (snapshot-version-coexistence, subscription-name-mismatch); one is an OpenAPI rule (batch-operation-structure). Each will likely need a custom function under `schemas/spectral/functions/` since the logic involves cross-file resolution (snapshot $refs) or file-name vs declared-name comparison (operation file stem).

**Severity:** the handbooks make these promises today; until the rules ship, the promises are unenforced. New projects bootstrapped from the kit can violate these contracts and not know it. Worth landing before Phase 7 (smoke test of an imminent second project).

### `x-action-class` non-introduction

The handbooks document `x-action-class` as a "not introduced" extension whose semantics are inferred from the message-name suffix (`*Created`/`*Updated`/`*Deleted`/state-transition). The kit does not currently enforce that this extension is NOT used — a project author could declare `x-action-class: stateTransition` on a message and the kit's rules would silently allow it. (Note: `x-trigger-mode` is now an introduced, required extension on context-bearing transitions — see Vendor_Extensions §12.2 — and is no longer forbidden.)

**Action:** add a single rule (`specfuse-async-non-introduced-extensions-forbidden`) that flags any use of `x-action-class`, `x-pii`, `x-sensitive`, `x-deprecated`, `x-tags`, or `x-category` as a hard error pointing at the handbook section that explains why the extension isn't introduced. Pure structural check — no custom function needed.

**Severity:** low — the kit's authoring path (Claude Code agents from `/design-*` commands) doesn't generate these extensions, so the gap is theoretical for kit-conformant projects. Adding the rule closes the gap for projects that author by hand.

### `aiAccess` required-on-every-entity is generator-enforced, not yet kit Spectral

As of v0.3 the handbooks require `aiAccess` on every `x-entity` (Vendor §1.1.1), with empty `operations: []` + `reason` as the canonical Tier 0 form and absence raising `ENTITY_AIACCESS_MISSING`. Two of those checks are **generator/DDD-validator-side only** and have no kit Spectral rule yet:

- **`ENTITY_AIACCESS_MISSING`** — flag any `x-entity` with no `aiAccess` block (WARN).
- **`reason` required when `operations: []`** — the Tier 0 justification.

The kit's structural rule (`schemas/spectral/specfuse-openapi.yaml`) was updated to *accept* empty `operations` (removed the `minItems: 1`) so the canonical Tier 0 form does not fail lint, but it does not yet *require* the block or the empty-case `reason`.

**Action:** add a Spectral rule (custom function) that warns on `x-entity` without `aiAccess` and errors on empty `operations` lacking `reason`. Until then these are enforced only by the generator.

**Severity:** low for generator-driven projects (the generator catches both); matters for projects that lint with the kit ruleset alone.
