# Project File

> **Status:** Canonical reference. This document is the authoritative specification of the Specfuse project file — the JSON document consumed at the project root by the generator. The generator's own internal documentation should be a short summary that points back here. The authoritative parser source of truth lives in `dev.specfuse.generator.configs.ProjectDefinition`, `ArtifactGroup`, `TenancyDefinition`, `BrokerDefinition`, and `ProjectNamingOverrides`.

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
| `broker` | object | optional | ✱ C# event-runtime only | Messaging-broker dialect / topology settings. |
| `broker.type` | enum | optional | ✱ | `azureServiceBus` (only working value). |
| `broker.topology` | enum | optional | ✱ | `runtime` (default) \| `bicep` (experimental — emits stub). |
| `broker.outboxDialect` | enum | optional | ✱ | `sqlServer` (default) \| `postgres` (experimental — emits stub). |
| `persistence` | object | optional | — | Multi-backend persistence configuration. Absent = no persistence artifacts. See §6. |
| `persistence.connections` | object<name, conn> | yes (when `persistence` set) | — | Named connection descriptors. Every referenced connection must be declared here. |
| `persistence.connections.<name>.provider` | enum | yes | — | `sqlServer` \| `postgres` \| `mySql` \| `cosmos` \| `azureBlob`. Must match the `kind` of any descriptor referencing this connection. |
| `persistence.connections.<name>.managed` | boolean | optional | — | Whether the generator owns DDL for entities on this connection. Default `true`. |
| `persistence.connections.<name>.schemaCheck` | enum | optional | — | `block` (default) \| `warn` \| `off`. Mode for unmanaged entities on this connection. |
| `persistence.default` | descriptor | optional | — | Backend descriptor used for any `x-entity` not in `entities`. Required if any entity is unlisted. |
| `persistence.entities` | object<entityName, descriptor> | optional | — | Per-entity descriptor overrides. Keys must match `x-entity` schemas in the bundled spec. |
| `persistence.schemaCheckTimeoutSeconds` | number | optional | — | Wall-clock cap for the startup schema-compatibility check, in seconds. Default `30`. |
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
| `groups[].unknownEnumPolicy` | enum | optional | ✱ Dart/Flutter only | `strict` \| `fallback` (default) \| `null`. |
| `groups[].formatPolicy` | enum | optional | ✱ Dart/Flutter only | `strict` (default) \| `lax`. |
| `groups[].mutationOverrides[]` | array<string> | optional | ✱ Dart/Flutter only | Operation IDs to flip between query / mutation classification. |

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

**Validation severity**: Arazzo errors are **downgraded to warnings** before being merged into the overall result. Arazzo does not yet drive code generation in lockstep with OpenAPI/AsyncAPI.

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

---

## 4. Tenancy

### 4.1 `tenancy` *(C# only today)*

**Purpose**: Declares the project's multi-tenant entity topology. In the C# target, it drives marker-interface generation (`I{Tenant}Scoped` / `I{SubTenant}Scoped`) and entity partial-class derivation from `x-entity.belongsTo`. It also feeds AsyncAPI validators (tenant FK ordering) and broker tenant scoping.

The Python and Dart/Flutter artifact factories do **not** register a tenancy-marker artifact today and emit no `I{Tenant}Scoped` equivalents. The block is still useful for those languages indirectly: AsyncAPI validation rules (e.g. tenancy ordering on `belongsTo`, the "events from emitting entities should include the tenant in their chain" suggestion) consult `tenancy` regardless of which language group consumes the result.

**Required**: Optional. Single-tenant projects omit the entire block.

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
    }
  }
}
```

**Validation** (all enforced at load):

- An empty `tenancy: {}` block is rejected.
- `tenancy.tenant` is required whenever the block is declared.
- Per tier, every field is required.
- `entity` must be PascalCase.
- `foreignKey` must be PascalCase **and** end in `Id`.
- `marker` must match `^I[A-Z][A-Za-z0-9]*$`.

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

- **`x-entity.schema`** — deprecated. Storage technology has been removed from the spec; schema names now live in `persistence` descriptors. See `Vendor_Extensions.md` §1.1.
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
| `PROJECT_BROKER_TYPE_UNKNOWN` / `PROJECT_BROKER_TOPOLOGY_UNKNOWN` / `PROJECT_BROKER_DIALECT_UNKNOWN` | `broker.type` / `broker.topology` / `broker.outboxDialect` set to an unrecognised value. |
| `INVALID_DART_GROUP_FIELD` | `unknownEnumPolicy` or `formatPolicy` outside its accepted set (Dart/Flutter groups only). |
| `INVALID_FILTER` | `groups[].filter` malformed — multiple top-level operators, unknown operator, wrong value shape. |
| `UNKNOWN_LANGUAGE` | `groups[].language` not registered. |
| (cleanScope) | A `cleanScope` entry is absolute or contains `..` segments. |
| `PERSISTENCE_*` | Persistence-block validation failures. The full list lives in §6.6 alongside the field definitions. |

The OpenAPI / AsyncAPI / Arazzo spec contents are validated separately by the per-spec validators after the project file loads.

---

## 10. Field Interactions and Cross-Field Behaviour

- **`name` ⟷ `dbContextClassname`** — when `dbContextClassname` is unset, the C# templates derive `{name}DbContext`. When `name` is also unset, they fall back to `AppDbContext`.
- **`name` ⟷ `configs.applicationPackage`** — the C# event-contract test artifact derives `{name}.Application` when no explicit value is set; if both are absent, the artifact fails with a hard error.
- **`groups[]` ⟷ event-runtime opt-in** — when any group registers the `eventRuntime` artifact (or the language equivalents `eventRuntimeImpl` / `eventRuntimeFunctions`), the generator stamps a project-wide `hasEventRuntime: true` additional property visible to every artifact in every group. This is the unambiguous opt-in marker for event-runtime emission.
- **`namingOverrides` ⟷ `x-enumCase`** — `x-enumCase: preserve` on a schema wins over a project-wide `enumValue` override.
- **`tenancy` ⟷ `x-entity.belongsTo`** — entities whose `belongsTo` references the tenancy entities receive the corresponding `I{Tenant}Scoped` marker interface in the C# target. The project-file loader does not validate that `tenancy.tenant.entity` resolves to a real `x-entity` schema; see §4.1 for the downstream symptoms.
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

**Snapshot date:** 2026-05-26. **Live source:** `templates --language csharp`.

`apiMapper`, `apiModel`, `domainModel`, `entity`, `annotatedEntity`, `valueObject`, `valueObjectConverter`, `enum`, `entityTypeConfiguration`, `repository`, `repositoryInterface`, `serviceInterface`, `service`, `dbContext`, `apiController`, `applicationServiceInterface`, `applicationService`, `apiFunctionalTest`, `useCaseInterface`, `entityBuilder`, `newDtoBuilder`, `updateDtoBuilder`, `valueObjectFake`, `apiModelFake`, `testSeed`, `serviceUnitTest`, `autoMapperTest`, `valueObjectTest`, `efConfigTest`, `authMatrixTest`, `eventContractTest`, `infrastructureProject`, `domainProject`, `domainValidation`, `domainExceptions`, `apiProject`, `event` (+ legacy alias `asyncEvent`), `asyncEventHandler`, `asyncJobInterface`, `asyncConsumerRegistration`, `azureFunctionTopicTrigger`, `azureFunctionTimerTrigger`, `eventBuilder`, `tenancyMarker`, `eventRuntime`, `eventRuntimeImpl`, `eventRuntimeFunctions`, `snapshot`, `snapshotContext`, `recipeFixture`, `scenarioFunctionalTest`.

### 11.2 Python artifacts

**Snapshot date:** 2026-05-26. **Live source:** `templates --language python`.

`entity`, `enum`, `valueObject`, `repository`, `aiEntity`, `aiRepository`, `event`, `eventBuilder`, `snapshot`, `eventOutbox`, `defaultEventEmitter`, `asyncEventHandler`, `eventContractTest`, `aiWorker`.

### 11.3 Dart / Flutter artifacts

**Snapshot date:** 2026-05-26. **Live source:** `templates --language dart` (Dart and Flutter share the same factory).

`entity`, `enum`, `valueObject`, `dartDto`, `dartRepositoryInterface`, `dartApiClient`, `dartRepositoryImpl`, `dartDtoMapper`, `dartUseCase`, `dartQueryProvider`, `dartMutationProvider`, `dartPaginatedNotifier`, `dartFormWidget`, `dartListTile`, `dartBarrelExport`, `dartProblemDetails`, `dartTypedError`, `dartDioErrorInterceptor`, `dartEntityBuilder`, `dartNewDtoBuilder`, `dartUpdateDtoBuilder`, `dartRepositoryFake`, `dartProviderOverrides`, `dartJsonFixture`, `dartFixtureLoader`, `dartCodegenSmokeTest`, `dartSerializationTest`, `dartRepositoryTest`, `dartQueryProviderTest`, `dartMutationProviderTest`, `dartValidatorTest`, `dartPaginationTest`.

### 11.4 Markdown artifacts

**Snapshot date:** 2026-05-26. **Live source:** `templates --language markdown`.

`scenarioDocument`, `scenarioIndex`, `recipeDocumentation`, `entityDiagram`, `eventCatalog`, `channelTopology`, `docsIndex`.

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
        "dartQueryProvider", "dartMutationProvider",
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

## Appendix A — Lifecycle Summary

1. **Load** — `Project.Load(file)` or `Project.LoadAndResolve(file)` deserialises the JSON into `ProjectDefinition`. Jackson's `@JsonAlias` accepts `specifications` as a synonym for `openApiSpecifications`. Unknown fields are silently dropped.
2. **Resolve paths** — when `LoadAndResolve` is used, every relative path becomes absolute against the project-file directory. `stateDir` is defaulted to `<dir>/.specfuse/state` if absent.
3. **Validate groups** — `ArtifactGroup.validate()` runs once per group, raising `INVALID_DART_GROUP_FIELD` on bad Dart-only values.
4. **`generate()`** — `ProjectDefinition.validateConfiguration()` checks `dbContextClassname`; `validateSpecification()` runs OpenAPI + (optionally) AsyncAPI + Arazzo validators unless `--skip-validation` is set.
5. **Resolve persistence** — every `x-entity` in the bundled spec is matched against `persistence.entities` and then `persistence.default`; `managed` and `schemaCheck` are resolved through the three-level chain (entity → connection → project default). Unresolved entities, undeclared connection references, kind/provider mismatches, nested hybrids, and missing `x-content` on hybrid entities all raise `PERSISTENCE_*` codes here.
6. **Per-group emission** — for each group: build the codegen configurator (stamping `projectName`, `dbContextClassnameOverride`, `hasEventRuntime`, every entry in `configs`, and the Dart `dartGroup.*` keys); run `cleanGenerated` if requested; invoke the artifact factory. Repository emission consults the resolved persistence descriptor per entity and dispatches to the matching backend template family.
7. **Post-regen hooks** — once every group has written its tree, the `ChangelogTracker` snapshots each group's surface to `<stateDir>/<groupName>.json` and emits `CHANGELOG.md`. The Dart formatter then runs on every Dart/Flutter group's package root.
8. **`ai-access-manifest.json`** — written once in the parent directory of `openApiSpecifications`, not per-group.
