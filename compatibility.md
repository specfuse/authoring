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

| `v0.5.6` (incubating) | generator **`0.5.4`** (pin unchanged) | **Kit-only release — delivery. Nothing the kit shipped after `init` had any way of reaching an existing project.** **(1) `specfuse authoring upgrade <project>`** (with `--dry-run`), replacing the blind `refresh` (kept as a deprecated alias). Mirrors the scaffold overlay in `specfuse/loop`: a `.specfuse/authoring/VERSION` stamp that refuses a downgrade, a sha256 `.scaffold-manifest` ownership record, clobber warnings that distinguish a locally-modified kit file from a project-authored one, and a manifest-scoped prune that removes only what the kit provably wrote. Projects predating the overlay are adopted on first run (`kit unversioned -> …`). Project content — `api/`, `CLAUDE.md`, the project file, `.gitignore` — is seeded once at `init` and never touched again. **(2) The `scripts/` tooling the plugin skills invoke.** 23 script paths were referenced across the skills and **none existed in the kit** — `/preview` called `./scripts/specfuse/serve-docs.sh`, `/bundle` called `./scripts/specfuse/bundle-spec.sh`, and the design skills called validators that were never shipped. 17 scripts now ship and land at `<project>/scripts/`: nine validators, bundling, the two preview servers, and the docs generation. The Spectral validators lint against the rulesets the overlay delivers into `.specfuse/authoring/schemas/spectral/` rather than a project-local copy that drifts, and `generate-scenario-docs.sh` drives the generator through `specfuse authoring generate` instead of a bundled jar. **(3) Content the kit shipped but never delivered:** the Spectral `schemas` themselves (projects were told to lint against rulesets they never received), `ai-access-policy-template.md` (the README told users to copy a file that reached no project), and the two ideation backlog templates referenced by `ideation-capture`. `init` now writes the same overlay set as `upgrade` rather than keeping its own list — the drift between the two is how this content went undelivered. **(4) Two defects in the `project-init` template**, fixed in `examples/hello-orders/` when Spectral entered CI but not in the template it derives from, so every bootstrapped project began with five errors: `Role` enums lacked `x-enum-case: PascalCase`, and `asyncapi.yaml` carried a root `tags` key that is invalid in AsyncAPI 3.0. CI now lints a freshly scaffolded project with the scripts that project ships, closing the gap that let this survive. **Spec-author action:** run `specfuse authoring upgrade <project>` to receive the scripts, schemas and templates. Edits to shipped kit files do not survive an upgrade — the warning names them — so send improvements upstream. Existing projects should re-apply the two template fixes to their own `enums.yaml` and `asyncapi.yaml`, which `upgrade` does not touch because they are project content. `bundle-async-spec.sh` needs PyYAML (`pip install PyYAML`); every script reports what it is missing. |

| `v0.5.7` (incubating) | generator **`0.5.5`** — `Specfuse/generator-dist` release `v0.5.5`, asset `specfuse-generator-0.5.5.jar`, sha256 `e9b02532…c52d6` | **Generator re-pin + a missing script.** (1) **Re-pin to generator 0.5.5** (was 0.5.4). No kit-side contract change: no vendor extension, naming convention or validation rule moves in this bump, so no spec-author migration. The published release notes do not enumerate the generator-side changes, and the generator source tags were not available to diff — this row records the pin, not a changelog. (2) **`validate-generator.sh` shipped.** `validate-specs.sh` runs nine layers and the ninth calls `validate-generator.sh`, which the `0.5.6` script port missed — so the aggregate validator every project runs before a commit died on its last step. It drives the generator through `specfuse authoring validate-source` / `validate` rather than a bundled jar, discovers `<name>-project.json`, and follows the project's spec version. CI now asserts that every inter-script reference in `scripts/` resolves, which is the check that would have caught this: the `0.5.6` verification ran each validator individually but never the aggregate that composes them. **Spec-author action:** `specfuse authoring upgrade <project>` to receive the missing script. |

| `v0.5.8` (incubating) | generator **`0.5.5`** (pin unchanged) | **Kit-only release — the scaffolded project now passes generator validation (authoring #30).** Two defects, both from the same cause: nothing had ever run the generator against the template. **(1) The project file was a different shape than the generator accepts.** Of its top-level keys the generator recognised only `name` and `description`; `specs`, `bundle`, `Backend`, `Frontend`, `Workers` and `$schema` were all rejected, so `validate` and `generate` failed on the project file of every bootstrapped project. `handbooks/Project_File.md` documented the correct shape all along — the template and `examples/hello-orders/` diverged from it. Both now use `openApiSpecifications` / `asyncSpecifications` / `arazzoSpecifications` / `asyncSourceRoot` / `stateDir` / `groups`. The template ships `groups: []` rather than the previous `"language": "TODO"` placeholders, which fail validation outright (`Language 'TODO' is not registered in the LanguageRegistry`); fill it in from `Project_File.md` §14. **(2) The 412 response carried an inline schema**, which the generator rejects (`INLINE_RESPONSE_SCHEMA`) because an unnamed response shape cannot become a typed DTO. Extracted to a named `PreconditionFailedBody` in both the template and the example. A freshly scaffolded project now validates at **0 generator errors**. **Spec-author action:** `specfuse authoring upgrade <project>` does **not** fix this — the project file and `common/responses/` are project content, not kit-owned. Existing projects must re-apply both changes by hand; see the `0.5.8` template as the reference. |

| `v0.5.9` (incubating) | generator **`0.5.5`** (pin unchanged) | **Kit-only release — four consumer-reported defects, all found by pointing a tool at something it had never been pointed at.** **(1) `examples/hello-orders/` had six generator errors (#33).** `Customer` and `Order` declared `belongsTo: [Tenant]` and every route is scoped by `/v1/tenants/{tenantId}`, but no schema carried `x-entity` for it — the example demonstrated multi-tenancy with the tenancy root absent. Added as an aggregate with no `belongsTo`, a `tenant` domain, and a Tier 0 `aiAccess` block. Two required state-machine enums also had no default (`CustomerStatus` → `active`, `OrderStatus` → `draft`). **(2) `Vendor_Extensions.md` §4.6 was wrong about `x-default`** — it advised preferring the standard `default`, but on an enum the generator errors (`ENUM_MISSING_X_DEFAULT`) unless **both** are present with the same value. Following the handbook produced an error. Corrected, with `REQUIRED_ENUM_MISSING_DEFAULT` and the note that the default belongs on the enum schema, not beside the `$ref` (OpenAPI 3.0 drops `$ref` siblings). **(3) `validate-openapi-generator.sh` fed `asyncapi.yaml` to openapi-generator (#38).** It globbed `*.yaml` at the spec root, where the documented layout puts both roots — so the layer could never pass in any project with async specs, and `validate-specs.sh` aggregates it. OpenAPI documents are now identified by a top-level `openapi:` key. Also fixes an unparenthesised `-o` that let `-maxdepth 1` apply to only the first term. **(4) `specfuse-xentity-shape` rejected three documented keys (#36)** — `valueObjects`, `cascadeDelete` and `children`, so any spec following the handbook failed lint at error severity. The generator read a key its own linter rejected. The closed allow-list stays: it is what turns a typo into an error, and the fixture asserts both directions. **(5) Snapshot guardrails did not exist (#37).** `AsyncAPI_Handbook.md` §2.3 described three as Spectral-enforced; none were implemented, and `x-classification` appeared in no ruleset at all. New `specfuse-async-snapshot-guardrails` enforces the size limit and the shape and honesty of both overrides — a bare list, a justification under 20 characters, or an acknowledgement naming a property the snapshot lacks are all rejected. The two checks that compare a snapshot to its source entity stay generator-side (follow-up #15); the entity is in the OpenAPI document. **Spec-author action:** `specfuse authoring upgrade <project>` for the script fix; pair every enum `default` with a matching `x-default`. Nothing else changes meaning. Note the snapshot privacy gate is still only partly automatic — a classified field with no acknowledgement at all passes kit lint. |
| `v0.6.0` (incubating) | generator **`0.5.5`** (pin unchanged) | **Kit release — a new vendor key, and the kit moves onto the suite's single command.** *Minor, not patch: this release adds to the contract vocabulary (`x-entity.delete`) rather than only fixing what 0.5 shipped, and changes the documented command surface.* The Specfuse suite is now driven through one `specfuse` command, and this kit is `specfuse authoring …` (umbrella `0.11.0`). The umbrella hard-depends on every component, so `pipx install specfuse` / `uv tool install specfuse` brings the kit with no extras and no `--include-deps`, and `pipx upgrade specfuse` re-resolves it — an umbrella floor bump is no longer what delivers a kit release. **(1) Every command reference migrated** across the README, `docs/`, the `generate` skill, the `project-init` template and the scripts the kit ships: `specfuse-authoring <verb>` is now `specfuse authoring <verb>`. **(2) `--help` and `--version` print the name actually invoked** — `specfuse authoring` under the umbrella (and for `python -m`), the flat name when the deprecated script is called directly. **(3) The scaffolded `validate-generator.sh` and `generate-scenario-docs.sh` resolve the CLI at run time**: `specfuse authoring` when the suite CLI is installed, the flat `specfuse-authoring` otherwise, with `SPECFUSE_AUTHORING` overriding both. **Spec-author action:** none required — the flat `specfuse-authoring` command keeps working as a deprecated alias until `1.0.0`, when it is removed in a coordinated release train across all three components. Run `specfuse authoring upgrade <project>` to pick up the migrated scripts and `CLAUDE.md` wording; install the suite with `pipx install specfuse` rather than the standalone package, and do not run both installs (they provide the same flat command name and fight over it — `specfuse doctor` reports which one owns it).**(4) New vendor key `x-entity.delete`** (generator FEAT-2026-0080 gate 1). Shorthand `hard` | `soft`, or `{ mode, retention }` with `retention` = `none` or an ISO-8601 duration; absent resolves to `hard`, the pre-FEAT-2026-0080 generator behaviour, so no existing entity changes meaning. It replaces an inference — the generator's delete template branched on whether a linked AsyncAPI message carried `x-trigger-when`, letting an operation description promise retention while the service destroyed the row. The kit enforces the closed value sets, the long-form sub-keys and the retention format (`specfuse-xentity-shape`, fixtures in both directions); the eight coherence rules are generator-side and validation-only in gate 1. `API_Handbook.md` no longer states soft delete as a fact — it is a convention that `delete: soft` makes true of an entity — and its examples filter on `deletedAt` rather than a `status: deleted` member. **Spec-author action for this part:** audit DELETE operations against the generator's `DELETE_SEMANTICS_UNDECLARED` warning; an entity documented as soft-deleting with no declaration is hard-deleting today. See follow-up §16 for the two gaps gate 1 leaves open.**(5) A drift guard for the closed extension guards.** `check-extension-vocabulary.py` (shipped into `scripts/`, wired into `validate-spectral.sh`) compares every Spectral rule that closes a vendor extension with `additionalProperties: false` against the key constants in the pinned generator jar, and fails when the generator knows a key the ruleset rejects — the direction that blocks adoption. One-way by design: keys a ruleset accepts but the jar never mentions are informational, since the generator reaches some keys through indirect constants. With no cached jar it skips loudly and exits 0; CI passes `--require-jar`. Guards are discovered structurally, so `x-entity`, `x-value-object`, the async and Arazzo rulesets and any project-local `<token>-*-shape` rule are all covered without a list to maintain. See follow-up §17. |

| `v0.7.0` (incubating) — **⚠ SUPERSEDED, upgrade to `0.7.1`** | generator **`0.5.6`** — `Specfuse/generator-dist` release `v0.5.6`, asset `specfuse-generator-0.5.6.jar`, sha256 `19bd5268…5dbec` | **⚠ This release documented and linted an `x-entity.concurrency` contract its own pinned generator rejects.** Published to PyPI in that state; `0.7.1` fixes it by re-pinning to generator 0.5.7, where every form described below is valid. **On 0.5.6 the only accepted value is the bare scalar `optimistic`** — `none` is reserved and the object form is compared as a string, so both fail `validate` at ERROR (`ENTITY_CONCURRENCY_INVALID`), and omitting the key is that generator's documented opt-out. Everything in items (2), (3) and the spec-author action below describes FEAT-2026-0088, which 0.5.6 does not ship. `concurrency: optimistic` is the one form valid on both generators and needs no rework. The rest of this row is left as written, because it is the record of what shipped. **Kit release — `x-entity.concurrency` enters the kit's vocabulary** (authoring #47, generator FEAT-2026-0078 / FEAT-2026-0088). *Minor, not patch: it adds to the contract vocabulary.* **(1) The key was missing from `specfuse-xentity-shape` entirely**, and that guard is `additionalProperties: false` — so **every** authored form failed lint at error severity, not only the scalar shorthand a consumer report described. The hand-patch that unblocked FEAT-2026-0078 rollout (recorded in follow-up §17) was applied in a consumer's ruleset, never upstream, so the kit still rejected the key it had documented the drift lesson about. **(2) The key is now accepted and shape-checked.** `optimistic` \| `none` as a scalar, or `{ mode, reason }`. **Required with no default** — absent means *undeclared*, a third state the generator's census counts separately from a declared `none`, so no `default:` is set in the guard. `reason` is left an open string deliberately: the vocabulary is generator-owned and not frozen until FEAT-2026-0091, and closing a set the kit does not own is precisely how `domain`, `concurrency` and `delete` each blocked their own adoption. **(3) Both `none` forms pass lint, and a new WARNING asks for the justification.** `specfuse-xentity-concurrency-unprotected-needs-reason` fires on the bare `concurrency: none` and on `{ mode: none }` with no `reason`. Rejecting the scalar outright was the alternative and was declined: the generator accepts it, and a closed guard that rejects what generates fine blocks the adoption rather than the bad spec. The warning fires unconditionally, including on entities with no unsafe write — the write surface is not visible from inside the `x-entity` block, and the precise "`none` **and** an unsafe write" check is generator-side. **(4) Handbook framing corrected.** `API_Handbook.md` §"Concurrency Control" scoped ETags to *"safe autonomous operations by AI agents"*; an approval workflow where an employee cancels a request while a manager approves it is two writers with no AI anywhere. Treating the AI-reachable set as the answer under-protects everything else, so the handbook now frames it as a floor. `Vendor_Extensions.md` §1.1 documents the key, the recommended `reason` vocabulary including `not-assessed`, and why `mutability` cannot supply it. **Spec-author action:** declare `concurrency` on every entity. Start from the AI-writable set, then add approval workflows, shared rosters and anything else reachable by two callers. Where the analysis has not been done, declare `{ mode: none, reason: not-assessed }` rather than claiming a justification that is not true — it is the honest state and it is queryable; it is also the value expected to be refused when the key hardens to ERROR. See follow-up §18. | **(6) Generator re-pin 0.5.5 -> 0.5.6, and it is NOT a silent bump.** **⚠ Two validation rules ship at ERROR that did not exist in 0.5.5**, so a spec that validated clean against 0.5.5 can fail against 0.5.6. `PROJECTION_STRICTER_THAN_SOURCE` (generator #973/#976) — a `Basic{Resource}` read projection requiring a property the source schema leaves optional; unsatisfiable, because a record of the source may omit it and the response then violates its own schema. `VALUE_OBJECT_AUDIT_NAMED_PROPERTY` (#969/#976) — a value object declaring a date-time `createdAt`/`updatedAt`, which the generator silently drops from every generated type in all four languages. Both were promoted from WARNING at the restomanager-specs owner's request; measured on that repo the flip moved 7 findings from warning to error. **Spec-author action:** run `validate` before adopting — fix any `Basic*` that tightens `required` relative to its source, and rename an audit-named value-object property. **⊕ Also in 0.5.6, no action required:** `x-entity.concurrency` is now enforced at ERROR for a misspelled sub-key or an out-of-set value, which is the runtime half of what (1)–(3) above define — note this is **not** FEAT-2026-0088, which would make the key *required* and is still unshipped, so an absent `concurrency` remains legal. A sub-resource DELETE no longer resolves to its path parent (#978, closes #974), removing false-positive `DELETE_SEMANTICS_*` findings on action-style and composite-key deletes. Plus the TypeScript surface: generated output now type-checks clean on a real bundle (#955), carries no unused imports (#963) or escaped quotes in JSDoc (#965), and repository fakes serve paginated list envelopes instead of throwing (#968).
| `v0.7.1` (incubating) | generator **`0.5.7`** — `Specfuse/generator-dist` release `v0.5.7`, asset `specfuse-generator-0.5.7.jar`, sha256 `77d41956…0fc33` | **Kit patch — the `reason` vocabulary closes, and the kit follows the jar.** *Patch, not minor: it adds no key. It tightens a value set the kit had deliberately left open pending the generator, and adds the one sub-key that set requires.* **(1) `reason` is now a closed set** — `append-only`, `single-writer`, `reference-data`, `rare-write`, `not-assessed`, `other`. v0.7.0 left it an open string on purpose, with a note to tighten it when the jar shipped the vocabulary; generator 0.5.7 (FEAT-2026-0088/T07) ships it, so this is that tightening. Free text is `INVALID_EXTENSION_VALUE` at parse time now, so an open guard would pass lint and fail generation — the failure direction that costs an author a whole edit cycle to diagnose. **(2) New sub-key `reasonText`, and it rides with `other` alone.** Both directions are errors: `other` without `reasonText`, and `reasonText` alongside any other member. The guard mirrors the generator's cross-field check exactly via `if/then`. **(3) One shape the guard deliberately still accepts:** `reasonText` with no `reason` at all. The generator's check is `reason != null && reason != OTHER`, so it accepts that too — and a guard must never reject what the generator accepts. Reported upstream; tighten here once the jar does. **(4) Fixtures in both directions**, pinned in CI: `ConcurrencyOtherWithText` lints clean; `ConcurrencyFreeTextReason`, `ConcurrencyOtherNoText` and `ConcurrencyTextWithoutOther` are flagged. **Spec-author action:** if you declared `concurrency` with a prose `reason` against 0.5.6, move it to a member — or to `reason: other` with the prose in `reasonText`. Nothing in the RestoManager bundle had adopted the key when 0.5.7 shipped, so the measured blast radius there was zero. **⊕ Also in 0.5.7, and it is the headline:** `x-entity.concurrency` becomes **required with no default** (FEAT-2026-0088). Absent is *undeclared*, a third state distinct from a declared `none`. It ships at **WARNING** — `ENTITY_CONCURRENCY_UNDECLARED` on every `x-entity` with no `concurrency` key (86 warnings on that bundle, zero errors), plus `ENTITY_CONCURRENCY_REASON_REQUIRED` on a bare `mode: none` that still exposes an unsafe write, and a `ENTITY_CONCURRENCY_CENSUS` SUGGESTION counting `optimistic`/`none`/undeclared in one `validate` run. Also new: `ENTITY_CONCURRENCY_WRITER_ROLE_UNREADABLE` (WARNING) where an entity's unsafe-write roles are not a subset of the roles that can read it — a caller that may write but can never read the `ETag` its `If-Match` must echo. The ERROR promotion is **not** in 0.5.7; it is generator FEAT-2026-0092, gated on the adoption sweep reaching zero `not-assessed`. |
| `v0.8.0` (incubating) | generator **`0.5.8`** — `Specfuse/generator-dist` release `v0.5.8`, asset `specfuse-generator-0.5.8.jar`, sha256 `517795ce…97c97` | **Kit release — the generator publishes its own vocabulary, and the drift guard finally has an authority to check against.** *Minor, not patch: it documents a new extension (`x-legacy-names`) and a new language target, both additions to the contract surface.* **⚠ Not a silent pin bump — four new rule families arrive, all at WARNING, none at ERROR.** Verified against `examples/hello-orders`: 0.5.7 gave 2 ERROR / 24 WARNING / 3 SUGGESTION; 0.5.8 gives 2 ERROR / 27 WARNING / 4 SUGGESTION, with the two errors identical and pre-existing. Nothing that validated clean against 0.5.7 fails against 0.5.8. **(1) `extensions --format json` (generator FEAT-2026-0098) prints the parser's own `x-entity` key set**, so `check-extension-vocabulary.py` now asks the jar instead of parsing its constant pool. Authority is per surface: the subcommand covers `x-entity` today and says nothing about `x-sample`, `x-value-object` or `x-ai.entities`, which keep the heuristic scan — treating an unpublished surface as an empty vocabulary would report every key the ruleset allows as drift. **(2) The guard no longer passes vacuously.** Ruleset discovery targeted a provisioned project's layout and matched nothing in the kit repo, so the maintainer-facing invocation in `bump-generator-pin` exited 0 having examined nothing. It now also discovers `schemas/spectral/`, accepts `--ruleset`, and under `--require-jar` treats "found nothing to check" as exit 2. This is how `x-entity.schema` reached an ERROR-severity rejection unnoticed (follow-up 23). **(3) The reverse direction is now reportable.** With an authoritative source, keys the ruleset accepts and the parser does not know are real: `cascadeDelete`, `children`, `requiresPagination`. `ENTITY_SHAPE_UNKNOWN_PROPERTY` (new, WARNING, once per schema+key) reports each as *"dropped silently and has no effect on generated output"* — so a consumer declaring `mutability` across 47 entities gets 47 warnings on this bump. `mutability` is declared kit-only in the new `vocabulary-exceptions.yaml`: the kit's own lint reads it (`specfuse-main-resource-has-updatedAt`, `specfuse-xentity-mutability-exemption`), so the generator's message is right about codegen and wrong about the key's purpose. The other three are unresolved and tracked in follow-up 23. **(4) New extension `x-legacy-names`** (`Vendor_Extensions.md` §2.2) — former names of a value-object property, so JSON written before a rename still deserialises. Read order is current key, each legacy name in order, then the type default; `LEGACY_NAME_COLLIDES` and `LEGACY_NAME_REDUNDANT` validate it. No closed guard rejects it (it is property-level, not inside `x-value-object`), so it was adoptable before being documented — documented now so it is discoverable. **(5) New language target `typescript`** with 20 artifacts including Vue-style query/mutation composables (`Project_File.md` §8.3, §11.4). **(6) The bundled example stops advertising protection it did not have.** All four entities now declare `concurrency`, clearing 4 `ENTITY_CONCURRENCY_UNDECLARED`; `Order` and `Customer` are `optimistic` (both expose a PATCH that already required `If-Match`), `OrderLine` is `{ none, single-writer }` (aggregate-internal, written only through the gated parent), `Tenant` is `{ none, reference-data }`. `placeOrder` drops its `If-Match` and `412`: it is an action-style POST delegating to a consumer-owned service, so no generated write call site exists for a gate — the new `CONCURRENCY_PRECONDITION_UNENFORCEABLE` names exactly that, and opting the entity in does not change it. **Spec-author action:** none required. Expect new warnings if you declare `cascadeDelete`, `children`, `requiresPagination`, or `mutability`; expect `CONCURRENCY_PRECONDITION_UNENFORCED` wherever an operation requires `If-Match` on an entity that never declared `concurrency: optimistic` — that finding is telling you the client is sending a validator nothing checks. **⊕ Also in 0.5.8, no kit action:** `PROJECTION_NARROWS_NULLABILITY` (a `Basic*` projection declaring a property non-nullable where its source allows null — the nullability sibling of `PROJECTION_STRICTER_THAN_SOURCE` from 0.5.6) and `OPERATION_TARGET_UNRESOLVABLE` (`x-operation.target` naming an unregistered entity). **None of the four forwarded follow-ups shipped** — verified by byte-comparing classes against 0.5.7, not by reading notes: `#1027` (`emit-*` coverage), `#1028` (`x-expand-of` twin asymmetry) and `#1047` (`readOnly` persistence default) are all unchanged, and `ENTITY_CONCURRENCY_UNDECLARED` is still WARNING, so FEAT-2026-0092 has not landed. Follow-ups 19, 20 and 22 stand as written, and `API_Handbook.md` §1.9 row four correctly still reads as intent rather than behaviour. |
| `v0.9.0` (incubating) | generator **`0.5.8`** — unchanged; `Specfuse/generator-dist` release `v0.5.8`, asset `specfuse-generator-0.5.8.jar`, sha256 `517795ce…97c97` | **Kit release — the ruleset stops trusting the handbooks and starts checking them.** *Minor, not patch: it documents a new extension surface (`info.x-services`, `holds`, `Read{Entity}`) and it renames every `x-scopes` value, which is breaking for any project that declares them.* **No pin change** — the generator is still `0.5.8`. **(1) `info.x-services` documented ahead of the pin.** Service ownership, held replicas and `Read{Entity}`, plus `groups[].service`; the vocabulary ships in the generator release after `0.5.8`, so on this pin it is inert. The ahead-of-pin argument and the pin-bump checklist are follow-up 24 — read it before moving the pin. **(2) `x-scopes` regrammared** to `<domain>[.<Entity>].<operation>`, replacing a camelCase convention that rejected the kebab-case domains and PascalCase entity names the rest of the kit requires, and a second tag-keyed grammar in `API_Handbook.md`. Breaking and not mechanical — the old first segment was a tag, the new one is a domain (follow-up 28). **(3) `x-classification` value rules implemented** — the half `PiiClassificationValidationRule` explicitly delegates to Spectral and the kit had never picked up, plus two §1.5 corrections where following the handbook produced the wrong spec (follow-up 26). **(4) Three extensions found to be read by nothing** and marked as such rather than deleted: `x-ai-safe` (25), `x-content` and the whole `Project_File.md` §6 persistence block (27), `x-scopes` (28). The §6 banner matters most — that block fails *silently*, so a project configuring it has no way to learn it did nothing. **16 new Spectral rules** across four groups, each pinned in CI in both directions. |
| `v0.10.0` (incubating, current) | generator **`0.5.8`** — unchanged; `Specfuse/generator-dist` release `v0.5.8`, asset `specfuse-generator-0.5.8.jar`, sha256 `517795ce…97c97` | **Kit release — the kit stops claiming a directory it does not own, and a scaffolded project finally passes its own validator.** *Minor, not patch: kit tooling moves from `scripts/` to `scripts/specfuse/`, which is breaking for any project that invokes those paths from its own CI or docs.* **No pin change.** **(1) BREAKING — `scripts/` → `scripts/specfuse/`.** The kit shipped ~20 generically-named scripts (`validate-specs.sh`, `bundle-spec.sh`, `serve-docs.sh`) straight into the consumer's `scripts/`, and a project file colliding with one was overwritten on upgrade with only a stderr warning. Deletion was already manifest-scoped and safe; **writes were not**. Ownership is now structural: `OVERLAY` and `PRUNE_DIRS` are scoped to the subdirectory, so an upgrade cannot walk the project's `scripts/` at all — which also protects the shared substrate's `validate-event.py` / `validate-frontmatter.py`, which live there and the kit does not own. **`upgrade` migrates automatically**, deleting the old copies under the same rule prune uses (only what the manifest proves the kit wrote), so a project file that merely shares a name is never touched. **What the kit cannot fix for you:** your own references to `./scripts/<name>` in CI, Makefiles, docs or editor tasks. Re-point them at `./scripts/specfuse/<name>`; there is no shim. **(2) A scaffolded project failed its own `validate-specs.sh`.** Two anonymous `type: object` placeholders in `errors.yaml` (`Error.details`, `PreconditionFailedBody.currentResource`) were rejected by the generator's `ANONYMOUS_OBJECT_PLACEHOLDER`. Both are genuine open maps no `$ref` can name, now declared with `additionalProperties`; `API_Handbook.md` records them as the only sanctioned open maps and why they do not soften the event-payload ban. It hid because that check needs the private jar, so CI never ran it — a jar-free YAML shape guard now covers it. **(3) Ten `given` expressions normalised** from `$.paths[*].[verb,…]` to the bracket form, with a CI grep against reintroduction; a consumer reported the dotted form leaking outside `paths`, which did **not** reproduce here (follow-up 29). **(4) First consumer measurement of `info.x-services`** corrected our adoption guidance: quote `holds` pairs, not crossing edges — a five-service split cut pairs 99 → 36 but edges only 168 → 138. |

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

**Convention shift:** the former "`belongsTo` wins, `x-references` degrades to a hint" precedence is **removed**. `x-references` is association-only; declaring it against an *unbound* `belongsTo` for the same target is an error.

**Binder-awareness (correction, consumer-reported 2026-08-12).** The exclusion is per-FK, not per-target name. A `belongsTo <T>` is consumed by the property that satisfies it — a conventional `{t}Id` or an `x-fk-for: <T>` — and once consumed, a sibling property may carry `x-references: <T>` legally. `DDD_DUAL_RELATIONSHIP_DECLARATION` must therefore fire on an unclaimed `belongsTo`, not on the target name appearing twice on one entity. The generator implements this; the handbooks stated the blanket form until `Vendor_Extensions.md` §1.7 rule 2 was added.

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

### 18. `x-entity.concurrency` — **RESOLVED in generator 0.5.7 / kit `0.7.1`**

**Status:** delivered. The generator ships FEAT-2026-0078 (the key), FEAT-2026-0088 (required with no default, the `none` + `reason` object form, and the coherence rules) and the closed `reason` vocabulary, all as of **0.5.7**. The kit mirrors it exactly in `specfuse-xentity-shape` and documents it in `Vendor_Extensions.md` §1.1. What remains open is the ERROR promotion, tracked as **FEAT-2026-0092** below.

**What the vocabulary became.** The ask was a closed set that includes a `not-assessed` member, argued from a consumer census of 86 entities rather than an estimate: administrative reference data ~23, append-only ~4, owner-only ~2, and **~15 genuinely contended and simply not analysed yet**. That last group is a *status*, not a justification — a vocabulary of justifications cannot express it, and forcing it into `rare-write` or a free-text escape hatch manufactures exactly the false claims the vocabulary exists to make auditable. It shipped as asked: `append-only | single-writer | reference-data | rare-write | not-assessed | other`, with `other` carrying free text in a `reasonText` sub-key.

**A `0.7.0` erratum, recorded because the row above is what someone debugging a 0.5.6 pin will read.** Kit `0.7.0` was **published to PyPI** documenting and linting this key against FEAT-2026-0088 semantics while pinned to generator **0.5.6**, which ships none of them — there, `optimistic` is the only accepted value, `none` is reserved, and omission is the opt-out. The handbook and the lint agreed with each other and both disagreed with the pinned jar, so following the `0.7.0` handbook produced `ENTITY_CONCURRENCY_INVALID` at ERROR. `0.7.1` resolves it by re-pinning to 0.5.7; `concurrency: optimistic` is the one form valid on both and needs no rework.

**The guard gap that let it ship.** `check-extension-vocabulary.py` (§17) fails only when the generator knows a **key** the ruleset rejects. That one-way design is justified for keys, because the generator reaches some through indirect constants and the reverse direction produces false alarms. **It does not extend to values.** A ruleset that accepts a *value* the generator errors on is equally adoption-blocking and equally silent, and `0.7.0` carried exactly that while passing every check in this repo — including the pin-time gate during the 0.5.6 re-pin. Fixtures now pin the specific instance in both directions (`BareConcurrencyNone`, `ConcurrencyObjectForm`, `ConcurrencyTextNoReason`). A general value-level comparison against the jar is **unsolved** and is the thing worth building the next time §17's guard is touched.

**Still open:**

1. **FEAT-2026-0092 — the ERROR promotion.** `ENTITY_CONCURRENCY_UNDECLARED` ships at WARNING so that adopting the key across an existing project does not turn `validate` red mid-migration. Promotion is gated on the adoption sweep reaching zero `not-assessed`; `ENTITY_CONCURRENCY_CENSUS` is the metric. `not-assessed` is the member the promotion must refuse to pass.
2. **`reasonText` with no `reason` is accepted.** The generator throws only when `reason != null && reason != OTHER && reasonText != null`, so a `reasonText` with the `reason` member absent passes. The kit's guard accepts it too rather than tightening past the jar, pinned by `ConcurrencyTextNoReason`. Reported upstream; likely an oversight. Tighten both when the jar does.
3. **The kit's `specfuse-xentity-concurrency-unprotected-needs-reason` is now redundant** with the generator's `ENTITY_CONCURRENCY_REASON_REQUIRED` and fires more broadly — it does not condition on an unsafe write, because that surface is not visible from inside the `x-entity` block. A read-only entity declaring `{ mode: none }` therefore draws a kit warning `validate` does not issue. Documented in the handbook; worth deciding whether to keep or drop.

**Do not plan to derive it from `mutability`.** `appendOnly` looks like it could supply `reason: append-only` automatically. In the same census `mutability` was declared on 10 of 86 entities — an optional key with a permissive default is too sparse to source a required one.

**Severity:** additive as a vocabulary. As a *finding*, it is not: a spec with no `concurrency` anywhere is not a protected spec, it is an unmeasured one, and the entities most likely to be missed are the human-vs-human contended ones (approval workflows, shared rosters) that an AI-safety framing does not surface.

### 19. `emit-*` coverage is enforced for one producer kind out of three (`clabonte/generator#1027`)

**Status:** generator-side, filed by a consumer. The kit-side half is documentation only and is done (`AsyncAPI_Handbook.md` §6.3).

The cross-spec validator requires a matching `emit-*` send operation for every `x-emits` on an **`on-*` receive operation**, and requires nothing for the other two producer kinds. Measured on the reporting consumer's bundle: 273 `x-emits` declarations, 212 distinct events, 177 `emit-*` operations, **37 events published with no declaration** — 35 from OpenAPI write operations, 2 from `run-*` jobs, 0 from `on-*` workers. The `on-*` half holding perfectly is what makes the other half's absence easy to miss.

What keeps it quiet is that the 37 are not broken: each has a message file with a matching `x-label` and sits on the shared channel's `messages` map, so it is a fully wired event missing only its publishing declaration. Nothing fails. The consequence is a convention that splits with nothing pushing either way — in that consumer, one domain authors `emit-*` for REST-produced events and three do not, and both pass lint. "Does this event have an `emit-*`?" then answers *which domain wrote it*, not anything semantic, and the `emit-*` set stops being the index of what is on the bus.

**Generator action:** extend the existing check to every producer kind. If any operation declares `x-emits: X.Y` — OpenAPI write operation, `run-*`, or `on-*` — require an `emit-*` send operation whose message carries `x-label` `X.Y`.

**Ship it at WARNING, not ERROR.** At ERROR it fails a real consumer bundle 37 times on the day it lands. The same reasoning set `ENTITY_SHAPE_UNKNOWN_PROPERTY`'s initial severity (FEAT-2026-0098 / generator #1011) and worked there. Promote once consumers report clear.

**This belongs in the generator, not in kit tooling.** The rule spans two documents — `x-emits` in the OpenAPI document, `emit-*` in the AsyncAPI one — and Spectral lints one document at a time, so no rule in `specfuse-openapi.yaml` or `specfuse-asyncapi.yaml` can see both halves. The generator's cross-spec validator already holds both, and keeping it there respects the kit's position that it is a spec-authoring contract and not a CI product.

**The general form, which is the more valuable half:** every declared link between two spec documents needs a cross-document enforcement story. Where the generator does not provide one, each consumer invents a different workaround — the reporting consumer built a source-tree ratchet guard, and got the silence-failure bug in it on the first try. `x-emits` → `emit-*` is the instance in hand; it will not be the last.

### 20. `x-expand-of` twin check is asymmetric (`clabonte/generator#1028`) — kit side **FIXED**

**Status:** kit side fixed in `openapiProjectionCoherence.js`; the generator's `DDD_INVALID_EXPAND_OF` carries the same logic and the same message and still needs the matching change.

Both the kit function and the generator rule accepted a `format: uuid` FK twin **with no `required` check**, while demanding that a `type: string` natural-key twin be listed in `required`. The stated rationale — "a projection needs a dependable identifier to expand" — applies identically to both, and none was given for the split.

It rejects legitimate models. The reporting consumer has `ComplianceItem.authority` expanding `authorityCode`, an optional natural-key FK to an aggregate keyed by `code` rather than a uuid; the create DTO's `required` is `[kind, title]`, so an item with no authority is a supported state and making `authorityCode` required would assert a promise the create contract cannot keep.

The deeper tension settles the direction: a projection is `readOnly` and — by this same function's other check — **forbidden** from `required`, precisely because the server may decline to populate it. Requiring its *twin* to be `required` sits against that. So the fix drops the `required` condition rather than adding one to the uuid branch. Fixture `GoodMarkers` now carries an optional uuid twin and an optional string twin; `BadExpandOfTwin` still fires on a non-identifier twin.

**Consequence while the generator lags:** a consumer running both sees the kit accept what the generator rejects. `specfuse-projection-coherence` is otherwise adoptable — the reporting consumer held it back at ERROR for this single false positive.

### 21. `groups[].domains` is undocumented in `Project_File.md` — **RESOLVED, documented in §8.13.1**

**Status:** answered and written up. The generator confirms the key in `docs/ARCHITECTURE.md` § Per-Group Domain Filter (FEAT-2026-0053) — `include` / `exclude`, exactly one, each name validated against `info.x-domains` when that registry is non-empty and permissive when it is absent, applied once at the group model/event-selection layer and shared by C#, Dart, Python, async and Markdown. That is the confirmation the note below was waiting for, so the kit now documents it (`Project_File.md` §8.13.1) rather than inferring it, along with the `filter` interaction: they are unrelated mechanisms — `filter` is a predicate tree over AsyncAPI workers, `domains` is a scope over entities and every derived surface.

The `service` binding that shares the field's job arrived alongside it and is documented in §8.13.2; see follow-up 24 for its pin state.

**The original note, kept because it is the record of what was asked:**

A consumer runs six generation groups carrying:

```json
"domains": { "exclude": ["crm"] }
```

Neither `domains` nor `exclude` appears anywhere in `handbooks/Project_File.md` — not in §8's field list, not in any example. Every other top-level key of that consumer's project file is documented; this is the only gap, which suggests the doc is behind the generator rather than the key being invented.

**Generator action:** confirm whether `groups[].domains` (and its `exclude`, and any sibling `include`) is supported, and state its interaction with `filter` (§8.11), which today is documented as AsyncAPI-workers-only. If it is supported, the kit documents it in §8. If it is not, consumers depending on it need to hear so — silently-ignored config is the shape that fails at the worst time.

Do not document it kit-side on inference. Writing a spec for behaviour nobody has confirmed is how a handbook starts disagreeing with the jar.

### 22. `readOnly` + `required` + `default` emits no persistence default (`clabonte/generator#1047`)

**Status:** generator-side, filed by a consumer at severity `critical`. The kit documents the intended rule in `API_Handbook.md` §1.9 and marks that row explicitly as intent rather than behaviour until this lands.

A property that is `required` **and** `readOnly` **and** carries a `default` has exactly one consumer left for that default: the database. `readOnly` removes it from the `New{Resource}` DTO and from `aiAccess.writableProperties`, so no caller can supply it. No generated stack currently emits it — not EF `HasDefaultValue`, not SQLAlchemy `default=` / `server_default=`, not a C# property initializer. The column lands `NOT NULL` with no database default and nothing able to fill it.

Both failure modes were observed on one property (`status`, `required` + `readOnly: true` + `default: pending`):

- **Python** — `readOnly` correctly excludes the property from the writable whitelist, so the repository's create-field assertion rejects a caller that sets it, and omitting it violates `NOT NULL`. The create path cannot succeed at all. Loud, and therefore the cheap one.
- **C#** — the create path maps `New{Resource}` → entity; the DTO has no such member and the entity property has no initializer, so the column receives the CLR zero value. For an enum that is the synthetic `UNKNOWN = 0`, **which is not a literal of the declared OpenAPI enum**. The insert succeeds and the data is wrong. Silent, and it had been happening for as long as the endpoint existed.

**What makes this a generator bug rather than an authoring one:** a *writable* sibling with the identical `required` + `default` pair does receive its initializer. Adding `readOnly` silently loses it. The author changed nothing about the default.

**Generator action:** emit the `default` as a persistence default in every stack for any `readOnly` + `required` property that declares one. The precedent already exists — the generated base-entity infrastructure plus its pre-flush hook implement exactly this shape for `Id` / `CreatedAt` / `UpdatedAt`, values a caller cannot supply that are filled by infrastructure rather than by the whitelist. #1047 asks to generalise that.

**Adoption note for the kit:** whatever a persistence default emits must agree with whatever the enum converter writes on the same column. A consumer reported (unverified, statically read) that a generated enum converter overrides only the from-string direction, so the to-string path falls through to `TypeConverter` and writes the C# member name rather than the `[EnumMember]` wire value — `"Pending"` where the spec says `pending`. If true, fixing #1047 without fixing that produces a default that disagrees with every subsequent write. Worth confirming before or alongside.

**Blast radius is small and findable:** sweep for `readOnly: true` on a property that is also in `required` and carries a `default`. The reporting consumer found exactly two across their whole tree, both enums. The eleven other `readOnly` + `required` properties they found had no `default` and were `createdAt` / `updatedAt`, already handled by base-entity infrastructure.

**`RequiredEnumDefaultValidationRule` is confirmed present in generator `0.5.7`** — the version `generator.lock` pins — verified against the published jar (sha256 matches the pin). The consumer had only checked `0.5.8-SNAPSHOT` and asked the kit to confirm before citing it. It is safe to cite, and `Vendor_Extensions.md` §4.6 already documents its `REQUIRED_ENUM_MISSING_DEFAULT` and `ENUM_MISSING_X_DEFAULT` findings; §4.6 now also names `ENUM_PROPERTY_LEVEL_DEFAULT_IGNORED` and `ENUM_DEFAULT_MISMATCH`, which it described behaviourally but had not tied to their diagnostics.

**Do not add a kit rule flagging `required` + `default`.** It reads like a contradiction and is not — the consumer measured 66 correct instances across 43 schemas in one bundle. Such a rule was drafted downstream and withdrawn; see `clabonte/generator#982`.

### 23. `specfuse-xentity-shape` rejected `x-entity.schema`, which the generator still parses — **FIXED**

**Status:** kit side fixed. No generator action; `schema` is deprecated but supported, and its removal is already planned as a migration into the project file.

The shape guard allowed 16 sub-keys with `additionalProperties: false` at **error**, and `schema` was not among them. The generator parses it — `EntityDefinition` carries the field with a getter and setter and lists it in `KNOWN_SUB_KEYS`, verified against the published `0.5.7` jar, the version `generator.lock` pins. A consumer reported 17 live schemas failing lint on it.

The kit had already documented the key as deprecated in `Vendor_Extensions.md` §1.1 and `Project_File.md` §6.8, pointing at `persistence.entities.<Entity>.schema` as the replacement. **That replacement does not exist yet** — the generator parses no part of the `persistence` block (follow-up 27), so the migration this note recommended moves a working declaration onto a key nothing reads, and silently. `Vendor_Extensions.md` §1.1 now says to keep `x-entity.schema` where it is and treat the WARNING as a marker for a future move. The rest of this entry stands: the guard must still accept a form the generator accepts. Only the ruleset disagreed — and it disagreed in the direction that converts "deprecated" into "removed": an error-severity finding means migrate now or stop linting, which is not what the generator is saying.

**The fix is two halves, and both are load-bearing.** The shape guard now accepts `schema: { type: string }`, on the standing rule that a closed guard must never reject a form the generator accepts (the `concurrency: none` precedent, follow-up 18). A new WARNING, `specfuse-xentity-schema-deprecated`, carries the migration notice with the replacement path. Accepting without warning would let a deprecated key go silent and leave projects to discover the removal the hard way; warning without accepting is the bug being fixed. Both directions are pinned in CI via `DeprecatedSchemaKey`.

**This is the fourth instance of the same failure** — `domain`, `concurrency`, `delete`, now `schema` — where a generator sub-key ships and a hand-maintained allow-list has to gain a matching property before any spec can use it. Tracked generator-side as `clabonte/generator#959`.

**The drift also runs the other way, and that half is still open.** Diffing the pinned jar's `KNOWN_SUB_KEYS` (13) against the kit's allow-list (now 17) leaves four keys the kit advertises that the generator's `EntityDefinition` does not parse:

| Key | Evidence in the `0.5.7` jar |
|---|---|
| `cascadeDelete` | No occurrence anywhere in the jar |
| `requiresPagination` | No occurrence anywhere in the jar |
| `mutability` | Present only in `AiAccessValidationRule` and `ValueObjectValidationRule` — not as an `x-entity` sub-key |
| `children` | No `x-entity`-scoped use found |

This independently corroborates the consumer reports behind `clabonte/generator#815` (`mutability`) and `#1026` (`requiresPagination`): both are declared across their entity definitions and consumed by nothing. The kit documents all four, so authors are writing metadata that no generated code reads — intent that can silently stop being true. **Generator action:** for each, either parse it or tell the kit to retire it. Worth settling in the same window as a jar cut, since the answer changes what the handbooks should say.

**The durable fix for both directions** is the vocabulary check in follow-up 17 (see also follow-up 24, which found the published vocabulary does not cover `info`-level extensions at all). `check-extension-vocabulary.py` currently fails only when the generator knows a key the ruleset rejects — the direction that caught nothing here, because it reads the jar's class constants rather than the guard's allow-list. Generator FEAT-2026-0098 is reported to publish the vocabulary as `specfuse-generator extensions --format json`; that subcommand is **not** in `0.5.7` (checked). When it lands, point the guard at it and diff both directions.

### 24. `info.x-services`, `holds`, `Read{Entity}` — kit documents and lints ahead of the pin

**Status:** kit-side work **done** (`Vendor_Extensions.md` §14, `Project_File.md` §8.13.2, nine Spectral rules, `schemas/spectral/fixtures/service-topology.yaml`, a both-directions CI step). Generator-side the vocabulary is **not in the pinned jar** and ships in the release after `0.5.8`.

**The pin state, measured rather than assumed.** `java -jar ~/.specfuse/jars/specfuse-generator-0.5.8.jar extensions --format json` reports `x-entity` keys only — no `x-services`, and no `info`-level extension of any kind. The feature (generator `FEAT-2026-0102`, PRs `#1158` / `#1160` / `#1162`) is on generator `main` at `0.5.9-SNAPSHOT`. So on kit `0.8.0`'s pin the vocabulary is **inert**: declaring it changes nothing that is generated and produces no generator finding.

**Why the kit documents and lints it anyway, when `0.7.0` is the cautionary tale for exactly this** (follow-up 18). The two cases differ in direction, and the direction is what makes one dangerous:

| | `0.7.0` (`x-entity.concurrency`) | this |
|---|---|---|
| what the pinned jar did | **rejected** the value the handbook told you to write | has **no opinion** — the key is unread |
| result of following the handbook | `ENTITY_CONCURRENCY_INVALID` at ERROR, generation blocked | nothing; the key is inert |
| specs affected today | every spec adopting the key | none — no spec declares `info.x-services` or a `Read*` schema |

The pinned jar cannot contradict these rules because it does not read the surface they cover. That is the whole of the safety argument, and it stops holding the moment the pin moves — which is what the pin-time checklist below is for.

**Two upstream defects found while verifying this handoff.** Both were found by reading the jar's source against its own docs; report them with the next generator round-trip:

1. **`SERVICE_CROSS_BOUNDARY_REFERENCE`'s severity is stale in the generator's own docs** (`clabonte/generator#1197`). `docs/VENDOR-EXTENSIONS.md` states it twice as `WARNING`, and `docs/ARCHITECTURE.md` § Held entities says a declared hold "does not reduce its count". Both are wrong as of `#1158`: `ServiceBoundaryReferenceValidationRule` emits `ValidationIssue.error(...)` and returns early when `heldEntitiesOf(sourceOwner).contains(targetEntity)`, and `CHANGELOG.md` records the `WARNING → ERROR` promotion (`FEAT-2026-0102/T16`) and that "a declared hold still suppresses". **The vendor-extensions doc is the surface a consumer reads to decide whether adoption can turn `validate` red**, and it currently says it cannot. The kit documents the source's behaviour (`Vendor_Extensions.md` §14.9), not the doc's.
2. **`extensions --format json` does not publish `info`-level extensions** (`clabonte/generator#1196`). Verified against both `0.5.8` and `0.5.9-SNAPSHOT`: the output is a single `x-entity` array. This is the command follow-up 17's drift guard reads and the command a consumer is told to derive a ruleset from — so **`info.x-services`, `info.x-domains` and `info.x-roles` are invisible to both**, and `check-extension-vocabulary.py` cannot detect drift on any of them. The registries are precisely the surface where a closed guard is most adoption-blocking, because a project declares them once at the top of the bundle. **Generator action:** extend the published vocabulary to `info`-level registries, including each one's accepted shapes (`x-domains` takes a sequence *or* a mapping; `x-services` takes a mapping only).

**What the kit ships, and the severity contract it holds to.** Nine rules in `specfuse-openapi.yaml`, each mirroring a generator finding id at the same severity — the mapping is in `Vendor_Extensions.md` §14.9 and repeated as a comment on each rule so the next pin bump can diff it instead of re-deriving it. Sixteen further generator finding ids have **no** kit rule and are listed as such: each needs the AsyncAPI surface, the OpenAPI surface, or both loaded at once, which no single Spectral run has. Two custom functions (`openapiServiceRegistry.js`, `openapiReadModelShape.js`) both run `resolved: false` — the nested-entity and wire-type checks key on `$ref` **names**, which resolution erases, the same reason the generator's own rule scans raw YAML.

**At the next pin bump, before anything else:**

1. Re-run `extensions --format json` against the new jar and diff the `info`-level output (if defect 2 has been fixed) against `Vendor_Extensions.md` §14.2.
2. Re-check every severity in the §14.9 table against the jar's rule sources, **not** against its docs — defect 1 is the reason.
3. Confirm `SERVICE_CROSS_BOUNDARY_REFERENCE` is still ERROR and still suppressed by a declared hold. If either changed, §14.9's closing paragraph is the sentence that has to change with it.
4. Re-run the fixture step; a jar that starts validating this surface is the first opportunity to catch a kit rule that is stricter than the jar.
5. **Widen the `x-entity.delete` guard for `reason` / `reasonText`** (`clabonte/generator#1208`, reported by `restomanager-specs` — see follow-up 30). Deferred to the bump and not taken earlier because the **pinned `0.5.8` rejects the key outright**: `ENTITY_INVALID_CONFIG: Unknown x-entity.delete key: 'reason'`. Adding it while pinned to `0.5.8` is the `0.7.0` erratum verbatim. Verify against the *released* jar, not a SNAPSHOT, then land in the same PR as the pin:
   - `reason` as a closed enum `no-delete-surface | reordered-rows | patch-reconciled | other`, `reasonText: { type: string, minLength: 1 }`, and the `if/then/else` that requires `reasonText` **only** for `other` — mirroring `DELETE_REASON_TEXT_REQUIRED` in both directions, the same treatment `concurrency.reasonText` already gets in this ruleset. Confirm the member names against the jar rather than the handoff.
   - Add the five new diagnostics to `Vendor_Extensions.md` §1.1's `delete` table: `DELETE_REASON_MISSING`, `DELETE_REASON_INVALID`, `DELETE_REASON_REQUIRES_HARD`, `DELETE_REASON_TEXT_REQUIRED`, `DELETE_REASON_CONTRADICTED` — with severities read off the rule sources, per item 2 above.
   - **Do not adopt the reporter's two house rules**: they require `reason` on every `mode: hard` and restrict the string shorthand to `soft`. Correct for a soft-delete-only project, wrong for a kit where `delete` is optional and `hard` is the fallback. They filed the severity question as `clabonte/generator#1220`, which is where it belongs.
   - **Check `clabonte/generator#1219` has landed first.** `DELETE_REASON_CONTRADICTED` is reported to reject `patch-reconciled` on every entity following the PATCH-reconcile pattern, because it does not resolve the `Update{Child}` `items.$ref` indirection FEAT-2026-0066 mandates. Documenting a member no conforming spec can declare is worse than documenting none.

**What adoption costs a consumer, in kind rather than in counts.** All of it is spec-side; nothing waits on further generator work. A `Read{Entity}` per replication target; a `holds` entry per (service, target) pair; **`x-entity.delete` declared on every source entity**, which is the prerequisite for every replica rule and is commonly declared nowhere; a snapshot-carrying event surface for each held entity; and a tenant FK on each replica. Counts measured against one bundle at one moment do not transfer — re-derive them with `validate` against the current bundle and the intended topology.

**Severity:** additive in every direction. A project that declares neither `info.x-services` nor a `Read*` schema is unaffected by every rule here and by every generator finding id behind them, at any severity setting including `--strict`.

### 25. `x-ai-safe` is documented and read by nothing; `x-effects` is the consumer's replacement, deferred

**Status:** kit-side documentation **corrected** (`Vendor_Extensions.md` §4.1 and §9.2, `AI_Access_Policy_Framework.md`). `x-effects` itself is **not adopted** and should not be — see below. Generator action outstanding on `x-ai-safe`.

**`x-ai-safe` is unread.** Searched the generator source with controls in the same search: `x-public` appears in 3 files, `x-manual` in 3, `x-mcp` in 5; **`x-ai-safe` in 0**, as does any `aiSafe` identifier. No kit Spectral rule enforces it either. So an operation declaring `x-ai-safe: true` is gated by nothing while reading exactly like a safety control — the failure direction that matters, because the whole point of the key is to say an autonomous caller may proceed without a human. This is the follow-up 23 class (`cascadeDelete`, `requiresPagination`, `mutability`, `children`) with a sharper edge: those four produce metadata nobody reads, this one produces a *permission* nobody checks.

**Generator action:** parse it or tell the kit to retire it — filed as `clabonte/generator#1194`. The kit has marked it unread rather than deleting the section, because retiring an extension is the generator's call — but of the five keys now in this state, this is the one worth answering first.

**The live control for the same question is `x-mcp.safeForAutoInvoke`**, on an Arazzo scenario workflow (`Arazzo_Handbook.md` §4.8) — parsed into `McpConfig` and validated by `ArazzoValidator`, so it is enforced where `x-ai-safe` is not. It sits on the **workflow**, not the operation, which is the substantive difference and the reason the next item is a reconciliation rather than an addition.

#### `x-effects` — a consumer proposal, deliberately deferred

A consumer (`restomanager-specs`) has retired `x-ai-safe` locally and replaced it with **`x-effects`**, declaring an operation's real-world consequences: `reversibility` (`reversible` | `compensable` | `irreversible`), `compensatedBy` (an operationId, required iff `compensable`), `externalEffects` (a list, where `[]` is the explicit no-effects declaration on the `aiAccess` Tier 0 precedent), and `requiresConfirmation` (whose schema permits only `true`, so the unsafe value is unwritable). The canonical text is the consumer's own `RestoManager_Vendor_Extensions.md` §4.1 with rule specs in `RestoManager_MCP_Spec_Review.md` §7.1–§7.2; the summary here is a pointer, not a spec.

**Do not adopt it yet, and the deferral is the consumer's own.** Two reasons, one theirs and one found here:

1. **Theirs:** an unresolved scope decision — required on MCP-referenced write operations only, or on every write operation whose event reaches an external-effect worker. It changes one Spectral `given` and nothing else, but it changes what the extension *means*, so the kit should not take a position first. The work is also bound to MCP support work that has not started on their side.
2. **Found while verifying:** the handoff states the kit "has no `x-ai-safe` and nothing in the same role", and concludes adoption would be "additive rather than a reconciliation". **Both are wrong.** The kit documents `x-ai-safe` in `Vendor_Extensions.md` §4.1 with two cross-references, and `x-mcp.safeForAutoInvoke` occupies the same role and is *enforced*. Adopting `x-effects` therefore means answering **where the enforcement input lives** — the handoff's own stated rule is that enforcement inputs belong on the operation and presentation inputs in the tool manifest, and `x-mcp.safeForAutoInvoke` is an enforcement input sitting on an Arazzo workflow. That contradiction has to be settled before either side writes a rule, and it is not visible from the consumer's heading-similarity comparison.

**What is worth keeping from the proposal regardless of whether the extension lands**, because each is a design position the kit will need either way: `reversibility` classifies the *business* effect and not the database row (a soft-deleted row that already sent notifications is `irreversible`; for a `202` the classification is the eventual job, not the acknowledgement); `compensatedBy` asserts an inverse exists in the *system* and not that this caller may invoke it, so a consumer must re-run authorization and treat an uninvokable compensator as `irreversible` — escalation only, never the reverse; absence differs from `[]`; and `blastRadius` is deliberately absent because it derives from tenancy markers rather than being authored twice.

**Severity:** the `x-ai-safe` half is a live correctness problem in the handbooks and is fixed here. The `x-effects` half is a proposal with an open question on both sides and nothing to do until the consumer's MCP work starts.

### 26. `x-classification` — the kit picks up the half the generator delegated to it

**Status:** kit-side work **done** (`Vendor_Extensions.md` §1.5, four Spectral rules, `schemas/spectral/fixtures/classification.yaml`, a both-directions CI step). Three generator-side items below.

**The split, stated by the generator itself.** `PiiClassificationValidationRule` carries the comment: *"The classification value itself isn't validated here — that's a structural concern handled by Spectral. We only enforce presence."* So the jar owns presence (`PII_FIELD_MISSING_CLASSIFICATION`) and the response-leak guard (`SENSITIVE_FIELD_IN_RESPONSE`), and everything decidable from the property schema alone was Spectral's — a delegation the kit had never picked up. The result was that §1.5's rules 1, 5 and 6 were documented as validation and enforced by **nothing on either side**, with rule 5 naming a finding id (`CLASSIFICATION_EXPOSED_CONTRADICTION`) that exists in neither codebase.

That gap has an asymmetric cost. A missing lint rule leaves a spec ungated; a *documented* missing lint rule leaves a spec ungated that someone believes is gated — and on this surface the belief is "a human reviewed this secret-shaped field and confirmed it is safe to return".

**Three handbook corrections, all of them cases where following the kit produced the wrong spec:**

1. **`*Token` was documented as secret-shaped; the generator excludes it deliberately.** §1.5 listed the `SENSITIVE_FIELD_IN_RESPONSE` heuristic as `*Hash, *Token, *Secret, *Salt, *Password`. `SensitiveFieldInResponseValidationRule` matches `hash` / `secret` / `salt` / `password` only, and its javadoc says "NOT plain `*token`". The handbook's own worked example then recommended `x-classification: [exposed]` for "an already-public `shareToken`" — advice to write a reviewed override of a rule that never fires. Corrected, along with the two structural pre-filters the section omitted (a non-string property and a temporal one are never candidates).
2. **`PII_FIELD_MISSING_CLASSIFICATION` is an ERROR and the kit documented nothing about it.** §1.5 said `x-classification` was "**Optional**: Yes", which is wrong for any property matching `format: email` / `tel` or one of 19 exact property names. An author following the handbook hit a hard generation failure the handbook had told them could not happen. The trigger list is now documented in full, including *why* it is exact-match rather than substring.
3. **Rules 5 and 6 now have an implementation** rather than a finding id nobody emits.

**What the kit now enforces**, all `error`, all mirroring or completing a jar position rather than tightening past one:

| rule | covers |
|---|---|
| `specfuse-classification-values` | §1.5 rule 1 — closed set, non-empty, no duplicates. Not scoped to entities: a typo is a typo wherever it is written |
| `specfuse-classification-exposed-contradiction` | §1.5 rule 5 |
| `specfuse-classification-exposed-needs-description` | §1.5 rule 6 |
| `specfuse-classification-pii-required` | mirrors `PII_FIELD_MISSING_CLASSIFICATION` so the author sees it in the editor |

The PII trigger list in `openapiClassification.js` is **copied from the jar and annotated as such**. Widening it is the forbidden direction (lint fails on a spec that generates fine, follow-up 18); narrowing it silently drops coverage the jar has. Change it only in step with the jar — and note that the same value-level drift §18 called unsolved applies here, since nothing compares this list to the jar automatically.

**Generator-side, three items** — all three raised on `clabonte/generator#999`, which is rewriting this vocabulary (see the expiry note below) rather than as standalone issues:

1. **`x-classification: [exposed]` satisfies `PII_FIELD_MISSING_CLASSIFICATION`.** The presence check accepts any non-empty value, so `dateOfBirth: { x-classification: [exposed] }` passes a PII gate while asserting the field is safe to return as authored. That is the one combination the rule exists to prevent, expressed in the vocabulary the rule accepts. The kit does **not** close this — a kit rule stricter than the jar is the forbidden direction — but the jar should: `exposed` alone should not satisfy the PII requirement.
2. **`ExtensionConstants` documents the value set as `pii` / `sensitive` / `encrypted`, omitting `exposed`**, while `SensitiveFieldInResponseValidationRule` reads `exposed`. The jar's own constant is behind the jar's own rule. Harmless today; it is the sort of drift that decides an argument about the closed set later.
3. **§1.5 rule 2 — `encrypted` requires a string-representable property — is enforced nowhere**, and is not decidable from the kit side alone for a `$ref`'d value object. Left as guidance and labelled as such in the handbook rather than presented as a gate.

**Severity:** the rules are new gates on an existing vocabulary, so a spec that already classified correctly is unaffected — verified: `examples/hello-orders/` gains zero findings. A spec that has been declaring `[exposed]` without a description, or writing an unlisted value, will see new errors, and those are the specs the rules exist for.

#### ⏳ These rules have a known expiry — the generator is replacing this vocabulary

**Do not treat §26's ruleset as settled.** `clabonte/generator#999` (the `field-encryption` epic, design approved at rev 7) splits the single list into two orthogonal axes — `x-classification` for *what the data is*, a new `x-protection` for *how it is handled* — and changes the set this kit just closed a guard over. Filed and in flight as of 2026-08-20, **after** kit `0.9.0` shipped.

What lands when it does:

| kit surface | what breaks |
|---|---|
| `specfuse-classification-values` | the closed set gains `confidential`, `financial`, `credential`, `cardholder`, `sad` and **loses `encrypted`** (it becomes `x-protection.atRest: encrypted`). The kit's enum would reject five valid values and accept one removed one — **both** forbidden directions at once |
| `specfuse-classification-exposed-contradiction` | the contradiction set becomes `sensitive` / `confidential` / an encrypted-or-hashed `atRest` (`#1168`, which is this rule filed generator-side) |
| `specfuse-xentity-shape` | **`x-entity.encryptedProperties` is retired outright** — not recomputed, not kept as a derived view — while the guard still accepts it inside `additionalProperties: false` |
| `Vendor_Extensions.md` §1.5 | documents `encrypted` as a classification implying `sensitive`, and `encryptedProperties` as a derived view. Both cease to be true |

**The `encryptedProperties` row is the dangerous one**, and it is follow-up 17's failure in the other direction: a closed guard that keeps accepting a **removed** key lets a spec lint clean and generate wrong, where the historical cases (`domain`, `concurrency`, `delete`) rejected a **new** key and failed loudly. `#999` already names the consumer shape guard as needing a matching change, which is the first time that coupling has been flagged upstream before the fact rather than after.

**Do not build against it yet.** The vocabulary is not frozen, and authoring a ruleset against an unfrozen design is the `0.7.0` mistake (follow-up 18) with the roles reversed — the kit would be the one that moved first. The kit has asked on `#999` to be pinged when the set freezes so the ruleset, the shape guard and §1.5 land in one window rather than after the first spec trips over them.

**When it does freeze, the work is one PR** and its shape is already known: widen the value enum, retarget the contradiction rule, drop `encryptedProperties` from the shape guard (with a deprecation WARNING first, per the `x-entity.schema` precedent in follow-up 23), and rewrite §1.5 around the two axes. The fixture (`schemas/spectral/fixtures/classification.yaml`) and its both-directions CI step carry over unchanged in structure.

### 27. `Project_File.md` §6 Persistence and `x-content` document a subsystem the generator does not implement

**Status:** kit-side **banners added**, section kept. Generator-side the whole design is unstarted; this entry is the tracker.

**Measured, with controls.** Against the pinned `0.5.8` and against generator `main`: **zero** `PERSISTENCE_*` codes and no parsing of the `persistence` block anywhere in the Java source. The only two case-insensitive matches for "persistence" are unrelated comments (`StateStore`'s "state persistence", `Property`'s "JSON-column persistence"). `x-content` does not appear at any spelling — not the key, not a constant, not a derived accessor — and neither does `PERSISTENCE_HYBRID_NO_CONTENT`. Controls run in the same search: `tenancy` 29 files, `namingOverrides` 15, `broker` 11, `dbContextClassname` 9, `cleanScope` 9.

**Why this is worse than an unimplemented feature usually is.** The failure mode is **silence, not error**. A `persistence` block in `project.json` is read by nothing: it does not warn, it does not change the exit code, and generation proceeds exactly as if the block were absent. So the project that declares `managed: false` believing DDL emission is off, or `kind: document` believing it is not getting EF configurations, gets neither the behaviour nor a diagnostic. §6.3 even documents a load-time warning for unknown `connections.<name>` sub-keys — a safety net that does not exist, asserted in the section that most needs one.

This is the `0.7.0` erratum (follow-up 18) inverted. There the jar **rejected** a value the handbook told you to write, which at least fails loudly. Here the jar **ignores an entire surface**, which fails quietly and can be believed for a long time.

**What the kit did, and what it deliberately did not do.** Both sections keep every word — a designed and agreed subsystem is worth having written down, and deleting it loses the design rather than the risk. Each gained an availability banner stating the measurement, the silence, and that it is a design of record rather than a contract: `Project_File.md` §6 and `Vendor_Extensions.md` §1.6. The kit did **not** invent a Spectral rule flagging the block's presence — a project file is not a spec surface these rulesets lint, and a rule saying "you configured something that does nothing" is the generator's diagnostic to emit, not the kit's to fake.

**One correction that is independent of when §6 ships.** Follow-up 23 and `Vendor_Extensions.md` §1.1 both told authors to migrate the deprecated `x-entity.schema` **to** `persistence.entities.<Entity>.schema`. That is advice to move off a key the jar reads onto one it does not, with no diagnostic either side of the move. Reversed: keep `x-entity.schema`, treat `specfuse-xentity-schema-deprecated` as a marker for a future migration rather than a task, and migrate when the block is parsed. The deprecation direction is unchanged and still correct.

**Generator action:** tracked upstream as `clabonte/generator#480` (F-028 Multi-Backend Persistence), with `#481` WU-01 `PersistenceConfig` parsing and `#491` WU-11 `x-content`. Implement the block, or — if the design has moved on — say so, because the kit is currently carrying roughly 200 lines of handbook for it and a deprecation that points at it. Until one of those happens, a load-time **warning** naming an unread `persistence` block would convert the silent case into a visible one at a fraction of the cost of the subsystem, and is worth doing first regardless of the eventual timeline.

**Severity:** documentation-only in this repo; no rule changed and no lint result moved. As a *finding* it is not documentation-only — the projects most exposed are the ones that configured `persistence` carefully and have been trusting it.

### 28. `x-scopes` grammar rewritten to `<domain>[.Entity].<operation>`

**Status:** kit-side work **done** (`Vendor_Extensions.md` §3.2, `API_Handbook.md` §14 and §"Authorization", three Spectral rules replacing one, `schemas/spectral/fixtures/scope-grammar.yaml`, a both-directions CI step, `examples/hello-orders/` and `samples/endpoint-samples.yaml` migrated). One generator-side item.

**`x-scopes` is read by nothing.** Zero occurrences across the generator source, against controls in the same search finding `x-roles` in 8 files and `x-public` in 3. The kit's Spectral rules are the only enforcement this vocabulary has ever had, and a project enforcing scopes at runtime is doing it in hand-written middleware. Third unread extension found in this batch, after `x-ai-safe` (follow-up 25) and `x-content` (follow-up 27) — **generator action** (`clabonte/generator#1195`): parse `x-scopes`, or say it will not, so the kit knows whether it is documenting a contract or a convention.

That fact is also what makes this change cheap and safe to make: there is no jar position to reconcile against and no way to be stricter than a jar that has no opinion. Nothing generated changes, and no runtime behaviour moves.

**The grammar.** `<domain>[.<Entity>].<operation>`, where the domain is kebab-case and a member of `info.x-domains`, the optional entity is PascalCase and names an `x-entity` schema, and the operation is one of `read` / `write` / `delete` / `all`. Two segments grants at domain level, three at entity level.

**Three decisions worth recording, because each had a defensible alternative:**

1. **Segment count is normative; casing is a lint rule, not the parser's discriminator.** The mixed casing is genuinely useful — each segment announces which registry it came from — but some identity providers normalise scope case at introspection, and where that happens `order.Order.read` and `order.order.read` collapse into one string. Anything resolving on case would then resolve the collapsed form differently from the authored one. Counting segments survives it.
2. **`delete` is disjoint from `write`, not a subset.** That is the point of separating them: edit-without-delete is the split projects most often want, and a subset relationship makes it inexpressible. `all` therefore means `read` + `write` + `delete`.
3. **`admin.*` is removed.** The old convention documented `admin.{resource}.{action}`. A scope answers *what* and a principal prefix answers *who*; mixing them gives two half-answers to authorization with no precedence between them. "Who" is `x-roles`, which is generator-enforced and registry-validated. It also did not fit the positional parse.

**What this replaces, and why the old rule was wrong twice over.** `specfuse-auth-scopes-pattern` enforced `^[a-z][a-zA-Z0-9]*(\.[a-z][a-zA-Z0-9]*)*$` at `warn` — camelCase dotted segments. It **rejected the kebab-case a domain is required to use everywhere else in the kit**, and it **rejected the PascalCase an entity name is required to use everywhere else**. It also tied nothing to a registry, so a scope could name a domain that did not exist and lint clean indefinitely.

`API_Handbook.md` carried a **third** grammar in its authorization section: `{tag}.{read|write|delete}`, keyed on the endpoint's tag. Tags are many-to-one against domains — that is stated in `info.x-domains`'s own documentation, where `crm` maps to five tags — so a tag-keyed scope cannot be resolved back to an owning domain. Removed rather than updated.

**No project overlay is needed**, unlike `x-roles`. Both registries the grammar references (`info.x-domains`, `components.schemas`) live in the spec, so the kit enforces the whole contract on its own.

**Severity: breaking for any project that declares `x-scopes`.** Every value changes, and the migration is **not** mechanical: the old first segment was a tag and the new one is a domain, so `customers.read` does not say whether the domain is `customer` or `crm`. Rewrite against `info.x-domains`. The rules ship at `error` (shape, registry) and `warn` (`all` usage) rather than at `warn`-to-be-promoted — that path is where `ENTITY_CONCURRENCY_UNDECLARED` has been parked since `0.7.1` (follow-up 18). For an existing corpus, turn them on through `scripts/spectral-ratchet.py` so inherited violations do not block every PR during the sweep. Nothing breaks at generation time either way, because nothing reads the extension.

### 29. First consumer measurement of `info.x-services`, and a reported JSONPath leak that does not reproduce

**Status:** kit-side **done** (ten `given` expressions normalised, a ruleset self-check added, `Vendor_Extensions.md` §14.8 corrected with the measured figures). One item returned to the reporter unresolved.

Source: a `restomanager-specs` handoff dated 2026-08-20, measured against a generator built from `main` because the feature is not in the pinned `0.5.8`.

#### The JSONPath report — normalised, but the stated cause did not reproduce

Ten `given` expressions in `specfuse-openapi.yaml` used the dot-before-bracket union `$.paths[*].[verb,…]` while the other ~20 used `$.paths[*][verb,…]`. The reporter observed rules with the dotted form firing on nodes **outside** `paths` once they declared `x-entity.delete` across their bundle — verbatim, `rm-ifmatch-on-write` at `components.schemas.ExternalMapping.x-entity.delete` — with three rules moving 0 → 94, 0 → 94 and 8 → 102, returning to baseline after they rewrote the expressions.

**That leak does not reproduce against this ruleset.** Probed both spellings directly on Spectral **6.16.2** (the reporter's version) against a document carrying decoy `x-entity.delete`, `responses` and `x-emits` keys under `components.schemas`: **both forms match the identical node set**, confined to `paths`. Normalising all ten moved no count on `examples/hello-orders/` (24 problems, 0 errors, before and after) or on any of the nine fixtures.

So the finding is real in their tree and the stated root cause is not sufficient to explain it. The difference is most likely their ruleset copy rather than the form itself — their file is `rm-*`-prefixed with different line numbers, so it has diverged. **Returned to the reporter** for the exact rule text and a minimal document; their fix is correct for them either way.

**Normalised anyway**, on grounds that do not depend on the leak: the dotted form is inconsistent with every other rule in the file, rests on a jsonpath-plus behaviour no rule should depend on, and costs nothing to retire. Proven behaviour-preserving before landing.

**Their third recommendation is the one worth keeping** and is implemented: a lint-the-linter guard, because Spectral cannot lint its own ruleset. They flagged the weakness in their own fix — theirs is a convention in `CLAUDE.md`, so a new rule can reintroduce the form and nothing catches it. Ours is a grep in CI over all three rulesets.

#### The severity report — already filed

The handoff's companion item is `SERVICE_CROSS_BOUNDARY_REFERENCE` documented as WARNING while the source emits ERROR. Independently found and filed as `clabonte/generator#1197` before this handoff arrived; their reproduction (**138 ERROR findings, exit=1**, five-service overlay, via the `validate <project.json>` path) is stronger evidence than the source-reading in that issue and has been noted there. Their comment that they *"planned adoption sequencing off that table and had to re-plan"* is the cost this defect carries, and is why follow-up 24's checklist says to verify severities against rule sources rather than docs.

#### The measurement — the first from any consumer, and it corrects our guidance

The feature closed at `met_locally` with no consumer having declared `info.x-services`. This is the first real measurement, and one claim inherited from the original handoff **did not survive it**: *"a plausible five-service split more than halves it."*

| | one service per domain | five-service split | change |
|---|---|---|---|
| crossing references | 168 | 138 | **−18%** |
| `holds` pairs | 99 | 36 | **−64%** |
| `Read{Entity}` schemas | 29 | 22 | −24% |

Consolidating the concentrated targets does **not** remove crossings — `Company` (35), `Employee` (32), `Restaurant` (31) and `User` (29) account for 127 of 168 edges and are referenced from nearly every domain, so every *other* service still reaches them. What collapses is the number of distinct (service, entity) pairs to author, which is the actual work. §14.8 now says to quote `holds` pairs rather than edge count, with these figures.

The top-four ranking also **shifted between two measurements two days apart** (`Restaurant` led on 2026-08-15, `Company` on 2026-08-17), which is the concrete case behind §14.8's instruction to re-derive rather than inherit a ranking.

Snapshot readiness, for the hydration gate: 20 of the 22 held targets under their five-service split already publish `{Entity}Snapshot`; the exceptions are `EmployeeSchedulingPreferences` and `EmployeeTimeOffBank`.

**They are not adopting.** Recorded on their side as available-and-declined. So `info.x-services` still has **zero** adopters, and follow-up 24's "the benefit is not proven" stands — but its cost is now measured on a real bundle rather than a mechanical overlay.

### 30. `cascadeDelete` / `children` are phantom keys, and the cascade was documented inverted

**Status:** kit-side **done** (`API_Handbook.md` §"Cascade Deletion" rewritten, `Vendor_Extensions.md` §1.1 corrected, two WARN rules, fixture and CI). Generator action outstanding: retire the keys or implement them.

Reported by `restomanager-specs`, 2026-08-20. Follow-up 23 already recorded that neither key appears in the jar — **the failure was that the handbooks went on teaching them anyway.** Recording an unread key in the compatibility matrix does nothing for the author reading §"Cascade Deletion"; that is the lesson worth keeping from this one.

**Two defects, and the second is worse than the first.**

1. **The keys are read by nothing.** `cascadeDelete` and `children` are accepted by `specfuse-xentity-shape`, so a spec declaring them lints clean, validates clean, and cascades nothing. The contract says the children are archived with the parent; the runtime leaves them live; nothing disagrees. That is the exact failure `x-entity.delete` was introduced to fix.
2. **The described behaviour was inverted.** The section promised a cascade under `delete: soft` — the mode that does **not** cascade — and said nothing about `delete: hard`, which does. So an author following it got the wrong mental model even setting the phantom keys aside. What the generator does:

   | `delete` | own row | children |
   |---|---|---|
   | `hard` | deleted | **cascades** — `DeleteWithCascade` over the descendant set, FK-ordered; optional inbound `x-references` FK nulled first, required one refuses with `409` naming each blocking type and row count |
   | `soft` | `deletedAt` stamped | **no cascade.** Children stay live and individually addressable; they vanish only when reached *through* the archived parent's navigation |

**The keys stay accepted.** Two WARN rules (`specfuse-xentity-cascade-phantom`, `specfuse-xentity-children-phantom`) carry the notice, on the `x-entity.schema` precedent from follow-up 23: rejecting them would convert a silently-inert declaration into a lint error on specs that generate exactly as they do today — the forbidden direction — for a key the generator has not said it is dropping. Accepting *without* warning is how a phantom key stays invisible; warning without accepting is the bug that would replace it. CI pins all three properties: both rules fire, the shape guard still accepts, and neither rule touches an entity declaring neither key.

**Generator action:** parse them or tell the kit to retire them. This is the fifth key in that state (`x-ai-safe` §25, `x-content` §27, `x-scopes` §28, plus `requiresPagination` / `mutability` from §23) and the only one whose absence silently changes data-lifecycle behaviour rather than just wasting metadata.

**Not adopted from the same handoff: `delete.reason`** — see follow-up 24's pin-bump checklist. It is shipped generator-side per `clabonte/generator#1208` and the reporter asks the kit to widen its guard for it. **Measured against the pinned jar first, and the answer is no, not yet:**

```
$ java -jar specfuse-generator-0.5.8.jar validate <bundle-with-delete.reason>
[ERROR] ENTITY_INVALID_CONFIG: Invalid x-entity configuration: Unknown x-entity.delete key: 'reason'
```

`0.5.8` **rejects** it. Widening the guard now would ship a ruleset accepting a value the pinned jar errors on — the `0.7.0` erratum verbatim (follow-up 18: *"a ruleset that accepts a value the generator errors on is equally adoption-blocking and equally silent"*). The reporter's framing that "the kit is the thing preventing adoption" is right about the guard and wrong about the cause: **the pin is the blocker**, and they are running a `0.5.9-SNAPSHOT` build, which is why it works for them. The guard change belongs in the same PR as the pin bump.

### 31. Thirteen rules — eleven at `error` — had never fired, and a clean run could not tell you

**Status:** kit-side **done** (11 OpenAPI `given`s and 1 AsyncAPI `given` repaired, 5 resolution/`then` defects fixed, coverage harness + rejection fixture wired into CI). No generator action.

Reported by `restomanager-specs`, 2026-08-21 (authoring #73) against kit `0.5.9`. The report named two rules. Thirteen had never fired: twelve had a `given` of the shape below, and a thirteenth was dead for the resolution reason recorded further down.

**The defect.** A JSONPath filter selects among the node's **children**. These rules put the filter *after* the method union had already selected the operation:

```yaml
given: $.paths[*][get,post,put,patch,delete][?(@ && @.security)]
```

so the filter asked which of `summary` / `parameters` / `responses` / `x-scopes` is itself an object with a truthy `.security`. None is. The empty set, in every valid OpenAPI document, since the rules were written.

**Why no amount of green CI surfaced it.** These rules emit output only when metadata is missing or malformed. A conformant spec produces silence; so does a rule that matches nothing. **A clean run and a no-op run are indistinguishable** — the same shape as the crash-reads-as-pass problem `scripts/spectral-lint.sh` exists for, one level further in.

**What was actually inert.** All thirteen. Every row but the last two is `severity: error`; the reporter's report covered `specfuse-auth-meta-present` and a scopes rule since replaced:

| Rule | Severity |
|---|---|
| `specfuse-401-required`, `specfuse-401-predefined` | error |
| `specfuse-403-required`, `specfuse-403-predefined` | error |
| `specfuse-400-required`, `specfuse-400-predefined` | error |
| `specfuse-404-predefined` | error |
| `specfuse-list-response-requires-pagination-params` | error |
| `specfuse-auth-meta-present`, `specfuse-auth-roles-pascal` | error |
| `specfuse-async-ai-must-have-entities` (AsyncAPI, same shape) | error |
| `specfuse-415-when-request-body`, `specfuse-406-when-alt-accept` | warn |

So the RFC 9457 error-envelope contract — 400/401/403/404 must be present *and* must use the kit's predefined components — was unenforced on every project extending this ruleset, alongside the authorization-metadata gate the report opened with.

**Repairing the JSONPath was not sufficient.** Three rules stayed silent with a working `given`:

1. `function: pattern` reports **nothing when the field is absent**, so the four `-predefined` rules passed any response declaring no `$ref` at all — an inline response bypassing the shared component was clean. Each now pairs `truthy` with the pattern.
2. The same four ran on the **resolved** document, where the `$ref` they inspect has already been inlined. They now carry `resolved: false`.
3. `specfuse-list-response-requires-pagination-params` keys off a response schema whose `$ref` **name** ends in `List` — also erased by resolution. It now runs unresolved, and its parameter check accepts both the inline (`name: page`) and `$ref` forms, since an unresolved `$ref` parameter has no `name`.

**One rule contradicted its own description once live.** `specfuse-406-when-alt-accept` demands 406 only when *multiple* response media types are declared, but a JSONPath filter cannot count an object's keys — so the `given` matched any operation with a 200 body and produced 8 findings against a conformant `hello-orders`. While the rule was inert nobody could notice, because **a rule that matches nothing never contradicts its own description.** The media-type count moved into `then` as `minProperties: 2`.

**Consumer impact — read this before upgrading.** Ten `error`-severity rules that have never reported will start reporting against specs written while they were asleep. `examples/hello-orders/` needed one real change (415 on the five operations with request bodies; `UnsupportedMediaTypeError` is now in the errors template), but a project of any size should expect a first number. This is exactly the case `scripts/spectral-ratchet.py` and `schemas/README.md` §"Turning the ruleset on against existing specs" exist for: baseline per rule, fail on regression, burn down the inherited count separately.

**The guard.** `scripts/spectral-rule-coverage.py` probes every rule's `given` with a `then` that fails against any value, so the finding count per rule is the number of nodes it selects; zero is a build failure unless allowlisted with a reason, and the allowlist is checked in both directions. All three rulesets run at full coverage with an empty allowlist (102/102, 78/78, 27/27). Because that only proves a rule **selects**, `fixtures/inert-rules-regression.yaml` violates each of the thirteen once and CI asserts every finding appears — which is what caught defects 1–3 above.

**Worth stating plainly, because the reporter said it first and it generalises past this ruleset:** the reporter recorded *"dropping `x-roles` fails validation on all 38 operations"* in a design doc and planned an overlay around it. There was no break. They planned a migration to relax a gate that was never closed. A lint result you have not proven can fail is not evidence.

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

### A per-service bundle splitter — decide whether the kit ships one

**Status:** open decision, deliberately not taken while adopting follow-up 24's vocabulary.

The generator does **not** subset one spec per service. It reads the bundle it is handed. `info.x-services` therefore leaves two viable topologies, both documented in `Vendor_Extensions.md` §14.7:

- **single bundle, many groups** — one master spec; each service repo binds its group with `groups[].service`. Needs no new tooling, because N project files already work.
- **split bundles** — a specs-side splitter derives a per-service bundle from the master spec, using `info.x-services` as its manifest.

Only the second needs anything built, and if the kit builds it, `info.x-services` is its input — which is the reason to decide before the registry accumulates consumers who have assumed one topology or the other.

**Argument for not shipping it yet:** the kit is a spec-authoring contract, deliberately not a CI product — the same line drawn for `spectral-ratchet.py`, which ships as a reference implementation a project copies and owns. A splitter is further from authoring than a ratchet is, and it has a harder correctness bar: a bundle that drops a shared enum or a `Read{Entity}`'s value object produces code that does not compile, in a repo whose author cannot see why. The single-bundle mode has neither problem and is the cheaper way to find out whether a topology is right at all.

**Argument for shipping it eventually:** every consumer that goes split writes the same closure walk, and getting it wrong is silent until compile time in someone else's repository.

**Do not decide this from the kit side alone** — decide it after the first consumer adopts `info.x-services` and reports which mode it actually ran. No consumer has declared the registry yet.

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
