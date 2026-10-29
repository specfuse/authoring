# Project File

> **Status:** Canonical reference. This document is the authoritative specification of the Specfuse project file — the JSON document consumed at the project root by the generator. The generator's own internal documentation should be a short summary that points back here. The authoritative parser source of truth lives in `dev.specfuse.generator.configs.ProjectDefinition`, `ArtifactGroup`, `TenancyDefinition`, `BrokerDefinition`, `WorkerPlacementDefinition`, `FunctionalTestConfig`, and `ProjectNamingOverrides`.

The project file declares everything the generator needs to turn a bundled OpenAPI specification, an optional AsyncAPI specification, and optional Arazzo workflow specifications into per-language code trees. It tells the generator:

- where the bundled specs live;
- which target languages and artifact sets to emit;
- where each generated tree lands on disk;
- cross-language identifier casing rules;
- multi-tenant entity wiring;
- messaging-broker dialect for the event runtime;
- per-group filtering, cleanup, and runtime-policy knobs.

The file is JSON on disk. **All examples in this document use JSON.**

> ### ⚠ Two foot-guns to read before anything else
>
> 1. **Unknown fields are silently ignored.** Jackson is configured with default field handling: any unknown top-level field, group field, or nested field is dropped without warning, error, or log line. Typos in field names (`cleanScopes` vs `cleanScope`, `tenancyConfig` vs `tenancy`, `arazzo` vs `arazzoSpecifications`) produce a silently-misconfigured generation. Always diff the generated output after editing the project file, and prefer copy-pasting field names from a known-good file.
>
> 2. **`stateDir` resolves differently depending on how the file is loaded.** Under the CLI, relative paths are resolved against the working directory and an unset `stateDir` defaults to `<cwd>/.specfuse/state`. Under the programmatic load-and-resolve entry point used by internal regen-loop tests, relative paths are resolved against the project file's parent directory and an unset `stateDir` defaults to `<projectFileDir>/.specfuse/state`. Always set `stateDir` explicitly if your generator runs are invoked from more than one working directory.

---

## Quick Reference

Language-coupling column: ✱ means the field is honoured only for a specific language target; "—" means it applies to every target.

| Path | Type | Required | Lang | Purpose |
|------|------|----------|------|---------|
| `openApiSpecifications` | string (path) | yes for generation | — | Path to the bundled OpenAPI spec. |
| `specifications` | string (alias) | — | — | Deprecated alias of `openApiSpecifications`. |
| `asyncSpecifications` | string (path) | optional | — | Path to the bundled AsyncAPI spec. |
| `arazzoSpecifications` | string (path) | optional | — | Path or directory containing `.arazzo.yaml` / `.recipe.yaml` files. |
| `asyncSourceRoot` | string (path) | optional | — | Spec source root for snapshot-file discovery (pre-bundle tree). |
| `name` | string | recommended | — | Project name, propagated to templates and used to derive defaults. |
| `description` | string | optional | — | Free-form description; not consumed by the generator. |
| `dbContextClassname` | string | optional | ✱ C# only | Overrides the EF Core `DbContext` class name; must be a valid C# identifier. Ignored for other languages. |
| `stateDir` | string (path) | optional | — | Per-group changelog state directory. Default depends on the load path — see foot-gun #2 above. |
| `namingOverrides` | object<role, case> | optional | — | Project-wide identifier casing per semantic role. |
| `tenancy` | object | optional | ✱ C# only (today) | Tenant / sub-tenant entity declarations. Drives C# marker-interface generation; ignored by other languages' artifact factories. |
| `tenancy.tenant.entity` | string | yes (when `tenancy` set) | ✱ | PascalCase tenant entity name. |
| `tenancy.tenant.foreignKey` | string | yes (when `tenancy` set) | ✱ | PascalCase FK column ending in `Id`. |
| `tenancy.tenant.marker` | string | yes (when `tenancy` set) | ✱ | Marker interface, `I` + PascalCase. |
| `tenancy.subTenant` | object | optional | ✱ | Same shape as `tenancy.tenant`. |
| `tenancy.enforcement` | enum | optional | ✱ C# only | **From generator `0.21.0`, deprecated on arrival.** `route` is the only value: it suppresses the generated `Tenant` query filter. Absent means the filter is always on. See §4.1. |
| `broker` | object | optional | ✱ C# event-runtime only | Messaging-broker dialect / topology settings. |
| `broker.type` | enum | optional | ✱ | `azureServiceBus` (only working value). |
| `broker.topology` | enum | optional | ✱ | `runtime` (default) \| `bicep` (experimental — emits stub). |
| `broker.outboxDialect` | enum | optional | ✱ | `sqlServer` (default) \| `postgres` (experimental — emits stub). |
| `persistence` | object | optional | **⚠ not implemented** | Multi-backend persistence configuration. **Read by nothing today — declaring it changes nothing and raises no diagnostic.** Design of record; see the banner on §6 and `compatibility.md` §27. Every `persistence.*` row below carries the same caveat. |
| `persistence.connections` | object<name, conn> | yes (when `persistence` set) | — | Named connection descriptors. Every referenced connection must be declared here. |
| `persistence.connections.<name>.provider` | enum | yes | — | `sqlServer` \| `postgres` \| `mySql` \| `cosmos` \| `azureBlob`. Must match the `kind` of any descriptor referencing this connection. |
| `persistence.connections.<name>.managed` | boolean | optional | — | Whether the generator owns DDL for entities on this connection. Default `true`. |
| `persistence.connections.<name>.schemaCheck` | enum | optional | — | `block` (default) \| `warn` \| `off`. Mode for unmanaged entities on this connection. |
| `persistence.default` | descriptor | optional | — | Backend descriptor used for any `x-entity` not in `entities`. Required if any entity is unlisted. |
| `persistence.entities` | object<entityName, descriptor> | optional | — | Per-entity descriptor overrides. Keys must match `x-entity` schemas in the bundled spec. |
| `persistence.schemaCheckTimeoutSeconds` | number | optional | — | Wall-clock cap for the startup schema-compatibility check, in seconds. Default `30`. |
| `encryption` | object | optional | — | Compliance floors and key scope for the `x-protection` axis. **Absent means no floors are applied and nothing warns** — see §15. |
| `encryption.profiles[]` | array<string> | optional | — | `law25` \| `pci` \| `soc2`. Composed as a **union of floors, not a ladder**. See §15. |
| `encryption.keyScope` | string | optional | — | `tenant` \| `global`. Governs `PROTECTION_ENCRYPTED_TENANT_SCOPE_REQUIRED` and the generated `EncryptionProfile.DeclaredKeyScope`. Absent disables both. See §15. |
| `authorization` | object | optional | ✱ C# runtime; validation for all | Authorization mode and the claims the generated C# runtime reads. Absent is `mode: roles`, byte-identical to before generator `0.14.0`. See §16. |
| `authorization.mode` | enum | optional | — | `roles` (default) \| `scopes`. `scopes` raises the role/scope coherence WARNINGs to ERROR and gates C# controllers with `[ScopesRequired]`. See §16. |
| `authorization.shadow` | boolean | optional | ✱ C# only | Emit both gates and log divergence; never decides by scopes. Requires `mode: scopes`. |
| `authorization.claims.{roles,userId,rolesShape,roleKey}` | string | optional | ✱ C# only | Claim types and shape for the generated `ClaimsPrincipalReader`. Defaults `roles`, `sub`, `name`, `role`. |
| `authorization.kioskSession.scheme` | string | optional | ✱ C# only | Authentication scheme of a kiosk-session principal. Absent makes `x-kiosk-session` inert. |
| `authorization.kioskSession.role` | string | optional | validation | **From generator `0.15.0`.** The role a kiosk-session principal carries. Arms `KIOSK_SESSION_ROLE_UNSATISFIABLE`. See §16. |
| `authorization.testGrants` | string (path) | optional | ✱ C# tests only | **From generator `0.15.0`.** A role-grants file for the generated authorization tests of a `scopes`-mode project whose spec declares no grants. See §16. |
| `functionalTests` | object | optional | ✱ C# tests | xUnit collection assignment for the generated API functional tests: `collectionNamePattern` (placeholders `{tag}` / `{group}`; by default every test is in one collection, `ApiFunctionalTest`) and `collectionGroups` (group name → list of operation tags). See §9 for `FUNCTIONAL_TEST_TAG_UNGROUPED`. |
| `functionalTests.emitAssertions` | enum | optional | ✱ C# scenario tests | **From generator `0.21.0`.** `off` (default) \| `strict`. `strict` makes a scenario step's `x-async.emit` an awaited assertion the test fails on. See §18. |
| `generateUserHelper` | boolean | optional | ✱ C# only | **From generator `0.20.0`.** Default `false`. `true` makes `authorizationRuntime` emit `Utils/UserHelper.g.cs`. See §16. |
| `workerPlacement` | object | optional | ✱ C# workers | **From generator `0.20.0`.** Which host runs each topic worker: `azureFunctions` (default) or `genericHost`. See §17. |
| `workerPlacement.messages.default` | enum | optional | ✱ | `azureFunctions` (default) \| `genericHost`. |
| `workerPlacement.messages.azureFunctions[]` / `.genericHost[]` | array<string> | optional | ✱ | AsyncAPI operation names placed on that host, whatever the default. |
| `workerPlacement.messages.genericHost` (pools) | object<string, array<string>> | optional | ✱ | **From generator `0.22.0`.** Pool name → operation names; each pool deploys as its own unit. See §17.1. |
| `groups[]` | array<object> | yes for generation | — | One artifact group per output tree. |
| `groups[].name` | string | recommended | — | Human-readable group label; used by `--group` and diagnostics. |
| `groups[].description` | string | optional | — | Free-form description. |
| `groups[].language` | string | yes | — | `csharp` \| `c#` \| `python` \| `dart` \| `flutter` \| `markdown`. |
| `groups[].generator` | string | optional | — | Internal — leave unset (or use `default`). See §8.4. |
| `groups[].basePackage` | string | yes for code | — | Logical package/namespace root for the group. |
| `groups[].destination` | string (path) | yes for code | — | Output directory. |
| `groups[].artifacts[]` | array<string> | yes for code | — | Artifact types to emit (see §11). |
| `groups[].configs` | object<string,string> | optional | — | Pass-through additional properties for templates. |
| `groups[].cleanGenerated` | boolean | optional | — | Wipe generated subtree before emitting. Default `false`. |
| `groups[].cleanScope[]` | array<string> | optional | — | Explicit relative paths to wipe instead of the language default. |
| `groups[].filter` | object | optional | — | Predicate tree — **AsyncAPI workers only (v1)**. Other artifact types ignore it. |
| `groups[].domains` | object | optional | — | Scope the group to a subset of domains: exactly one of `include` / `exclude`. Mutually exclusive with `pillar`. See §8.13.1. |
| `groups[].pillar` | string | optional | ✱ generator ≥ 0.14.0 (`service` in 0.6.0–0.13.x) | Pillar in `info.x-pillars` whose owned domains scope this group. Mutually exclusive with `domains`. See §8.13.2. |
| `groups[].unknownEnumPolicy` | enum | optional | ✱ Dart/Flutter only | `strict` \| `fallback` (default) \| `null`. |
| `groups[].formatPolicy` | enum | optional | ✱ Dart/Flutter only | `strict` (default) \| `lax`. |
| `groups[].mutationOverrides[]` | array<string> | optional | ✱ Dart/Flutter only | Operation IDs to flip between query / mutation classification. |
| `groups[].modelNameMapping` | object<string,string> | optional | ✱ generator ≥ `0.15.0`; TypeScript only | Schema name → emitted type identifier. Overrides the `Model` suffix given to a name that shadows a JS/DOM global. See §3.3. |

---

## File Location, Discovery, and CLI Invocation

The project file path is passed explicitly to the generator; the generator does **not** search for it.

```bash
java -jar specfuse-generator.jar generate path/to/project.json
java -jar specfuse-generator.jar generate --group Domain path/to/project.json
java -jar specfuse-generator.jar validate path/to/project.json
java -jar specfuse-generator.jar validate --producers path/to/project.json
```

The `validate` subcommand auto-detects intent from the file extension: a `.json` argument is treated as a project file and runs OpenAPI + AsyncAPI + Arazzo validation through the configured spec paths; a `.yaml` argument is treated as a raw spec.

### Filename convention

The filename is **pure convention**. Any `.json` file is accepted as a project file; no `*-project.json` suffix is enforced by the loader. Repositories conventionally use `{ProjectName}-project.json` to disambiguate when multiple project files coexist, but `project.json`, `my-config.json`, or anything else with a `.json` extension works.

### Multiple project files

A repository may contain any number of project files — each is an independent generation target. Two files in the same directory will not collide unless they declare overlapping `groups[].destination` + `groups[].basePackage` combinations.

### Working directory and path resolution

Relative paths in the project file are interpreted **relative to the JVM's working directory** when loaded via the CLI. The programmatic load-and-resolve entry point (used by internal regen-loop tests so they run from any IDE working directory) resolves paths against the project file's parent directory instead.

| Field | Resolved against |
|-------|------------------|
| `openApiSpecifications`, `asyncSpecifications`, `arazzoSpecifications`, `asyncSourceRoot` | CWD (CLI) or project-file dir (load-and-resolve). |
| `stateDir` | Same; default falls back to `<projectFileDir>/.specfuse/state` (load-and-resolve) or `<cwd>/.specfuse/state` (CLI). |
| `groups[].destination` | Same. |
| `groups[].cleanScope[]` | Relative to that group's `destination`; `..` segments are rejected. |

### Environment variables

The generator currently honours no environment-variable overrides for the project-file path or its fields. Every path is taken verbatim from the file.

---

## 1. Specs

The three spec-path fields tell the generator where to find the bundled inputs.

### 1.1 `openApiSpecifications`

**Purpose**: Path to the bundled OpenAPI 3.x specification. Drives every code-generation artifact and the OpenAPI validator.

**Required**: Yes for `generate`. Optional for `validate` (the CLI accepts a bare `.yaml`/`.json` file path instead).

**Type**: string — a filesystem path. Absolute paths are honoured as-is; relative paths follow the rules in [Working directory and path resolution](#working-directory-and-path-resolution).

**Consumed by**: OpenAPI parser, validator, every artifact group's underlying codegen configurator. The AI access manifest writer also drops one file in the spec's parent directory regardless of group destinations.

**Deprecated alias**: `specifications` is accepted by the parser for legacy project files. Migrate to `openApiSpecifications`.

```json
{ "openApiSpecifications": "./output/openapi-bundled.yaml" }
```

### 1.2 `asyncSpecifications`

**Purpose**: Path to the bundled AsyncAPI 3.x specification. Drives event-runtime, snapshot, event-handler, outbox, and worker artifacts.

**Required**: Optional. Absent or blank disables AsyncAPI parsing entirely — every async artifact in any group becomes a no-op for that run.

**Consumed by**: AsyncAPI parser, event-runtime artifacts, snapshot validation, the `extensionEquals` / `hasExtension` filter evaluator on per-worker artifacts.

```json
{ "asyncSpecifications": "./output/asyncapi-bundled.yaml" }
```

### 1.3 `arazzoSpecifications`

**Purpose**: Path or directory containing Arazzo scenario / recipe documents (`.arazzo.yaml`, `.recipe.yaml`).

**Required**: Optional. When set, Arazzo files are parsed, validated, cross-linked against the OpenAPI build context, and made available to scenario / recipe artifacts (Markdown docs, C# fixture & test classes).

**Validation severity**: Arazzo errors are **not** downgraded: an Arazzo ERROR fails `validate` like any other (measured on `0.14.0` and `0.15.0`; earlier revisions of this line said they were downgraded to warnings). Arazzo does not yet drive code generation in lockstep with OpenAPI/AsyncAPI.

```json
{ "arazzoSpecifications": "./api/specs/v3" }
```

### 1.4 `asyncSourceRoot`

**Purpose**: Path to the pre-bundle AsyncAPI source tree containing per-domain `events/{Entity}Snapshot.yaml` files. When set, the parser walks the tree and loads each snapshot into the build context so snapshot validators and snapshot artifacts can emit against them.

**Required**: Optional. Projects that have not adopted snapshot files leave it unset; the corresponding validators silently no-op.

**Default**: `null` (snapshot validation skipped).

```json
{ "asyncSourceRoot": "./api/specs/v3" }
```

---

## 2. Project Identity

### 2.1 `name`

**Purpose**: Project name. Propagated to templates as the `projectName` additional property, used to derive package conventions per language (e.g. the C# `{ProjectName}DbContext` default) and stamped into generated headers.

**Required**: Recommended. The CLI does not refuse a missing name, but several artifacts derive their defaults from it. The C# event-contract test artifact in particular falls back to a hard error if both `name` and an explicit application-package override are unset.

**Type**: string. No structural validation is enforced — keep it short, PascalCase, and free of path-unsafe characters.

```json
{ "name": "HelloOrders" }
```

### 2.2 `description`

**Purpose**: Free-form human description. Carried in the parsed model but consumed by no generator subsystem.

**Required**: Optional.

```json
{ "description": "Backend + Flutter + AI worker code for the HelloOrders domain." }
```

### 2.3 `dbContextClassname` *(C# only)*

**Purpose**: Overrides the EF Core `DbContext` class name used by generated C# code. Ignored by every non-C# language target.

**Required**: Optional.

**Default**: Derived from `name` as `{ProjectName}DbContext`. Falls back to `AppDbContext` when `name` is blank.

**Validation**: Must match `^[A-Z][A-Za-z0-9_]*$` (a valid C# class identifier). A blank value is ignored (the convention default wins); a non-blank invalid value fails the load.

**Set this only when** the consumer's actual `DbContext` class does not follow the convention.

```json
{ "dbContextClassname": "HelloOrdersDbContext" }
```

### 2.4 `stateDir`

**Purpose**: Directory where the per-group changelog tracker persists surface manifests (one JSON file per group: `<stateDir>/<groupName>.json`). The tracker uses these to diff regen-over-regen and emit `CHANGELOG.md` plus one-cycle deprecation shims.

**Required**: Optional.

**Default**: Depends on the load path. See foot-gun #2 at the top of this document.

**Type**: string (path). Absolute or relative; relative is resolved as in [Working directory and path resolution](#working-directory-and-path-resolution).

```json
{ "stateDir": "out/dart/.specfuse-state" }
```

---

## 3. Naming Overrides

### 3.1 `namingOverrides`

**Purpose**: Project-wide case overrides for identifiers that cross language boundaries (DB columns, wire field names, channel names, etc.). Every artifact that emits one of these identifiers consults the override before falling back to the active language's default case (see §3.2).

**Required**: Optional.

**Default**: No global default map — a missing role falls back to the language profile's per-role default in §3.2.

**Type**: `object<roleName, caseName>` where:

**Role names** (case- and separator-insensitive):

| Role | Applies to |
|------|------------|
| `dbColumn` | Database column names (EF Core `HasColumnName("…")`, SQLAlchemy `mapped_column("…")`). |
| `wireField` | JSON / GraphQL / Service Bus payload field names. |
| `enumValue` | Serialized enum member string values. |
| `channel` | AsyncAPI channel / topic / queue / exchange names. |
| `header` | Custom HTTP header names. |
| `pathParam` | URL path parameter keys (`{key}` inside route templates). |
| `queryParam` | URL query string parameter keys. |

**Case names** (case- and dash/underscore-insensitive):

| Case | Output |
|------|--------|
| `PascalCase` (`Pascal`) | `OrderId`, `UserName` |
| `camelCase` (`camel`) | `orderId`, `userName` |
| `snake_case` (`snake`) | `order_id`, `user_name` |
| `kebab-case` (`kebab`) | `order-id`, `user-name` |
| `SCREAMING_SNAKE_CASE` (`constant`, `upper_snake`) | `ORDER_ID`, `USER_NAME` |
| `Preserve` (`asIs`, `identity`, `none`) | Identifier returned unchanged. Used for headers and topic names that have RFC-defined canonical forms. |

**Per-enum override**: `x-enumCase: preserve` on a schema wins over `namingOverrides.enumValue` for ISO-code enums (Currency, CountryCode, Province). See `Vendor_Extensions.md`.

**Validation**: Unknown role keys or unknown case values fail the load.

```json
{
  "namingOverrides": {
    "dbColumn":   "PascalCase",
    "wireField":  "camelCase",
    "enumValue":  "camelCase",
    "pathParam":  "camelCase",
    "queryParam": "camelCase",
    "header":     "Preserve",
    "channel":    "Preserve"
  }
}
```

### 3.2 Per-language defaults for each role

When `namingOverrides` does not declare a role, this is the case the language produces. Use this table to decide whether you actually need an override.

| Role | C# / `csharp` | Python / `python` | Dart / `flutter` | Markdown / `markdown` |
|------|---------------|-------------------|------------------|-----------------------|
| `dbColumn` | `PascalCase` | `snake_case` | `snake_case` | `PascalCase` (inherited) |
| `wireField` | `camelCase` | `snake_case` | `camelCase` | `PascalCase` (inherited) |
| `pathParam` | `camelCase` | `snake_case` | `camelCase` | `PascalCase` (inherited) |
| `queryParam` | `camelCase` | `snake_case` | `camelCase` | `PascalCase` (inherited) |
| `enumValue` | `Preserve` | `Preserve` | `Preserve` | `PascalCase` (inherited) |
| `channel` | `Preserve` | `Preserve` | `Preserve` | `PascalCase` (inherited) |
| `header` | `Preserve` | `Preserve` | `Preserve` | `PascalCase` (inherited) |

**Notes**:

- The C# / Python / Dart profiles deliberately `Preserve` `enumValue`, `channel`, and `header`. Those identifiers have canonical wire forms the spec author picks deliberately (RFC-defined headers, dotted topic names, deliberate enum casing). Re-casing them would be visibly wrong.
- The Markdown profile inherits the framework default `PascalCase` for every role and does not override any of them — but no Markdown artifact currently emits identifiers in any of these roles, so the value rarely matters.
- A polyglot project that wants the same wire JSON shape across C# and Python typically sets `wireField: camelCase` to override Python's `snake_case` default. Without the override, the C# group writes `customerId` and the Python group writes `customer_id` for the same field.

### 3.3 TypeScript type names that shadow a global — `Model` suffix and `modelNameMapping`

**From generator `0.15.0`, a generated TypeScript type never takes the name of a JS or DOM global** (`clabonte/generator#1740`). A schema whose name TypeScript's standard library declares as a global type (`lib.es5`, `lib.es20xx` or `lib.dom`) is declared and referenced with a fixed `Model` suffix: `Error` becomes `ErrorModel`, `Event` becomes `EventModel`, and `Document`, `Location` and `Screen` change the same way. Only the type identifier changes. File names, module paths, barrels, and builder, fixture and composable names (`buildError`, `errorFixture`) keep the schema name. No deprecated alias for the old name is emitted, because `export type Error = ErrorModel` would bring back the shadowing. **Client action:** change every import of a renamed type. The kit's own example is affected: its shared `Error` schema is emitted as `export interface ErrorModel` in `src/common/data/dtos/error.ts` (measured on `examples/hello-orders`; `0.14.0` emitted `Error`). Dart and C# names do not change.

To choose another name for one schema, set `modelNameMapping` on the group: a map from the declared schema name to the identifier to emit. An entry takes precedence over the suffix.

```json
{ "language": "typescript", "name": "Web", "modelNameMapping": { "Error": "ProblemBody" }, "artifacts": ["dto"] }
```

Measured on `examples/hello-orders`: on a TypeScript group the entry renames the declaration and every reference. On a C# group it is accepted and changes nothing. Generator `0.14.0` rejects the key and fails the load (`Unrecognized field "modelNameMapping"`), so add it only after the pin bump.

---

## 4. Tenancy

### 4.1 `tenancy` *(C# only today)*

**Purpose**: Declares the project's multi-tenant entity topology. In the C# target, it drives marker-interface generation (`I{Tenant}Scoped` / `I{SubTenant}Scoped`) and entity partial-class derivation from `x-entity.belongsTo`. From generator `0.15.0`, a property declaring `x-references: { entity: <tenant entity>, resolve: remote }` also gives its entity the tenant marker, with no `belongsTo`. The property must be named after `tenant.foreignKey`, which the marker's property is; from `0.16.0` any other name is `TENANT_REMOTE_REFERENCE_FOREIGN_KEY_MISMATCH` (ERROR) at project-level `validate`. The `subTenant` tier still follows `belongsTo` only. See `Vendor_Extensions.md` §14.11. It also feeds AsyncAPI validators (tenant FK ordering) and broker tenant scoping.

The Python and Dart/Flutter artifact factories do **not** register a tenancy-marker artifact today and emit no `I{Tenant}Scoped` equivalents. The block is still useful for those languages indirectly: AsyncAPI validation rules (e.g. tenancy ordering on `belongsTo`, the "events from emitting entities should include the tenant in their chain" suggestion) consult `tenancy` regardless of which language group consumes the result.

**Required**: Optional. Single-tenant projects omit the entire block, whatever C# artifacts they register. From generator `0.20.0` no artifact requires it. `eventRuntime`, `eventRuntimeImpl`, `eventRuntimeFunctions`, `tenancyMarker` and `eventContractTest` all generate without it (`clabonte/generator#2883`): `eventRuntime` emits a do-nothing `Tenancy/ITenantScoped.g.cs` that no type implements, so an event envelope's `CompanyId` stays unset, and `tenancyMarker` emits nothing. Through `0.19.0` those artifacts failed the load with `PROJECT_EVENT_RUNTIME_TENANCY_REQUIRED`, `PROJECT_TENANCY_REQUIRED` or `PROJECT_EVENT_CONTRACT_TEST_TENANCY_REQUIRED`. Generated services always use the event runtime, so at `0.19.0` a project registering `service` needed a `tenancy` block. All three codes are removed. A single-tenant project that added a placeholder `tenancy` block to get past them can delete it, but read "What declaring `tenancy` turns on" below first: from `0.21.0` the block does much more than declare markers.

**Type**: object with mandatory `tenant` and optional `subTenant`.

**Shape**:

```json
{
  "tenancy": {
    "tenant": {
      "entity":     "<PascalCase>",
      "foreignKey": "<PascalCase>Id",
      "marker":     "I<PascalCase>"
    },
    "subTenant": {
      "entity":     "<PascalCase>",
      "foreignKey": "<PascalCase>Id",
      "marker":     "I<PascalCase>"
    },
    "enforcement": "route"
  }
}
```

`enforcement` is optional, read from generator `0.21.0`, and deprecated on arrival (below).

**Validation** (all enforced at load):

- An empty `tenancy: {}` block is rejected.
- `tenancy.tenant` is required whenever the block is declared.
- Per tier, every field is required.
- `entity` must be PascalCase.
- `foreignKey` must be PascalCase **and** end in `Id`.
- `marker` must match `^I[A-Z][A-Za-z0-9]*$`.
- `enforcement`, when present, must be `route` (generator `0.21.0`, `PROJECT_TENANCY_ENFORCEMENT_UNKNOWN`). Any other value fails the load. Generator `0.19.0` and `0.20.0` drop the key without a word, like any unknown key.
- `marker` must not be `ITenantScoped` or `ISubTenantScoped` (generator `0.18.0`, `PROJECT_TENANCY_MARKER_RESERVED`). Those are the abstract markers the C# `tenancyMarker` artifact always emits. A concrete marker of the same name was written to the same file as `interface ITenantScoped : ITenantScoped`, which failed `dotnet build` with `CS0529` while `validate` and `generate` passed. An entity named `Tenant` invites the name; pick another (`IHelloTenantScoped`, `ITenantOwned`).

**Cross-spec entity resolution**: The project-file loader does **not** check that `tenancy.tenant.entity` (or `subTenant.entity`) actually names an `x-entity` schema in the bundled OpenAPI spec. A typo or missing schema produces no load-time error. Detection moves downstream:

- AsyncAPI validation runs `belongsTo` checks that reference the tenant entity name; if entities declare `belongsTo: [Comapny]` (typo), the rule reports `ASYNC_BELONGS_TO_OBJECT_DERIVATION` against the entity, not against the tenancy block — so the wrong name in `tenancy.tenant.entity` shows up as cascading errors against every entity that *did* spell the name correctly.
- C# template emission silently produces the configured marker interface anyway (the templates substitute the name without verifying it). The resulting code may reference a non-existent base type.

If you change the tenant entity name, double-check both `tenancy.tenant.entity` and every `x-entity.belongsTo` reference in the spec.

**Interactions**: Combines with `x-entity.belongsTo` to decide which entities get which marker interface. See `Vendor_Extensions.md` § Entity Modeling.

```json
{
  "tenancy": {
    "tenant":    { "entity": "Organization",    "foreignKey": "OrganizationId",    "marker": "IOrganizationScoped" },
    "subTenant": { "entity": "Store", "foreignKey": "StoreId", "marker": "IStoreScoped" }
  }
}
```

#### What declaring `tenancy` turns on (generator `0.21.0`, breaking for C#)

Through `0.20.0` the block declared marker interfaces and nothing filtered a query by tenant. From `0.21.0`, in a C# project that declares `tenancy`:

- **Every entity whose `belongsTo` chain reaches the tenant entity is filtered by a generated `Tenant` named query filter** in `AppDbContext`. The filter follows the shortest owning chain, so a child with no tenant column of its own is filtered through its owner. The tenant entity is filtered by its own `Id`. A row reached through an optional hop whose foreign key is null is hidden. An entity with no path to the tenant gets no filter.
- **The host must register an `IRecordVisibilityResolver`.** `AddSqlServerDatabase` registers a placeholder that throws, naming the interface, at the first query that reads a filtered entity. The host still builds and starts, so the failure appears at the first filtered read, not at startup.
- **A get, update or delete of another tenant's row answers `404`** through the generated service, because the filtered by-id query returns nothing. A list never returns the other tenant's rows. Declare `404` on every operation with an id path parameter (`API_Handbook.md` §2).
- **An entity that declares `x-entity.visibility` gains a second filter, `Visibility`**, within the tenant (`Vendor_Extensions.md`). A row hidden by it also answers `404`, not `403`.

The host-side migration (the resolver, background paths, hand-built `DbContext`s, a bare `IgnoreQueryFilters()`, test hosts) is C# component work, covered in `docs/csharp-component-guide.md`. A project with no `tenancy` block generates byte-identical output.

`validate` also reports `VISIBILITY_NOT_ENFORCED` (WARNING, generator `0.21.0`) once per Python group and tenant-owned entity it reads: every entity, for a group registering `repository`; the `aiAccess` entities, for one registering `aiRepository`. SQLAlchemy readers carry no tenant filter, so scope those queries by hand. A project with a Python group and a `tenancy` block sees new warnings on the jar bump; they fail nothing.

#### `tenancy.enforcement: route` (generator `0.21.0`, deprecated on arrival)

A transition switch for a project whose list routes do not yet carry the tenant path parameter, where the always-on filter would break existing reads. `"enforcement": "route"` suppresses the `Tenant` query filter only; tenant isolation is then the host's route checks, as it was through `0.20.0`. The `Visibility` filter and the soft-delete filter stay on.

While the switch is set, project-level `validate` reports `TENANCY_ENFORCEMENT_ROUTE` (WARNING), once, naming each tenant-owned entity that a list route returns without a tenant path parameter. Those entities are readable across tenants. A route parameter named for either tier's `foreignKey` counts. The message also counts the further entities that only the sub-tenant's parameter covers. With no such entity the warning does not fire.

**Remove the switch once every list route carries the tenant path parameter.** The generator's release gate refuses to ship a release after 2027-01-31 while the switch still exists in its code, so a project that keeps it will lose it on a later pin bump. Under the switch, `tenantIsolationTest` emits only the `Visibility` facts (none when no entity declares `visibility`), `VISIBILITY_NOT_ENFORCED` names only entities with a `visibility` narrowing, and `bareIgnoreSourceScanTest` emits nothing (§11.1).

---

## 5. Broker

The broker block is meaningful only for projects that emit the event-runtime artifacts (currently a C# concern). **The only fully-supported broker is Azure Service Bus** — `broker.type: azureServiceBus` is both the default and the only value with a working runtime. The other broker fields are open enums whose non-default values exist as placeholders for future work and emit stub code today.

### 5.1 `broker`

**Purpose**: Messaging-broker configuration. Drives the topology-ensure flow (whether the dispatcher creates topics at runtime or expects them to exist) and the SQL dialect of the outbox drainer's lease query.

**Note**: The Service Bus *topic name* itself is not a code-gen input — the dispatcher reads it at runtime from the `AzureServiceBus:TopicName` configuration key.

**Required**: Optional. An empty `broker: {}` accepts every default.

**Fields**:

| Field | Type | Default | Allowed values |
|-------|------|---------|----------------|
| `type` | enum | `azureServiceBus` | `azureServiceBus` |
| `topology` | enum | `runtime` | `runtime` \| `bicep` (experimental — emits stub) |
| `outboxDialect` | enum | `sqlServer` | `sqlServer` \| `postgres` (experimental — emits a `NotImplementedException` stub in the drainer) |

**Validation**: Unknown values fail the load with a Levenshtein-based "did you mean" suggestion.

```json
{
  "broker": {
    "type":          "azureServiceBus",
    "topology":      "runtime",
    "outboxDialect": "sqlServer"
  }
}
```

---

## 6. Persistence

> ## ⚠ Design of record — not yet a contract
>
> **The generator does not read the `persistence` block.** Verified against the pinned `0.5.8` and against generator `main`: **zero** `PERSISTENCE_*` codes and no parsing of the block anywhere in the Java source. The only two case-insensitive matches for "persistence" are unrelated comments. Controls run in the same search land where you would expect — `tenancy` in 29 files, `broker` in 11, `namingOverrides` in 15.
>
> **The failure mode is silence, which is why this banner is here and the section is not.** A `persistence` block in `project.json` today is **read by nothing**: it does not warn, it does not change the exit code, and generation proceeds exactly as if the block were absent. So a project that declares `managed: false` and believes DDL emission is off, or `kind: document` and believes it is not getting EF configurations, gets neither the behaviour nor a diagnostic. §6.6's validation codes do not fire, and the load-time warning §6.3 promises for unknown `connections.<name>` sub-keys does not exist either.
>
> This section stays because it is the agreed design and losing it would lose the design. **Do not author against it yet.** Track it as `compatibility.md` §27; the banner comes off when the generator parses the block, not before.

The `persistence` block tells the generator how each entity in the bundled OpenAPI spec maps to a concrete storage backend. The spec itself stays storage-agnostic — `persistence` is where database engines, connection names, schema names, container names, and schema-ownership decisions live.

### 6.1 Principle

Specs describe **what** the data is; `persistence` describes **how it is realized**. The same spec ships to two projects that disagree on the storage stack; each project's `persistence` block resolves the disagreement without touching the spec.

Two orthogonal axes drive the resolution:

- **`kind`** — how the generator talks to the entity at runtime. One of `relational`, `document`, `blob`, `hybrid`.
- **`managed`** — whether this project owns DDL / migration / container-provisioning artifacts for the entity.

> **`managed: false` does not mean read-only.** It means the schema is evolved elsewhere — writes are still permitted. The dominant scenario is a SaaS application integrating with a customer-managed database: the customer's DBA owns migrations; the application writes data freely.

### 6.2 `persistence` block shape

```json
{
  "persistence": {
    "connections": {
      "Main":    { "provider": "sqlServer", "managed": true,  "schemaCheck": "block" },
      "Legacy":  { "provider": "postgres",  "managed": false, "schemaCheck": "warn" },
      "Cosmos":  { "provider": "cosmos" },
      "Blob":    { "provider": "azureBlob" }
    },
    "default": { "kind": "relational", "connection": "Main", "schema": "dbo" },
    "entities": {
      "Invoice":    { "kind": "relational", "connection": "Main", "schema": "billing" },
      "AuditEvent": { "kind": "document",   "connection": "Cosmos", "container": "audit" },
      "Document":   {
        "kind": "hybrid",
        "metadata": { "kind": "relational", "connection": "Main" },
        "content":  { "kind": "blob",       "connection": "Blob",   "container": "docs" }
      },
      "LegacyUser": { "kind": "relational", "connection": "Legacy" }
    },
    "schemaCheckTimeoutSeconds": 30
  }
}
```

**Top-level fields**:

| Field | Purpose |
|-------|---------|
| `connections` | Named map of connection descriptors. Every connection referenced anywhere in `persistence` must be declared here. |
| `default` | Backend descriptor applied to any `x-entity` schema not listed in `entities`. |
| `entities` | Per-entity overrides keyed by `x-entity` schema name. |
| `schemaCheckTimeoutSeconds` | Total wall-clock cap for the startup schema-compatibility check, in seconds. Default `30`. |

**Required**: Optional as a whole. When `persistence` is absent, no persistence-related artifacts are emitted (the project is treated as wire-only). When `persistence` is present, see §6.5 for resolution rules.

### 6.3 `connections`

Every connection used by `default` or any entity descriptor must be declared here by name. Connection names are case-sensitive identifiers — they have no production-time meaning beyond serving as the link between the project file and a runtime configuration entry (which resolves the actual connection string from environment variables or a secret store).

**Connection descriptor**:

| Field | Type | Required | Default | Purpose |
|-------|------|----------|---------|---------|
| `provider` | enum | yes | — | One of `sqlServer`, `postgres`, `mySql`, `cosmos`, `azureBlob`. Determines the SQL dialect for the schema-compatibility check, the document/blob API surface, and the generated typed connection-config class. |
| `managed` | boolean | no | `true` | Whether the generator owns DDL for entities on this connection. Falls through to `persistence.default.managed` if both are absent. |
| `schemaCheck` | enum | no | inherited | One of `block`, `warn`, `off`. Default mode for unmanaged entities on this connection. See §6.7. |

**Validation**:

- `provider` must be consistent with the `kind` of every entity descriptor referencing this connection: `relational` kinds require `sqlServer` / `postgres` / `mySql`; `document` requires `cosmos`; `blob` requires `azureBlob`. Mismatches fail the load.
- Undocumented fields under `connections.X` produce a load-time **warning** (not silent acceptance, not hard rejection) so future per-connection metadata can be introduced without breaking older project files.

### 6.4 Backend descriptors

A backend descriptor appears in three places: `persistence.default`, each entry of `persistence.entities`, and within a hybrid descriptor's `metadata` / `content` sub-descriptors.

**Common fields** (every descriptor):

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `kind` | enum | yes | One of `relational`, `document`, `blob`, `hybrid`. |
| `connection` | string | yes (except for `hybrid`) | Name of a declared connection. `hybrid` descriptors carry no top-level `connection` — their sub-descriptors carry their own. |
| `managed` | boolean | no | Overrides the connection-level and project-level default. See §6.5. |
| `schemaCheck` | enum | no | Overrides the connection-level and project-level default. See §6.7. |

**Per-kind fields**:

#### `kind: relational`

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `schema` | string | no | Database schema name (`dbo`, `public`, `billing`, …). Defaults to the provider's convention. Rejected on any non-relational descriptor. |

#### `kind: document`

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `container` | string | yes | Cosmos container name. |
| `inspectSample` | boolean | no | When `true`, the schema-compatibility check fetches a sample document and verifies required fields are present. Default `false` (container-existence check only). |

#### `kind: blob`

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `container` | string | yes | Azure Blob container name. |

#### `kind: hybrid`

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `metadata` | descriptor | yes | The descriptor for the queryable side. Any non-hybrid kind is legal. |
| `content` | descriptor | yes | The descriptor for the payload side. Any non-hybrid kind is legal. |

**Hybrid rules**:

- Nested hybrid is rejected — `kind: hybrid` inside `metadata` or `content` fails the load.
- The owning entity must have at least one property carrying `x-content: true` (see `Vendor_Extensions.md` §1.6).
- Repository implementation, mapping, and DTOs are generated against the entity as a whole — the split is internal to the generated repository.

### 6.5 Resolution order

For every `x-entity` schema in the bundled spec the generator resolves a single effective descriptor.

**Descriptor resolution**:

1. `persistence.entities.<EntityName>` (per-entity override) — used verbatim when present.
2. `persistence.default` — applied otherwise.
3. If neither is present, the load fails with `PERSISTENCE_DESCRIPTOR_MISSING`. (Incremental adoption: set `persistence.default` once, then override per entity as backends diverge.)

**`managed` / `schemaCheck` resolution** (most specific wins):

1. The descriptor itself (`persistence.entities.X.managed`, `…schemaCheck`).
2. The connection (`persistence.connections.<conn>.managed`, `…schemaCheck`).
3. The project default (`persistence.default.managed`, `…schemaCheck`, otherwise built-in defaults: `managed: true`, `schemaCheck: block`).

**Schemas excluded from resolution**:

- `x-value-object` schemas are not subject to persistence resolution — they are persisted as part of their owning entity (see `Vendor_Extensions.md` §2).
- Schemas without `x-entity` (wire-only DTOs, derivatives like `Basic*` / `New*` / `Update*`) are excluded.

### 6.6 Validation rules

All errors fail the load with a stable error code.

| Code | Condition |
|------|-----------|
| `PERSISTENCE_CONNECTION_UNDECLARED` | A descriptor references a connection name not present in `persistence.connections`. |
| `PERSISTENCE_PROVIDER_KIND_MISMATCH` | A descriptor's `kind` is inconsistent with the referenced connection's `provider`. |
| `PERSISTENCE_ENTITY_NOT_FOUND` | A key in `persistence.entities` does not match any `x-entity` schema in the bundled spec. |
| `PERSISTENCE_DESCRIPTOR_MISSING` | An `x-entity` schema has no descriptor (no entry in `entities`, no `default`). |
| `PERSISTENCE_NESTED_HYBRID` | A hybrid sub-descriptor is itself `kind: hybrid`. |
| `PERSISTENCE_HYBRID_NO_CONTENT` | A `kind: hybrid` entity has no property marked `x-content: true`. |
| `PERSISTENCE_SCHEMA_ON_NON_RELATIONAL` | A non-relational descriptor carries a `schema` field. |
| `PERSISTENCE_CONTAINER_MISSING` | A `document` or `blob` descriptor omits `container`. |

A property marked `x-content: true` that is also `required: true` is rejected by spec validation (not project-file load). See `Vendor_Extensions.md` §1.6.

### 6.7 Schema compatibility check

When `managed: false` resolves for an entity, the generator emits a startup schema-compatibility check artifact. The check runs once at application startup and compares the spec-declared shape against the live store.

**Per-entity `schemaCheck` modes**:

- `block` (default) — emit a structured drift report and fail startup.
- `warn` — emit the same drift report; do not fail startup.
- `off` — skip the check entirely (escape hatch for known-flaky entities).

The drift-report shape is identical across modes; only the startup disposition differs:

```json
{ "entity": "...", "side": "metadata|content", "field": "...", "expected": "...", "actual": "...", "severity": "..." }
```

The `side` field is present only for hybrid entities.

**Per-kind check behavior**:

| Kind | What is verified |
|------|------------------|
| `relational` | Column names, column types (per the provider's type-equivalence table), nullability, FK targets. Indexes, constraints, and comments are skipped. |
| `document` | Container exists. When `inspectSample: true`, a sample document is fetched and required fields are verified. |
| `blob` | Container exists. For `managed: true`, missing containers are auto-created at startup. For `managed: false`, a missing container hard-fails. |
| `hybrid` | Metadata-side and content-side checks both run. Either side failing marks the entity as drifted; the diagnostic names the failing side. |

**Type-equivalence rules** (relational): width-matched `VARCHAR(n)` / `NVARCHAR(n)` pairs count as equivalent; integer-width aliases (`INT` / `INTEGER`) are equivalent; unicode/non-unicode variants of the same width are equivalent. Any type pair outside the per-provider equivalence table is drift. The equivalence tables are published in the generator's own docs alongside the check implementation.

**Language matrix**:

| Language | Artifact emitted |
|----------|------------------|
| C# | `IHostedService` registered to run once at startup. |
| Python | Startup function called from the FastAPI / worker bootstrap. |
| Dart / Flutter | None. Flutter consumes wire DTOs and does not talk to a store directly. |

**Execution model**:

- Per-connection checks run in parallel.
- Per-entity checks within a single connection run serially.
- Total wall-clock is capped by `persistence.schemaCheckTimeoutSeconds` (default `30`). Exceeding the timeout is treated as a `block`-mode failure for entities still in flight.

### 6.8 Interactions with spec extensions

- **`x-entity.schema`** — deprecated *in direction*, supported *in fact*. Storage technology is designed out of the spec, with schema names moving to `persistence` descriptors — but the generator parses `x-entity.schema` and does not read `persistence` at all, so **do not migrate yet**: the move lands on a key nothing reads, with no diagnostic either side of it. Keep the key; migrate when §6 is implemented. See `Vendor_Extensions.md` §1.1 and `compatibility.md` §27.
- **`x-content` properties** — declared at the property level on entity schemas. Marks opaque payload not intended for query, filter, projection, or pagination. Required for `kind: hybrid` entities. See `Vendor_Extensions.md` §1.6.
- **`aiAccess`** — remains in the spec; composes with persistence per-entity. AI-scoped repository methods inherit the entity's backend kind and are generated against the same `kind`-specific template family as the production repository.
- **`tenancy`** (§4) — orthogonal to backend kind. Tenant scoping applies across all backends via the kind's native mechanism: FK column for `relational`, partition key for `document`, key prefix for `blob`, both sides for `hybrid`.
- **`x-value-object.storage`** (`single_json`, `flatten`, `serialized`, `separate_table`, `collection_json`) — interpreted as hints by the persistence layer. Each backend kind honors what it can and reinterprets the rest: a `document` adapter typically ignores `flatten` (the whole entity is one document anyway); a pure-`blob` adapter only accepts `serialized`. See `Vendor_Extensions.md` §2.
- **Test fakes** — emitted regardless of `managed`. For `managed: false` entities, the generated fake class carries a one-line header comment noting that the production schema is owned externally. Useful for unit tests against in-memory providers; consumers running integration tests against the real DB are responsible for their own seed strategy.
- **Snapshots** (`events/{Entity}Snapshot.yaml`, §1.4) — flow through `persistence.entities` keyed as `<Entity>Snapshot`. When no snapshot-specific row exists, the snapshot inherits its parent entity's descriptor. Override by adding a `<Entity>Snapshot` row when snapshots need a different store. Pure-`blob` overrides cannot support aggregate-id + timestamp lookups; `hybrid` (relational metadata + blob content) is the natural shape when separation is needed.

---

## 7. Groups

### 7.1 `groups`

**Purpose**: One generation unit per output tree. Each group has its own language, package/namespace root, destination, artifact list, and per-group policy knobs. Groups in the same project can — and routinely do — share a single `destination` (e.g., a C# Backend solution with separate Domain / Application / Infrastructure groups), in which case each writes into its own `basePackage` subfolder.

**Required**: Yes for `generate` (an empty `groups: []` produces no output).

**Type**: array of group objects (§8).

---

## 8. Group Fields

### 8.1 `name`

**Purpose**: Human-readable identifier for the group. Used by the `--group` CLI flag (case-insensitive match), in log messages, in the per-group changelog state file (`<stateDir>/<name>.json`), and as the diagnostic context for filter / clean-scope errors.

**Required**: Recommended. Unnamed groups still generate but report as `<unnamed>` in diagnostics.

**Type**: string.

### 8.2 `description`

**Purpose**: Free-form description. Not consumed by the generator.

**Required**: Optional.

### 8.3 `language`

**Purpose**: Selects the language profile, post-processor, and artifact factory for the group.

**Required**: Yes. When omitted, the generator falls back to C# for backwards compatibility — do not rely on this; declare it explicitly.

**Allowed values** (case-insensitive):

| Value | Profile / Factory | Notes |
|-------|-------------------|-------|
| `csharp`, `c#` | C# profile + C# factory | Full DDD + EF Core + AsyncAPI + Azure Functions set. |
| `python` | Python profile + Python factory | SQLAlchemy + Pydantic + AI worker scaffolding. |
| `dart`, `flutter` | Dart profile + Dart factory | Riverpod + freezed stack; both aliases resolve to the same profile. |
| `typescript` | TypeScript profile + TypeScript factory | Entities, DTOs and builders, enums, value objects, an API client, repositories (interface / impl / fake), Vue-style query and mutation composables, and their tests. Added in generator `0.5.8`. |
| `markdown` | Markdown profile + Markdown factory | Documentation generators (scenario docs, recipe docs, entity diagrams, event catalog). |

**Validation**: An unregistered value fails the load with the full list of known languages.

### 8.4 `generator` *(internal — leave unset)*

**Purpose**: Selects the underlying openapi-generator name. There is currently no reason to set this field in a normal project file — `default` (or omit) resolves to the bundled Specfuse generator, which is the only generator registered with each language profile.

**Required**: Optional. Defaults to the bundled Specfuse generator.

**Allowed values**: Leave unset, or pass `default`. A custom name is accepted only if you have explicitly registered one in code; otherwise the value is ignored. **Treat as internal; do not set unless you have registered a custom generator.**

### 8.5 `basePackage`

**Purpose**: Logical root for the group: C#/.NET namespace root, Python package, Dart package name, Markdown subdirectory. Used in two ways:

- as the package/namespace stamped into generated source files;
- as the **wipe scope** for `cleanGenerated` when no explicit `cleanScope` is set — the cleaner walks `{destination}/{basePackage}/` rather than the whole `destination`, so sibling groups sharing a destination are safe.

**Required**: Yes for groups that emit code. Markdown documentation groups may pass an empty string when their destination already points at the final folder.

**Type**: string. Format is language-specific — `HelloOrders.Domain` for C#, `hello_orders_contracts` for Python, `hello_orders_core` for Dart.

**C#: other groups reference a layer by its owner's `basePackage` (generator `0.23.0`, breaking).** When the Api group uses a domain type, it writes the namespace of the group that emits the Domain layer, not the project `name` plus `.Domain`. The same holds for `.Infrastructure`, `.Api` and `.Test`, and for `Assembly.Load` and `InternalsVisibleTo` targets. Through `0.22.0` a project with `name: Acme` and groups rooted at `Shop.*` generated `using Acme.Domain.Events;` and failed to build. A layer no group emits, the `Application` layer and `{name}DbContext` still use the project `name`. Nothing changes when `name` already equals the groups' root. In hand-written code, replace any `using <name>.<Layer>…;` that named the project root with the owning group's `basePackage`; a project that builds today has no such line. Two groups that emit the same layer must be told apart by `pillar`, or loading fails with `AMBIGUOUS_LAYER_OWNER` (§9).

### 8.6 `destination`

**Purpose**: Output directory for everything this group emits.

**Required**: Yes for groups that emit code.

**Type**: string (path). Absolute or relative; resolution rules as in [Working directory and path resolution](#working-directory-and-path-resolution).

**Hard rule**: When sibling groups share a `destination`, each group's artifacts (including any supporting files registered by the artifact) must only write inside `{destination}/{basePackage}/`. Cross-group writes are erased the next time a sibling regenerates with `cleanGenerated: true`. Split the artifact into per-layer artifacts whose subtrees do not overlap.

### 8.7 `artifacts`

**Purpose**: List of artifact types the group emits. Each entry must match an artifact registered in the language's factory (§11).

**Required**: Yes for groups that emit code.

**Type**: array of strings.

**Validation**: Unknown types fail the load with every available artifact for that language listed. Obsolete v1-AsyncAPI types (`asyncCommand`, `asyncCommandHandler`, `asyncCommandHandlerInterface`, `asyncSagaOrchestrator`, `commandClass`, `commandHandlerInterface`, `commandHandler`, `sagaOrchestrator`) are silently ignored with a one-line warning steering you toward v2-clean event-only modelling.

### 8.8 `configs`

**Purpose**: Pass-through additional-properties map for the underlying codegen configurator. Every key/value pair becomes visible to Mustache templates and to artifact code as additional properties.

**Required**: Optional.

**Type**: `object<string, string>`.

**Well-known keys**:

| Key | Required for | Purpose |
|-----|--------------|---------|
| `applicationPackage` | `azureFunctionTopicTrigger`, `azureFunctionTimerTrigger`, `eventContractTest` | Fully-qualified .NET namespace of the Application project (e.g. `HelloOrders.Application`). When unset, the event-contract test artifact derives `{name}.Application`; the Azure Functions templates require an explicit value. |

This is the complete list of keys the artifact code itself reads from the `configs` map. Arbitrary additional keys are allowed and will pass through to templates as additional properties, but no other artifact currently introspects them.

```json
{ "configs": { "applicationPackage": "HelloOrders.Application" } }
```

### 8.9 `cleanGenerated`

**Purpose**: When `true`, the generator deletes the group's generated subtree before regenerating its artifacts. Stale files left over from removed schemas, renamed artifacts, or dropped artifact types disappear without manual cleanup.

**Required**: Optional. Default `false`.

**Wipe target** (in priority order):

1. If `cleanScope` is non-empty, every listed path (relative to `destination`) is deleted recursively.
2. Otherwise the language's generated-folder name (`gen-src/` for C#, `_generated/` for Python) is used as a folder-name pattern walked under `{destination}/{basePackage}/`.

Files outside the wipe target are never touched — hand-written consumer code is safe. The file `CHANGELOG.md` is preserved across wipes inside any cleaned subtree.

**Interactions**:

- The wipe is **gated on a full-group regen for every language target**. Single-artifact runs and filtered runs (where `--artifact <type>` is set) skip the wipe so partial regen against a wiped tree cannot delete files belonging to other artifacts. This rule is enforced uniformly across C#, Python, Dart/Flutter, and Markdown — there is no per-language exception.
- The internal consumer-verification workflow forces `cleanGenerated: true` on every group regardless of the file's setting.
- For languages without a generated-folder convention (Markdown, Dart) `cleanGenerated: true` is meaningful only when `cleanScope` is also set — otherwise the cleaner logs a one-line "skipped" message and emits nothing.

### 8.10 `cleanScope`

**Purpose**: Explicit list of relative paths to wipe (under `destination`) when `cleanGenerated` is true. Overrides the language's generated-folder convention.

**Required**: Optional. Use this for Markdown / Dart groups, or whenever a group writes to a dedicated subtree that should be wiped wholesale.

**Type**: array of strings (relative paths).

**Validation**: Each path must be relative and must not escape `destination` via `..` segments. Invalid entries fail the load.

```json
{
  "cleanGenerated": true,
  "cleanScope": ["hello_orders_core/lib/presentation"]
}
```

> **Enumerate the generated paths. Never name a parent directory that also holds hand-authored files.**
>
> `cleanScope` is a recursive delete, and it does not distinguish generated output from anything else living under the same path. A consumer set a Markdown group's scope to a `flows/` directory whose `scenarios/` subfolder was the generated part; the next run wiped **21 hand-authored flow documents** alongside it. They came back from git, which is the only reason it was a scare rather than a loss.
>
> The correct scope was the generated leaves, listed one per domain — `flows/orders/scenarios`, `flows/billing/scenarios`, and so on — never the `flows/` tree that contains them. When generated and hand-authored output share a tree, enumerate the generated paths explicitly, and re-check the list whenever a domain is added.

**Glob patterns are not supported** — entries are matched as literal relative paths, consistent with the type above. A wildcard entry does not expand and does not error: it matches nothing, the clean silently does nothing for that entry, and the group regenerates over stale output that still looks current (consumer-verified, 2026-08-12). This is the same failure as the one above in the opposite direction, and it is the quieter one — an over-broad scope announces itself by deleting something, while a scope that matches nothing announces nothing at all. After changing `cleanScope`, verify from the run output that the files you expected to be removed actually were.

### 8.11 `filter` *(AsyncAPI workers only, v1)*

**Purpose**: Predicate tree restricting which AsyncAPI worker targets the group generates. **The filter applies to AsyncAPI workers only — every other artifact type ignores it.** A missing or empty filter includes everything (backwards compatible).

**Required**: Optional.

**Type**: object with exactly one top-level operator.

**Operators**:

| Operator | Value shape | Meaning |
|----------|-------------|---------|
| `hasExtension` | string | The named extension is present on the target. |
| `notHasExtension` | string | The named extension is absent on the target. |
| `extensionEquals` | `object<dottedPath, expected>` | Dotted path equality against a nested value within an extension. Multiple entries are AND-ed. |
| `allOf` | array<filter> | Every sub-filter matches. |
| `anyOf` | array<filter> | At least one sub-filter matches. |
| `not` | filter | Negates a single sub-filter. |

**Validation**: A filter block must contain exactly one operator (wrap multiples in `allOf`/`anyOf`). Unknown operators fail the load.

```json
{ "filter": { "hasExtension": "x-ai" } }
```

```json
{
  "filter": {
    "allOf": [
      { "extensionEquals": { "x-worker.type":   "eventHandler" } },
      { "extensionEquals": { "x-worker.domain": "Orders" } }
    ]
  }
}
```

### 8.12 Dart-only group fields

These fields are honoured only when `language` resolves to `dart` or `flutter`. Other languages parse them but ignore them. Invalid values fail the load and name the accepted set.

The resolved values are surfaced to templates under the `dartGroup.*` namespace (`dartGroup.unknownEnumPolicy`, `dartGroup.formatPolicy`, `dartGroup.mutationOverrides`).

#### 8.12.1 `unknownEnumPolicy`

**Purpose**: How the generated deserialiser treats enum values it does not recognise.

**Required**: Optional. Default `fallback`.

**Allowed values**: `strict` (throw) \| `fallback` (use the enum's configured fallback member) \| `null` (set the property to `null`; only valid for nullable fields).

#### 8.12.2 `formatPolicy`

**Purpose**: Validator severity for generated runtime checks (consumed by the generated validator tests).

**Required**: Optional. Default `strict`.

**Allowed values**: `strict` \| `lax`.

#### 8.12.3 `mutationOverrides`

**Purpose**: Operation IDs that should be classified opposite to the default query-vs-mutation rule, consumed by the Riverpod provider split. Operations the generator would otherwise treat as queries become mutations and vice versa.

**Required**: Optional. Default `[]`.

**Type**: array of strings (operation IDs).

```json
{
  "language": "dart",
  "unknownEnumPolicy": "fallback",
  "formatPolicy": "strict",
  "mutationOverrides": ["listPendingApprovals"]
}
```

### 8.13 Domain scope — `domains` and `pillar`

A group generates every domain in the bundle unless it says otherwise. These two fields are the two ways of saying otherwise. They answer different questions and are **mutually exclusive**; declaring both fails the load.

#### 8.13.1 `domains`

**Purpose**: scope a group to a subset of the project's domains, so a split-repo product (one project file per repo, each owning a subset) generates exactly the code it owns.

**Required**: Optional. Absent means all domains — byte-identical to a project that has never used the field.

**Type**: object carrying **exactly one** of `include` or `exclude`, each a non-empty array of domain names.

```json
{
  "language": "csharp",
  "destination": "src/Scheduling",
  "domains": { "include": ["scheduling", "roster"] }
}
```

**Rules**:

- Exactly one of `include` / `exclude`. Both non-empty fails with `INVALID_DOMAIN_FILTER`, checked language-agnostically.
- Each named domain must be a member of `info.x-domains` when that registry is non-empty; the check is **permissive** when the registry is absent, because the field still carries a literal, checkable value.
- Shared value objects and enums carry no domain and are retained by **dependency closure** from the in-scope entities — a filter never strips a type an in-scope entity is typed against.
- Derived DTOs (`New*` / `Update*` / `Basic*`) follow their owning entity.
- Async workers, events, channels, and Markdown docs scope from the same decision, so one filter covers every surface.
- **A cross-domain aggregate edge fails loud.** An in-scope entity that `belongsTo` an out-of-scope entity raises `CROSS_DOMAIN_ENTITY_REFERENCE` rather than silently re-widening the filter. The only thing that softens it is a declared hold — see §8.13.2.

**This field is not a legacy of `pillar`.** It scopes a group *within one bundle*, for reasons that need have nothing to do with pillar ownership — a Flutter group declaring `{"exclude": ["crm"]}` because the mobile app does not need that domain is a correct use that predates pillars entirely.

#### 8.13.2 `pillar`

**Purpose**: name the pillar this group generates for, and let the spec's `info.x-pillars` registry supply its domains instead of hand-listing them.

**Required**: Optional. See `Vendor_Extensions.md` §14 for the registry itself.

> **Available since generator `0.14.0`.** The field shipped in `0.6.0` as `service`, bound to `info.x-services`; `0.14.0` renamed both outright, with no alias. A group still carrying `"service"` now fails to load with `INVALID_PILLAR_FILTER`, naming `pillar` — rename the key, the value is unchanged. See `compatibility.md` §24 and §41.

**Type**: string — a pillar name declared in `info.x-pillars`.

```json
{
  "language": "csharp",
  "destination": "src/Scheduling",
  "pillar": "scheduling-pillar"
}
```

**Rules**:

- `pillar` and `domains` are **mutually exclusive**; both set, or a blank value, fails with `INVALID_PILLAR_FILTER`. There is no merge semantics for two answers to one question.
- The pillar's owned domains expand into an ordinary `include` filter, which then takes exactly the path a hand-written include list takes. **No second filtering mechanism exists** — nothing downstream learns about pillars.
- Membership is checked when the filter is applied, not when the project file is parsed: the registry is built from the spec, which project-file validation cannot see.
- **Unlike an unregistered domain name, an unresolvable pillar is fail-closed.** `UNKNOWN_PILLAR_FILTER` when the registry is absent, empty, or does not declare the pillar; `EMPTY_PILLAR_DOMAINS` when the named pillar owns zero domains. There is nothing to expand the name to, and generating everything is worse than any explicit value.
- **Binding to a pillar does not by itself soften the cross-domain edge check.** A pillar-bound group whose owned domains reach a foreign entity still fails with `CROSS_DOMAIN_ENTITY_REFERENCE`. What softens it is a **declared hold**, or, from generator `0.15.0`, a reference declared `x-references: { entity: X, resolve: remote }`, which is a plain uuid column and never an edge (`Vendor_Extensions.md` §14.11). A hold works when the group's pillar declares `holds: [X]` and `X`'s owner publishes a `ReadX` schema: the reference resolves to that replica, and the group emits a read-only `ReadX` with no write surface. The group must register `heldEntity` and `heldEntityConfiguration` for the replica to exist; otherwise the rebound navigation names a class nothing emits. From generator `0.18.0`, `validate` and `generate` warn `PROJECT_HELD_ENTITY_MISSING` when no C# group bound to the pillar registers `heldEntity`, and `PROJECT_CONFIGURATION_CONVERTERS_MISSING` when a group registers `heldEntityConfiguration` over a replica that maps a scalar enum, or `entityTypeConfiguration`, and no C# group with the same `basePackage` registers `infrastructureProject`. Both configurations call `EnumValueConverter<T>`, which only `infrastructureProject` emits, so register `heldEntityConfiguration` in the Infrastructure group. See `Vendor_Extensions.md` §14.3.
- **Validate the project file, then generate each pillar.** `validate <project>.json` builds each group's context and reports a cross-domain edge the group cannot generate (`CROSS_DOMAIN_ENTITY_REFERENCE`); spec-level `validate` does not. From generator `0.18.0` it also stops a child-create nested under a parent in another pillar, with `OPERATION_NESTED_CROSS_PILLAR` (ERROR), which spec-level `validate` reports too; through `0.17.0` that route passed both levels and failed `generate`. At generator `0.16.0`, as at `0.15.0`, a cross-pillar `belongsTo` with a hold generates in both pillars' groups, and a cross-pillar reverse `hasMany` fails both with `PILLAR_CROSS_BOUNDARY_REFERENCE`, which spec-level `validate` reports too. At `0.14.0` the `belongsTo` failed in the owner's group (`CROSS_DOMAIN_ENTITY_REFERENCE`) and the reverse edge failed in both. `Vendor_Extensions.md` §14.10 has the measured matrix and the forms that generate.

**Declare `pillar` even in a split-bundle topology, where the domain filter is redundant.** The identity is not redundant: resolving a reference to a held entity asks *"is this target held by **this group's** pillar"*, and a per-pillar bundle that preserves the whole registry for ownership context has more than one candidate to choose from.

**Worker host groups are per pillar too.** A host group (`azureFunctionTopicTrigger`, `hostedTopicConsumer`) emits only the workers in its own pillar's scope, while `workerPlacement` is project-wide. A project with several pillars gives each pillar its own host groups. §17.2 covers this and two placements `validate` does not catch.

---

## 9. Validation Rules

The project file fails to load when any of the following conditions hold. All errors carry a stable error code and an actionable suggestion.

| Code | Condition |
|------|-----------|
| `PROJECT_DB_CONTEXT_CLASSNAME_INVALID` | `dbContextClassname` is set and not a valid C# identifier. |
| `PROJECT_TENANCY_EMPTY` | `tenancy: {}` declared with no `tenant` key. |
| `PROJECT_TENANCY_TENANT_MISSING` | `tenancy` block present but `tenant` absent. |
| `PROJECT_TENANCY_FIELD_MISSING` | A tier is missing `entity`, `foreignKey`, or `marker`. |
| `PROJECT_TENANCY_ENTITY_NOT_PASCAL` | Tier `entity` is not PascalCase. |
| `PROJECT_TENANCY_FK_NOT_PASCAL` | Tier `foreignKey` is not PascalCase. |
| `PROJECT_TENANCY_FK_NOT_ID` | Tier `foreignKey` does not end in `Id`. |
| `PROJECT_TENANCY_MARKER_NOT_INTERFACE` | Tier `marker` does not match `^I[A-Z][A-Za-z0-9]*$`. |
| `PROJECT_TENANCY_ENFORCEMENT_UNKNOWN` | **From generator `0.21.0`.** `tenancy.enforcement` is set to anything but `route` (§4.1). |
| `UNKNOWN_WORKER_HOST` | **From generator `0.20.0`.** `workerPlacement.messages.default`, or a key under `messages`, names neither `azureFunctions` nor `genericHost` (§17). |
| `UNKNOWN_EMIT_ASSERTIONS` | **From generator `0.21.0`.** `functionalTests.emitAssertions` is neither `off` nor `strict` (§18). |
| `TRIGGER_REQUIRES_EVENT_RUNTIME_IMPL` | **From generator `0.20.0`, breaking.** A group registers `azureFunctionTopicTrigger`, `hostedTopicConsumer` or `heldEntityHydrationTrigger`, and no group of the same language registers `eventRuntimeImpl` (§10). |
| `PROJECT_BROKER_TYPE_UNKNOWN` / `PROJECT_BROKER_TOPOLOGY_UNKNOWN` / `PROJECT_BROKER_DIALECT_UNKNOWN` | `broker.type` / `broker.topology` / `broker.outboxDialect` set to an unrecognised value. |
| `INVALID_DART_GROUP_FIELD` | `unknownEnumPolicy` or `formatPolicy` outside its accepted set (Dart/Flutter groups only). |
| `INVALID_FILTER` | `groups[].filter` malformed — multiple top-level operators, unknown operator, wrong value shape. |
| `INVALID_DOMAIN_FILTER` | `groups[].domains` declares both `include` and `exclude` non-empty. |
| `INVALID_PILLAR_FILTER` | `groups[].pillar` set alongside `groups[].domains`, or set to a blank value — or the group still carries the pre-`0.14.0` key `service`, which is refused by name rather than ignored. |
| `UNKNOWN_PILLAR_FILTER` | `groups[].pillar` names a pillar `info.x-pillars` does not declare — or the registry is absent or empty. Raised at filter-application time, not at parse time. |
| `EMPTY_PILLAR_DOMAINS` | `groups[].pillar` names a pillar that owns zero domains. |
| `UNKNOWN_LANGUAGE` | `groups[].language` not registered. |
| `AMBIGUOUS_LAYER_OWNER` | **From generator `0.23.0`, breaking.** Two C# groups emit the same layer (both register `domainProject`, `infrastructureProject` or `apiProject`), share no `pillar` and differ in `basePackage`, so a group that reads the layer cannot tell which namespace to use. Raised before any destination is cleaned. Fix: give the groups distinct `pillar` values (a reading group takes the owner in its own pillar, else the one group without a `pillar`), or register the layer's project artifact on one group only (§8.13.2). |
| `UNKNOWN_AUTHORIZATION_MODE` | `authorization.mode` is neither `roles` nor `scopes` (§16). |
| `AUTHORIZATION_SHADOW_REQUIRES_SCOPES_MODE` | `authorization.shadow: true` with `mode` absent or `roles` (§16). |
| `UNKNOWN_ROLES_SHAPE` | `authorization.claims.rolesShape` is neither `name` nor `object` (§16). |
| (cleanScope) | A `cleanScope` entry is absolute or contains `..` segments. |
| `PERSISTENCE_*` | Persistence-block validation failures. The full list lives in §6.6 alongside the field definitions. |

The OpenAPI / AsyncAPI / Arazzo spec contents are validated separately by the per-spec validators after the project file loads.

**Removed in generator `0.20.0`:** `PROJECT_TENANCY_REQUIRED`, `PROJECT_EVENT_RUNTIME_TENANCY_REQUIRED` and `PROJECT_EVENT_CONTRACT_TEST_TENANCY_REQUIRED`. A single-tenant project may now register the event runtime, `tenancyMarker` and `eventContractTest` (§4.1).

**Project-level `validate` findings** (they need the specs, so they run under `validate <project>.json` and `generate`, not at load):

| Code | Severity | From | Fires when | Fix |
|---|---|---|---|---|
| `WORKER_PLACEMENT_UNKNOWN_WORKER` | ERROR | `0.20.0` | A name under `workerPlacement.messages` matches no AsyncAPI operation. | Spell it as the operation key under `operations`, or remove the line. |
| `WORKER_PLACEMENT_NOT_A_TOPIC_WORKER` | ERROR | `0.20.0` | The name is a scheduled job, a publisher or an `x-ai` worker. | Remove it. Only a topic worker can be placed. |
| `WORKER_PLACEMENT_NO_HOST_GROUP` | ERROR | `0.20.0` | A topic worker is placed on a host whose artifact (`azureFunctionTopicTrigger` or `hostedTopicConsumer`) no C# group registers, so nothing emits it. | Register the host artifact, or place the worker elsewhere. |
| `WORKER_PLACEMENT_CONFLICT` | ERROR | `0.20.0` | An operation is listed under both hosts, or (from `0.22.0`) in two pools of `genericHost`, or one C# group registers both `azureFunctionTopicTrigger` and `hostedTopicConsumer`. | List it once; give each host artifact its own group. |
| `WORKER_PLACEMENT_POOL_NAME_INVALID` | ERROR | `0.22.0` | A pool name under `genericHost` is not a DNS-1123 label of at most 20 characters, so it cannot name a Deployment. | Use lowercase letters, digits and `-`, starting and ending with a letter or digit (§17.1). |
| `WORKER_PLACEMENT_POOL_EMPTY` | ERROR | `0.22.0` | A pool under `genericHost` lists no worker, so it would deploy nothing. | Add its workers, or remove the pool. |
| `WORKER_K8S_NAME_COLLISION` | ERROR (generation) | `0.20.0` | In a group registering `hostedTopicConsumer`, two topic workers derive the same `k8sName` for `workers.json` (kebab-case of the operation id, at most 52 characters). Generation fails. | Rename one operation. |
| `WORKER_TIMEOUT_EXCEEDS_FUNCTIONS_LOCK_RENEWAL` | WARNING | `0.21.0` | A topic worker on `azureFunctions` declares an `x-worker.timeout` above 240 s, while a C# group registers `azureFunctionTopicTrigger` (`AsyncAPI_Handbook.md` §4.3). | Place it on `genericHost` (§17), or lower its timeout to 240 s or less. |
| `PROJECT_AUTHORIZATION_RUNTIME_MISSING` | WARNING | `0.20.0` | A C# group registers `apiController`, some operation declares `x-roles` or `x-scopes`, and no C# group with the same `basePackage` registers `authorizationRuntime`. The generated controllers then fail `dotnet build` (CS0246 / CS0234) on `[RoleRequired]` / `[ScopesRequired]`. | Register `authorizationRuntime` in that group or a same-`basePackage` group (§11.1). Ignore it only if you hand-write those types. The operation scan covers the whole spec, whatever the group's `pillar` or `domains`. |
| `TENANCY_ENFORCEMENT_ROUTE` | WARNING | `0.21.0` | `tenancy.enforcement: route` is set and a tenant-owned entity is listed by a route with no tenant path parameter (§4.1). | Add the tenant path parameter to those routes, then remove the switch. |
| `VISIBILITY_NOT_ENFORCED` | WARNING | `0.21.0` (Python groups) | A Python `repository` / `aiRepository` group reads a tenant-owned entity (§4.1). | Scope those Python queries to the tenant by hand. |

From generator `0.16.0`, `validate` also warns `FUNCTIONAL_TEST_TAG_UNGROUPED` when `functionalTests.collectionNamePattern` uses `{group}` and an operation tag is in no `collectionGroups` entry. That tag silently becomes its own collection (measured: `Tag 'Customers' is in no functionalTests.collectionGroups entry, so its functional tests get their own collection 'CustomersFunctionalTests'`), and nothing in the consumer's test project defines it. A pattern without `{group}` opts out.

---

## 10. Field Interactions and Cross-Field Behaviour

- **`name` ⟷ `dbContextClassname`** — when `dbContextClassname` is unset, the C# templates derive `{name}DbContext`. When `name` is also unset, they fall back to `AppDbContext`.
- **`name` ⟷ `configs.applicationPackage`** — the C# event-contract test artifact derives `{name}.Application` when no explicit value is set; if both are absent, the artifact fails with a hard error.
- **`groups[]` ⟷ event-runtime opt-in** — when any group registers the `eventRuntime` artifact (or the language equivalents `eventRuntimeImpl` / `eventRuntimeFunctions`), the generator stamps a project-wide `hasEventRuntime: true` additional property visible to every artifact in every group. This is the unambiguous opt-in marker for event-runtime emission.
- **`service` ⟷ `eventRuntime` (generator `0.16.0`, breaking)** — a C# group rendering `service` for an operation whose `x-emits` links to an AsyncAPI message requires some group to register `eventRuntime` (or `configs.hasEventRuntime`). Otherwise `validate` and `generate` fail with `PROJECT_EVENT_RUNTIME_REQUIRED` (ERROR), one finding per operation, naming its messages and the group. Before `0.16.0` such a project generated service methods that read `beforeSnapshot` / `afterSnapshot` without declaring them, and failed only at `dotnet build` (CS0103). Measured: adding `service` to `hello-orders`' Domain group gives six findings, one per `x-emits` write. **Fix:** register `eventRuntime` in a C# Domain group, or remove the operation's `x-emits`. Through `0.19.0` `eventRuntime` also required a project-level `tenancy` block; from `0.20.0` it does not (§4.1). The generator's own fix text still says it does; ignore that clause. **Scope (generator `0.17.0`):** an operation counts for a group only when the group's `pillar` or `domains.include` scope keeps it, the same test `service` applies when it renders. At `0.16.0` a filtered group was flagged for every `x-emits` operation in the whole spec, so a pillar owning no event-emitting entity failed with one finding per emitting operation elsewhere (`clabonte/generator#2651`). An unfiltered group is flagged as before. Every pillar-bound group that renders an emitting operation still needs `eventRuntime` registered somewhere in the project (`Vendor_Extensions.md` §14.6).
- **Topic-worker host artifacts ⟷ `eventRuntimeImpl` (generator `0.20.0`, breaking)** — a project registering `azureFunctionTopicTrigger`, `hostedTopicConsumer` or `heldEntityHydrationTrigger` must register `eventRuntimeImpl` in some group of the same language, or the load fails with `TRIGGER_REQUIRES_EVENT_RUNTIME_IMPL`, naming the trigger artifact and its group. The triggers call the message decision core (`MessageDecisionCore`), which only `eventRuntimeImpl` emits into Infrastructure. Through `0.19.0` such a project loaded and emitted triggers that did not compile. The check is project-wide and order-independent, and runs at load and again before `generate` cleans any destination. **Fix:** add `eventRuntimeImpl` to the Infrastructure group (with its own destination subtree), or drop the trigger artifact. A project that already registers both is unaffected.
- **`workerPlacement` ⟷ host groups (generator `0.20.0`)** — a C# group registering `azureFunctionTopicTrigger` is the Azure Functions host, one registering `hostedTopicConsumer` is the generic host, and each emits only the topic workers placed on it (§17). With no `workerPlacement`, every topic worker is on Azure Functions, so a `hostedTopicConsumer` group emits no consumer.
- **`namingOverrides` ⟷ `x-enumCase`** — `x-enumCase: preserve` on a schema wins over a project-wide `enumValue` override.
- **`tenancy` ⟷ `x-entity.belongsTo`** — entities whose `belongsTo` references the tenancy entities receive the corresponding `I{Tenant}Scoped` marker interface in the C# target. From generator `0.15.0`, so does an entity with a `resolve: remote` reference to the tenant entity (§4.1). The project-file loader does not validate that `tenancy.tenant.entity` resolves to a real `x-entity` schema; see §4.1 for the downstream symptoms.
- **`broker.outboxDialect` ⟷ event-runtime functions artifact** — `postgres` emits a stub in the drainer; only `sqlServer` produces a working runtime today.
- **`persistence` ⟷ `x-entity`** — every `x-entity` schema in the bundled spec must resolve to a backend descriptor (either via `persistence.entities.<EntityName>` or `persistence.default`). Unresolved entities fail the load. `x-value-object` schemas are excluded — they persist as part of their owning entity.
- **`persistence` ⟷ `tenancy`** — orthogonal. Tenant scoping is generated against the resolved backend kind: FK column for `relational`, partition key for `document`, key prefix for `blob`, both sides for `hybrid`.
- **`persistence` ⟷ `aiAccess`** — AI-scoped repository methods inherit the entity's backend kind. Generated AI surfaces use the same `kind`-specific template family as the production repository.
- **`persistence.entities.<Entity>Snapshot` ⟷ snapshot artifacts** — snapshots flow through `persistence` keyed as `<Entity>Snapshot`. Absent rows inherit the parent entity's descriptor. Pure-`blob` snapshot overrides cannot serve aggregate-id + timestamp lookups; use `hybrid` when snapshots need a separate store.
- **CLI `--group` ⟷ `groups[].name`** — case-insensitive exact match. A missing match lists every available group name in the error.
- **CLI `--skip-validation` ⟷ `validate` rules** — bypasses the OpenAPI + AsyncAPI + Arazzo validators, but the project-file structural validators (`PROJECT_*` codes) always run.

---

## 11. Supported Artifacts per Language

The full live inventory is available via `java -jar specfuse-generator.jar templates --language <lang>` — treat that command as the authoritative source. The lists below are a snapshot of every artifact type accepted in `groups[].artifacts[]` per language. Artifact-type strings are case-sensitive.

### 11.1 C# / `.csharp` artifacts

**Snapshot date:** 2026-09-17 (generator `0.12.0`). **Live source:** `templates --language csharp`.

`apiMapper`, `apiModel`, `domainModel`, `entity`, `annotatedEntity`, `valueObject`, `valueObjectConverter`, `enum`, `entityTypeConfiguration`, `repository`, `repositoryInterface`, `serviceInterface`, `service`, `dbContext`, `apiController`, `applicationServiceInterface`, `applicationService`, `apiFunctionalTest`, `useCaseInterface`, `entityBuilder`, `newDtoBuilder`, `updateDtoBuilder`, `valueObjectFake`, `apiModelFake`, `testSeed`, `serviceUnitTest`, `mapperTest` (+ legacy alias `autoMapperTest`), `valueObjectTest`, `efConfigTest`, `authMatrixTest`, `eventContractTest`, `infrastructureProject`, `domainProject`, `domainValidation`, `domainExceptions`, `apiProject`, `event` (+ legacy alias `asyncEvent`), `asyncEventHandler`, `asyncJobInterface`, `asyncConsumerRegistration`, `azureFunctionTopicTrigger`, `azureFunctionTimerTrigger`, `eventBuilder`, `tenancyMarker`, `eventRuntime`, `eventRuntimeImpl`, `eventRuntimeFunctions`, `snapshot`, `snapshotContext`, `recipeFixture`, `scenarioFunctionalTest`, `heldEntity`, `heldEntityConfiguration`, `heldEntityHydration`, `heldEntityHydrationTrigger` (generator `0.6.0`, for `holds`, see `Vendor_Extensions.md` §14), `fieldEncryptionConformanceTest` (generator `0.12.0`: known-answer vectors for the generated field-encryption format, with test-only key fakes).

`applicationService` is not printed by `templates` on `0.11.0` or `0.12.0`, though the jar still binds the name. It is kept here until that is confirmed either way.

**From generator `0.15.0`, `autoMapperTest` is renamed `mapperTest`** (`clabonte/generator#464`), because the generated C# maps through Mapperly instead of AutoMapper (§11.1.1). `autoMapperTest` stays an alias: a project file naming it loads and generates the replacement without a warning. Measured on `examples/hello-orders`, either id now emits one file, `Generated/Unit/Domain/DomainMapperTests.g.cs`, where `0.14.0` emitted two AutoMapper profile tests (Domain and Api). Prefer the new id in new project files. From the same release `templates` prints an aliased artifact once, under its own id, so neither `autoMapperTest` nor `asyncEvent` appears in its output. On `0.14.0` the C# `event` artifact was listed twice, once for the alias. **`event` is not removed:** it is still accepted and still emits one record per AsyncAPI event message.

#### Artifacts added in generator `0.20.0` and `0.21.0`

Three opt-in C# ids, none in the snapshot list above. Each emits only when registered.

| Id | From | Group | What it emits | Conditions |
|---|---|---|---|---|
| `hostedTopicConsumer` | `0.20.0` | A C# group of its own (the generic host), beside `asyncEventHandler`, `asyncConsumerRegistration` and `event` | One `<Handler>TopicConsumer` per topic worker placed on `genericHost` (§17), each reading the worker's subscription through one `ServiceBusProcessor` and calling the same `I<Handler>` the Functions trigger calls; the `HostedTopicConsumer` base and `WorkerHostContext`; `services.AddGeneratedWorkers()` (hosted services, graceful SIGTERM stop, `live` / `ready` health checks), and from `0.22.0` `builder.AddGeneratedWorkers()`, which selects a pool by `Workers:Pool` (§17.1); `workers.json` and `WorkerManifest` listing every topic worker and its host; `WorkerProvisioning` for a `provision` command. No `Program.cs`. | Registering it beside `azureFunctionTopicTrigger` in one group is `WORKER_PLACEMENT_CONFLICT`. Needs `eventRuntimeImpl` in the project (`TRIGGER_REQUIRES_EVENT_RUNTIME_IMPL`). Scheduled jobs stay in the Functions group. With no `workerPlacement`, it emits no consumer. |
| `tenantIsolationTest` | `0.21.0` | Test | `Generated/Unit/Infrastructure/TenantIsolationTests.g.cs`: per tenant-owned entity, a list never returns the foreign tenant's rows, a get, update or delete of a foreign row answers not found, `Unrestricted` sees both tenants, an empty visibility sees nothing, the model carries the `Tenant` filter. Adds the within-tenant facts for entities that declare `x-entity.visibility`. `TestSeed` gains the foreign tenant's graph. | Needs a `tenancy` block. Emits nothing unless a `Tenant` or `Visibility` filter is declared. The Test project must reference Infrastructure. Runs in memory under the unit-test step, not under the functional suite. |
| `bareIgnoreSourceScanTest` | `0.21.0` | Test | `Generated/Unit/Infrastructure/BareIgnoreSourceScanTest.g.cs`: fails when hand-written C# calls `IgnoreQueryFilters()` with no argument, which drops the `Tenant` filter too, unless the call is listed in `bare-ignore-query-filters.baseline` at the solution root. | Needs a `tenancy` block and `tenancy.enforcement` unset; otherwise it emits nothing. The baseline is yours, never generated, and only shrinks: a missing file reads as empty, and a line for a call that is gone fails as stale. |

`hostedTopicConsumer`'s host must register a `ServiceBusClient`, set `AzureServiceBus:TopicName`, and reference `Microsoft.Extensions.Hosting` and `Microsoft.Extensions.Diagnostics.HealthChecks`. The C# host wiring is in `docs/csharp-component-guide.md`.

#### 11.1.1 Generated C# mapping and test libraries (generator `0.15.0`)

Two package changes reach a consumer's C# projects on the first regeneration. Both replace a library that became commercially licensed.

- **Mapperly replaces AutoMapper** (`clabonte/generator#464`). No generated file references AutoMapper or `IMapper`. Each aggregate's `service` gains a companion `Mappers/{Aggregate}DomainMapper.g.cs` with three static partial classes: `{Aggregate}DomainMapper` (entity onto a response), `{Aggregate}DomainRequestMapper` (request onto an entity, including the in-place `Apply` a replace uses) and `{Aggregate}DomainMapperHooks`. The Domain and Api `AutoMapperProfile.g.cs` files are no longer emitted. **What a project must change:** reference `Riok.Mapperly` 4.x (the generator targets 4.3.1) in Domain and Api and remove the `AutoMapper` references; remove `AddAutoMapper(...)`; stop passing `IMapper` to a hand-written subclass of a generated `Default*Service`, whose constructor drops it. A hand-written profile is ported: an `AfterMap` becomes an implementation of the generated `static partial void OnAfterTo{Entity}(...)` in a non-generated `partial class {Aggregate}DomainMapperHooks`, and a `ForMember(... MapFrom ...)` becomes a user mapping method in a non-generated partial of the mapper. A response that is not a projection of its source (a computed response) compiles, and throws `NotImplementedException` until you implement `MapTo{Target}` in the hooks class. AutoMapper had no map for it either. The `apiMapper` classes now map a schema's `created` / `updated` onto the entity's `CreatedAt` / `UpdatedAt`, which both libraries left empty before. To enforce Mapperly's strictness, set `RMG012`, `RMG020`, `RMG037`, `RMG038` and `RMG066` to `error` in `.editorconfig`.
- **AwesomeAssertions replaces FluentAssertions in generated tests** (`clabonte/generator#2506`). Every generated test file that asserts carries `using AwesomeAssertions;`; the `.Should()` calls are unchanged. **What a project must change:** replace the test project's `FluentAssertions` package reference with `AwesomeAssertions` 9.6.0 or later, and switch hand-written tests' `using FluentAssertions;` in the same change. Both libraries define `Should()` on the same types, so a project importing both gets ambiguous-call errors. Hand-written tests written against FluentAssertions 7 also pick up FluentAssertions 8 semantics: `AllSatisfy` and `OnlyContain` pass on an empty collection, and `BeGreaterOrEqualTo` / `BeLessOrEqualTo` are replaced by `BeGreaterThanOrEqualTo` / `BeLessThanOrEqualTo`.


#### Authorization artifacts (generator `0.14.0`)

Three opt-in artifact ids, none in the lists above, which predate them. Each is emitted only when registered, because existing C# consumers own hand-written types of the same names and unconditional emission would break their next regeneration.

| Id | Languages | What it emits |
|---|---|---|
| `authorizationRuntime` | C#, TypeScript, Dart, Python | **C#** (API group): the whole gate in `{apiPackage}.Authorization` — `AuthorizedRole`, `RoleRequiredAttribute` / `RoleRequirement` / `RoleAuthorizationHandler` / `RoleAuthorizationFilter`, `ScopesRequiredAttribute` / `ScopeRequirement` / `ScopeAuthorizationHandler` / `ScopeAuthorizationFilter`, `PrincipalRole`, `IPrincipalReader` + `ClaimsPrincipalReader`, `IPrincipalPolicy` (allow-all default), `ITenantResourceCheck`, `IKioskSessionPolicy` + `KioskSessionPolicy`, `IGrantResolver`, `RoleGrants`, `ScopeCatalog`, `GrantMatcher`, and `AddSpecfuseAuthorization()`. From generator `0.22.0` it also emits `IOperationAuthorizer` + `OperationAuthorizer`, `OperationInvocation` and `OperationAuthorizationCatalog`: a transport-neutral check that gives a caller with no `HttpContext` (a worker, an agent tool) the decision the REST scope path makes for an `operationId`, refusing an `operationId` the catalog does not list. **TypeScript, Dart, Python**: `RoleGrants`, `ScopeCatalog` and the grant matcher only (`grantCovers` / `hasGrant`, `grant_covers` / `has_grant`). |
| `authorizationConformanceTest` | C#, TypeScript, Dart, Python | **C#** (Test group): `AuthorizationConformanceTests`, `FakeTenantResourceCheck`, `RoleClaimsTestPrincipalFactory`, `AuthorizationTestSupport.ForbiddenRoles`. Registering it also moves the generated `WithForbiddenRole` theory onto `ForbiddenRoles`, derived as registry − listed − superuser − implicit with no role hierarchy. **TypeScript, Dart, Python**: one test per grant-matcher known-answer vector, the table every runtime is proved against so no two disagree on a wildcard. |
| `authorizationMatrix` | Markdown | See §11.5. |

**The C# runtime is the same set of files in either `mode`** — measured: 23 files under `roles` and under `scopes`. `mode` changes the attribute on each controller action (§16), not the runtime. `AddSpecfuseAuthorization()` registers every service with `TryAdd`, so a host registration made before or after it wins. In a project that declares `tenancy` it registers `ITenantResourceCheck` as a **throwing placeholder**: a host that forgets to implement it fails by name on first use. **From generator `0.20.0`, a project with no `tenancy` gets `RoleSufficientTenantResourceCheck` instead**, which returns `true`, so the role or scope gate is the whole decision. A single-tenant host that relied on the throw to refuse every gated request must register its own check. **Also from `0.20.0`, `AddSpecfuseAuthorization()` adds `RoleAuthorizationFilter` and `ScopeAuthorizationFilter` to `MvcOptions.Filters`** when the host has not added them (`clabonte/generator#2864`). The attributes are metadata only, so through `0.19.0` a host that never added the filters served every gated action to every caller. After the bump such a host starts answering `401` / `403`. `PROJECT_AUTHORIZATION_RUNTIME_MISSING` (WARNING, §9) flags a C# `apiController` group whose `basePackage` no `authorizationRuntime` group shares. `generateUserHelper` (§16) adds `Utils/UserHelper.g.cs` to this artifact. The decision order is `IPrincipalPolicy`, then effective roles (claimed ∪ `implicit`), then a `superuser` role passes without the tenant check, then a listed `implicit` role passes without it, then listed ∩ held — empty is `403` — then `ITenantResourceCheck` with exactly the holding roles. A role not listed in `x-roles` never reaches the tenant check, so a hand-written handler that let a resource check admit unlisted roles does not carry over.

### 11.2 Python artifacts

**Snapshot date:** 2026-05-26. **Live source:** `templates --language python`.

`entity`, `enum`, `valueObject`, `repository`, `aiEntity`, `aiRepository`, `event`, `eventBuilder`, `snapshot`, `eventOutbox`, `defaultEventEmitter`, `asyncEventHandler`, `eventContractTest`, `aiWorker`.

**`aiWorker` settings name no model from generator `0.20.0` (breaking at run time).** Each worker's generated `*Settings` class declares `primary_model: str` with no default, read from `<PREFIX>_PRIMARY_MODEL`, where `<PREFIX>` is the worker's `x-worker.settingsPrefix` (`AsyncAPI_Handbook.md` §4.3). Through `0.19.0` it defaulted to `claude-sonnet-4-6`. A worker started without the variable fails at settings construction with pydantic's `primary_model Field required`. Set it in every environment that runs the worker, including local `.env.local` files.

From generator `0.20.0`, every Python project registering `repository` or `aiRepository` also gets `{core}/_generated/consumer_defaults.py` (a fallback error taxonomy) and `{core}/_generated/__init__.py`. A consumer-written `{core}/errors.py` still wins.

### 11.3 Dart / Flutter artifacts

**Snapshot date:** 2026-09-15 (generator `0.11.0`). **Live source:** `templates --language dart` (Dart and Flutter share the same factory).

`entity`, `enum`, `valueObject`, `dto`, `dartRepositoryInterface`, `dartApiClient`, `dartRepositoryImpl`, `dartUseCase`, `dartQueryProvider`, `mutationBinding`, `dartPaginatedNotifier`, `dartFormWidget`, `dartListTile`, `dartBarrelExport`, `dartProblemDetails`, `dartTypedError`, `dartDioErrorInterceptor`, `entityBuilder`, `newDtoBuilder`, `updateDtoBuilder`, `dartRepositoryFake`, `dartProviderOverrides`, `fixture`, `dartFixtureLoader`, `dartCodegenSmokeTest`, `serializationTest`, `dartRepositoryTest`, `dartQueryProviderTest`, `mutationBindingTest`, `validatorTest`, `dartPaginationTest`, `dartEtagTest`, `dartFormWidgetTest`, `dartListTileTest`.

`dartListTileTest` (from generator `0.15.0`) emits one render-smoke test per generated list tile, at `<package>/test/widgets/<model>_list_tile_test.dart`. It builds each tile's `Basic*` item from its entity's builder, so register `entityBuilder` in the same package. A `Basic*` model whose main model is not an entity gets no test.

### 11.4 TypeScript artifacts

**Snapshot date:** 2026-09-15 (generator `0.11.0`). **Live source:** `templates --language typescript`. Added in generator `0.5.8`.

`entity`, `enum`, `valueObject`, `dto`, `updateDto`, `entityBuilder`, `newDtoBuilder`, `updateDtoBuilder`, `typescriptApiClient`, `typescriptRepositoryInterface`, `typescriptRepositoryImpl`, `typescriptRepositoryFake`, `typescriptQueryComposable`, `mutationBinding`, `fixture`, `typescriptRepositoryTest`, `typescriptQueryComposableTest`, `mutationBindingTest`, `serializationTest`, `validatorTest`, `typescriptApiClientTest`.

`mutationBinding` is one concept with a per-language layout: a Riverpod mutation provider in Dart, a Vue mutation composable in TypeScript — one per write operation, each with a generated `mutationBindingTest`. The query side keeps its framework-named ids (`dartQueryProvider` / `typescriptQueryComposable`).

### 11.4.1 Removed artifact ids (deprecated in `0.11.0`, removed in `0.19.0`)

**From generator `0.19.0` these ids fail the load.** A group still declaring one fails `Project.Load` (`UNKNOWN_ARTIFACT_TYPE`): nothing is cleaned and nothing is generated. Measured on `0.19.0`: `validate` exits 2 with *"Group '…' declares artifact 'dartJsonFixture', which this generator does not recognise for language 'Dart'"*, followed by the recognised list. From `0.11.0` through `0.18.0` they generated the same files as their replacement and logged a `WARN`. Rename each in `artifacts[]`:

| Removed id | Replacement |
|---|---|
| `dartDto` | `dto` |
| `dartEntityBuilder` | `entityBuilder` |
| `dartNewDtoBuilder` | `newDtoBuilder` |
| `dartUpdateDtoBuilder` | `updateDtoBuilder` |
| `dartSerializationTest`, `typescriptSerializationTest` | `serializationTest` |
| `dartValidatorTest`, `typescriptValidatorTest` | `validatorTest` |
| `dartApiClientTest` | `dartEtagTest` (renamed, not merged: it tests the fake's entity-tag round trip, a different concept from `typescriptApiClientTest`) |
| `dartMutationProvider`, `typescriptMutationComposable` | `mutationBinding` |
| `dartMutationProviderTest`, `typescriptMutationComposableTest` | `mutationBindingTest` |
| `dartJsonFixture`, `typescriptFixture` | `fixture` |

### 11.4.2 Retired artifact ids (generator `0.15.0`)

| Retired id | What happens | What to do |
|---|---|---|
| `dartDtoMapper` | Emits no files. The project still loads and generates, with a load-time `WARN` naming the id and the group, under both `validate` and `generate`. A `cleanGenerated` group whose `cleanScope` covers `lib/data` removes the `lib/data/mappers/` files it emitted before. The generator's `0.15.0` notes said the next release would remove the id. It has not: on `0.19.0` it still loads, with the same `WARN` (measured). | Remove it from `artifacts[]` and delete any hand-written import of `data/mappers/`. The entity's own `toJson()` is the supported serializer; the old `toMap()` put enums, dates and nested models into the map raw (`clabonte/generator#1860`). |

### 11.5 Markdown artifacts

**Snapshot date:** 2026-09-02. **Live source:** `templates --language markdown`.

`scenarioDocument`, `scenarioIndex`, `recipeDocumentation`, `entityDiagram`, `eventCatalog`, `channelTopology`, `docsIndex`, `dataProtectionAudit`, `authorizationMatrix` (generator `0.14.0`).

#### `dataProtectionAudit` (generator 0.9.0)

Emits `DATA_PROTECTION_AUDIT.md` plus a machine-readable companion `data-protection-audit.json` carrying the same record. It reads the `x-classification` and `x-protection` declarations already in the specifications and turns them into the compliance deliverable those declarations exist to support, in six sections:

| Section | What it states |
|---|---|
| 1. Data inventory | every classified field, its classification, at-rest handling, and whether it is persisted |
| 2. Protection matrix | per field: at-rest, mode, blind index, masking, `unbounded`, reviewer, review date, review status |
| 3. Exceptions register | classified fields neither encrypted nor hashed, with the rationale and sign-off — the encryption programme's burndown list |
| 4. Key management | declared counts per control |
| 5. Egress map | every route by which a classified field leaves the datastore: entity snapshots, event payloads, AI readability under `aiAccess`, and the API operations that return it |
| 6. Erasure capability | per field, the erasure this system can perform **today**, and why |

**Register it or it does not exist.** The artifact is not emitted unless `dataProtectionAudit` appears in a group's `artifacts[]`, and nothing warns you at generation time that a compliance document you believe in is not being produced. `reachability` (§ the generator's `reachability` subcommand) is what audits a project file for unregistered guarantee-bearing artifacts — the generator's own words are that unregistered, *"the declared-protection evidence is never emitted and the compliance deliverable silently reverts to a hand-maintained spreadsheet nothing checks."*

```json
{
  "language": "Markdown",
  "name": "Compliance",
  "basePackage": "docs",
  "destination": "./docs/compliance/",
  "artifacts": ["dataProtectionAudit"]
}
```

**What it is and is not.** Every row is a declaration the specifications carry, not an observation of a running system — which is the property that makes it useful: it is diffable, so `git blame` answers *"when did this field start being encrypted, and who approved it"* with a commit. It says so itself, in the document. Three findings are reported and **none fails the build**: declarations reviewed more than 18 months ago, classified fields reaching a snapshot without a `x-snapshot-pii-acknowledged` entry, and fields made AI-readable by an explicit `aiAccess.readableProperties` listing that the implicit expansion would have withheld. The stale-review finding is deliberately non-fatal, and the generator explains why in the document: a build that fails on a calendar date guarantees somebody rubber-stamps a date bump to go green.

**The floors the audit's exception register is measured against are configured, not built in** — see §15 for the project file's `encryption` block, and note that a project declaring no profiles has no floors at all.

The runtime contracts behind these declarations — the key provider, the failure classifier, the poisoned-field tracker — are documented in `Field_Encryption_Runtime.md`.

Key custody, rotation cadence, split knowledge and dual control are runtime properties of the key provider and appear nowhere — the document states that silence explicitly rather than letting an empty section read as a pass.


#### `authorizationMatrix` (generator `0.14.0`)

Emits `AUTHORIZATION_MATRIX.md` and a `role-grants.json` companion from `info.x-roles`. The Markdown has one row per operation: its scopes, its declared `x-roles` verbatim, and **`Reachable by`**, the roles whose grants cover every scope it requires. A row where the two role columns differ is exactly the divergence `authorization.mode: scopes` would turn into behaviour, so this is the document to read before switching (§16). The JSON carries, per role, its declared grants, `implicit` / `superuser` / `delegable`, the scopes it covers and the operations it reaches. Opt-in like `dataProtectionAudit`: not emitted unless registered in a Markdown group's `artifacts[]`. Useful only against the mapping form of `info.x-roles` (`Vendor_Extensions.md` §3.1); a sequence declares no grants.

---

## 12. Deprecated and Silently-Ignored Fields

| Field | Status | Migration |
|-------|--------|-----------|
| `specifications` | Deprecated alias of `openApiSpecifications`. Accepted by the parser. | Rename to `openApiSpecifications`. |
| `groups[].artifacts[]` containing `asyncCommand`, `asyncCommandHandler`, `asyncCommandHandlerInterface`, `asyncSagaOrchestrator`, `commandClass`, `commandHandlerInterface`, `commandHandler`, `sagaOrchestrator` | Obsolete v1-AsyncAPI types. Ignored at generation with a one-line warning. | Reframe commands and sagas as events; remove from `artifacts`. |
| `asyncEvent` (artifact type) | Accepted as a backwards-compat alias for `event`. | Prefer `event` in new project files. |

### Silently-ignored fields

See foot-gun #1 at the top of this document.

---

## 13. Known Limitations

- **No `$schema` URL, no JSON Schema shipped.** The project file does not carry a `$schema` field today, and no JSON Schema is published with the generator. Editors and CI lint tools get no completion, no field-name validation, and no shape checking — every constraint is enforced by the parser at load time. Combined with foot-gun #1 (silent ignore of unknown fields), this is the project file's largest authoring hazard. **A JSON Schema (with `additionalProperties: false`) ships with the persistence rollout — phase 1a.**
- **`groups[].filter` is AsyncAPI-workers-only in v1.** Filtering by extension on REST operations, entities, or value objects is not supported today.
- **`broker.topology: bicep` and `broker.outboxDialect: postgres` are placeholders.** They are accepted by the parser but emit stub code in the runtime templates.
- **Tenancy artifacts are C# only today.** Python and Dart/Flutter consume the `tenancy` block indirectly (via AsyncAPI validation rules) but do not emit marker interfaces.
- **Cross-spec tenancy entity name is not validated.** A typo in `tenancy.tenant.entity` produces no load-time error; see §4.1 for the downstream symptoms.

---

## 14. Examples

### 14.1 Minimal project (single C# Domain group)

```json
{
  "openApiSpecifications": "./output/openapi-bundled.yaml",
  "name": "Sample",
  "groups": [
    {
      "language": "C#",
      "name": "Domain",
      "basePackage": "Sample.Domain",
      "destination": "./out/Backend/",
      "cleanGenerated": true,
      "artifacts": ["entity", "valueObject", "enum"]
    }
  ]
}
```

### 14.2 Realistic project (multi-language, multi-group, AsyncAPI, Arazzo, tenancy)

```json
{
  "openApiSpecifications": "./output/openapi-bundled.yaml",
  "asyncSpecifications":   "./output/asyncapi-bundled.yaml",
  "arazzoSpecifications":  "./api/specs/v3",
  "asyncSourceRoot":       "./api/specs/v3",
  "name": "HelloOrders",
  "description": "Backend, AI worker, and Flutter app code generation.",
  "dbContextClassname": "HelloOrdersDbContext",
  "namingOverrides": {
    "dbColumn":   "PascalCase",
    "wireField":  "camelCase",
    "enumValue":  "camelCase",
    "pathParam":  "camelCase",
    "queryParam": "camelCase"
  },
  "tenancy": {
    "tenant":    { "entity": "Organization",    "foreignKey": "OrganizationId",    "marker": "IOrganizationScoped" },
    "subTenant": { "entity": "Store", "foreignKey": "StoreId", "marker": "IStoreScoped" }
  },
  "broker": {
    "type":          "azureServiceBus",
    "topology":      "runtime",
    "outboxDialect": "sqlServer"
  },
  "persistence": {
    "connections": {
      "Main":        { "provider": "sqlServer", "managed": true },
      "LegacyCrm":   { "provider": "postgres",  "managed": false, "schemaCheck": "warn" },
      "AuditStore":  { "provider": "cosmos" },
      "ReceiptBlob": { "provider": "azureBlob" }
    },
    "default": { "kind": "relational", "connection": "Main", "schema": "dbo" },
    "entities": {
      "AuditLog":       { "kind": "document",   "connection": "AuditStore", "container": "audit" },
      "LegacyCustomer": { "kind": "relational", "connection": "LegacyCrm" },
      "Receipt": {
        "kind": "hybrid",
        "metadata": { "kind": "relational", "connection": "Main" },
        "content":  { "kind": "blob",       "connection": "ReceiptBlob", "container": "receipts" }
      }
    }
  },
  "stateDir": "./.specfuse/state",
  "groups": [
    {
      "language": "C#",
      "name": "Domain",
      "basePackage": "HelloOrders.Domain",
      "destination": "../Backend/",
      "cleanGenerated": true,
      "artifacts": [
        "domainProject", "entity", "valueObject", "enum",
        "repositoryInterface", "serviceInterface", "service",
        "event", "snapshot", "snapshotContext",
        "tenancyMarker", "eventRuntime"
      ]
    },
    {
      "language": "C#",
      "name": "AzureFunctions",
      "basePackage": "HelloOrders.AzureFunctions",
      "destination": "../Backend/",
      "cleanGenerated": true,
      "configs": { "applicationPackage": "HelloOrders.Application" },
      "artifacts": ["azureFunctionTopicTrigger", "eventRuntimeFunctions"]
    },
    {
      "language": "python",
      "name": "PythonWorkers",
      "basePackage": "",
      "destination": "../hello-orders-ai/tools",
      "cleanGenerated": true,
      "filter": { "hasExtension": "x-ai" },
      "artifacts": ["aiWorker"]
    },
    {
      "language": "dart",
      "name": "FlutterPresentation",
      "basePackage": "hello_orders_core",
      "destination": "../hello_orders_app/packages/",
      "cleanGenerated": true,
      "cleanScope": ["hello_orders_core/lib/presentation"],
      "unknownEnumPolicy": "fallback",
      "formatPolicy": "strict",
      "mutationOverrides": ["listPendingApprovals"],
      "artifacts": [
        "dartQueryProvider", "mutationBinding",
        "dartPaginatedNotifier", "dartFormWidget", "dartListTile"
      ]
    },
    {
      "language": "markdown",
      "name": "Documentation",
      "basePackage": "",
      "destination": "./docs/generated",
      "cleanGenerated": true,
      "cleanScope": ["."],
      "artifacts": ["entityDiagram", "eventCatalog", "channelTopology", "docsIndex"]
    }
  ]
}
```

---

## 15. Encryption

**Numbering note.** This section documents a top-level block that has been parsed since the `x-protection` axis landed in generator `0.6.0` and was never written up. It is numbered 15 rather than inserted after §6 so that every existing `§7`–`§14` cross-reference, here and in the other handbooks, keeps pointing at the same content.

```json
{
  "encryption": {
    "profiles": ["law25", "pci"],
    "keyScope": "tenant"
  }
}
```

**Absent means no floors, and nothing says so.** This is the whole reason the section exists. An absent `encryption` block, or an absent `profiles` list, means **no compliance floor is applied to any declaration** — and the result is indistinguishable, from a validation run, from a project whose floors are all satisfied. A project can classify a field `credential`, declare `atRest: none` with a one-word rationale, and validate clean, not because the declaration was reviewed against a floor but because no floor was ever configured. Same shape as *"Register it or it does not exist"* in §11.5, and the same remedy: declare the block deliberately, even if the answer is one profile.

### `profiles`

A **union of floors, not a ladder.** Each declared profile sets a minimum `atRest` per classification token, and declaring two applies both; there is no ordering between them and no "highest wins". Three are recognised by the pinned generator (`0.12.0`):

| Profile | What it adds |
|---|---|
| `law25` | Privacy floors per classification token. A classified property below the floor is `PROTECTION_LAW25_FLOOR`, whose remedy is *declare `x-protection.atRest: encrypted`, or `hashed` (with a rationale stating the value is never read back in plaintext, unless classified `credential`)*. |
| `pci` | Cardholder-data floors. `cardholder` must be `atRest: encrypted` with `masking.first <= 6` and `masking.last <= 4`, or `atRest: hashed` with a rationale (PCI-DSS 3.5.1). `sad` must be `never-persist` — sensitive authentication data may not be stored after authorisation. Reported as `PROTECTION_PCI_FLOOR`. |
| `soc2` | Not a floor but a metadata gate: it makes `rationale`, `reviewedOn` **and** `reviewedBy` mandatory on every declared `x-protection` (`PROTECTION_SOC2_METADATA_REQUIRED`). A `reviewedOn` older than 18 months is a **finding**, never a build failure — see §11.5 for why that is deliberate. |

An unrecognised profile token is not a floor; it is simply not one of the three, and it configures nothing.

### `keyScope`

Declares the scope at which data keys are expected to exist. Two values are meaningful: **`tenant`** (matched case-insensitively) and **`global`**.

It does two things, and both are silent when the key is absent:

- **`tenant` turns on a spec-level check.** An encrypted property on an entity that is not tenant-scoped — no tenant in its `belongsTo` chain — is `PROTECTION_ENCRYPTED_TENANT_SCOPE_REQUIRED` (FE-G26). The remedy the generator names is *add the project's tenant to this entity's `belongsTo` chain, or set `encryption.keyScope: global` if this entity is intentionally global.* **With `keyScope` absent the check does not run at all**, so a non-tenant-scoped encrypted entity passes validation in a project that intended tenant-scoped keys.
- **The declared value is carried into the generated C# `EncryptionProfile.DeclaredKeyScope`**, where the runtime compares it against the scope the host's key provider is configured for and refuses to continue on a disagreement (`DeclaredKeyScopeMismatchException`) — because proceeding writes ciphertext keyed at a scope the specification never declared. Declare nothing and `DeclaredKeyScope` is `null`, and that mismatch can never be raised.

Anything other than `tenant` reads as "not tenant scoped" for the first check and is passed through verbatim for the second, so treat `global` as the spelling to use rather than a synonym of your own.

### Where the declarations it governs live

The block sets floors; the per-property decisions are `x-classification` and `x-protection` in the OpenAPI document (`Vendor_Extensions.md` §1.5), and the deliverable that renders both is the `dataProtectionAudit` artifact (§11.5). None of the three is reachable from the other two by inspection, which is why each names the others.

---

## 16. Authorization

**From generator `0.14.0`.** A top-level block choosing how generated code decides authorization, and how the generated C# runtime reads the caller's claims. Every key is optional and the block may be absent: absent is `mode: roles`, which produces output **byte-identical** to `0.13.0`.

```json
{
  "authorization": {
    "mode": "scopes",
    "shadow": true,
    "claims": {
      "roles": "roles",
      "userId": "sub",
      "rolesShape": "object",
      "roleKey": "role"
    },
    "kioskSession": { "scheme": "KioskSession", "role": "Kiosk" },
    "testGrants": "./api/test-grants.yaml"
  }
}
```

`kioskSession.role` and `testGrants` are read from generator `0.15.0`. Generator `0.14.0` drops both without a word, like any unknown project key (Appendix A, step 1).

| Key | Default | What it does |
|---|---|---|
| `mode` | `roles` | `roles` \| `scopes`. Anything else fails the load (`UNKNOWN_AUTHORIZATION_MODE`). See below. |
| `shadow` | `false` | `true` emits **both** gates and compares them, never deciding by scopes. Requires `mode: scopes`; with `roles` — including an absent `mode` — it fails the load (`AUTHORIZATION_SHADOW_REQUIRES_SCOPES_MODE`). |
| `claims.roles` | `roles` | The role-claim type the generated `ClaimsPrincipalReader` reads. |
| `claims.userId` | `sub` | The user-id claim type. |
| `claims.rolesShape` | `name` | `name` (the claim value is the role name) \| `object` (the value is a JSON object carrying the role name under `roleKey`). Anything else fails the load (`UNKNOWN_ROLES_SHAPE`). |
| `claims.roleKey` | `role` | Under `rolesShape: object`, the property holding the role name. Typed tenant ids are read through `tenancy` (§4), not here; every other key of the object is kept on the principal's role as an attribute. |
| `kioskSession.scheme` | none | The authentication scheme a kiosk-session principal signs in under. Absent, `x-kiosk-session` is inert (`Vendor_Extensions.md` §3.3). |
| `kioskSession.role` | none | **From generator `0.15.0`.** The role the kiosk principal carries, compared ignoring case. Declaring it arms `KIOSK_SESSION_ROLE_UNSATISFIABLE`: an operation flagged `x-kiosk-session: true` whose `x-roles` lacks this role is an ERROR, because every kiosk call to it would be `403`. Validation only, with or without `scheme`; no generated byte changes. See `Vendor_Extensions.md` §3.3. |
| `testGrants` | none | **From generator `0.15.0`.** Path, relative to the project file, to a JSON or YAML file in the `info.x-roles` mapping shape. Feeds the generated C# authorization tests only. See below. |

`claims` and `kioskSession.scheme` are read only by the generated runtime; `kioskSession.role` only by validation; `testGrants` only by test generation; `mode` and `shadow` also change validation and controllers.

### `testGrants`

For a `scopes`-mode project whose roles' grants live **outside** the spec. With no grants in the spec, the generator cannot work out which roles an operation that declares only `x-scopes` admits. So the generated C# functional tests for such an operation fall back to a single anonymous test: no allowed-role theory, no forbidden-role theory. `testGrants` supplies the grants for **test derivation only**:

```yaml
# api/test-grants.yaml — the info.x-roles mapping shape (Vendor_Extensions.md §3.1)
Manager:
  grants: [customer.Customer.read, customer.Customer.write, order.Order.read, order.Order.write]
Customer:
  grants: [customer.Customer.read, order.Order.read]
```

Measured on a `hello-orders` copy in `mode: scopes`, with list-form `info.x-roles` and the operation-level `x-roles` removed so that only `x-scopes` remained. Without the key, `GetCustomer_AsAllowedRole_ShouldReturn200` was one `[Fact]` using an anonymous client. With it, `apiFunctionalTest` emitted an `[InlineData]` theory over the granted roles plus `AsAnonymous` (401) and `WithForbiddenRole` tests. **An operation that declares its own `x-roles` is unaffected**: on the unmodified copy, adding the key changed no generated file. `AuthorizedRole`, the authorization runtime and the conformance tests keep reading the spec, so no runtime file changes either way.

| Code | Fires when |
|---|---|
| `TEST_GRANTS_FILE_UNREADABLE` | the file is missing, or is not a map of role name to role metadata. Measured: `authorization.testGrants file './nope.yaml' cannot be read: file not found`. |
| `TEST_GRANTS_CONFLICTS_WITH_SPEC_GRANTS` | the spec's `info.x-roles` already carries grants — two sources of truth for what a role may do. |
| `TEST_GRANTS_REQUIRES_SCOPES_MODE` | `mode` is absent or `roles`, where nothing reads the file. |
| `TEST_GRANTS_GRANT_INVALID` | **From generator `0.16.0`.** A grant is neither `*` nor a well-shaped `<domain>[.<Entity>].<operation>` scope, the shape `ROLE_GRANT_INVALID` enforces on `info.x-roles`. `customer.*` is not a wildcard. Measured: `role 'Manager' declares the grant 'customer.*', which is neither the '*' wildcard nor a well-shaped <domain>[.<Entity>].<operation> scope, so it would match nothing.` Through `0.15.0` such a grant loaded and matched nothing. Its role then moved from the allowed-role tests to the forbidden-role tests, so the generated suite expected `403` for a role the author meant to admit. |

All four fail `Project.Load`, like the codes under "Where it is checked" below, and the CLI prints the message, not the code. **Prefer grants in the spec** (the mapping form, `Vendor_Extensions.md` §3.1) when you can. `testGrants` is for a project whose grants are owned elsewhere, and it does not make the generated runtime enforce them.

### `mode`

**It changes three things, and nothing on the wire** — four from generator `0.15.0`. No DTO, database column or event contract moves.

- **Severity.** The role/scope coherence rules (`Vendor_Extensions.md` §3.1) and `OPERATION_SCOPE_UNBOUND` are WARNING under `roles` and **ERROR** under `scopes`. `ROLE_DEAD_GRANT`, `SCOPE_UNHELD` and `OPERATION_SCOPE_SHAPE_INVALID` stay WARNING in both. Measured on a mapping-form copy of `hello-orders`: four coherence WARNINGs under the default became four ERRORs, and `validate` went from `PASSED` to `FAILED`, with only `"authorization": {"mode": "scopes"}` added.
- **The controller gate.** A generated C# controller action carries `[ScopesRequired("<scope>", …)]` from its `x-scopes` instead of `[RoleRequired(AuthorizedRole.X, …)]` from its `x-roles`. Measured on the same copy.
- **Which key a secured operation must declare** (from generator `0.15.0`). Under `scopes` without `shadow` it is `x-scopes`: `OPERATION_MISSING_SCOPES` (ERROR) fires on a non-`x-public` operation that declares none, including one that declares only `x-roles`, and `OPERATION_MISSING_ROLES` does not fire. Under `roles`, and under `scopes` with `shadow` (where the role decision still governs), `x-roles` stays required. Measured on a copy of `hello-orders` with one operation stripped of `x-roles` and another of `x-scopes`: `0.14.0` reports `OPERATION_MISSING_ROLES` on the first; a build of generator main reports `OPERATION_MISSING_SCOPES` on the second instead, and `OPERATION_MISSING_ROLES` again once `shadow: true` is added. Through `0.14.0` a scopes-mode spec had to keep an `x-roles` list on every operation.
- **Test derivation.** An operation declaring only `x-scopes` gets its roles derived — the roles whose grants cover every declared scope — for `AuthorizationMatrixTest`, the functional-test theories and recipe-fixture role selection, which used to read `x-roles` only.

**Switch only on a coherent registry.** `scopes` admits whichever roles' grants cover an operation's scopes, whatever its `x-roles` lists, so every `OPERATION_ROLE_UNLISTED` WARNING under `roles` is a role that `scopes` lets in. Read the `authorizationMatrix` artifact (§11.5) first, or run `shadow` in production before switching. From generator `0.15.0` the switch also checks every Arazzo actor against its role's grants (`ARAZZO_ACTOR_LACKS_SCOPE`, `Arazzo_Handbook.md` §4.6), and a sequence-form `info.x-roles` grants nothing: unmodified `hello-orders` passes `validate` under `scopes` on `0.14.0` and fails it with three of those ERRORs on a build of generator main. Move the registry to the mapping form first.

**Every `[ScopesRequired]` names its operation (generator `0.22.0`).** The generated attribute always carries `OperationId`, and in `scopes` and `scopes + shadow` mode `ScopeAuthorizationFilter` decides through `IOperationAuthorizer`, so REST and non-HTTP callers run one code path. A `[ScopesRequired]` with no `OperationId`, or one the catalog does not list, is refused with 403. A hand-written controller that uses the attribute must set `OperationId` to an operation of the spec. Roles mode is unchanged.

**The attribute is not the runtime.** `mode: scopes` changes the attribute on the controller whether or not the group registers `authorizationRuntime` — measured: without it, the controllers still carry `[ScopesRequired]` and import `{apiPackage}.Authorization`, which then has to supply that type. Register `authorizationRuntime` (§11.1), or own a hand-written `ScopesRequiredAttribute` in that namespace.

### `shadow`

For moving from roles to scopes without betting a release on it. Each action carries both `[RoleRequired]` and `[ScopesRequired(…, OperationId = "…")]`. **The role decision always governs the request.** The generated `ScopeAuthorizationFilter` evaluates the scope requirement alongside it, and when the two disagree it logs a structured event and increments the counter `authorization.divergence{operationId, decidedBy}` on the meter `Specfuse.Authorization`. A scope evaluation that throws is logged and never rethrown, so a defect on the scope side cannot fail a live request. Measured: both attributes and the counter are emitted.

### `generateUserHelper` (top-level key, generator `0.20.0`)

A boolean at the **top level** of the project file, not under `authorization`. Default `false`. With `true`, `authorizationRuntime` emits `Utils/UserHelper.g.cs` into the Api group: a static `{Api}.Utils.UserHelper.GetUser(ClaimsPrincipal)` returning the `AuthenticatedUser` every generated controller passes down (`new CallerContext(UserHelper.GetUser(User))`). It returns `Anonymous` with no roles for an unauthenticated principal, takes the user id from the `claims.userId` claim type (default `sub`, falling back to `Identity.Name`), and fills the roles, plus each role's tenant ids and attributes as properties, from the default `ClaimsPrincipalReader`. It ignores a custom `IPrincipalReader` registration, because a static method cannot resolve a service.

```json
{ "generateUserHelper": true }
```

**Delete a hand-written `{Api}.Utils.UserHelper` before turning it on**, or the build fails with CS0101. Absent or `false`, nothing is emitted and you keep writing the class yourself. Generator `0.19.0` drops the key without a word.

### Where it is checked

| Code | Fires when |
|---|---|
| `UNKNOWN_AUTHORIZATION_MODE` | `mode` is neither `roles` nor `scopes`. |
| `AUTHORIZATION_SHADOW_REQUIRES_SCOPES_MODE` | `shadow: true` with `mode` absent or `roles`. |
| `UNKNOWN_ROLES_SHAPE` | `claims.rolesShape` is neither `name` nor `object`. |

All three fail `Project.Load`. The CLI prints the message, not the code (`Validation failed: Authorization mode 'bogus' is not recognized. Valid modes: roles | scopes.`).

---

## 17. Worker Placement

**From generator `0.20.0`.** `workerPlacement` says which host runs each C# topic worker: Azure Functions (`azureFunctions`) or a generic .NET host such as a Kubernetes pod (`genericHost`). Keys under `messages` are AsyncAPI operation names, as written under `operations`.

```json
{
  "workerPlacement": {
    "messages": {
      "default": "azureFunctions",
      "genericHost": ["onCompanyPurgeStarted", "onDataExportRequested"]
    }
  }
}
```

| Key | Default | Meaning |
|---|---|---|
| `messages.default` | `azureFunctions` | The host of every topic worker no list names. |
| `messages.azureFunctions[]` | none | Operations placed on Azure Functions whatever the default. Use it when `default` is `genericHost`. |
| `messages.genericHost[]` | none | Operations placed on the generic host whatever the default. From generator `0.22.0` it may also be an object of named pools (§17.1). |

Any other key under `messages`, or a `default` that names no host, fails the load with `UNKNOWN_WORKER_HOST`. Without that check a misspelt host would leave the worker silently on Azure Functions.

**Only topic workers can be placed**: an `on-*` receive operation that is not `x-ai`. Scheduled jobs stay on the Azure Functions group, and AI workers are Python. A C# group's host follows from its artifacts: `azureFunctionTopicTrigger` makes it the Azure Functions host, `hostedTopicConsumer` the generic host (§11.1), and Domain, Application, Infrastructure and Test groups are never narrowed. Each host group emits only the workers placed on it, with their handler bases and registrations. Moving a worker is one line, a regeneration and a rebuild; the handler class does not change.

**Absent, every topic worker runs on Azure Functions**, and output is byte-identical to `0.19.0`. Generator `0.19.0` drops the key without a word.

The `WORKER_PLACEMENT_*` codes (ERROR, §9) catch a name that matches no worker, a name that is not a topic worker, a worker placed on a host no group emits, and a worker listed twice or a group registering both host artifacts. From generator `0.22.0` two more catch an invalid or empty pool (§17.1). They are silent for a project with no `workerPlacement`. They check the project as a whole, not each pillar: see §17.2 for the two placements they miss.

**When to move a worker to `genericHost`.** The Functions host renews a message lock for five minutes whatever the worker's `x-worker.timeout`, and a lock lapses 60 s after its last renewal. A worker kept on Functions whose timeout is above 240 s can lose its lock while its handler still runs, and the broker redelivers the message. From generator `0.21.0` `validate` reports it as `WORKER_TIMEOUT_EXCEEDS_FUNCTIONS_LOCK_RENEWAL` (WARNING), with or without a `workerPlacement`. The generic host renews each worker's lock for its own timeout plus 130 s, so long-running workers belong there.

### 17.1 Named pools

**From generator `0.22.0`.** `genericHost` is either the flat array above or an object that maps a pool name to operation names. A pool is a set of generic-host workers that deploys as its own unit, with its own shutdown budget. That way a slow handler's termination grace period does not hold a fast one's pod.

```json
{
  "workerPlacement": {
    "messages": {
      "default": "azureFunctions",
      "genericHost": {
        "fast": ["onAccountCreated"],
        "slow": ["onCompanyCreated"]
      }
    }
  }
}
```

- **The flat array is one pool, named `default`.** A worker that reaches `genericHost` through `"default": "genericHost"` belongs to pool `default` too. `azureFunctions` keeps the array form only.
- **A pool name is a DNS-1123 label of at most 20 characters**, so it fits a chart-prefixed Deployment name. Otherwise `validate` reports `WORKER_PLACEMENT_POOL_NAME_INVALID`. An empty pool is `WORKER_PLACEMENT_POOL_EMPTY`, and a worker listed in two pools is `WORKER_PLACEMENT_CONFLICT`.
- **`workers.json` gains a `pool` per entry and a top-level `pools` array**, mirrored by `WorkerManifest.Pools`. Each pool entry carries `name`, `k8sName`, `workers`, `subscriptions`, `shutdownTimeoutSeconds`, `terminationGracePeriodSeconds` (`shutdownTimeoutSeconds` + 30), `concurrencyTotal` and `criticality`: the fields a Helm chart needs for one Deployment per pool. `k8sName` is the pool name as-is. Any release or app prefix is the chart's to add. The new fields are additive, and `schemaVersion` stays `1`.
- **One image serves every pool; `Workers:Pool` picks which one a process runs.** Unset, it serves every pool. An unknown name fails at startup. The setting is read by `builder.AddGeneratedWorkers()` on the host builder. A project that declares a pool other than `default` has only that form, so a leftover `builder.Services.AddGeneratedWorkers()` stops compiling. A flat-array project keeps the `IServiceCollection` form.
- **`provision` still covers every worker**, whatever its pool. Run it once, not once per pool.

### 17.2 Several pillars

`workerPlacement` is project-level and keyed by operation name, but each host group renders only the workers in its own pillar's scope (§8.13.2). The `WORKER_PLACEMENT_*` codes check the project as a whole. So, in a project with more than one pillar:

1. **Give each pillar its own host groups.** Each pillar that has topic workers needs a group registering `azureFunctionTopicTrigger` and, if any of its workers are placed on `genericHost`, a group registering `hostedTopicConsumer`. Each group gets its own `pillar` and `destination`.
   - Why: a worker placed on a host its own pillar has no group for is emitted nowhere, and `validate` does not report it. `WORKER_PLACEMENT_NO_HOST_GROUP` is satisfied by a group in *any* pillar. The worker's Functions group drops it because it is placed elsewhere, and the other pillar's host group never sees it. Its subscription then has no consumer, and nothing fails. The per-pillar split is the shape the generator supports.
2. **Deploy each pillar as its own release or namespace, or prefix Deployment names per pillar in the chart.**
   - Why: from generator `0.22.0`, `pools[].k8sName` is the bare pool name. A flat `genericHost` array is pool `default` in every pillar, so two pillars deployed into one namespace under one prefix both declare a Deployment named `default`.
3. **A named pool lists workers of one pillar only.** Use per-pillar pool names, such as `a-fast` and `b-fast`.
   - Why: a pool that names workers from two pillars becomes two Deployments with the same name. Each one has half the workers and half the concurrency, and `validate` does not flag it.
4. **One database per pillar** (from the next generator release, which ships C# timer workers on the generic host).
   - Why: the generated scheduled-job lock and the `ScheduledJobRun` watermark are keyed by job name. The three runtime functions, `EventOutboxDrainerFunction`, `EventOutboxRetentionFunction` and `EventInboxRetentionFunction`, have the same name in every pillar. Two pillars sharing one SQL database would contend for one lock and one watermark row, and each would see the other's runs as skipped.

---

## 18. Functional Tests

`functionalTests` configures the generated C# functional tests. `collectionNamePattern` and `collectionGroups` assign tests to xUnit collections (Quick Reference, and `FUNCTIONAL_TEST_TAG_UNGROUPED` in §9).

### `emitAssertions` (generator `0.21.0`)

Whether a scenario step's `x-async.emit` is checked by the generated scenario test (`scenarioFunctionalTest`, `Arazzo_Handbook.md` §6.2).

| Value | Generated test |
|---|---|
| `off` (default) | Each `emit` entry is a reviewer comment, as through `0.20.0`. Output is byte-identical. |
| `strict` | Each `emit` entry is an awaited `Fixture.WaitForEventAsync<TEvent>(predicate, timeoutMs: N)` plus `Assert.NotNull`, so the test fails when the event is never published. `expect` is a subset predicate; `timeout` defaults to `PT10S`. |

```json
{ "functionalTests": { "emitAssertions": "strict" } }
```

Any other value fails the load with `UNKNOWN_EMIT_ASSERTIONS`. The default is `off` because existing scenarios carry `emit` declarations nobody has checked, so switching to `strict` can turn a green suite red. `strict` calls the `ApiTestFixture.WaitForEventAsync<TEvent>(Func<TEvent, bool>, int timeoutMs)` member that `x-async.await` already uses. It scans the outbox, so an event an earlier step wrote also satisfies a later `emit` unless `expect` is keyed on the step's own outputs.

---

## Appendix A — Lifecycle Summary

1. **Load** — `Project.Load(file)` or `Project.LoadAndResolve(file)` deserialises the JSON into `ProjectDefinition`. Jackson's `@JsonAlias` accepts `specifications` as a synonym for `openApiSpecifications`. Unknown fields are silently dropped.
2. **Resolve paths** — when `LoadAndResolve` is used, every relative path becomes absolute against the project-file directory. `stateDir` is defaulted to `<dir>/.specfuse/state` if absent.
3. **Validate groups** — `ArtifactGroup.validate()` runs once per group, raising `INVALID_DART_GROUP_FIELD` on bad Dart-only values.
4. **`generate()`** — `ProjectDefinition.validateConfiguration()` checks `dbContextClassname`; `validateSpecification()` runs OpenAPI + (optionally) AsyncAPI + Arazzo validators unless `--skip-validation` is set.
5. **Resolve persistence** — every `x-entity` in the bundled spec is matched against `persistence.entities` and then `persistence.default`; `managed` and `schemaCheck` are resolved through the three-level chain (entity → connection → project default). Unresolved entities, undeclared connection references, kind/provider mismatches, nested hybrids, and missing `x-content` on hybrid entities all raise `PERSISTENCE_*` codes here.
6. **Per-group emission** — for each group: build the codegen configurator (stamping `projectName`, `dbContextClassnameOverride`, `hasEventRuntime`, every entry in `configs`, and the Dart `dartGroup.*` keys); run `cleanGenerated` if requested; invoke the artifact factory. Repository emission consults the resolved persistence descriptor per entity and dispatches to the matching backend template family.
7. **Post-regen hooks** — once every group has written its tree, the `ChangelogTracker` snapshots each group's surface to `<stateDir>/<groupName>.json` and emits `CHANGELOG.md`. The Dart formatter then runs on every Dart/Flutter group's package root.
8. **`ai-access-manifest.json`** — written once in the parent directory of `openApiSpecifications`, not per-group.
