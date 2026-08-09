# Vendor Extensions

> **Status:** Canonical reference. This document is the authoritative specification of all vendor extensions consumed by the Specfuse generator across OpenAPI, AsyncAPI, and Arazzo specs. The generator's own `docs/VENDOR-EXTENSIONS.md` is a short summary that points back here. The authoritative parser source of truth lives in the generator's `ExtensionConstants.java` and `VendorExtensionParser`.

This document provides a comprehensive specification of all vendor extensions (`x-*`) used in Specfuse projects. These extensions provide metadata for code generation, database modeling, authorization, AI agent integration, async event modeling, and behavioral scenario testing. They are consumed by:

- **Code generation engines** — template-driven code generation for multiple target languages
- **Database schema generators** — entity relationship modeling and storage optimization
- **Authorization systems** — role-based access control and OAuth scope validation
- **AI agents** — autonomous system integration and workflow automation
- **Documentation tools** — enhanced API documentation with implementation details
- **Test generators** — happy-path and negative functional test scaffolding
- **Scenario runners** — Arazzo workflow execution and assertions

> **Adopting a key documented here is two edits, not one.** Several of these
> extensions are validated by a Spectral rule that closes the schema
> (`additionalProperties: false`) — a closed schema over a vocabulary the
> *generator* owns. If the key is not also listed in that guard, the spec that
> declares it fails lint with an `additionalProperties` error naming your spec,
> not the ruleset, and the natural fix — deleting the key — abandons the
> generator feature you were adopting. Three keys on `x-entity` reached exactly
> that state (`domain`, across 78 entities, undetected for months;
> `concurrency`; `delete`).
>
> Before adopting a key the project has not used: check the guard covering that
> surface in `.specfuse/authoring/schemas/spectral/`, and run
> `./scripts/check-extension-vocabulary.py`, which compares every closed guard
> against the pinned generator's vocabulary and names any key the generator
> knows and the rulesets reject. Kit maintainers run the same check at generator
> pin time — see `bump-generator-pin` — so the drift is caught where it is born
> rather than by the first spec author to trip over it.

---

## 1. Entity Modeling Extensions

### 1.1 x-entity

**Purpose**: Defines entity types, relationships, and shape characteristics for domain modeling.

**Scope**: Applied to main resource schemas (entities and aggregates)

**Schema**:
```yaml
x-entity:
  domain: string                  # Required: owning domain (kebab-case; MUST be a key in info.x-domains)
  type: string                    # Required: "aggregate" | "entity"
  belongsTo: object | string[]   # Optional: Parent aggregate relationships with cardinality
  hasOne: string[]               # Optional: One-to-one child relationships
  hasMany: string[]              # Optional: One-to-many child relationships
  filterableProperties: string[] # Optional: Fields usable in OData filter expressions
  searchableProperties: string[] # Optional: Fields available for free-text search
  encryptedProperties: string[]  # Optional: Fields requiring encryption at rest
  requiresPagination: boolean    # Optional: Whether lists require pagination (default: true for aggregates)
  mutability: string             # Optional: "mutable" | "immutable" | "appendOnly" (default: "mutable")
  delete: string | object        # Optional: "hard" | "soft", or { mode, retention } (default: "hard")
  valueObjects: object           # Optional: Value object storage configuration
  aiAccess: object               # Optional: AI agent access policy (see 1.1.1). Absent = no AI access.
```

**`domain` (required, leads the block).** Every entity is assigned to exactly one domain. The value is a kebab-case name that **MUST** be a key in the project's domain registry `info.x-domains` (see `API_Handbook.md §0.1` and the new-project scaffold's `openapi.yaml`). The registry is a **closed universe**: an entity may only name a registered domain, and the validator rejects an `x-entity.domain` that has no matching `info.x-domains` key (`ENTITY_DOMAIN_UNREGISTERED`, ERROR). The value also matches the entity's `domains/{domain}/` folder and lines up 1:1 with the AsyncAPI channel `x-domain` (§12.1) and Arazzo workflow `x-domain` (§13.1) — one domain vocabulary shared across all three specs. Author it first so the entity's home is unambiguous before any relationship or access metadata is read.

> **Storage technology choices are not declared on `x-entity`.** Database engine, connection, schema name, and container name live in `project.json.persistence` — see `Project_File.md` §6. The `schema` property previously recognised on `x-entity` is **deprecated**; configure schema names through `persistence.entities.<EntityName>.schema` (relational descriptors only).

**Entity Types**:
- **`aggregate`**: Domain aggregate root
  - Has independent lifecycle
  - Can be directly queried and modified
  - Usually requires pagination for lists
  - Examples: `Tenant`, `Customer`, `Order`, `Catalog`

- **`entity`**: Domain entity within an aggregate
  - Has identity but belongs to an aggregate
  - Managed through aggregate operations
  - Examples: `OrderLine`, `CustomerPreferences`, `CatalogItem`

**`mutability` (optional, default `mutable`).** Declares the write policy for the entity's rows after insert.

| Value | Meaning | Typical entities |
|---|---|---|
| `mutable` | Rows are updated in place. The default; omitting the property means this. | Most entities |
| `immutable` | Rows are never modified after insert. | Audit trails, ledger transactions |
| `appendOnly` | New rows are added; existing rows are never modified. | Event logs, append-only histories |

Declare it when the entity's write policy is a real constraint rather than an
accident of the current implementation. The reason to bother is that it turns a
narrative claim into a machine-readable one: an entity whose description says
*"there is no separate `updatedAt` because audit rows are immutable"* is stating
a constraint no tool can act on. Declaring `mutability` makes it checkable.

**What consumes it today:** `specfuse-main-resource-has-updatedAt`. That rule
requires every entity to expose `updatedAt`, which silently assumes every entity
mutates. For an immutable or append-only entity, an `updatedAt` column
permanently equals `createdAt` — a field asserting something untrue — so a
declared non-mutable write policy exempts the entity from the requirement. `id`
and `createdAt` remain required regardless; only `updatedAt` is meaningless for
rows that never change.

This is not an escape hatch from the `updatedAt` requirement. The value is
validated against the closed set above by `specfuse-xentity-shape`, so
mislabelling a mutable entity to dodge the rule is a visible, reviewable edit
rather than a silent suppression.

> **Runtime enforcement is not implemented.** Nothing currently prevents an
> update to a row on an entity declared `immutable` — the property drives lint
> behaviour, not generated persistence code. Treat it as a declared and
> lint-checked intent, not an enforced guarantee. Generator-side enforcement is
> tracked in `compatibility.md`.

```yaml
AuditEntry:
  type: object
  x-entity:
    domain: compliance
    type: entity
    mutability: immutable       # audit rows are never modified; no updatedAt
  properties:
    id: { type: string, format: uuid }
    createdAt: { type: string, format: date-time }
    actorId: { type: string, format: uuid }
    action: { $ref: './AuditAction.yaml' }
```

**`delete` (optional, default `hard`).** Declares what an HTTP `DELETE` on this
entity does to its own row: destroy it, or mark it archived and keep it.

Before this key existed, the answer was invisible from the spec. The generator's
delete template branched on whether a linked AsyncAPI message carried
`x-trigger-when` — if one did, the generated service updated the entity; if not,
it removed the row. An operation description could say *"stays in the database"*
while the generated code hard-deleted it, and nothing anywhere disagreed.
`delete` is that decision moved into the contract.

Three authored forms:

```yaml
delete: hard                # shorthand — destroy the row
delete: soft                # shorthand — stamp deletedAt, keep the row

delete:                     # long form
  mode: soft
  retention: P30D           # ISO-8601 duration, or `none` = keep forever
```

| Value | Meaning |
|---|---|
| `hard` | The row is removed. The default; omitting the property means this. |
| `soft` | The row is retained and stamped `deletedAt`; reads exclude it by default. |
| `retention` | How long a soft-deleted row is kept before it may be destroyed. `none` means forever. Only meaningful with `mode: soft`. |

Absent `delete` resolves to `hard`, which is the pre-FEAT-2026-0080 generator
behaviour — adding this key to the vocabulary changes the meaning of no existing
entity. **Note that this default is the opposite of the `API_Handbook.md`
project-wide soft-delete convention.** If your project follows that convention,
undeclared entities are silently hard-deleting today; see §"Deletion" in the API
Handbook.

**Not the same key as `cascadeDelete`.** `delete` scopes the entity's own row;
`cascadeDelete` scopes what happens to its `children`. An aggregate may carry
both, and they are not required to agree — a hard-deleted parent can still
cascade a soft delete to children that outlive it.

**The `deletedAt` shape contract.** A soft-delete entity declares the property
itself, following the `createdAt`/`updatedAt` convention, so that it lands in
read DTOs and clients can see when a record was archived. It must be:

```yaml
deletedAt:
  type: string
  format: date-time
  nullable: true
```

`deletedByUserId` is optional. When present, the generated service stamps it
from the caller context, and it is legal only on a soft-delete entity.

**What consumes it today:** `specfuse-xentity-shape` validates the shape — the
closed value sets, the long-form sub-keys, and that `retention` is `none` or an
ISO-8601 duration with at least one component. Generator-side, gate 1 of
FEAT-2026-0080 adds six ERROR and two WARNING coherence rules:

| Rule | Severity | Fires when |
|---|---|---|
| `DELETE_SOFT_REQUIRES_DELETED_AT` | ERROR | `soft`, but no `deletedAt` property |
| `DELETE_SOFT_DELETED_AT_SHAPE` | ERROR | `deletedAt` is not string / date-time / nullable |
| `DELETE_HARD_DECLARES_DELETED_AT` | ERROR | `hard` (declared or defaulted) but `deletedAt` present |
| `DELETE_AUDIT_REQUIRES_SOFT` | ERROR | `deletedByUserId` on a non-soft entity |
| `DELETE_RETENTION_REQUIRES_SOFT` | ERROR | `retention` alongside `mode: hard` |
| `DELETE_RETENTION_INVALID` | ERROR | `retention` is neither `none` nor a valid ISO-8601 duration |
| `DELETE_SEMANTICS_UNDECLARED` | WARNING | the entity is the target of a DELETE operation and declares no `delete` |
| `DELETE_SOFT_STATUS_ENUM_OVERLAP` | WARNING | a soft-delete entity whose status enum also carries a `deleted`/`archived` member |

> **Gate 1 is validation only.** No stamping, no column, no read filtering is
> generated yet — that lands in gate 2. An entity that declares `delete: soft`
> and adds `deletedAt` before gate 2 ships has a real property in the contract
> that nothing writes: an archived row reads back `deletedAt: null`. Sequence
> the declaration accordingly.
>
> `retention` is declared-but-not-enforced in both gates. The cleanup worker
> that acts on it is `FEAT-2026-0081`, which is blocked on this feature.
>
> `DELETE_SEMANTICS_UNDECLARED` ships at WARNING deliberately, so that adopting
> the vocabulary does not turn `validate` red across a project mid-migration. It
> tightens to ERROR in gate 2.

```yaml
Customer:
  type: object
  x-entity:
    domain: crm
    type: aggregate
    delete:
      mode: soft
      retention: none         # kept until a manual privacy-request deletion
  properties:
    id: { type: string, format: uuid }
    createdAt: { type: string, format: date-time }
    updatedAt: { type: string, format: date-time }
    deletedAt: { type: string, format: date-time, nullable: true }
    deletedByUserId: { type: string, format: uuid, nullable: true }
```

**Relationship Cardinality**:

The `belongsTo` property supports explicit cardinality constraints to eliminate ambiguity for code generation:

**Cardinality Keywords**:
- `allOf: [aggregates]` - MUST belong to ALL listed aggregates (required)
- `oneOf: [aggregates]` - MUST belong to EXACTLY ONE from list (mutually exclusive)
- `oneOrMore: [aggregates]` - MUST belong to AT LEAST ONE from list
- `optional: {...}` - Wraps nested cardinality that is optional
- `zeroOrMore: [aggregates]` - MAY belong to zero or more (fully optional)
- `optionalLinks: {...}` - Named optional relationship group

**Cardinality Examples**:

```yaml
# Required base + optional exclusive context
OrderAttachment:
  x-entity:
    type: entity
    belongsTo:
      allOf: [Tenant]  # Always required
      optional:
        oneOf: [Order, Customer, Refund]  # May belong to exactly one

# Multiple required relationships
OrderLine:
  x-entity:
    type: entity
    belongsTo:
      allOf: [Tenant, Order]  # Both always required

# Required + optional flexible
ActivityLogEntry:
  x-entity:
    type: aggregate
    belongsTo:
      allOf: [Tenant]  # Always required
      optional:
        zeroOrMore: [Order, Customer]  # May belong to none, one, or both

# Single required relationship
Order:
  x-entity:
    type: aggregate
    belongsTo:
      allOf: [Tenant]  # Always required

# Deprecated array syntax (still supported, generates warning)
Customer:
  x-entity:
    type: aggregate
    belongsTo: [Tenant, Order]  # ⚠️ Ambiguous - use explicit cardinality instead
```

**Custom DDD Interpretation**:
- Aggregates CAN have `belongsTo` to express tenant hierarchy (e.g., Customer belongs to Tenant)
- Entities MUST have `belongsTo` to specify their aggregate context
- This enables proper multi-tenant data isolation and relationship modeling

**Validator-enforced relationship rules**:

The generator enforces six rules on entity relationships. See `API_Handbook.md §9.4` → "REST Route Patterns by Cardinality", "Entity type by polymorphic shape", and "M:M Junction Navigation" for the full reference, worked examples, and anti-pattern table.

- **M:M junctions** — when an entity declares `belongsTo.allOf: [A, B]` as a junction, both parents must list the junction in `hasMany`, never each other directly. A direct `hasMany: [OtherParent]` triggers `REDUNDANT_JUNCTION_HASMANY` (ERROR) because the generator back-projects a non-nullable FK onto the other parent's table. The rule only fires when neither parent declares the other under `belongsTo` (so parent/child tenancy tiers like `Tenant → Customer` are unaffected).
- **Polymorphic parents (`oneOf` / `optional.oneOf`)** — each parent in the list requires a parent-scoped create route (`POST /{parent-plural}/{parentId}/{entity-plural}`); the URL is the single source of truth for the parent FK. The `New{Entity}` DTO MUST NOT declare the polymorphic parent FK fields. A flat `POST /{entity-plural}` is **forbidden** under required `oneOf` (no valid input under the polymorphic CHECK) and **required** under pure `optional.oneOf` (the orphan case). Compound shapes (`allOf: [Tenant] + optional.oneOf: [...]`) do not need a fully-flat route — the tenant-scoped route serves "no sub-parent within tenant". Rule codes: `MISSING_PARENT_SCOPED_CREATE`, `FORBIDDEN_FLAT_CREATE_ON_REQUIRED_ONEOF`, `MISSING_FLAT_CREATE_ON_OPTIONAL_ONEOF`, `PARENT_FK_LEAK_IN_NEW_DTO` (all ERROR).
- **Entity classification vs polymorphic shape** — if `belongsTo` admits a fully-null parent FK state at insert (absent, or pure `optional.*` / `zeroOrMore` with no `allOf` clause), `type` MUST be `aggregate`, not `entity`. Child entities (`type: entity`) "cannot be accessed without going through their aggregate root" (§9.1); an orphan-allowing shape contradicts that invariant, and the generator emits a service body calling `repository.Add(entity)` against the wrong repository (no per-entity repo exists), producing non-compiling code. Resolution: promote to `type: aggregate`, or add `belongsTo.allOf` with at least one required parent. Rule code: `ENTITY_MUST_BE_AGGREGATE_WHEN_ORPHAN_ALLOWED` (ERROR). This is the entity-side counterpart of the four polymorphic-create rules above — together they guarantee no path leads to a non-compiling regen.

**Complete Example**:
```yaml
Customer:
  type: object
  x-entity:
    domain: customer
    type: aggregate
    hasMany: [Order, CustomerPreference]
    belongsTo:
      allOf: [Tenant]
    searchableProperties: [firstName, lastName, email, phone]
    encryptedProperties: [taxId]
    requiresPagination: true
    valueObjects:
      homeAddress:
        storage: 'single_json'
        queryable: false
      emergencyContact:
        storage: 'flatten'
        propertyPrefix: 'emergency_'
```

### 1.1.1 aiAccess (within x-entity)

**Purpose**: Declares the access policy that generated repositories and service layers must enforce for AI agents interacting with this entity. Consumed by the code generator to emit AI-scoped repository methods, field allow-lists, and audit hooks.

**Scope**: Required on every `x-entity` block (main resource schemas — aggregates and entities). Tier 0 entities (those the AI must not touch) use the explicit empty-operations form (see below) rather than omitting the block.

**Semantic default when absent**: No AI access — agents cannot read, create, update, or delete the entity through any generated AI-facing surface. However, **absence is a validator warning** (`ENTITY_AIACCESS_MISSING`), because it cannot be distinguished from authoring oversight. Every entity must make the AI-access decision explicit by declaring an `aiAccess` block. For entities the AI must not touch, use the canonical Tier 0 form: `operations: []` with `reason`.

**Schema**:
```yaml
aiAccess:
  operations: string[]          # Required. Subset of [read, create, update, delete]. Empty array signals deliberate Tier 0 (no AI access).
  readableProperties: string[]  # Optional when 'read' in operations. Absent = all non-encrypted top-level properties.
  writableProperties: string[]  # Required when operations contains create, update, or delete.
  immutableOnUpdate: string[]   # Optional subset of writableProperties. Fields set on create but not modifiable on update.
  ownedBy: string               # Optional: shared | ai | backend (default: shared). Conflict-resolution authority.
  reason: string                # Required when operations is empty (Tier 0 justification) OR contains any write verb. Free-text audit justification.
```

**Field semantics**:

- **`operations`** — authoritative list of what the AI can do. Presence is the single source of truth; there is no separate `mode` flag. An **empty array** (`[]`) is the canonical Tier 0 declaration — explicit, reviewable, distinguishable from "author forgot." Absence is also semantically "no access" but triggers an authoring warning (`ENTITY_AIACCESS_MISSING`).
- **`readableProperties`** — when omitted and `read` is granted, the agent may read every top-level property **except** fields listed in `encryptedProperties`. To grant read access to an encrypted field, list it explicitly. This enforces a safe-by-default read surface.
- **`writableProperties`** — must reference top-level properties of the entity. Write access is always an explicit allow-list; there is no "all fields" shortcut for writes. Required whenever `operations` includes any of `create`, `update`, `delete`.
- **`immutableOnUpdate`** — subset of `writableProperties`. Fields the agent may supply on create but never modify on update (e.g., foreign keys, tenant scope).
- **`ownedBy`** — records the system of record when both AI and backend can write:
  - `shared` (default): either side may write; last-writer-wins with audit
  - `ai`: the AI agent is authoritative; backend writes are reconciled against AI state
  - `backend`: the backend is authoritative; AI writes are advisory and may be overridden
- **`reason`** — required in two cases: (a) `operations` is empty (the Tier 0 justification — why this entity is intentionally outside the AI surface), and (b) `operations` contains any write verb (the audit justification for granting writes). Free-text surfaced in generated doc-comments and the AI manifest. Should not reference the target programming language — describe the business need.

**Validation rules** (enforced by Spectral + DDD validator):

1. `aiAccess` is required on every `x-entity` block. Absence triggers a WARN-level finding (`ENTITY_AIACCESS_MISSING`) — present-but-empty `operations` is the canonical Tier 0 declaration.
2. `operations` must be present. An empty array (`[]`) is valid and signals deliberate Tier 0 / explicit no-access. When `operations` is empty, `reason` is required.
3. If `operations` contains any of `create`/`update`/`delete`, then `writableProperties` (non-empty) and `reason` (non-empty) are required.
4. `readableProperties`, `writableProperties`, and `immutableOnUpdate` must reference top-level properties that exist on the entity schema (BilingualText subfields like `title.en` allowed).
5. `immutableOnUpdate` must be a subset of `writableProperties`.
6. Encrypted fields (from `encryptedProperties`) are **not** included in the "absent = all properties" expansion of `readableProperties`. To grant AI read access to an encrypted field, list it explicitly in `readableProperties`.
7. `aiAccess` may only appear on schemas that carry `x-entity` (same placement rules as other entity metadata — never on derivatives like `Basic*`, `New*`, `Update*`).

**Examples**:

```yaml
# Read-only access to every non-encrypted field
Customer:
  x-entity:
    type: aggregate
    encryptedProperties: [taxId]
    aiAccess:
      operations: [read]
      # readableProperties omitted → every top-level field except taxId

# Full CRUD with explicit write surface and immutable scope
Order:
  x-entity:
    type: aggregate
    aiAccess:
      operations: [read, create, update]
      writableProperties:
        - status
        - priority
        - notes
        - shippingAddress
        - currency
        - customerId
      immutableOnUpdate:
        - customerId
      ownedBy: ai
      reason: |
        The order-triage agent owns intake-to-acceptance end-to-end,
        including status promotion. Backend writes are reconciled against
        agent state for audit and conflict resolution.

# Read-only with explicit access to one encrypted field
Customer:
  x-entity:
    type: aggregate
    encryptedProperties: [taxId]
    aiAccess:
      operations: [read]
      readableProperties:
        - firstName
        - lastName
        - email
        - phone
        - taxId   # Explicitly granted — not auto-included
      reason: |
        Tax-reconciliation agent needs the tax ID to match external
        accounting system records.

# Tier 0 — explicit no AI access (canonical form)
PaymentMethod:
  x-entity:
    type: entity
    belongsTo:
      allOf: [Tenant]
    aiAccess:
      operations: []
      reason: |
        Financial credentials and payment tokens. AI agents must never
        read or modify these — handled by a dedicated PCI-scoped service.
```

**Interaction with other extensions**:
- **`encryptedProperties`**: AI read of encrypted fields requires explicit listing in `readableProperties`. Masking rules still apply on the wire.
- **`filterableProperties` / `searchableProperties`**: these govern HTTP query surfaces, not AI repository methods. AI filtering/search allow-lists may be derived separately by the generator from `readableProperties`.
- **`x-ai-safe` (operations, §4.1)**: operates at the HTTP operation level — whether an AI agent may invoke a specific endpoint without approval. `aiAccess` operates at the entity/repository level — what the AI may touch via generated data-access code. The two are complementary.
- **Future per-agent scoping**: the single `aiAccess` block treats "AI" as monolithic. When multiple agents with different trust levels emerge, this will be extended to allow `aiAccess` keyed by agent role without breaking the single-block form. Until then, keep access blocks conservative.

### 1.2 x-value-object

**Purpose**: Marks schemas as value objects and defines default storage and code generation behavior.

**Scope**: Applied to value object schemas (immutable data structures without identity)

**Schema**:
```yaml
x-value-object:
  defaultStorage: string           # Required: Default storage pattern when embedded
  defaultQueryable: boolean | string[]  # Optional: Default queryable fields
  defaultPropertyPrefix: string    # Optional: Default prefix for flattened storage
  immutable: boolean              # Optional: Generate immutable classes (default: true)
  comparable: boolean             # Optional: Generate equality/comparison (default: true)
  validationRules: object[]       # Optional: Value object validation rules
  generateBuilder: boolean        # Optional: Generate builder pattern (default: false)
  customSerializers: string[]     # Optional: Custom serialization formats
```

> **Naming note:** the generator's internal extension constant uses the camelCase form `x-valueObject` as an alias. The kit's canonical kebab-case form is `x-value-object`. Either form is accepted by the parser; new specs should use the kebab-case form.

> **`validationRules` is a value-object sub-key and nothing else.** It is scoped
> to `x-value-object`, and it expresses **self-contained invariants** — rules
> decidable from the value object's own properties alone, such as `min <= max`.
> There is no entity-level `validationRules`; `x-entity` does not accept the key.
>
> The name invites a specific confusion, so it is worth stating the boundary
> explicitly. A rule that queries other rows, reads request context, or depends
> on which operation is being performed is **not** an invariant — it is an entity
> business rule, and it belongs in the HTTP contract as a `409 Conflict` response
> on the operations that can violate it (see `API_Handbook.md`). Signs you have
> crossed the line: the rule needs fields like `appliesTo`, `autoResolve`, or a
> resolution policy, or it cannot be evaluated without a second database read.
>
> The two views are the same gap seen from opposite ends. An entity declaring a
> business rule this way is usually paired with an operation missing its `409` —
> `specfuse-409-on-put-patch` and `specfuse-409-on-delete` flag that end
> independently.

**Value Object Characteristics**:
- **Immutable**: Value objects represent immutable data without identity
- **Comparable**: Equality based on property values, not object identity
- **Embeddable**: Designed to be embedded within entities as properties
- **Reusable**: Same value object can be used across multiple entities

**Storage Integration**:
When a value object is used within an entity's `valueObjects` configuration, the defaults from `x-value-object` are applied unless explicitly overridden:

```yaml
# Value Object Definition
PriceRange:
  type: object
  x-value-object:
    defaultStorage: 'single_json'
    defaultQueryable: false
    immutable: true
    comparable: true
    validationRules:
      - rule: "min <= max"
        message: "Minimum price cannot exceed maximum price"
        severity: "error"

# Entity Usage (inherits defaults)
CatalogItem:
  x-entity:
    type: entity
    valueObjects:
      priceBand: {}              # Uses all defaults from PriceRange

      # OR override specific settings:
      customPriceBand:
        storage: 'flatten'        # Override defaultStorage
        propertyPrefix: 'price_'  # Override defaultPropertyPrefix
        # queryable inherits defaultQueryable (false)
```

**Code Generation Benefits**:
- **C#**: Generate immutable record types with proper equality and validation
- **TypeScript**: Generate readonly interfaces with type guards
- **Java**: Generate value objects with equals/hashCode and validation
- **Python**: Generate dataclasses with frozen=True and validation

### 1.3 x-internal-only

**Purpose**: Marks an entity property as **server-internal** — persisted on the domain entity and its storage column, but excluded from every generated DTO (request *and* response) and from the test-support builder. Use for fields the system stores and reasons over but must never accept from or return to a client (e.g. a `passwordHash`, an internal `riskScore`, a computed `dedupeKey`).

**Scope**: Applied to a property schema inside an `x-entity` main resource. Ignored on value-object schemas and on derivatives (`Basic*`, `New*`, `Update*`) — the derivatives simply never receive the property.

**Optional**: Yes. Default = the property flows into DTOs per the normal rules.

**Schema**:

```yaml
x-internal-only: true
```

**Semantics**:

- The property **is** generated on the domain entity and its persistence column (unlike a spec field that is simply omitted — the value is stored).
- The property is **excluded from every DTO layer**: request DTOs (`New*`/`Update*`/`*Request`), response DTOs, and the paginated `Basic{Entity}` projection. A client can neither set nor read it.
- The property is **excluded from the generated test-support builder** — tests construct it through domain logic, not the builder surface.
- Because it never reaches a response, an `x-internal-only` property with a secret-shaped name satisfies the `SENSITIVE_FIELD_IN_RESPONSE` rule (see §1.5).

**Relationship with `writeOnly`**: `writeOnly: true` (OpenAPI-native) keeps a property in **request** DTOs but drops it from **response** DTOs — the client sets it, never reads it (e.g. a plaintext `password` on `New*`). `x-internal-only` is stricter: the property leaves **both** directions. Choose `writeOnly` when the client supplies the value; choose `x-internal-only` when only the server ever touches it.

**Validation rules**:

1. `x-internal-only: true` may only appear on property schemas inside an `x-entity` main resource. Enforced at spec validation (`INTERNAL_ONLY_*` guards).
2. `x-internal-only` and `writeOnly` MUST NOT co-occur on the same property — they express conflicting request-DTO intent (internal-only removes it, writeOnly keeps it).
3. A property carrying `x-internal-only: true` MUST NOT be `required: true` on any client-facing operation — a required field a client can never supply is unsatisfiable.

**Example**:

```yaml
User:
  type: object
  x-entity:
    type: aggregate
  properties:
    id:
      type: string
      format: uuid
    email:
      type: string
      format: email
      x-classification: [pii]
    passwordHash:
      type: string
      x-internal-only: true        # stored + queried server-side; never in any DTO
    password:
      type: string
      writeOnly: true              # client SETS on New*/Update*; never returned
```

### 1.4 x-enum-case

**Purpose**: Overrides the default camelCase formatting applied by the code generator to enum values when the standard convention doesn't make sense (e.g., industry-standard codes that must be preserved as-is).

**Scope**: Applied to enum schemas only (schemas with `type: string` and `enum` values)

**Optional**: Yes — omit when the default camelCase formatting is appropriate.

**Schema**:
```yaml
x-enum-case: string  # One of: preserve | PascalCase | camelCase | snake_case | kebab-case | SCREAMING_SNAKE_CASE
```

> **Naming note:** the generator also accepts the camelCase alias `x-enumCase`. The kit's canonical form is `x-enum-case`.

**Allowed Values**:
- `preserve` — emit enum values exactly as written in the spec, no transformation
- `PascalCase` — transform values to PascalCase
- `camelCase` — transform values to camelCase (this is the default when `x-enum-case` is absent)
- `snake_case` — transform values to snake_case
- `kebab-case` — transform values to kebab-case
- `SCREAMING_SNAKE_CASE` — transform values to SCREAMING_SNAKE_CASE

**When to use**:

Use `x-enum-case: preserve` **only** when the enum represents externally-defined standard codes where the exact casing is part of the specification:
- ISO 4217 currency codes (e.g., `CAD`, `USD`, `EUR`)
- ISO 3166-1 alpha-2 country codes (e.g., `CA`, `US`, `FR`)
- ISO 3166-2 subdivision/region codes (e.g., `US-CA`, `CA-QC`)
- BCP 47 language codes (e.g., `en`, `fr`, `en-CA`)
- IANA timezone identifiers (e.g., `America/New_York`)
- Other industry-standard identifiers where casing is normative

Do **not** use `x-enum-case` for regular domain enums — define values in camelCase and let the generator apply its default transformation.

**Example**:
```yaml
# Currency codes — values must be preserved exactly (ISO 4217)
CurrencyCode:
  type: string
  x-enum-case: preserve
  enum:
    - USD
    - EUR
    - GBP
    - JPY

# Region codes — values must be preserved exactly (ISO 3166-2)
RegionCode:
  type: string
  x-enum-case: preserve
  enum:
    - US-CA
    - US-NY
    - CA-ON
    - CA-QC

# Regular domain enum — no x-enum-case needed, generator uses camelCase default
OrderStatus:
  type: string
  enum:
    - placed
    - submitted
    - fulfilled
    - cancelled
```

### 1.5 x-classification

**Purpose**: Marks an entity property as carrying data of a particular sensitivity class. Drives downstream policy: encryption-at-rest, snapshot inclusion review (PII acknowledgement), audit logging, and AI access shaping.

**Scope**: Applied to a property schema inside an entity (`x-entity`) main resource. May appear on any scalar property; not used on relationship properties.

**Optional**: Yes. Default = unclassified (no PII / sensitive / encryption requirements).

**Schema**:
```yaml
x-classification:
  - pii          # personally identifying — name, email, phone, address, government IDs
  - sensitive    # business-confidential — financial details, internal evaluations, disciplinary records
  - encrypted    # MUST be encrypted at rest (also implies sensitive)
  - exposed      # secret-shaped name, human-reviewed, safe to expose (grants no access)
```

**Allowed values** (closed set):

| Value | Meaning | Implications |
|-------|---------|--------------|
| `pii` | Personally identifying information | Snapshot inclusion requires `x-snapshot-pii-acknowledged` justification (see §11.2). AI read access requires explicit listing in `aiAccess.readableProperties`. |
| `sensitive` | Business-confidential data | Same snapshot/AI-access rules as `pii`. Triggers heightened audit logging on read. |
| `encrypted` | Must be encrypted at rest | Generator emits encryption converters. The property is excluded from the default "all readable" expansion in `aiAccess.readableProperties` (see §1.1.1 rule 5). Implies `sensitive`. |
| `exposed` | Secret-shaped name, human-reviewed, safe to expose | Escape hatch for the `SENSITIVE_FIELD_IN_RESPONSE` validator (see below). Asserts a reviewer confirmed the field is safe on a response despite a secret-shaped name. **Grants no access** on its own; carries no encryption/masking obligation. Contradictory with `sensitive`/`encrypted` — MUST NOT co-occur with either. Requires a `description` justifying why exposure is safe. |

**Multiple classifications** are allowed (e.g., `[pii, encrypted]` for a tax ID). The generator unions the implications.

**Relationship with `x-entity.encryptedProperties`**: the `encrypted` classification on a per-field basis is the canonical declaration. The `x-entity.encryptedProperties` array remains valid for backward compatibility but is treated as a derived view — when a field carries `x-classification: [encrypted]`, the entity's `encryptedProperties` set is computed automatically by the generator. Authors should prefer per-field `x-classification` on new entities; existing entities may use either form.

**Example**:

```yaml
Customer:
  type: object
  x-entity:
    type: aggregate
  properties:
    id:
      type: string
      format: uuid
    email:
      type: string
      format: email
      x-classification: [pii]
    taxId:
      type: string
      x-classification: [pii, encrypted]
    creditScore:
      type: number
      x-classification: [sensitive]
    avatarHash:
      type: string
      description: Content-address of the public avatar image; not a credential. Safe on responses despite the secret-shaped name.
      x-classification: [exposed]   # override SENSITIVE_FIELD_IN_RESPONSE — reviewed, public
    avatarUrl:
      type: string
      # no classification — unclassified
```

**Validation rules** (Spectral + Specfuse):

1. Values must come from the closed set `[pii, sensitive, encrypted, exposed]`.
2. `x-classification: [encrypted]` requires the property to also be representable as a string (encryption produces opaque ciphertext).
3. When a snapshot file references a property whose source entity carries `pii` or `sensitive`, the snapshot file MUST declare `x-snapshot-pii-acknowledged.{propertyName}` with a justification ≥ 20 chars (see §11.2).
4. When `aiAccess.readableProperties` is omitted, properties classified `encrypted` are excluded from the implicit allow-set (existing rule 5 in §1.1.1, now driven by classification).
5. `x-classification: [exposed]` MUST NOT co-occur with `sensitive` or `encrypted` on the same property — those demand masking/encryption, which contradicts "safe to expose." A property carrying both fails validation (`CLASSIFICATION_EXPOSED_CONTRADICTION`).
6. A property carrying `x-classification: [exposed]` MUST also carry a non-empty `description` justifying why the field is safe to expose despite its name.

**`SENSITIVE_FIELD_IN_RESPONSE` — the `exposed` escape hatch**

The generator's `SENSITIVE_FIELD_IN_RESPONSE` rule flags any **response-bound** entity property whose name is *secret-shaped* — matches the heuristic `*Hash`, `*Token`, `*Secret`, `*Salt`, `*Password` (case-insensitive suffix) — because such a field on a response DTO is a likely credential leak.

A secret-shaped, response-bound property **passes** the rule only if it carries exactly one of:

- `writeOnly: true` — the field is never serialized onto responses, so there is nothing to leak; or
- `x-internal-only: true` — the field is stripped from all external response layers (see §1.3); or
- `x-classification: [encrypted]` — the serialized value is opaque ciphertext; or
- `x-classification: [exposed]` — a reviewer has confirmed the field is safe to return as-is.

`x-classification: [sensitive]` alone does **not** satisfy the rule: `sensitive` means *must be masked*, not *may be exposed*. Using `exposed` is an explicit, reviewed override — reach for it only when the secret-shaped name is a false positive (e.g. a public `avatarHash` content-address, an already-public `shareToken`).

### 1.6 x-content

**Purpose**: Marks an entity property as **opaque payload** — data the system carries but does not query, filter, project, or paginate over. The persistence layer decides where to store it; the API may stream it, lazy-load it, or omit it from metadata reads.

**Scope**: Applied to a property schema inside a main resource (`x-entity`). May appear on any property — scalars (typically `type: string` with `format: binary` or `format: byte`), structured payloads (free-form objects), or arrays of either.

**Optional**: Yes. Default = the property is treated as queryable metadata.

**Schema**:

```yaml
x-content: true
```

**Semantics**:

- The property is **not** included in default list/projection DTOs (e.g., the generated `Basic{Entity}` shape used by paginated list endpoints).
- The property is **not** auto-included in `aiAccess.readableProperties` when the latter is omitted (same safe-by-default treatment as `x-classification: [encrypted]`).
- The persistence layer chooses storage based on the resolved `kind` in `project.json` — typically a JSON/JSONB column for `relational` entities, the document body itself for `document` entities, a separate blob for `hybrid` entities. The spec does not encode the choice.

**Required for `kind: hybrid` entities**: a hybrid backend descriptor splits an entity into a queryable metadata side and an opaque content side. The split is driven by `x-content`: every property carrying `x-content: true` lands on the content side; every other property lands on the metadata side. A hybrid entity with no `x-content` property fails project-file load (`PERSISTENCE_HYBRID_NO_CONTENT` — see `Project_File.md` §6.6).

**Validation rules**:

1. A property marked `x-content: true` MUST NOT be `required: true`. Metadata reads must be allowed to omit the payload; a required-and-omitted field is a contract violation. Enforced at spec validation.
2. `x-content` may only appear on property schemas inside an `x-entity` main resource. It is ignored on derivatives (`Basic*`, `New*`, `Update*`) and on value-object schemas.
3. `x-content` and `x-classification: [encrypted]` may co-occur. Encryption applies to the opaque payload at rest.

**Examples**:

```yaml
# Document entity with a binary body
Document:
  type: object
  x-entity:
    type: aggregate
  properties:
    id:
      type: string
      format: uuid
    title:
      type: string
    contentType:
      type: string
    sizeBytes:
      type: integer
    body:
      type: string
      format: binary
      x-content: true        # Lives on the content side under hybrid kind
  required: [id, title, contentType, sizeBytes]
                              # body is intentionally not required

# Embedding vector — opaque to the system, large, not queryable
Article:
  type: object
  x-entity:
    type: aggregate
  properties:
    id:
      type: string
    summary:
      type: string
    embedding:
      type: array
      items: { type: number }
      x-content: true
```

**Interactions**:

- **`persistence` (`Project_File.md` §6)**: drives whether `x-content` becomes a separate column, a blob, or stays inline.
- **`aiAccess` (§1.1.1)**: AI agents must explicitly list `x-content` properties in `readableProperties` to read them — they are excluded from the implicit allow-set.
- **`Basic*` / list-projection DTOs**: the generator omits `x-content` properties from these shapes automatically. Authors do not need to duplicate the exclusion.

---

### 1.7 x-references

**Purpose**: Declares a `format: uuid` property to be a **non-owning association FK** — a pointer to another entity that does **not** make this entity part of that entity's aggregate.

**Scope**: Applied to a `type: string, format: uuid` property inside a main resource (`x-entity`).

**Optional**: Yes, but see "Every FK-shaped property must be classified" below — in practice an unclassified uuid property is a spec defect, not a default.

**Schema**:

```yaml
x-references: Customer      # target entity name (PascalCase), or the literal `none`
```

**Semantics**:

- **Association only.** The referencing entity is *not* a member of the target's aggregate. Contrast `belongsTo`, which declares composition and aggregate membership.
- **Delete behaviour is `NoAction`.** Deleting the target does not cascade to the referencing rows, because they are not owned. A composition FK (`belongsTo`) cascades; an association FK must not.
- **Nullability follows `required`.** The property is nullable unless listed in the schema's `required` array. There is no separate nullability marker.
- Test-seed naming for the FK follows `TestSeed.<Entity>Id`.

**`x-references: none`** marks a `format: uuid` property that is **not a foreign key at all** — a correlation id, an idempotency token, an externally-minted identifier. Because this suppresses relationship classification entirely, it MUST be accompanied by a `description` justifying why the value is opaque. An unjustified `none` is indistinguishable from an author who did not want to think about the relationship.

**Every FK-shaped property must be classified.** Since the retirement of implicit `{Entity}Id` → `belongsTo` inference (kit `0.5.4`), a `format: uuid` property named after an entity carries no relationship meaning on its own. Exactly one classification applies:

| Intent | Declaration |
|---|---|
| This entity is part of the target's aggregate | `belongsTo: <Target>` on `x-entity` (composition, Cascade, aggregate membership) |
| This entity merely points at the target | `x-references: <Target>` on the property (association, NoAction, no membership) |
| The uuid is not a foreign key | `x-references: none` on the property + a justifying `description` |

Leaving an FK-shaped property unclassified is a spec defect.

**Validation rules**:

1. `x-references: <Target>` and a `belongsTo` naming the same target on the same entity are **mutually exclusive** — declaring both is an error. There is no precedence between them and no "degrades to a hint" fallback; if the entity is owned, use `belongsTo`, and if it merely points, use `x-references`.
2. `x-references` and `x-fk-for` (§1.8) MUST NOT appear on the same property. They declare opposite ownership.
3. `x-references: none` requires a non-empty `description`.
4. The value MUST be `none` or a PascalCase entity name.

**Examples**:

```yaml
# Association: a note points at the customer it concerns, but the note is not
# part of the Customer aggregate — deleting the customer must not cascade.
Note:
  type: object
  x-entity:
    domain: support
    type: entity
    belongsTo: { allOf: [Tenant] }
  required: [id, tenantId, body]
  properties:
    id:         { type: string, format: uuid }
    tenantId:   { type: string, format: uuid }
    customerId:
      type: string
      format: uuid
      x-references: Customer          # association, nullable (not in `required`)
    body:       { type: string }

# Opaque uuid: not a foreign key, so classification is suppressed — and justified.
    correlationId:
      type: string
      format: uuid
      x-references: none
      description: >-
        Client-generated correlation id echoed back on the response. Not a
        foreign key — no entity is identified by this value.
```

**Interactions**:

- **`belongsTo` (§1.1)**: the owning counterpart. Mutually exclusive per target.
- **`x-fk-for` (§1.8)**: for an *owning* FK whose column name does not follow the `{Entity}Id` convention.

---

### 1.8 x-fk-for

**Purpose**: Binds an **owning** FK property to its target entity when the property name does not follow the `{Entity}Id` convention — typically a legacy or deliberately-differently-named column that must nevertheless keep composition semantics.

**Scope**: Applied to a `type: string, format: uuid` property inside a main resource (`x-entity`) whose `x-entity.belongsTo` already declares the target.

**Optional**: Yes. Needed only when the property name does not resolve to the target on its own.

**Schema**:

```yaml
x-fk-for: Order          # target entity name (PascalCase)
```

**Semantics**:

- Composition is **preserved**: Cascade delete, aggregate membership, and every other consequence of `belongsTo` apply exactly as if the property had been named `orderId`.
- It is a *binding*, not a declaration. `x-fk-for` does not create a relationship; it names which declared `belongsTo` a misnamed column satisfies.

**Validation rules**:

1. The target named by `x-fk-for` MUST appear in the same entity's `x-entity.belongsTo`. An `x-fk-for` with no matching `belongsTo` is an error — it looks like a relationship declaration but declares nothing.
2. `x-fk-for` and `x-references` MUST NOT appear on the same property (§1.7).
3. The value MUST be a PascalCase entity name. `none` is not valid here — an owning FK always has a target.

**Example**:

```yaml
# The column is `parentTicketRef` for historical reasons, but it is the owning
# FK to Ticket and must keep Cascade semantics.
TicketComment:
  type: object
  x-entity:
    domain: support
    type: entity
    belongsTo: { allOf: [Ticket] }
  required: [id, parentTicketRef, body]
  properties:
    id: { type: string, format: uuid }
    parentTicketRef:
      type: string
      format: uuid
      x-fk-for: Ticket
    body: { type: string }
```

> Prefer renaming the property to `{Entity}Id` when you control the schema. `x-fk-for` exists so that a name you cannot change does not force you to give up composition semantics — not as a general alternative to the naming convention.

---

### 1.9 x-expand-of and x-projection

**Purpose**: Mark **read-only projections** — properties that surface data belonging to another entity for read convenience, and which must never be treated as owned state.

**Scope**: Property schemas inside a main resource (`x-entity`).

**Optional**: Yes, but an unmarked projection embed is a spec defect (see below).

**Schema**:

```yaml
x-expand-of: customerId     # scalar projection: names the twin property it expands
x-projection: true          # collection projection: array of $ref, read-only
```

**Semantics**:

- **`x-expand-of: <twin>`** marks a **scalar** projection embed. The named twin MUST be a sibling property in the same schema, and MUST be either a `format: uuid` FK or a required `type: string` natural key. The projection is excluded from persistence (EF-Ignored) — it is computed on read, never written.
- **`x-projection: true`** marks a **collection** projection: a non-owned array of `$ref`. It is read-only and MUST NOT be `required`, because a projection is a convenience the server may decline to populate.

**Validation rules**:

1. An embed that projects another entity's data MUST carry one of the two markers. An unmarked projection embed is indistinguishable from owned state and will be persisted as such.
2. `x-expand-of` MUST name an existing sibling property, and that property must be a uuid FK or a required string natural key.
3. `x-projection: true` MUST be applied to an array-of-`$ref` property, and that property MUST NOT appear in `required`.
4. Both markers are read-only: the properties they mark MUST NOT appear in `New*` or `Update*` derivatives.

**Example**:

```yaml
Note:
  type: object
  x-entity: { domain: support, type: entity }
  required: [id, customerId]
  properties:
    id:         { type: string, format: uuid }
    customerId: { type: string, format: uuid, x-references: Customer }
    customer:
      # Scalar projection of the entity identified by `customerId`.
      allOf: [{ $ref: './BasicCustomer.yaml' }]
      x-expand-of: customerId
    recentOrders:
      # Collection projection — not owned, never required.
      type: array
      items: { $ref: './BasicOrder.yaml' }
      x-projection: true
```

**Interactions**:

- **`x-references` (§1.7)**: a scalar projection almost always expands an association FK. The FK carries the relationship; the projection carries the convenience copy.
- **`Basic*` derivatives**: projections typically reference the lightweight shape of the target, not its full read model.

---

## 2. Value Object Storage Extensions

> **`storage` patterns are hints, not directives.** The patterns below (`single_json`, `flatten`, `serialized`, `separate_table`, `collection_json`) were originally designed against a relational target. Under the multi-backend persistence model (`Project_File.md` §6), each backend kind honors the hints it can and reinterprets the rest: a `document` adapter typically ignores `flatten` (the whole entity is one document anyway); a pure-`blob` adapter accepts only `serialized`; a `relational` adapter honors every pattern. Authors should pick the hint that matches the *semantic intent* (one blob vs. flat columns vs. side table) and let the resolved backend decide the physical realisation.

### 2.1 valueObjects (within x-entity)

**Purpose**: Defines how value objects are stored within their parent entity. Works in conjunction with `x-value-object` defaults.

**Scope**: Property of `x-entity` metadata

**Integration with x-value-object**: When a property references a schema marked with `x-value-object`, the entity-level configuration inherits defaults and allows overrides:

```yaml
# If PriceRange has x-value-object with defaultStorage: 'single_json'
valueObjects:
  priceBand: {}                        # Inherits: storage: 'single_json'
  customPriceBand:
    storage: 'flatten'                 # Overrides: storage: 'flatten'
    # Other properties inherit from x-value-object defaults
```

**Schema**:
```yaml
valueObjects:
  {propertyName}:
    storage: string        # Required: Storage pattern
    queryable: string[]    # Optional: Queryable fields within value object
    indexHints: string[]   # Optional: Fields that should be indexed
    propertyPrefix: string # Optional: Prefix for flattened properties
    serializer: string     # Optional: Serialization format
```

**Storage Patterns**:

#### `collection_json`
- **Use**: Array of value objects stored as JSON
- **Database**: JSON/JSONB column containing array
- **Query Support**: Can query individual array elements
- **Example**: `tags: [{type: "loyalty", value: "gold"}]`

#### `single_json`
- **Use**: Single value object stored as JSON
- **Database**: JSON/JSONB column containing object
- **Query Support**: Limited, mainly for retrieval
- **Example**: `shippingPreferences: {method: "expedited", insurance: true}`

#### `flatten`
- **Use**: Value object properties as direct columns
- **Database**: Individual columns in parent table
- **Query Support**: Full SQL query capabilities
- **Example**: `effectiveDate`, `expirationDate` columns

#### `serialized`
- **Use**: Value object serialized as string/blob
- **Database**: TEXT/BLOB column
- **Query Support**: None (opaque storage)
- **Example**: JSON string, XML, binary data

#### `separate_table`
- **Use**: Value object in its own table
- **Database**: Separate table with foreign key
- **Query Support**: Full relational capabilities
- **Example**: Complex value objects with their own relationships

**Example**:
```yaml
Order:
  x-entity:
    type: aggregate
    valueObjects:
      tags:
        storage: 'collection_json'
        queryable: ['type', 'value']
        indexHints: ['type']
      validityWindow:
        storage: 'flatten'
        propertyPrefix: ''
      shippingPreferences:
        storage: 'single_json'
        queryable: false
      pricingDetails:
        storage: 'serialized'
        serializer: 'json'
```

---

## 3. Authorization Extensions

### 3.1 x-roles

**Purpose**: Specifies which user roles can access an operation.

**Scope**: Applied to OpenAPI operations

**Schema**:
```yaml
x-roles: string[]  # Array of role names from the project's closed role enum
```

**Valid Roles**: The role values are **project-defined**. Declare the closed role enum in the project's OpenAPI common enums file (typically `common/enums.yaml`); the Spectral validator enforces that every `x-roles` member is drawn from that enum. The illustrative roles used throughout this document (`Admin`, `Manager`, `Customer`, `Authenticated`) are examples only — replace them with your project's actual values.

**Recommended convention:** projects that distinguish pre-business-role flows (e.g., self-service signup, invitation acceptance, where the user has a valid auth token but no assigned role yet) should include an `Authenticated` role for that case.

**Example**:
```yaml
paths:
  /customers:
    get:
      x-roles: [Admin, Manager]
    post:
      x-roles: [Admin]
```

### 3.2 x-scopes

**Purpose**: Specifies OAuth scopes required for an operation.

**Scope**: Applied to OpenAPI operations

**Schema**:
```yaml
x-scopes: string[]  # Array of OAuth scope names
```

**Scope Naming Convention**: `{resource}.{action}` in camelCase
- Read operations: `{resource}.read` (e.g., `customers.read`)
- Write operations: `{resource}.write` (e.g., `customers.write`)
- Admin operations: `admin.{resource}.{action}` (e.g., `admin.templates.write`)

**Example**:
```yaml
paths:
  /customers:
    get:
      x-scopes: [customers.read]
    post:
      x-scopes: [customers.write]
  /admin/templates:
    post:
      x-scopes: [admin.templates.write]
```

---

## 4. AI Agent Integration Extensions

### 4.1 x-ai-safe

**Purpose**: Marks operations as safe for autonomous AI agent execution.

**Scope**: Applied to OpenAPI operations

**Schema**:
```yaml
x-ai-safe: boolean  # Default: false for write operations, true for read operations
```

**Usage**: AI agents can execute operations marked as `x-ai-safe: true` without human approval.

### 4.2 x-batch-operation

**Purpose**: Identifies operations that support batch processing.

**Scope**: Applied to OpenAPI operations

**Schema**:
```yaml
x-batch-operation:
  maxItems: number     # Maximum items per batch
  atomicity: string    # "all-or-nothing" | "partial-success"
  supports: string[]   # Supported batch features
```

**Example**:
```yaml
paths:
  /customers:batch:
    post:
      x-batch-operation:
        maxItems: 100
        atomicity: "all-or-nothing"
        supports: ["validateOnly", "dryRun"]
```

### 4.3 x-idempotency-support

**Purpose**: Indicates operations that support idempotency keys.

**Scope**: Applied to OpenAPI operations (typically POST)

**Schema**:
```yaml
x-idempotency-support:
  required: boolean    # Whether idempotency key is required
  keyHeader: string    # Header name (default: "Idempotency-Key")
  ttl: string         # Time-to-live for idempotency keys
```

### 4.4 x-public

**Purpose**: Marks an endpoint as anonymous-access (no authentication required). Opt-in opposite of the default authenticated-by-default policy.

**Scope**: Applied to OpenAPI operations

**Schema**:
```yaml
x-public: boolean   # true = anonymous; default: false (authenticated)
```

**Rules**:
- When `true`, the endpoint must NOT declare `x-roles` or `x-scopes` (the role/scope checks are bypassed).
- Use sparingly — typical cases are health probes, public discovery endpoints, and invitation-acceptance flows where a magic-link token (not a session) is the entry credential.

### 4.5 x-manual

**Purpose**: Skips automatic service-implementation emission for an operation. The generator still emits the controller, route, and DTO bindings, but the service layer is hand-written by the consumer.

**Scope**: Applied to OpenAPI operations

**Schema**:
```yaml
x-manual: boolean   # true = consumer provides the service implementation; default: false
```

**Use cases**: operations whose business logic is too custom for template-driven scaffolding (e.g., complex aggregation queries, third-party integration handlers, legacy code-path wrappers).

### 4.6 x-default

**Purpose**: Declares default values for properties or enum entries that the generator uses when emitting fakes, fixtures, or initial values.

**Scope**: Applied to OpenAPI schema properties or enum values

**Schema**:
```yaml
x-default: <any>   # Literal default value matching the property's type
```

**Relationship with OpenAPI `default` — on an enum schema, declare both.** OpenAPI Generator does not reliably pick up `default` alone on an enum, so the two keywords must appear together and carry the same value. Declaring `default` without `x-default` is an error (`ENUM_MISSING_X_DEFAULT`):

```yaml
# CustomerStatus.yaml
type: string
description: Lifecycle status of a Customer.
default: active
x-default: active      # must match `default`
enum: [active, inactive, suspended]
```

**A required enum property needs one.** An entity with a required enum property and no default has no defined state at creation, which is an error (`REQUIRED_ENUM_MISSING_DEFAULT`). Either give the enum a default as above, or make the property required in the `New{Entity}` schema so the client must supply it. Suppress deliberately with `x-skip-default-validation: true` on the property.

**Where it goes.** On the **enum schema**, not beside the `$ref` that points at it — OpenAPI 3.0 ignores keywords declared as siblings of `$ref`, so a default written next to the reference is silently dropped.

Outside enum schemas, prefer the standard `default` keyword on its own. Use `x-default` alone for cases the standard keyword does not cover — e.g. a value the generator should use for test data without declaring it as a schema-level default.

---

## 5. Operation Categorization Extensions

### 5.1 x-operation

**Purpose**: Defines operation categories and code generation hints for proper service pattern selection.

**Scope**: Applied to operation objects (GET, POST, PUT, PATCH, DELETE)

**Schema**:
```yaml
x-operation:
  type: object
  required: [category]
  properties:
    category:
      type: string
      enum: [aggregate, reference, coordination, resource, admin, discovery, query]
      description: Operation category for code generation patterns
    codeGenHints:
      type: object
      properties:
        cacheable:
          type: boolean
          default: false
          description: Whether this operation should be cached
        auditRequired:
          type: boolean
          default: false
          description: Whether this operation requires audit logging
        eventEmission:
          type: boolean
          default: false
          description: Whether this operation should emit domain events
        transactional:
          type: boolean
          default: false
          description: Whether this operation requires transaction management
```

**Operation Categories**:

- **`aggregate`**: Standard CRUD operations within aggregate boundaries
  - Code Generation: AggregateService, DomainEvents, ValidationRules, BusinessLogic
  - Patterns: CommandHandler, EventSourcing, UnitOfWork
  - Examples: `POST /tenants/{tenantId}/customers`, `PATCH /tenants/{tenantId}/settings`

- **`reference`**: Read-only operations on system-wide reference data
  - Code Generation: Repository, CacheLayer, ReadOnlyService
  - Patterns: QueryHandler, CacheAside, ReadThrough
  - Examples: `GET /catalogs`, `GET /catalogs/{catalogId}`

- **`coordination`**: Operations that coordinate across multiple aggregates
  - Code Generation: ApplicationService, Orchestrator, Saga
  - Patterns: ProcessManager, Workflow, CrossAggregateQueries
  - Examples: `GET /templates/preview`, `POST /onboarding/setup`

- **`resource`**: Direct access to individual resources regardless of aggregate context
  - Code Generation: ResourceService, DirectAccess, SimpleValidation
  - Patterns: CRUD, ResourceManager, AccessControl
  - Examples: `GET /attachments/{attachmentId}`, `PATCH /attachments/{attachmentId}`

- **`admin`**: Administrative operations with elevated permissions
  - Code Generation: AdminService, AuditLogger, ElevatedPermissions
  - Patterns: AdminCommand, SystemOperation, ComplianceTracking
  - Examples: `POST /admin/templates`, `DELETE /admin/templates/{templateId}`

- **`discovery`**: Public-facing discovery and search operations
  - Code Generation: QueryService, SearchEngine, PublicAPI
  - Patterns: ReadModel, SearchIndex, PublicEndpoint
  - Examples: `GET /catalogs/items?category=foo`, `GET /tenants?region=us-east`

- **`query`**: Computational operations that process input parameters to generate derived data
  - Code Generation: QueryProcessor, ComputationEngine, CacheableService
  - Patterns: QueryHandler, Calculator, Preview, Projection
  - Examples: `GET /templates/preview`, `GET /reports/analytics`, `GET /calculations/pricing`

**Default Values by Category**:
```yaml
aggregate:
  cacheable: false, auditRequired: true, eventEmission: true, transactional: true
reference:
  cacheable: true, auditRequired: false, eventEmission: false, transactional: false
coordination:
  cacheable: false, auditRequired: true, eventEmission: true, transactional: true
resource:
  cacheable: false, auditRequired: true, eventEmission: false, transactional: true
admin:
  cacheable: false, auditRequired: true, eventEmission: true, transactional: true
discovery:
  cacheable: true, auditRequired: false, eventEmission: false, transactional: false
query:
  cacheable: true, auditRequired: false, eventEmission: false, transactional: false
```

**Automatic Categorization (when x-operation is not present)**:

The code generator will automatically categorize operations using the following logic:

1. **Aggregate Category**: If an aggregate can be derived from the HTTP verb + path parameters + response schemas combination
   - Derivation: Path structure analysis (`/tenants/{tenantId}/customers` → Tenant aggregate)
   - Response schema analysis (schemas with `x-entity.type: aggregate`)
   - Examples: Most CRUD operations within aggregate boundaries

2. **Resource Category**: If an entity can be derived from the HTTP verb + path parameters + response schemas combination
   - Derivation: Individual resource access patterns (`/attachments/{attachmentId}`)
   - Response schema analysis (schemas with `x-entity.type: entity`)
   - Examples: Direct resource access operations

3. **Error**: If neither aggregate nor entity can be derived, the code generator will throw an error requiring explicit categorization

**Usage Examples**:

```yaml
# Minimal specification (uses defaults)
get:
  x-operation:
    category: reference
  # Defaults applied: cacheable=true, auditRequired=false, eventEmission=false, transactional=false

# Override specific hints
post:
  x-operation:
    category: coordination
    codeGenHints:
      cacheable: true  # Override default for this read-heavy coordination operation

# Automatic categorization (no x-operation specified)
patch:
  # Code generator will:
  # 1. Analyze path: /tenants/{tenantId}/settings
  # 2. Detect Tenant aggregate from path structure
  # 3. Automatically assign category: aggregate
  # 4. Apply aggregate defaults
```

**Integration with Existing Extensions**:
- Works with `x-entity` metadata for aggregate/entity detection
- Respects `x-roles` and `x-scopes` for admin operation identification
- Leverages HTTP verb semantics for read-only operation detection

---

## 6. Event Emission Extensions

### 6.1 x-emits

**Purpose**: Declares which events a write operation publishes on success. Creates a bidirectional link with AsyncAPI message specifications.

**Scope**: All write operations (POST, PUT, PATCH, DELETE)

**Required**: Yes — every write operation must declare at least one event.

```yaml
post:
  operationId: submitOrder
  x-emits:
    - event: Order.Submitted
      description: Emitted when the order is successfully submitted
```

**Schema**:

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `event` | Yes | string | Event identifier in `{Entity}.{Action}` format. Must match the `x-label` of an AsyncAPI message. |
| `description` | No | string | Human-readable description of when/why this event is emitted |

**Format**: The `event` value uses the same `{Entity}.{Action}` format as the AsyncAPI message `x-label`. The link is **one-directional** OpenAPI → AsyncAPI:
- **OpenAPI** → `x-emits: [{event: Order.Submitted}]` on the write operation declares what events it publishes
- **AsyncAPI** → the matching message file declares `x-label: {entity: Order, action: Submitted}`. The AsyncAPI side carries no reverse pointer; the cross-spec validator computes it.

**Multiple events**: An operation may emit multiple events:
```yaml
x-emits:
  - event: Order.Submitted
    description: Order status changed to submitted
  - event: Order.ItemsLocked
    description: All line items in the order are locked from edits
```

**Code generation impact**:
- The code generator wires up event publishing in the API layer (outbox pattern)
- Each event in `x-emits` generates a publish call at the end of the successful operation
- The Label is set to `{Entity}.{Action}` per the AsyncAPI Label convention (two segments only — tenancy lives in envelope ApplicationProperties)

**Cross-spec validation**:
- The structure validator checks that every `x-emits.event` has a matching AsyncAPI message with the same `x-label`
- The validator computes the reverse lookup (AsyncAPI message → OpenAPI emitters) from the same `x-emits` declarations — informational only, since events may also be published by `on-*`/`run-*` workers

**Arazzo cross-reference**: Arazzo scenarios use a related but structurally different mechanism — `x-async.emit` (nested under the step-level `x-async` extension) — to assert that a step publishes events. Both use the same `{Entity}.{Action}` event identity format, but they serve different purposes: `x-emits` on an OpenAPI operation is a **declaration** ("this operation publishes these events"), while `x-async.emit` on an Arazzo step is an **assertion** ("this step should produce these events during test execution"). Do not use top-level `x-emits` in Arazzo files. See §13.2 `x-async`.

### 6.2 x-aggregate-id

**Purpose**: Overrides the aggregate-ID property derivation when the payload's first required scalar isn't the right field. Maps to `aggregateIdProperty` + `aggregateIdType` in the rewritten event record.

**Scope**: AsyncAPI message payloads (or OpenAPI request DTOs feeding event emission)

**Schema**:
```yaml
x-aggregate-id: <propertyName>   # Name of the payload property to use as the aggregate ID
```

**When to use**: when the default derivation (first required scalar) picks the wrong property. For most events, the default is correct (the first required field is the aggregate ID). Use this extension only to override.

### 6.3 x-context-justification

**Purpose**: Required free-text rationale on operations that include a `Context` block in their event payload (per the project's event contract). Documents why transient metadata is being attached.

**Scope**: Applied to OpenAPI operations whose `x-emits` event payloads carry a `context` property

**Schema**:
```yaml
x-context-justification: string   # Free-text rationale; ≥ 40 chars
```

**Rules**:
- Required whenever the operation emits an event whose payload includes `context`.
- Validator group H rules enforce both presence and minimum length.
- The justification is preserved in generated doc-comments and the event audit trail.

---

## 7. Documentation and Test-Seed Extensions

### 7.1 x-business-rules

**Purpose**: Documents business rules and constraints.

**Scope**: Applied to schemas or properties

**Schema**:
```yaml
x-business-rules:
  - rule: string        # Rule description
    enforcement: string  # "database" | "application" | "manual"
    severity: string     # "error" | "warning" | "info"
```

### 7.2 x-examples

**Purpose**: Provides comprehensive examples for different scenarios.

**Scope**: Applied to schemas

**Schema**:
```yaml
x-examples:
  {scenarioName}:
    summary: string     # Example summary
    description: string # Detailed description
    value: object      # Example data
```

### 7.3 x-sample

**Purpose**: Annotates OpenAPI schema properties with realistic data-generation instructions. Consumed by Arazzo setup recipes (seed data), OpenAPI documentation renderers (realistic examples), mock servers, and dev/demo fixture seeding.

**Scope**: OpenAPI schema properties

**Required**: No — opt-in per property

**Schema**: `schemas/arazzo-extensions/x-sample.schema.json`

**Shape**:
```yaml
properties:
  firstName:
    type: string
    x-sample:
      provider: faker
      path: person.firstName

  status:
    type: string
    x-sample:
      provider: fixed
      format: active          # Literal value (for enums, weighted pick)

  email:
    type: string
    x-sample:
      provider: template
      format: "{person.firstName}.{person.lastName}@example.com"
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `provider` | Yes | string | Data generation strategy: `faker`, `fixed`, or `template` |
| `path` | When `faker` | string | Faker method path (e.g., `person.firstName`, `location.city`) |
| `locale` | No | string | Locale for data generation (e.g., `en-US`). Defaults to tenant locale when omitted. |
| `format` | No | string | Template string for the `template` provider (supports interpolation of faker paths), or literal value for `fixed` |

**Providers**:
- **`faker`** — generates data via faker library paths. The `path` field is required and maps to a faker method (e.g., `person.firstName`, `company.name`).
- **`fixed`** — returns a literal value from `format`. Useful for enums (weighted pick) and known constants.
- **`template`** — builds a string from a format template that interpolates faker paths in `{path}` placeholders.

**Rules**:
- `x-sample` may only appear on schema properties, not on the schema itself
- When `provider` is `faker`, the `path` field is required
- The `locale` field, when omitted, defers to the tenant's locale at generation time
- Do not place `x-sample` on properties that are server-generated (`id`, `createdAt`, `updatedAt`)
- **MUST place a DTO-local `x-sample` on any request-DTO property that `$ref`s an enum whose first literal is a sentinel** the handler will reject (`unknown`, `unspecified`, `none`, or any domain-specific auto sentinel like `accrual` for a transaction-type enum, `pending` when the DTO's flow transitions out of pending, etc.). The C# generator emits the enum's first literal as the field default; without the override the happy-path test 400s. See `API_Handbook.md §10.2` for the full checklist.

**Rationale**: Recipes need realistic, locale-aware test data without hardcoding values. `x-sample` provides a declarative, schema-adjacent annotation that multiple consumers (recipes, docs, mocks) can interpret independently. Without it, every recipe would embed ad-hoc data, leading to inconsistency and maintenance burden.

**See also**: `API_Handbook.md §10` (comprehensive authoring guide — scoping rules, canonical faker paths, locale handling, examples), `Arazzo_Handbook.md §7.7` (recipe data source), `schemas/arazzo-extensions/x-sample.schema.json`

---

### 7.4 x-test-seed-value

**Purpose**: Opts a specific non-`*Id`, non-enum string **path parameter** into a deterministic, seed-aligned literal in the generator's happy-path functional test. Replaces the default `Guid.NewGuid()` substitution that otherwise causes endpoints with backend-side value transformation (hashing, normalizing, slugifying) to 404.

**Scope**: OpenAPI path-parameter declarations only (not schema properties, not query/header params)

**Required**: No — opt-in per qualifying path parameter

**Introduced**: see `provenance.md` for the reference generator's PR history and the originating bug.

**Shape**:
```yaml
- name: token
  in: path
  required: true
  schema:
    type: string
  description: |
    Invitation token. Backend looks up by hash (column
    `Invitation.tokenHash`); consumer fixture must seed
    `tokenHash` with the backend's hash of the literal below.
  x-test-seed-value: "test-invitation-token-fixed"
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| value | Yes | string | Literal substituted into the generated happy-path test in place of `Guid.NewGuid()`. Embedded quotes auto-escaped. Empty string falls back to the legacy `Guid.NewGuid()` behavior. |

**Rules**:
- Apply ONLY when ALL of: `in: path`, `required: true`, `schema.type: string`, name does NOT end in `Id`, schema is NOT an enum, AND the backend transforms the value before lookup (hash / normalize / slugify / etc.)
- Do NOT apply to `*Id` path params — they already resolve via `TestSeed.<EntityName>Id`
- Do NOT apply to enum-typed path params — they already resolve via enum-literal substitution
- Do NOT apply when the param maps one-to-one to a directly-stored, case-sensitive spec property — use the entity's `x-sample` instead
- Recommended literal shape: `test-<entity>-<param>-fixed` (lowercase, hyphen-separated, `-fixed` suffix). Commit to ONE literal per `(entity, param)` tuple so the consumer fixture can mirror it exactly.
- The literal MUST satisfy the path param's own schema constraints (`minLength`, `maxLength`, `pattern`) — ASP.NET model binding runs first and 400s on violations before the handler ever queries the seeded entity. Pad the literal if needed (e.g. `test-invitation-token-fixture-aaaaa` for a `minLength: 32` token).
- The path-param `description` MUST document what transformation the backend applies and the storage column name (e.g. "Backend looks up by hash, column `Invitation.tokenHash`"). This note is what tells the consumer fixture how to wire the seed.

**Paired Backend work**: Adding the extension to a spec is necessary but not sufficient. The consumer backend fixture must seed an entity whose lookup column equals the backend's transformation of the literal. Open a tracking task on the backend repo when adopting this extension on a new endpoint — without the fixture, the generated test compiles but still 404s.

**Generator behavior**:
- Happy-path functional test → emits `var <param> = "<literal>";` instead of `var <param> = Guid.NewGuid();`
- Negative tests (401/Forbidden) → keep `Guid.NewGuid()`; no seed alignment needed
- Generated tests remain compile-clean whether the extension is present or absent

**Rationale**: Primary-key (`*Id`) and enum-typed path params have unambiguous seed sources the generator can infer. Opaque transformed lookup keys (magic-link tokens, share codes, slugs, normalized usernames) do not — the plaintext in the URL is never the value stored in the database. Without a declarative opt-in, every such endpoint produces a happy-path test that 404s, masking real coverage gaps.

**See also**: `API_Handbook.md §10.5` (authoring guide and qualification checklist), `provenance.md` (reference generator PR history)

---

### 7.5 x-membership-gated

**Purpose**: Test-emission-only opt-in on an OpenAPI operation declaring that the handler runs a runtime membership lookup (channel member, group participant, thread participant, project collaborator, etc.) *after* the role gate. Tells the generator to strip the highest-privilege role (typically `Admin`) from the `[InlineData]` rows of the happy-path test theory, because that role is a global unscoped principal with no membership row in the seed fixture.

**Scope**: OpenAPI operation objects (not schemas, not parameters)

**Required**: No — opt-in per qualifying operation

**Introduced**: see `provenance.md` for the reference generator's PR history and the originating bug.

**Shape**:
```yaml
post:
  operationId: sendMessage
  x-roles: [Admin, Manager, Member]
  # Handler verifies caller is an active ChannelMember of {channelId};
  # Admin has no ChannelMember row in the seed fixture.
  x-membership-gated: true
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| value | Yes | boolean | `true` strips the privileged role from the test theory's `[InlineData]` rows. `false` is equivalent to omitting the extension. |

**Rules**:
- Apply ONLY when the handler runs a membership lookup (`IsActiveMemberAsync`, `HasParticipantAsync`, `IsCollaboratorAsync`, …) after `[RoleRequired]` and returns 403 when missing.
- Do NOT apply when the role gate alone decides (no membership check).
- Do NOT apply when the principal is identity-resolved (per-user lookup with a 404 failure mode) — that's `x-self-scoped`.
- Do NOT apply when multiple non-privileged roles also lack the membership row — use `x-self-scoped` to whitelist seeded roles instead.
- Do NOT apply when the privileged role isn't in `x-roles` to begin with — nothing to strip.
- The accompanying YAML comment is mandatory: it documents what the handler dereferences so a reviewer can verify the opt-in.
- `x-roles` MUST stay complete — the privileged role remains in the production auth list. The extension only narrows the test theory, not the `[RoleRequired]` attribute.

**Test-emission-only**: This extension changes only the generator's emitted `[InlineData]` rows for the happy-path test theory. It does NOT change:
- `x-roles` (still the full authoritative list of permitted roles)
- The generated `[RoleRequired]` attribute on the controller
- The handler's runtime checks (consumer-written service code)

**No paired Backend work**: The seed fixture already populates membership rows for the non-privileged roles; the bug is purely that the privileged role can't be wired in.

**Rationale**: The privileged "global" role is unscoped with no natural per-org row. Channel/group/thread/project membership checks are correct in production (they keep the privileged role out unless explicitly added as a member), but they break the test theory's assumption that every role in `x-roles` succeeds in the happy path. The extension declaratively signals this runtime-data constraint so the generator can narrow the theory without authors hand-maintaining `[InlineData]` overrides.

**See also**: `API_Handbook.md §10.6` (authoring guide), `provenance.md` (reference generator PR history)

---

### 7.6 x-self-scoped

**Purpose**: Test-emission-only opt-in on an OpenAPI operation declaring that the handler resolves the caller to a per-principal runtime row (`Customer`, `Profile`, `Member`, etc.) and 404s when missing. Tells the generator to narrow the happy-path test theory to the role(s) for which the seed fixture pre-populates the row.

**Scope**: OpenAPI operation objects (not schemas, not parameters)

**Required**: No — opt-in per qualifying operation

**Introduced**: see `provenance.md` for the reference generator's PR history and the originating bug.

**Shape — single seeded role**:
```yaml
post:
  operationId: cancelMyOrder
  x-roles: [Admin, Manager, Customer]
  # Handler resolves caller → Customer via auth provider user id and 404s
  # if no row exists.
  x-self-scoped: Customer
```

**Shape — multiple seeded roles**:
```yaml
x-self-scoped: [Customer, GuestCustomer]
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| value | Yes | string \| string[] | Role(s) for which the seed fixture pre-populates the per-principal runtime row. Matching is case-insensitive. The intersection with `x-roles` wins; roles not in `x-roles` are silently dropped (typo guard). |

**Rules**:
- Apply ONLY when the handler resolves the caller to a per-principal row and 404s when missing. The canonical shape is `/me/*`, but the pattern applies anywhere "do something on behalf of the caller's `<entity>`" is in play.
- Do NOT apply when any authenticated user works (e.g. `/me/logout`) — the existing path-based privileged-role strip is sufficient.
- Do NOT apply when the endpoint is membership-gated rather than identity-resolved — use `x-membership-gated`.
- Do NOT apply when all roles in `x-roles` have the runtime row seeded — no narrowing needed.
- Do NOT apply when `x-roles` already lists only the self-scoped role (e.g. `[Customer]`) — nothing to narrow.
- The accompanying YAML comment is mandatory: it documents what the handler resolves so a reviewer can verify the opt-in.
- `x-roles` MUST stay complete — production auth list is untouched.

**Test-emission-only**: Same properties as `x-membership-gated` — narrows only the `[InlineData]` rows of the happy-path test theory; production auth, `[RoleRequired]`, and handler runtime checks are unchanged.

**No paired Backend work**: The seed fixture already populates the per-principal row for the named role(s); the bug was the test theory exercising other roles that don't get the row.

**Combines with `x-membership-gated`**: Orthogonal. Apply both when both conditions hold (e.g. a `/me/channels/{channelId}/markRead` endpoint that both resolves the caller's `Customer` row AND verifies channel membership). Narrowing applies sequentially.

**Role values are project-specific**: The runtime row may be `Customer`, `Profile`, `Member`, etc. Pick whichever role(s) the seed fixture pre-populates the runtime row for in your project.

**See also**: `API_Handbook.md §10.7` (authoring guide), `provenance.md` (reference generator PR history)

---

### 7.7 x-test-seed

**Purpose**: Overrides the C# expression used to resolve a **primary-key path parameter** in the generator's happy-path functional test, replacing the default `TestSeed.<Entity>Id` substitution with a consumer-provided seed-helper expression. Solves the case where several happy-path tests on the same primary-key path parameter have **mutually-exclusive entity-state preconditions** that one shared seed row cannot satisfy simultaneously.

**Scope**: OpenAPI operation objects (sibling of `operationId`, `x-roles`, `x-self-scoped`, …) — not on path parameters.

**Required**: No — opt-in per qualifying operation.

**Introduced**: see `provenance.md` for the reference generator's PR history and the originating bug.

**Shape**:
```yaml
post:
  operationId: submitMyOrder
  summary: Submit Placed Order
  x-test-seed:
    orderId: SeedOrderForSubmit()
  x-roles: [Admin, Manager, Customer]
  x-self-scoped: Customer
  # ...
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `<pathParameterName>` | At least one | string | C# expression emitted **verbatim** into the happy-path test body in place of `TestSeed.<Entity>Id`. Must be syntactically valid C# and return the path param's runtime type (typically `Guid`). Convention is a helper-method call (`SeedOrderForSubmit()`), but any expression resolving to the right type is accepted. |

**Rules**:
- Apply ONLY when multiple happy-path tests on the same primary-key path parameter have mutually-exclusive preconditions on entity fields (e.g. `Status`, `Priority`, `OwnerId`). The default `TestSeed.<Entity>Id` row can satisfy at most one set of preconditions; the others fail at runtime without an override.
- Do NOT apply when a single happy-path test exists on the path param — `TestSeed.<Entity>Id` is sufficient.
- Do NOT apply when the action only requires the row to exist (no precondition on column values) — no override needed.
- Do NOT apply to non-primary-key path params (tokens, slugs, codes) — use `x-test-seed-value` instead (§7.4).
- Each key MUST match an actual path-parameter name declared on the operation. A misspelled key produces an undefined-variable compile error in the generated test rather than silent fallthrough.
- The C# expression is emitted verbatim — pick a helper name the consumer can recognize and implement.

**Scope of the override** — applies ONLY to the `AsAllowedRole_ShouldReturn200` happy-path theory:
- `AsAnonymous_ShouldReturn401` → keeps `TestSeed.<Entity>Id` (auth gate fires before the row is loaded)
- `WithForbiddenRole_*_ShouldReturn403` → keeps `TestSeed.<Entity>Id` (role gate fires before the row is loaded)

Precondition state is irrelevant for the negative theories, so the shared seed row remains correct for them.

**Consumer contract**: The spec author and the consumer (backend test fixture) coordinate on the helper name. The consumer is responsible for providing the helper — typically a `protected` method on `ApiTestBase` (or whichever base class exposes seeding utilities) that:

1. **Inserts a fresh row** with the action's required preconditions.
2. **Returns the new row's primary key** for the generated test to use.
3. **Does NOT mutate the shared `TestSeed.<Entity>` row** — that row remains the generic GET/list reference for all other tests.

If the helper does not yet exist, the generated test fails to compile (the C# expression refers to an undefined symbol). This is intentional and explicit: the spec declares a contract; the consumer fulfills it.

**Distinction from `x-test-seed-value` (§7.4)**:

| | `x-test-seed` (this extension) | `x-test-seed-value` (§7.4) |
|---|---|---|
| Placement | Operation object | Path parameter object |
| Target path-param shape | Primary key (`*Id`) — `Guid`-typed | Non-`*Id` string (token, slug, code) |
| Override target | C# expression for the test sample | URL literal substituted into the request |
| Consumer responsibility | Provide a helper method that inserts a precondition-shaped row | Seed the entity's lookup column with the backend's transformation of the literal |
| Failure mode if absent | Precondition assertion fails at runtime | 404 on lookup (transformed key doesn't resolve) |

The two extensions are independent and may coexist on the same operation if both conditions hold (e.g. an opaque transformed-lookup key AND action-specific preconditions on a sibling `*Id` param).

**Canonical example**:

```yaml
# api/specs/v1/domains/order/operations/submit-my-order.yaml
post:
  operationId: submitMyOrder
  summary: Submit Placed Order
  x-test-seed:
    orderId: SeedOrderForSubmit()
  x-roles: [Admin, Manager, Customer]
  x-self-scoped: Customer
```

Generated (in `OrdersTest.g.cs`):

```csharp
public async Task SubmitMyOrder_AsAllowedRole_ShouldReturn200() {
    EnsureFakeData();
    var orderId = SeedOrderForSubmit();   // <-- was: TestSeed.OrderId
    // ...
}
```

Consumer side (test fixture):

```csharp
protected Guid SeedOrderForSubmit() => SeedOrder(o =>
{
    o.Status = OrderStatus.Placed;
});
```

Lifecycle-action endpoints are the canonical case: `submit`, `fulfill`, `cancel`, and `refund` on the same `/orders/{orderId}/*` family each require a different `Status` (plus other field constraints), so each action gets its own seed helper.

**Rationale**: `TestSeed.<Entity>Id` is a single shared row populated once per test fixture. It works for any read or list endpoint, and for write endpoints whose only precondition is "row exists." It breaks down when several happy-path tests on the same primary-key path param need different field values on the row (one needs `Status=Placed`, another needs `Status=Submitted`, etc.). Mutating the shared row to satisfy one test would break every other test that depends on it. `x-test-seed` lets each operation declare its own seed source without polluting the shared fixture row.

**See also**: `API_Handbook.md §10.8` (authoring guide), `provenance.md` (reference generator PR history)

---

## 8. Validation and Compliance

### 8.1 x-validation-rules

**Purpose**: Defines custom validation rules beyond OpenAPI schema validation.

**Scope**: Applied to schemas or properties

**Schema**:
```yaml
x-validation-rules:
  - rule: string        # Validation rule expression
    message: string     # Error message
    severity: string    # "error" | "warning"
```

### 8.2 x-compliance

**Purpose**: Documents regulatory compliance requirements.

**Scope**: Applied to schemas or properties

**Schema**:
```yaml
x-compliance:
  regulations: string[]  # Applicable regulations (e.g., ["GDPR", "PIPEDA"])
  dataClass: string     # Data classification level
  retention: string     # Data retention requirements
```

---

## 9. Extension Usage Guidelines

### 9.1 Mandatory Extensions

**All main resource schemas MUST include**:
- `x-entity` with appropriate type and relationships

**All secured operations MUST include**:
- `x-roles` with appropriate role restrictions
- `x-scopes` with appropriate OAuth scopes

**All write operations MUST include**:
- `x-emits` declaring the events the operation publishes

### 9.2 Optional Extensions

**Use when applicable**:
- `valueObjects` for entities containing value objects
- `x-ai-safe` for operations safe for autonomous execution
- `x-business-rules` for complex domain constraints

### 9.3 Extension Validation

Extensions are validated using Spectral rules defined in the project's Spectral ruleset (typically `schemas/spectral/specfuse.yaml`). Key validation rules:

**Entity and Relationship Validation**:
- Entity relationships must reference valid schemas (PascalCase aggregate names)
- Entities (type: entity) MUST have `belongsTo` defined
- `belongsTo` cardinality structure must use valid keywords (allOf, oneOf, oneOrMore, optional, zeroOrMore, optionalLinks)
- Deprecated array syntax for `belongsTo` generates warnings

**Storage and Security Validation**:
- Storage patterns must be from approved vocabulary (collection_json, single_json, flatten, serialized, separate_table)
- Role names must be from the project's closed role enum
- Scope names must follow naming conventions ({resource}.{action} in camelCase)

**Cardinality Validation Examples**:
```yaml
# ✅ Valid - Explicit cardinality
belongsTo:
  allOf: [Tenant]
  optional:
    oneOf: [Order, Customer]

# ⚠️ Warning - Deprecated array syntax
belongsTo: [Tenant, Order]

# ❌ Error - Invalid cardinality keyword
belongsTo:
  exactlyOne: [Tenant]  # Should be 'oneOf'

# ❌ Error - Entity missing belongsTo
x-entity:
  type: entity
  # Missing belongsTo - required for entities
```

---

## 10. Code Generation Integration

### 10.1 Template Data Structure

Code generation templates receive a normalized data structure derived from these extensions:

```json
{
  "entity": {
    "name": "Customer",
    "type": "aggregate",
    "relationships": {
      "belongsTo": {
        "required": ["Tenant"],
        "optional": {}
      },
      "hasMany": ["Order", "CustomerPreference"]
    },
    "properties": [],
    "valueObjects": [
      {
        "propertyName": "homeAddress",
        "schema": "Address",
        "storage": "single_json",
        "nullable": true,
        "queryable": false,
        "valueObjectMetadata": {
          "immutable": true,
          "comparable": true,
          "generateBuilder": false,
          "validationRules": [],
          "customSerializers": []
        }
      }
    ],
    "security": {
      "readRoles": ["Admin", "Manager"],
      "writeRoles": ["Admin"],
      "readScopes": ["customers.read"],
      "writeScopes": ["customers.write"]
    }
  }
}
```

### 10.2 Database Schema Generation

The cardinality constraints in `belongsTo` directly influence database schema generation:

**For `allOf` (Required Relationships)**:
```sql
-- Foreign key is NOT NULL
ALTER TABLE Customers
ADD CONSTRAINT FK_Customers_Tenant
FOREIGN KEY (TenantId) REFERENCES Tenants(Id) NOT NULL;
```

**For `optional.oneOf` (Optional Exclusive Relationships)**:
```sql
-- Foreign keys are nullable
ALTER TABLE OrderAttachments
ADD CONSTRAINT FK_OrderAttachments_Order
FOREIGN KEY (OrderId) REFERENCES Orders(Id);

-- Check constraint: at most one populated
ALTER TABLE OrderAttachments
ADD CONSTRAINT CHK_OrderAttachment_OptionalOwner
CHECK (
    (CASE WHEN OrderId IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN CustomerId IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN RefundId IS NOT NULL THEN 1 ELSE 0 END) <= 1
);
```

**For `optional.zeroOrMore` (Flexible Optional Relationships)**:
```sql
-- Foreign keys are nullable, no exclusivity constraint
ALTER TABLE ActivityLogEntries
ADD CONSTRAINT FK_ActivityLogEntries_Order
FOREIGN KEY (OrderId) REFERENCES Orders(Id);

ALTER TABLE ActivityLogEntries
ADD CONSTRAINT FK_ActivityLogEntries_Customer
FOREIGN KEY (CustomerId) REFERENCES Customers(Id);
-- Both can be populated simultaneously
```

### 10.3 Multi-Language Support

The same extension metadata generates appropriate code for different target languages:

- **C# EF Core**: Entity configurations, DbContext, repositories, immutable record types for value objects, nullable/non-nullable FK properties based on cardinality
- **TypeScript Prisma**: Schema definitions, client types, readonly interfaces for value objects, optional/required relations
- **Java JPA**: Entity classes, repository interfaces, value objects with equals/hashCode, @Column(nullable) based on cardinality
- **Python SQLAlchemy**: Model classes, relationship definitions, frozen dataclasses for value objects, nullable ForeignKey columns

---

## 11. Evolution and Versioning

### 11.1 Extension Versioning

Extensions follow semantic versioning principles:
- **Major**: Breaking changes to extension schema
- **Minor**: New optional properties or values
- **Patch**: Documentation updates, clarifications

### 11.2 Backward Compatibility

- New extension properties are always optional
- Deprecated properties are marked but remain functional
- Breaking changes require major version increment

### 11.3 Migration Path

When extensions evolve:
1. Update specification documentation
2. Update Spectral validation rules
3. Update code generation templates
4. Provide migration tools for existing specs

---

## 12. AsyncAPI Extensions (v2.1 — Pub-Sub + Snapshots)

The v2 async model is deliberately minimal: only two message categories (`event`, `scheduledJob`), only two channel types (`event-topic`, `scheduled-trigger`), and the entire architecture is pub-sub. Commands, sagas, point-to-point queues, and the thin-dispatcher-of-commands pattern have been removed.

For the full rules, rationale, and patterns, see the [AsyncAPI Handbook](./AsyncAPI_Handbook.md). This section is the extension reference.

### 12.1 Channel Extensions

#### x-domain
**Purpose**: Identifies the owning domain of a channel.
**Scope**: All channels
**Required**: Yes

```yaml
x-domain: order    # kebab-case domain name
```

The domain value must be drawn from the project's active domain list (defined in the project's overlay; location is project-specific).

**Arazzo cross-reference**: `x-domain` is also required on Arazzo workflow documents, where it identifies the owning domain of a scenario or recipe. The value set is the same project-defined domain list plus the reserved value `cross-domain` (valid only for files under `scenarios/cross-domain/`). See §13.1 `x-domain`.

#### x-channel-type
**Purpose**: Classifies the channel for code generation and infrastructure routing.
**Scope**: All channels
**Required**: Yes
**Values**: `event-topic`, `scheduled-trigger`

- `event-topic` — pub-sub topic; fan-out to N subscribers (e.g., Azure Service Bus topic, Kafka topic)
- `scheduled-trigger` — cron-triggered jobs, modelled as a logical channel (no real transport)

### 12.2 Message Extensions

#### x-message-category
**Purpose**: Classifies the message type.
**Scope**: All messages
**Required**: Yes
**Values**: `event`, `scheduledJob`

#### x-label
**Purpose**: Declares the message-routing Label segments AND the aggregate link.
**Scope**: All messages
**Required**: Yes

```yaml
x-label:
  entity: Order        # PascalCase aggregate/entity name — MUST match a schema with x-entity in OpenAPI
  action: Submitted    # PascalCase past-tense action verb
```

The runtime Label is exactly two segments: `{entity}.{action}` (e.g., `Order.Submitted`). **Tenancy never appears in the label** — `tenantId`, and any other tenant routing fields live in envelope ApplicationProperties. Subscription filters use `Label = '{Entity}.{Action}'` for single-action subscribers, `Label LIKE '{Entity}.%'` for wildcard-on-entity, or AND-merge `user.tenantId = '<guid>'` for tenant-scoped subscribers (see `x-subscription.requiredHeaders`).

**Action must be past-tense PascalCase.** `Created`, `Approved`, `Submitted`, `Archived`, `LinkedToNewTenant`, `QueuedForEmail`. Imperative verbs (`Create`, `Approve`) are not events — they are commands, which v2 architecture does not support.

`x-label.entity` IS the aggregate link — there is no separate `x-source-aggregate` or `x-target-aggregate`. The validator confirms `entity` matches a PascalCase schema with `x-entity` in OpenAPI specs.

**Labels are public contract.** Once a label has been published to a topic that has live consumers, it cannot be renamed. To change label semantics, mark the existing message `x-version.status: deprecated` with `replacedBy`, author the new message with the new label, and run both in parallel for the deprecation window.

**Arazzo cross-reference**: `x-label`'s `{Entity}.{Action}` format is the canonical event identity referenced by the Arazzo step-level `x-async` extension. When an Arazzo step declares `x-async.emit: [{event: Order.Submitted}]` or `x-async.await: {event: Order.Validated}`, the validator resolves the event name against AsyncAPI messages via their `x-label`. See §13.2 `x-async`.

#### x-version
**Purpose**: Schema versioning for backward-compatible message evolution.
**Scope**: All messages
**Required**: Yes

```yaml
x-version:
  current: 1              # Integer version number (>= 1)
  status: stable           # draft | stable | deprecated
  deprecatedAt: 2026-06-01 # ISO date — required when status == deprecated
  replacedBy: OrderSubmittedV2  # Successor message name — required when status == deprecated
  removalDate: 2026-12-01  # ISO date — optional target date for removing the deprecated version
```

**Evolution rules**: Within a version, only additive non-breaking changes (new optional fields, new enum values, relaxed constraints). Bump version for breaking changes (remove/rename fields, change types, make optional fields required).

**Snapshot version cascade**: when a snapshot referenced by an event message changes in a breaking way (renamed field, type change, removed required field, new required field), `x-version.current` MUST be bumped on every event message that `$ref`s that snapshot. Non-breaking snapshot changes (new optional field) require no bump anywhere. The Specfuse generator emits the impact graph at build time so cascades are visible at PR review.

**Snapshot dual-version coexistence**: when a breaking snapshot change forces a bump, the previous snapshot shape must remain available so deprecated event messages can still deserialize. The convention:

1. **Steady state (one live version):** snapshot file has no version suffix — `CustomerSnapshot.yaml` (the current shape).
2. **Breaking change lands:** rename the existing file to a versioned form (`CustomerSnapshotV1.yaml`), then author the new shape under the canonical name (`CustomerSnapshot.yaml`, now v2).
3. **Update event-message `$ref` paths:** existing event messages flip their `x-version.status` to `deprecated` with `replacedBy` pointing at the new-version event message, and rewrite their snapshot `$ref` from `CustomerSnapshot.yaml` → `CustomerSnapshotV1.yaml`. `x-version.current` on the deprecated message stays unchanged (it was always v1; only the `$ref` target moved).
4. **Author new event messages** at `x-version.current: 2` referencing `CustomerSnapshot.yaml`.
5. **After deprecation window expires** and `removalDate` passes: delete `CustomerSnapshotV1.yaml` and the deprecated event messages together.

The Spectral rule `specfuse-async-snapshot-version-coexistence` enforces both directions — deprecated event messages with a `replacedBy` pointing at a different version must `$ref` a versioned snapshot file (`*V{N}.yaml`); orphan versioned snapshot files with no deprecated referrer must be removed.

**Deprecation shape is unified across all three spec pillars** (OpenAPI, AsyncAPI, Arazzo). The same fields — `deprecatedAt`, `replacedBy`, `removalDate` — are used wherever `x-version` appears. There is no separate `x-deprecated` extension.

#### x-scheduled-job
**Purpose**: Cron schedule configuration for scheduled job messages.
**Scope**: Messages with `x-message-category: scheduledJob`
**Required**: Yes

```yaml
x-scheduled-job:
  cron: '0 2 * * 1'             # Standard cron expression (required)
  timezone: America/New_York     # IANA timezone (default: UTC)
  overlap: skip                  # skip | queue | cancelPrevious (default: skip)
  scope: perTenant               # global | perTenant | perCustomer (default: perTenant)
```

The `scope` enum values are project-tunable — define the scope levels that match your tenancy model. Generator accepts arbitrary kebab/camelCase values and emits one job instance per scope row.

#### x-partition-key
**Purpose**: Declares the session/partition key for ordered delivery on the transport.
**Scope**: Events requiring in-order processing
**Required**: No

```yaml
x-partition-key:
  property: orderId              # camelCase payload property
  scope: aggregate               # aggregate | tenant | customer (default: aggregate)
```

When present, the receiving operation's `x-subscription` should set `requiresSession: true`.

#### x-trigger-when
**Purpose**: Pure boolean predicate over `Before`/`After` snapshot fields that determines when a state-transition event fires.
**Scope**: State-transition messages (action suffix is NOT `Created`/`Updated`/`Deleted`)
**Required**: Yes on state-transition messages; **forbidden** on `*Created`/`*Updated`/`*Deleted`

```yaml
x-trigger-when: "After.status == 'archived' && Before.status != 'archived'"
```

**Why**: The action class of an event is inferred from its name suffix. State-transition events (anything not `*Created`/`*Updated`/`*Deleted`) need a declarative predicate so the generator-emitted service code knows *when* to emit the event during a save. The predicate is evaluated against `EntityEntry.OriginalValues` (Before) and `EntityEntry.CurrentValues` (After) before `SaveChangesAsync`. When matched, the transition event fires AND the corresponding `*Updated` is suppressed (mutual exclusivity).

**Predicate grammar (authoritative):**

| Construct | Allowed | Notes |
|---|---|---|
| `Before.<field>` / `After.<field>` references | ✅ | Top-level snapshot fields |
| Nested paths via dot (`After.address.city`) | ✅ | Owned value-object subfields only |
| Field-to-field comparisons (`After.startDate > After.endDate`) | ✅ | Both sides must be snapshot fields |
| Comparison operators (`==`, `!=`, `<`, `<=`, `>`, `>=`) | ✅ | |
| Boolean composition (`&&`, `||`, parens) | ✅ | |
| Primitive literals (int, string, bool) | ✅ | |
| `null` literal | ✅ | For nullable fields |
| Enum literals as strings (`'archived'`) | ✅ | Validated against the referenced enum schema |
| Function calls (`After.email.contains('@')`) | ❌ | Predicate must be pure |
| Time / `@now` arithmetic | ❌ | Predicate must be deterministic over the (Before, After) snapshot pair. If wall-clock matters, model it as a snapshot field. |
| Repository or DB lookups | ❌ | |
| Anything not pure over `(Before, After)` | ❌ | |

**Two enforcement surfaces**:
- **Spectral** (`specfuse-async-trigger-when-coherence`) catches authoring-time violations: required-on-transition / forbidden-on-CRUD / syntactic grammar parse.
- **Specfuse generator** type-checks the predicate against the snapshot schema at build time: unknown fields, type mismatches (e.g. comparing a `DateTimeOffset?` to `0`), invalid enum literals. Errors are emitted as `Specfuse-Build-Error` blocks with field suggestions.

**Mutual exclusivity & sibling-event semantics**: when one save satisfies multiple state-transition predicates, all matching transition events fire (siblings) and the `*Updated` is suppressed. Siblings share `correlationId`, `causationId`, `aggregateVersion`, and `producedAt`; each has its own `eventId`. Consumers MUST NOT depend on emit order.

**Context-bearing transitions**: when a state-transition event includes a `context` payload property (transient metadata that does not live on the entity, e.g., a cancellation reason), the auto-emission path cannot populate it. The author MUST declare `x-trigger-mode: explicit` (see below) so the Specfuse generator emits an explicit service method that takes the context as a parameter; the auto-emission path is suppressed for that event. `x-trigger-when` is still required on context-bearing events — it documents the semantic transition AND prevents the auto-path from emitting `*Updated`. The operation MUST also declare `x-context-justification` (see §6.3).

#### x-trigger-mode
**Purpose**: Selects how a state-transition event is emitted — `auto` (the generator-emitted dispatcher fires the event during `SaveChangesAsync` when `x-trigger-when` matches) or `explicit` (the generator emits a typed service method the handler calls, passing the `context`; the auto-dispatcher is suppressed).
**Scope**: State-transition messages.
**Required**: REQUIRED with value `explicit` whenever the payload carries a `context` field. Omit otherwise (defaults to `auto`).
**Valid values**: `auto | explicit`

```yaml
x-trigger-when: "After.status == 'cancelled' && Before.status != 'cancelled'"
x-trigger-mode: explicit          # payload carries `context`
payload:
  properties:
    context:
      allOf:
        - $ref: '../events/OrderCancelledContext.yaml'
      description: >-          # ≥ 40 chars justifying the transient metadata
        Transient per-cancellation metadata (reason, actor) not persisted
        on the order snapshot.
```

**Enforcement**: `specfuse-async-context-coherence` (context present ⇒ `x-trigger-mode: explicit` + `context.description` ≥ 40 chars) and `specfuse-async-subscription-trigger-mode-values` (enum check); the Specfuse generator's AsyncAPI validator errors identically.

#### x-method-name
**Purpose**: The imperative-verb name of the generated service method for a context-bearing explicit-mode transition. The generator cannot derive the imperative form from the past-tense action label (e.g. `OrderCancelled` → `CancelOrder`), so it must be declared.
**Scope**: State-transition messages with `x-trigger-mode: explicit`.
**Required**: REQUIRED on every context-bearing explicit transition. Generator-enforced (`MISSING_METHOD_NAME`); not a Spectral rule.
**Value**: PascalCase imperative verb phrase (e.g. `CancelOrder`, `Archive`, `Approve`).

```yaml
x-trigger-mode: explicit
x-method-name: CancelOrder        # imperative form of OrderCancelled
```

#### x-envelope-promote
**Purpose**: Marks a snapshot field that should also be stamped as an envelope ApplicationProperty so subscription filters can target it without inspecting the payload.
**Scope**: A property schema inside a snapshot file (e.g., `events/NotificationJobSnapshot.yaml`)
**Required**: No

```yaml
# In NotificationJobSnapshot.yaml
properties:
  channel:
    type: string
    enum: [email, sms, push]
    x-envelope-promote: true
```

**Why**: Filter granularity benefits from a small set of indexable headers (e.g., `channel` for `NotificationJob.*` events lets one channel-specific worker subscribe with `Label = 'NotificationJob.Created' AND user.channel = 'email'`). Without `x-envelope-promote`, the dispatcher would need entity-specific code to know which fields to promote — a leaky abstraction. With it, the generator emits generic stamping logic from the declaration.

**Rules:**
- Only scalar properties may be promoted (string, int, bool, enum, UUID). Objects and arrays are forbidden.
- Promoted values appear in the consumer's `EventEnvelope.AdditionalHeaders` dictionary keyed by the property name (camelCase).
- `requiredHeaders` on `x-subscription` (see §12.3) may reference any promoted header.
- Total promoted-header bytes per message MUST stay ≤ 1 KB (Spectral / generator enforces).
- Snapshot field and promoted header are guaranteed identical by the producer flow.

#### x-snapshot-size-acknowledged
**Purpose**: Acknowledgement opt-in on snapshot files that exceed the soft size cap (default 25 scalar fields).
**Scope**: Snapshot file root (`events/{Entity}Snapshot.yaml`)
**Required**: No (only when waiving the size warning)

```yaml
# At the root of CustomerSnapshot.yaml
x-snapshot-size-acknowledged: true
```

**Why**: Snapshots that grow large indicate the entity is doing too much, but some legitimate aggregates (settings bundles, configuration roots) genuinely have many scalar fields. Spectral warns above the cap; setting this flag silences the warning by recording an explicit team decision.

#### x-snapshot-pii-acknowledged
**Purpose**: Per-field justification block on snapshot files that intentionally include PII or sensitive entity properties.
**Scope**: Snapshot file root
**Required**: When a snapshot includes a property whose source entity field carries `x-classification: [pii]` or `x-classification: [sensitive]`

```yaml
# At the root of CustomerSnapshot.yaml
x-snapshot-pii-acknowledged:
  taxId: "downstream tax-reconciliation consumer needs decrypted tax ID; routed only to encrypted-channel subscribers"
  email: "invitation worker needs recipient address"
```

**Rules:**
- Each entry is a `propertyName: justification` pair. Bare lists (without justification) are rejected — Spectral requires the justification string ≥ 20 chars.
- Without an entry, a snapshot field whose source entity property carries a PII/sensitive classification fails Spectral validation.
- The acknowledgement is reviewed at PR time; the justification appears in generated audit logs.

### 12.3 Operation Extensions

#### x-worker
**Purpose**: Behavioral contract and runtime configuration for the handler.
**Scope**: All async operations
**Required**: Yes

```yaml
x-worker:
  name: order-enrichment         # Optional, kebab-case. Overrides the worker identity stem derived from the operation key.
  idempotent: true               # Default: true. Same input → same outcome.
  inboxDedup: true               # Default: true. Generator emits inbox-claim before HandleCoreAsync; set false for side-effect-free handlers.
  concurrency: 5                 # Default: 1. Max concurrent handler instances.
  timeout: 30s                   # Hard execution cap.
  settingsPrefix: OE             # Optional. Overrides the auto-derived env-var prefix for the settings class.
  tunables:                      # Optional. Worker-specific config fields emitted on the settings class.
    - name: enrichment_batch_size  # snake_case
      type: int                    # int | float | bool | str (default: str)
      default: 10                  # omit for a required field (no default)
```

**`name` (optional, kebab-case):** overrides the worker identity stem that the generator derives from the operation key. Affects the folder name, handler class name, worker class name, settings class name, and module/package name. Use when the operation key describes the triggering event but the worker's purpose is different — e.g., `on-customer-created` triggers the `customer-profile-setup` worker. When absent, the stem is derived by stripping the operation prefix (`on-`/`run-`/`emit-`) from the operation key.

**`inboxDedup` (optional boolean, default `true`):** controls whether the generated handler base inserts an inbox-claim row keyed on `(eventId, handlerName)` before invoking `HandleCoreAsync`. Default `true` is the safe choice: at-least-once delivery + inbox dedup gives effectively-once *processing*. Set `false` only for handlers with no DB writes and no externally-visible side effects (cache invalidator, metrics emitter) where the cost of the inbox row outweighs the safety. Coherence with `idempotent` and the operation's delivery-trait `guarantee` is enforced by Spectral rule `specfuse-async-worker-inbox-dedup-coherence`.

**`settingsPrefix` (optional, string):** overrides the auto-derived environment-variable prefix for the worker's generated settings class. By default, the generator takes the first letter of each kebab segment of `x-worker.name` (or the derived stem) and uppercases it (e.g., `order-enrichment` → `OE_`). Tunables are emitted as env vars under this prefix (e.g., `OE_ENRICHMENT_BATCH_SIZE=10`). Only set this when the auto-derived prefix would collide with another worker's prefix.

**`tunables` (optional, array of objects):** worker-specific configuration fields emitted as typed fields on the generated settings class. Each field becomes an environment-variable-configurable setting prefixed with the worker's env prefix. Each entry:

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | snake_case string | Field name on the generated settings class (e.g., `enrichment_batch_size`). |
| `type` | No | string | One of `int`, `float`, `bool`, `str`. Default: `str`. |
| `default` | No | any | Default value. Omit to declare the field as required (must be supplied via environment). |

Use `tunables` for runtime knobs that are not part of the event payload — thresholds, limits, feature toggles, external-service parameters — and that operations may want to tune per environment without a code change.

**What's intentionally not here:** `type`, `handlerName`, `namespace`. These are derived by the code generator from the operation's `action`, the channel's `x-channel-type`, the operation key (or `name` when set), and the target language's conventions. Putting language-specific names in the spec would violate the "specs do not dictate language" rule. `name` is NOT a replacement for these — it only controls the identity stem.

#### x-subscription
**Purpose**: Subscription configuration for event topic consumers.
**Scope**: `receive` operations on `event-topic` channels
**Required**: Yes (on event topic receivers). NOT used on `scheduled-trigger` channels.

```yaml
x-subscription:
  name: on-order-submitted            # MUST equal the operation file stem
  requiredHeaders:                    # Optional. Declarative envelope-header equality, AND-merged into the derived label filter.
    channel: email
  maxDeliveryCount: 10                # Default: 10
  lockDuration: 30s                   # Default: 30s
  requiresSession: false              # Default: false (set true when referenced message has x-partition-key)
```

| Field | Required | Type | Description |
|---|---|---|---|
| `name` | Yes | kebab-case string | MUST equal the operation file name minus `.yaml` (e.g., file `on-order-submitted.yaml` → name `on-order-submitted`). Validated by Spectral. |
| `requiredHeaders` | No | object | Declarative envelope-header equality map. Each `(key, value)` pair becomes `AND user.{key} = '{value}'` in the generated filter. Keys must be camelCase ApplicationProperty names that the universal envelope or `x-envelope-promote` declarations actually publish. |
| `filterOverride` | No | string | Raw SQL filter string. Mutually exclusive with `requiredHeaders`. Requires a `description` justification ≥ 40 chars on the operation explaining why derivation is insufficient. |
| `maxDeliveryCount` | No | integer | Max delivery attempts before dead-lettering. Default: 10. |
| `lockDuration` | No | duration | Lock duration during processing. Default: 30s. |
| `requiresSession` | No | boolean | Set `true` when the referenced message has `x-partition-key`. Default: false. |

**Filters are derived, not authored.** The generator computes the SQL filter from the operation's `messages:` list as an OR-chain over `Label` equality (or `LIKE` for wildcard-on-entity patterns). The legacy `filter` field is **forbidden** — Spectral rejects it. Three modes:

| Mode | Author writes | Generator emits |
|---|---|---|
| **Derived (default)** | `messages: [E1.Created.yaml, E2.Updated.yaml]` only | `Label = 'E1.Created' OR Label = 'E2.Updated'` |
| **`requiredHeaders`** | `messages:` list + `requiredHeaders: { channel: email }` | `<derived> AND user.channel = 'email'` |
| **`filterOverride`** | Raw SQL + mandatory `description` justification | The override verbatim |

`requiredHeaders` and `filterOverride` are mutually exclusive — Spectral rejects both on one operation.

**Filter cap**: a single filter may reference at most 10 distinct entity patterns (counting derived `Label = 'X.Y'` clauses or `LIKE 'X.` prefixes in an override). More than 10 is a smell; the worker likely needs splitting along a natural seam. Enforced by `asyncapi-subscription-filter-entity-cap` at error severity.

**Subscription name = operation file stem.** Spectral rule `specfuse-async-subscription-name-mismatch` validates this. Free-form kebab-case naming is no longer permitted.

#### x-observability
**Purpose**: Monitoring expectations, SLA thresholds, and alerting configuration.
**Scope**: All async operations
**Required**: Recommended (criticality required when present)

```yaml
x-observability:
  criticality: high              # low | medium | high | critical
  sla:
    maxProcessingTime: 5s        # Soft warning target
    maxAge: 60s                  # Alert if message queued too long
  metrics:
    - orderEnrichmentDuration    # Custom business metrics
  alertOnDlq: true               # Default: true
  tracing: full                  # full | minimal | none (default: full)
```

**Criticality enum** (standard four-level severity matching alerting infrastructure conventions):

| Level | Meaning | Alerting |
|---|---|---|
| `critical` | System unusable if this worker fails | Page on-call immediately |
| `high` | Core feature degraded | Alert within 5 minutes |
| `medium` | Non-core feature affected | Alert within 30 minutes |
| `low` | Cosmetic or deferrable impact | Daily digest |

The legacy value `normal` (used in early v2 specs) is no longer accepted — migrate to `medium`.

`sla.maxProcessingTime` is the soft warning; `x-worker.timeout` is the hard cap. Timeout should always be >= SLA.

#### x-ai
**Purpose**: Identifies workers requiring AI/LLM capabilities.
**Scope**: Operations that use AI/LLM for processing
**Required**: No

```yaml
x-ai:
  enabled: true
  task: recommendation           # generation | classification | extraction | summarization | analysis | translation | validation | recommendation
  model: claude-sonnet           # Informational — runtime configurable
  promptTemplate: order/enrich-order
  capabilities: [structuredOutput, toolUse]
  estimatedTokens: { input: 8000, output: 3000 }
  maxLatency: 30s
  fallback: queue                # skip | queue | default (default: queue)
  entities:                      # Required when enabled: true. Declares every entity the worker touches.
    reads: [Order, Customer]     # Entities the worker reads for context (must have aiAccess with 'read')
    creates: [OrderRecommendation] # Entities the worker creates (must have aiAccess with 'create')
    updates: [Order]             # Entities the worker updates (must have aiAccess with 'update')
    deletes: []                  # Entities the worker deletes (must have aiAccess with 'delete')
```

Valid `capabilities`: `structuredOutput`, `toolUse`, `rag`, `vision`, `streaming`, `multiTurn`, `batchProcessing`.

**`entities` field** (required when `enabled: true`):

Declares the complete set of entities the AI worker reads from and writes to. This makes the worker's data surface machine-readable for cross-spec validation and audit. Each entity name must be PascalCase and match a schema with `x-entity` in OpenAPI.

- **`reads`** — entities the worker reads for context or decision-making. Each must have `aiAccess` with `read` in `operations`.
- **`creates`** — entities the worker creates as part of its processing. Each must have `aiAccess` with `create` in `operations`.
- **`updates`** — entities the worker modifies. Each must have `aiAccess` with `update` in `operations`.
- **`deletes`** — entities the worker deletes. Each must have `aiAccess` with `delete` in `operations`. Empty in most cases (soft-delete is handled via `update`).

All four arrays are optional individually, but at least `reads` or one write array must be non-empty. The trigger entity (from the incoming message's `x-label.entity`) should appear in `reads` at minimum.

**Cross-spec validation rules** (enforced by the code generator):
1. Every entity in `reads` must have `aiAccess.operations` containing `read` in OpenAPI.
2. Every entity in `creates` must have `aiAccess.operations` containing `create`.
3. Every entity in `updates` must have `aiAccess.operations` containing `update`.
4. Every entity in `deletes` must have `aiAccess.operations` containing `delete`.
5. The trigger entity (incoming message's `x-label.entity`) must appear in at least `reads`.
6. Write-side entities (`creates`/`updates`/`deletes`) — each writable property the worker intends to set must be present in the entity's `aiAccess.writableProperties`. This is a design-time check (CLAUDE.md), not an automated validation, since the spec doesn't enumerate per-worker field usage.
7. Entity names must resolve to schemas with `x-entity` in the OpenAPI spec.
8. If `x-ai.entities` is absent but `x-ai.enabled` is `true`, emit an error.

The code generator chooses the target language using its own project configuration — the spec does not dictate it.

### 12.4 Delivery Trait Extensions

#### x-delivery
**Purpose**: Delivery guarantee and retry configuration, applied via operation traits.
**Scope**: Operation traits in `async-common/operation-traits/`

```yaml
x-delivery:
  guarantee: atLeastOnce         # atLeastOnce | atMostOnce | exactlyOnce
  maxRetries: 5                  # Default: 3
  retryBackoff: exponential      # linear | exponential
  deadLetterOnFailure: true      # Default: true
```

### 12.5 Removed and Forbidden Extensions

The following extensions existed in v1 (or were considered during v2 design) and have been **removed** or are **intentionally not introduced**. Specs referencing them will fail validation:

| Extension | Status | Replacement / Rationale |
|-----------|--------|-------------------------|
| `x-source-aggregate` | Removed | Use `x-label.entity` |
| `x-target-aggregate` | Removed | Commands removed — reframe as an event |
| `x-event` (type, aggregateType, triggerOperation) | Removed | Category is `event`; aggregate comes from `x-label.entity`; trigger is derived from OpenAPI `x-emits` |
| `x-command` | Removed | Commands removed — reframe as an event |
| `x-saga` | Removed | Sagas deferred to a future phase |
| `x-dispatches` | Removed | Use native AsyncAPI `send` operations instead |
| `x-worker.type` | Removed | Derived from `action` + `x-channel-type` |
| `x-worker.handlerName` | Removed | Derived from operation file name |
| `x-worker.namespace` | Removed | Derived from `x-domain` + target language convention |
| `x-channel-type: command-queue` | Removed | Use `event-topic` instead |
| `x-channel-type: job-queue` | Removed | Renamed to `scheduled-trigger` |
| `x-channel-type: saga` | Removed | Sagas deferred |
| `x-message-category: command` | Removed | Reframe as an event |
| `x-message-category: sagaStep` | Removed | Sagas deferred |
| `x-subscription.filter` (raw SQL author-written) | Forbidden | Filters are derived from the operation's `messages:` list; use `x-subscription.requiredHeaders` for header-equality and `x-subscription.filterOverride` only as a justified escape hatch. |
| `x-action-class` | Not introduced | Action class is inferred from the message-name suffix (`*Created` → created, `*Updated` → updated, `*Deleted` → deleted, anything else → state transition). |
| `x-pii` / `x-sensitive` (boolean per-field flags) | Not introduced as separate extensions | Use `x-classification` with values from the closed set `[pii, sensitive, encrypted, exposed]` on the entity property schema. See §1.5. |
| Three-segment `Label` (`{Entity}.{Action}.{tenantId}`) | Removed (v1 routing) | Labels are exactly two segments: `{Entity}.{Action}`. Tenant routing moves to envelope `tenantId` ApplicationProperty; tenant-scoped subscribers AND-merge `user.tenantId = '<guid>'` via `requiredHeaders`. |

### 12.6 OpenAPI ↔ AsyncAPI Cross-Spec Link

The link is **one-directional**: OpenAPI → AsyncAPI, via `x-emits` on write operations (see §6.1 `x-emits`). The AsyncAPI side carries no reverse pointer — the validator computes it.

- For every OpenAPI `x-emits.event`, the validator finds the matching AsyncAPI event message (same `x-label.entity` + `x-label.action`). Missing match → error.
- For every AsyncAPI event message, the validator may locate OpenAPI emitters (informational only — events can also be published by workers).

---

## 13. Arazzo Scenario and Recipe Extensions

Arazzo is the third pillar of the spec-first architecture (alongside OpenAPI and AsyncAPI). It describes multi-step behavioral scenarios — how actors interact with the API across operations, with assertions on responses and asynchronous outcomes. Arazzo vendor extensions provide actor binding, async modeling, documentation metadata, lifecycle management, and UI automation hints.

For the full rules, rationale, and patterns, see the [Arazzo Handbook](./Arazzo_Handbook.md). This section is the extension reference catalog.

**Eliminated extensions:** Three extensions originally considered during Arazzo design were eliminated before finalization:
- `x-category` — replaced by `x-recipe` presence as the discriminator (see Arazzo Handbook §7.1)
- `x-deprecated` — deprecation metadata lives inside `x-version` (see Arazzo Handbook §4.2)
- `x-tags` — uses native Arazzo `tags` array instead (see Arazzo Handbook §4.4)

### 13.1 Workflow-Level Extensions

#### x-actors

**Purpose**: Declares the actors who perform steps in a scenario. Each actor is bound to a role from the project's closed role enum and optionally to an entity seeded by a setup recipe.

**Scope**: Arazzo workflow

**Required**: Yes on scenario workflows; forbidden on recipe workflows

**Schema**: `schemas/arazzo-extensions/x-actors.schema.json`

**Shape**:
```yaml
x-actors:
  customer:
    role: Customer
    description: "The customer who placed the order"
    ref: $setup.outputs.customerId
  agent:
    role: SupportAgent
    description: "The support agent reviewing the request"
    ref: $setup.outputs.agentId
  manager:
    role: SupportManager
    description: "The support manager who oversees escalations"
    ref: $setup.outputs.managerId
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `<actorKey>` | — | object | Unique key within the workflow (camelCase) |
| `.role` | Yes | string | Role from the project's closed role enum (matches OpenAPI `x-roles`) |
| `.description` | No | string | Human-readable description of the actor's purpose |
| `.ref` | No | expression | Binds the actor to a recipe-seeded entity via `$setup.outputs.X` |

**Rules**:
- At least one actor must be declared (object must have `minProperties: 1`)
- Actor keys must be camelCase identifiers
- The `role` value must come from the project's closed role enum (same set as OpenAPI `x-roles`)
- The `ref` expression must follow the pattern `$setup.outputs.<name>`
- Recipes execute as an implicit `$system` actor mapped to the project's highest-privileged role — they must not declare `x-actors`

**Rationale**: Scenarios involve multiple users with different permissions acting on the same resources. Without explicit actor declarations, test generators cannot provision authentication contexts or enforce role-based access during execution.

**See also**: `Arazzo_Handbook.md §4.6`, §3.1 `x-roles` (role set), §13.1 `x-setup` (recipe binding)

#### x-doc (workflow level)

**Purpose**: Documentation metadata consumed by the doc generator and tutorial renderer. Provides a PM-facing summary, persona list, and business outcome for a workflow.

**Scope**: Arazzo workflow

**Required**: No (recommended on all scenario workflows)

**Schema**: `schemas/arazzo-extensions/x-doc.schema.json` (variant: `workflowDoc`)

**Shape**:
```yaml
x-doc:
  summary: "Customers can request a refund on a completed order, subject to agent approval."
  personas: [customer, support-agent]
  businessOutcome: "Self-service refund initiation reduces support burden."
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `summary` | Yes | string | One-paragraph PM-facing description |
| `personas` | No | string[] | User personas involved (informational) |
| `businessOutcome` | No | string | Why this workflow matters to the business |

**Rules**:
- When present, `summary` is required
- The workflow-level and step-level variants are mutually exclusive shapes within the same schema (JSON Schema `oneOf`)
- Do not duplicate the Arazzo `info.title` — the summary should add context beyond the title

**Rationale**: Generated documentation needs structured metadata to produce tutorial prose, persona-filtered views, and business-impact summaries. Without `x-doc`, the doc generator can only echo the workflow title.

**See also**: `Arazzo_Handbook.md §4.5`, §13.2 `x-doc (step level)` for the step-level variant

#### x-domain

**Purpose**: Identifies the owning domain of an Arazzo workflow document. Reuses the same domain vocabulary as AsyncAPI channels.

**Scope**: Arazzo workflow (document level)

**Required**: Yes

**Shape**:
```yaml
x-domain: order
```

**Valid values**: A kebab-case domain name drawn from the project's active domain list, or the reserved value `cross-domain`. The active domain list is defined by the project's overlay; the validator loads that list at lint time.

**Rules**:
- The `cross-domain` value is only valid for files under `scenarios/cross-domain/`; the validator enforces this path constraint
- The value determines the file's placement in the directory structure (`domains/{domain}/scenarios/`)

**Rationale**: Domain assignment drives file organization, documentation grouping, and CI impact analysis (which scenarios to run when a domain's OpenAPI operations change).

**See also**: `Arazzo_Handbook.md §4.3`, §12.1 `x-domain` (AsyncAPI channel usage)

#### x-mcp

**Purpose**: Declares whether a scenario workflow is exposed as an MCP (Model Context Protocol) tool for AI orchestrators. Inputs and outputs are derived from the workflow — not redeclared in `x-mcp`.

**Scope**: Arazzo workflow (scenario only)

**Required**: No (default: not exposed)

**Schema**: `schemas/arazzo-extensions/x-mcp.schema.json`

**Shape**:
```yaml
x-mcp:
  exposed: true
  toolName: request-refund
  description: "Request a refund for a completed order"
  requiresActorAuth: true
  safeForAutoInvoke: false
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `exposed` | Yes | boolean | Explicit opt-in for MCP tool exposure. Default: `false` |
| `toolName` | When exposed | string | kebab-case tool name, globally unique across all scenarios |
| `description` | When exposed | string | MCP-facing description of what the tool does |
| `requiresActorAuth` | No | boolean | Whether the tool requires actor authentication context. Default: `true` |
| `safeForAutoInvoke` | No | boolean | Whether an AI agent can invoke without human confirmation. Default: `false` |

**Rules**:
- When `exposed: true`, both `toolName` and `description` become required
- `toolName` must be globally unique across all scenarios in the repository (Spectral-enforced)
- `safeForAutoInvoke: true` should only be set for read-only, low-risk scenarios
- Forbidden on recipe workflows — recipes are infrastructure, not user-facing tools

**Rationale**: MCP tools allow AI orchestrators to discover and execute multi-step API workflows. Explicit opt-in (`exposed: false` default) prevents accidental exposure. Global `toolName` uniqueness is enforced from Phase 0 to prevent conflict accumulation before the MCP runtime ships (Phase 7).

**See also**: `Arazzo_Handbook.md §4.8`, `Arazzo_Handbook.md §11`

#### x-recipe

**Purpose**: Marks an Arazzo workflow as a setup recipe (test fixture provisioner) rather than a business scenario. Its presence is the recipe/scenario discriminator — there is no separate `x-category` field.

**Scope**: Arazzo workflow

**Required**: Conditional — required on recipe workflows; absent on scenario workflows

**Schema**: `schemas/arazzo-extensions/x-recipe.schema.json`

**Shape**:
```yaml
x-recipe:
  purpose: test-fixture
  extends: [minimal-customer]
  idempotent: true
  estimatedDurationMs: 800
  scope: scenario
```

| Field | Required | Type | Values | Description |
|-------|----------|------|--------|-------------|
| `purpose` | Yes | string | `test-fixture`, `demo-fixture`, `dev-fixture` | What the recipe provisions fixtures for |
| `extends` | No | string[] | Recipe file stems | Single-inheritance composition chain (max depth: 6) |
| `idempotent` | No | boolean | — | Whether running twice produces the same result. Default: `true` |
| `estimatedDurationMs` | No | integer | — | Estimated execution time (informational, for test scheduling) |
| `scope` | No | string | `scenario`, `session` | Lifetime of the fixture. Default: `scenario`. Session scope deferred to Phase 5+. |

**Rules**:
- All workflows in a file must share the same category (all recipes or all scenarios). Mixing is a validator error.
- Recipe composition via `extends` has a max chain depth of 6
- No cycles in the `extends` chain
- No output namespace collisions between parent and child recipes
- Recipes must not declare `x-actors`, `x-as`, `x-setup`, or `x-mcp`

**Rationale**: Recipes provide the foundation for reproducible test execution — they provision the entities, relationships, and state that scenarios exercise. The discriminator-by-presence pattern avoids a separate `x-category` enum and lets file paths confirm classification visually.

**See also**: `Arazzo_Handbook.md §7`, §13.1 `x-setup` (how scenarios reference recipes)

#### x-setup

**Purpose**: Declares which setup recipe must run before a scenario workflow to provision required test fixtures. The recipe's outputs become available via the `$setup.outputs.X` expression root.

**Scope**: Arazzo workflow (scenario only)

**Required**: No (optional on scenario workflows; forbidden on recipes)

**Schema**: `schemas/arazzo-extensions/x-setup.schema.json`

**Shape**:
```yaml
x-setup:
  recipe: completed-order-with-customer
  inputs:
    orderPlacedDate: "@today-7d"
    customerName: "Acme Co."
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `recipe` | Yes | string | File stem of the recipe (e.g., `completed-order-with-customer` resolves to `completed-order-with-customer.recipe.yaml`) |
| `inputs` | No | object | Values passed to the recipe's workflow `inputs`. Supports date tokens (`@today+3d`, `@now-1h`). |

**Rules**:
- The `recipe` value must resolve to an existing recipe file
- Recipes cannot reference `$setup` — only scenarios may. Recipes compose via `extends`.
- Date tokens in `inputs` values follow the grammar in Arazzo Handbook §8.3
- The recipe's `outputs` become available as `$setup.outputs.X` in the scenario

**Rationale**: Decoupling fixture provisioning (recipes) from business scenario logic (scenarios) enables reuse — the same recipe can back multiple scenarios — and keeps scenario files focused on the behavioral flow under test.

**See also**: `Arazzo_Handbook.md §4.7`, §13.1 `x-recipe` (recipe definition), `Arazzo_Handbook.md §8` (expression reference)

#### x-version

**Purpose**: Lifecycle and status metadata for Arazzo workflows. Unified shape shared across all three spec pillars (OpenAPI, AsyncAPI, Arazzo). Deprecation metadata lives inside this extension — there is no standalone `x-deprecated`.

**Scope**: Arazzo workflow (document level)

**Required**: Yes

**Schema**: `schemas/arazzo-extensions/x-version.schema.json`

**Shape**:
```yaml
x-version:
  current: 1
  status: stable

# Deprecated example:
x-version:
  current: 1
  status: deprecated
  deprecatedAt: "2026-06-01"
  replacedBy: request-refund-v2
  removalDate: "2026-12-01"
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `current` | Yes | integer | Schema version number (>= 1), monotonically increasing |
| `status` | Yes | string | `draft`, `stable`, or `deprecated` |
| `deprecatedAt` | When deprecated | string | ISO date when this version was deprecated |
| `replacedBy` | When deprecated | string | Successor scenario or recipe file stem |
| `removalDate` | No | string | Target date for removing the deprecated version |

**Rules**:
- Both `current` and `status` are always required
- When `status` is `deprecated`, `deprecatedAt` and `replacedBy` become required
- Within the same version, only non-breaking changes are allowed (add steps, add outputs, relax assertions)
- Breaking changes (remove/rename workflows, steps, or outputs; change required inputs) require bumping `current`

**Rationale**: A unified lifecycle extension across all three pillars provides consistent tooling for deprecation tracking, version-gated test generation, and CI enforcement. Embedding deprecation metadata inside `x-version` (rather than a separate `x-deprecated`) keeps lifecycle concerns in one place.

**See also**: `Arazzo_Handbook.md §4.2`, `Arazzo_Handbook.md §10`, §12.2 `x-version` (AsyncAPI usage)

### 13.2 Step-Level Extensions

#### x-as

**Purpose**: Identifies which actor performs a scenario step. The value must reference an actor defined in the workflow's `x-actors`.

**Scope**: Arazzo step

**Required**: Yes on all scenario steps; forbidden on recipe steps

**Schema**: `schemas/arazzo-extensions/x-as.schema.json`

**Shape**:
```yaml
steps:
  - stepId: create-refund-request
    x-as: $customer
    operationId: requestRefund
    requestBody:
      payload:
        orderId: $setup.outputs.orderId
    successCriteria:
      - condition: $statusCode == 201
```

**Rules**:
- The value is a string matching the pattern `$<actorKey>` (e.g., `$customer`, `$agent`)
- The actor key (after the `$` prefix) must resolve to an entry in the workflow's `x-actors`
- Recipe steps execute as the implicit `$system` actor and must not use `x-as`

**Rationale**: Multi-actor scenarios require explicit attribution of each step to a specific user — test generators need to switch authentication contexts, and documentation generators need to show who does what in sequence diagrams.

**See also**: `Arazzo_Handbook.md §5.1`, §13.1 `x-actors`

#### x-async

**Purpose**: Models event-driven interactions within a scenario step. Provides three verbs — `emit` (assert event publication), `await` (wait for an event), and `poll` (poll a REST endpoint) — to bridge the gap between Arazzo's REST-native step model and Specfuse's event-driven architecture.

**Scope**: Arazzo step

**Required**: No (used on steps involving asynchronous behavior)

**Schema**: `schemas/arazzo-extensions/x-async.schema.json`

**Shape**:
```yaml
# emit — assert that the step publishes events
x-async:
  emit:
    - event: Refund.Requested
      expect:
        customerId: $setup.outputs.customerId
      timeout: PT10S

# await — passively wait for an event
x-async:
  await:
    event: CustomerProfile.Enriched
    match:
      customerId: $steps.create-customer.outputs.customerId
    timeout: PT60S
    outputs:
      enrichmentStatus: $message.payload.status

# poll — poll a REST endpoint until a condition is met
x-async:
  poll:
    operationId: getRefund
    parameters:
      refundId: $steps.create-refund-request.outputs.refundId
    until: $response.body#/status == 'validated'
    interval: PT2S
    timeout: PT30S
```

**Verb reference**:

| Verb | Purpose | Key Fields |
|------|---------|------------|
| `emit` | Assert event publication | `event` (required), `expect` (partial payload match), `timeout` (default: `PT10S`) |
| `await` | Wait for an asynchronous event | `event` (required), `match` (payload filter), `timeout` (required), `outputs` (extracted values via `$message.*`) |
| `poll` | Poll a REST endpoint | `operationId` (required), `parameters`, `until` (required condition), `interval` (default: `PT2S`), `timeout` (required) |

**Rules**:
- At least one verb must be present (`emit`, `await`, or `poll`)
- A step may combine `emit` with either `await` or `poll`
- `await` and `poll` are mutually exclusive within the same `x-async` block
- Event names use `{Entity}.{Action}` PascalCase format matching AsyncAPI `x-label`
- Authors never write channel addresses — the validator derives channels from the resolved message
- `await` steps do not declare `operationId` (they are purely event-driven)
- For AI worker flows, assert observable outcomes only (terminal events or REST state), never internal worker details
- **Poll limitation (same-status transitions):** When async processing leaves the status unchanged (e.g., entity stays `draft` after regeneration), the `until` condition is trivially true. Pair `poll` with a preceding `await`, or document the limitation with `x-doc.tutorialNote`. See handbook §6.2.

**Rationale**: Arazzo 1.0.1 has no native async/event primitives. `x-async` bridges this gap with a minimal, self-contained extension that models the three interaction patterns needed for event-driven scenario testing. When Arazzo 1.1.0 ships with native AsyncAPI support, the migration from `x-async.emit`/`x-async.await` to native syntax is mechanical because the extension is nested and self-contained.

**See also**: `Arazzo_Handbook.md §6`, §6.1 `x-emits` (related OpenAPI declaration), §12.2 `x-label` (event identity format)

#### x-doc (step level)

**Purpose**: Step-level documentation metadata for tutorial generation. Provides contextual notes rendered in generated tutorial documentation.

**Scope**: Arazzo step

**Required**: No

**Schema**: `schemas/arazzo-extensions/x-doc.schema.json` (variant: `stepDoc`)

**Shape**:
```yaml
steps:
  - stepId: approve-refund
    x-as: $agent
    operationId: approveRefund
    x-doc:
      tutorialNote: "This step is visible only to support agents with pending refund requests."
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `tutorialNote` | No | string | Contextual note rendered in generated tutorial documentation |

**Rules**:
- The step-level variant has a different shape from the workflow-level variant (JSON Schema `oneOf` discriminates)
- At least one property must be present when `x-doc` is used at step level (`minProperties: 1`)

**Rationale**: Individual steps often need contextual notes that don't fit in the workflow summary — visibility conditions, prerequisite state, or domain-specific caveats. Without step-level `x-doc`, these notes would be lost or embedded in step descriptions that serve a different purpose.

**See also**: `Arazzo_Handbook.md §5.4`, §13.1 `x-doc (workflow level)` for the workflow-level variant

#### x-ui

**Purpose**: Provides UI automation hints consumed by the LLM-driven exploratory runner and the Playwright test generator. Each step may declare user-facing actions, expected visual outcomes, and optional Playwright selectors.

**Scope**: Arazzo step

**Required**: No (optional on steps with user-facing interactions)

**Schema**: `schemas/arazzo-extensions/x-ui.schema.json`

**Shape**:
```yaml
x-ui:
  platform: web
  page: /orders/history
  actions:
    - id: open-order
      text: "Click the order from last week"
    - id: open-refund-dialog
      text: "Click 'Request refund' button"
    - id: confirm-request
      text: "Click 'Confirm' to submit the refund request"
  expect:
    - "A toast confirms the request was submitted"
    - "The order tile shows a 'Refund pending' badge"
  selectors:
    - for: open-order
      playwright: "[data-testid='order-tile-recent']"
    - for: confirm-request
      playwright: "button:has-text('Confirm')"
  captureScreenshot: true
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `platform` | No | string | `web`, `mobile`, or `any`. Default: `any` |
| `page` | No | string | The page or route where this step takes place |
| `actions` | Yes | array | Ordered list of user-facing actions |
| `actions[].id` | Yes | string | Stable identifier (kebab-case) |
| `actions[].text` | Yes | string | Natural-language description for LLM agent and tutorial prose |
| `expect` | No | string[] | Expected visual outcomes after the step completes |
| `selectors` | No | array | Optional Playwright selector hints |
| `selectors[].for` | Yes | string | Must reference an `actions[].id` in the same step |
| `selectors[].playwright` | Yes | string | Playwright selector string |
| `captureScreenshot` | No | boolean | Whether to capture a screenshot after this step. Default: `false` |

**Rules**:
- `actions` is required and must contain at least one item
- Every `selectors[].for` value must match an `actions[].id` in the same step (dangling references are a Spectral error)
- Action `id` values must be kebab-case
- Two consumption modes: LLM-driven (reads `actions[].text` + `expect`) and Playwright (reads `selectors[].playwright`, falls back to LLM-derived selectors)

**Rationale**: Bridging API-level scenarios to UI-level test automation requires structured hints about where actions happen and what the user sees. `x-ui` enables both deterministic Playwright tests (via selectors) and adaptive LLM-driven exploratory testing (via natural-language action descriptions) from a single source of truth.

**See also**: `Arazzo_Handbook.md §5.3`

---

This specification ensures consistent, predictable, and maintainable use of vendor extensions across all Specfuse OpenAPI, AsyncAPI, and Arazzo specifications, enabling robust code generation, test generation, and system integration.
