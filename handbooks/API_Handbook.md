# API Handbook

This handbook defines authoritative rules for designing REST APIs and OpenAPI specs in a Specfuse project so they're consistent, code-gen friendly, and agent-friendly.

---

## 0) Conventions (global)

- **Casing**
  - **Models (schema names):** PascalCase (`Customer`).
  - **Paths, query params, JSON properties, enum values:** camelCase.
  - **Schema properties:** camelCase.
- **Paths & params**
  - Path parameters use `{resourceId}` form (e.g., `{customerId}`, `{orderId}`) even though the model field is `id`.
  - **Direct entity access omits the parent aggregate from the path.** Use `/{resource}/{resourceId}` — never `/parentResources/{parentId}/{resource}/{resourceId}`. The parent context is implied by the resource's own ID. This applies to GET, PATCH, DELETE on a specific resource, and to lifecycle action sub-paths.
    - ✅ `GET /orders/{orderId}`
    - ✅ `PATCH /orderLines/{orderLineId}`
    - ✅ `POST /orders/{orderId}/submit`
    - ❌ `GET /customers/{customerId}/orders/{orderId}`
    - ❌ `PATCH /orders/{orderId}/lines/{orderLineId}`
  - **Collection endpoints (list/create) use the parent path.** Use `/parentResources/{parentId}/{resource}` for scoped collections.
    - ✅ `GET /customers/{customerId}/orders`
    - ✅ `POST /customers/{customerId}/orders`
    - ✅ `POST /orders/{orderId}/lines`
  - **Lifecycle actions** use `POST /{resource}/{resourceId}/{action}` (slash, not colon).
    - ✅ `POST /orders/{orderId}/submit`
    - ✅ `POST /orders/{orderId}/cancel`
    - ❌ `POST /orders/{orderId}:submit`
- **Enums**
  - Never inline inside a model. Define as a separate schema named `{Resource}{EnumName}` (e.g., `OrderStatus`).
  - Enum values are **camelCase**.
  - Clients must tolerate new/unknown enum values.

---

## 0.1) OpenAPI File Structure (Domain-Driven Organization)

### Directory Structure

```
api/specs/v1/
├── openapi.yaml                    # Main spec file (references all domains)
├── common/                         # Shared components
│   ├── parameters/
│   │   ├── path.yaml              # Path parameters (tenantId, customerId, etc.)
│   │   ├── pagination.yaml        # Pagination parameters (page, pageSize, sort)
│   │   └── ai-integration.yaml    # AI-specific parameters
│   ├── responses/
│   │   └── errors.yaml            # Standard error responses
│   ├── headers/
│   │   └── common.yaml            # Common headers (ETag, API-Version, etc.)
│   ├── securitySchemes/
│   │   └── auth.yaml              # OAuth2 / OIDC configuration
│   ├── enums.yaml                 # Common enums (CurrencyCode, etc.)
│   └── common.yaml                # Other shared components
└── domains/                        # Domain-specific files
    └── {domain}/
        ├── models/                # Schema definitions
        │   ├── {Resource}.yaml
        │   ├── Basic{Resource}.yaml
        │   ├── New{Resource}.yaml
        │   └── ...
        └── operations/            # Operation definitions
            ├── list-{resources}.yaml
            ├── create-{resource}.yaml
            ├── get-{resource}.yaml
            └── ...
```

Domain folder names follow the project's domain naming convention (kebab-case, one folder per bounded context). The active domain list is the **domain registry** declared in `info.x-domains` on the OpenAPI root (see below).

### Domain registry (`info.x-domains`)

`info.x-domains` is the project's authoritative **closed universe** of domains. Every domain the project has must appear here exactly once, keyed by its kebab-case name; nothing outside this map is a valid domain.

```yaml
info:
  title: Acme API
  version: 1.0.0
  x-domains:
    order:
      title: Orders
      description: Order capture, fulfilment, and lifecycle.
    customer:
      title: Customers
      description: Customer accounts and profiles.
```

Every reference to a domain across the three specs resolves against this registry:

- `x-entity.domain` on each OpenAPI entity (`Vendor_Extensions.md §1.1`) — MUST be a registered key (`ENTITY_DOMAIN_UNREGISTERED`, ERROR otherwise).
- `x-domain` on every AsyncAPI channel and Arazzo workflow (`Vendor_Extensions.md §12.1`, `§13.1`) — same key set (plus the reserved `cross-domain` value for Arazzo files under `scenarios/cross-domain/`).
- The `domains/{domain}/` folder name and the entity's PascalCase OpenAPI tag.

A domain key's `title` is the PascalCase display/tag name; `description` is a one-line charter. Adding a domain is a single edit here first — then the folder, tag, and any `domain`/`x-domain` references may use it.

### File Naming Conventions

#### Model Files (in `domains/{domain}/models/`)
- **Full resource**: `{Resource}.yaml` (e.g., `Customer.yaml`)
- **Basic projection**: `Basic{Resource}.yaml` (e.g., `BasicCustomer.yaml`)
- **Create request**: `New{Resource}.yaml` (e.g., `NewCustomer.yaml`)
- **Update request**: `Update{Resource}.yaml` (e.g., `UpdateCustomer.yaml`)
- **Search request**: `{Resource}SearchRequest.yaml`
- **List wrapper**: `{Resource}List.yaml`
- **Enums**: `{EnumName}.yaml` (e.g., `CustomerStatus.yaml`)

#### Operation Files (in `domains/{domain}/operations/`)
- **ALWAYS** named after the `operationId` in **kebab-case**
- Examples:
  - `operationId: listCustomers` → `list-customers.yaml`
  - `operationId: getCustomer` → `get-customer.yaml`
  - `operationId: createCustomer` → `create-customer.yaml`
  - `operationId: updateCustomer` → `update-customer.yaml`
  - `operationId: archiveCustomer` → `archive-customer.yaml`

### OpenAPI Path References

**Direct operation references** (no intermediate resource files):

```yaml
paths:
  /customers/{customerId}:
    parameters:
      - $ref: './common/parameters/path.yaml#/customerId'
    get:
      $ref: './domains/customer/operations/get-customer.yaml#/get'
    patch:
      $ref: './domains/customer/operations/update-customer.yaml#/patch'
    delete:
      $ref: './domains/customer/operations/archive-customer.yaml#/delete'
```

### Operation File Structure

Each operation file contains:
1. **Parameters** (if needed at operation level)
2. **HTTP method** (get, post, patch, delete, put)
3. **Operation definition** (operationId, tags, summary, description, etc.)

Example (`get-customer.yaml`):
```yaml
parameters:
  - $ref: '../../../common/parameters/path.yaml#/customerId'

get:
  operationId: getCustomer
  tags: [Customers]
  summary: Get Customer
  description: |
    Returns a customer by ID with full details.
  x-roles: [Admin, Manager]
  x-scopes: [customer.Customer.read]
  responses:
    '200':
      description: OK
      content:
        application/json:
          schema:
            $ref: '../models/Customer.yaml'
    '404':
      $ref: '../../../common/responses/errors.yaml#/NotFoundError'
```

### Benefits of This Structure

1. **Domain isolation**: Each domain's models and operations are self-contained
2. **Discoverability**: Easy to find operations by operationId
3. **Maintainability**: Changes to one domain don't affect others
4. **Code generation**: Clear boundaries for generating domain-specific clients
5. **No duplication**: Direct references eliminate intermediate files
6. **Consistency**: Same pattern across all domains

### Rules for AI Assistants

When creating or modifying OpenAPI specs:

1. ✅ **DO** place model files in `domains/{domain}/models/`
2. ✅ **DO** name operation files after their operationId in kebab-case
3. ✅ **DO** reference operation files directly from `openapi.yaml`
4. ✅ **DO** use common parameters from `common/parameters/`
5. ❌ **DON'T** create intermediate "resource files" that group operations
6. ❌ **DON'T** use path-based naming for operation files
7. ❌ **DON'T** inline parameters that exist in `common/parameters/`

---

## 1) Resource models & derivatives (Phase #1)

Using **Customer** as an example; apply globally to any resource.

### 1.1 Main resource (full read)
- **Schema name:** `{Resource}` (e.g., `Customer`).
- **Must include:** `id`, `createdAt`, `updatedAt`.
- **Embedding subresources:** only when explicitly requested; default is not embedded.
- **Enums:** use separate schemas (e.g., `CustomerStatus`).

```yaml
components:
  schemas:
    Customer:
      type: object
      required: [id, createdAt, updatedAt]
      properties:
        id:        { type: string, format: uuid }
        createdAt: { type: string, format: date-time }
        updatedAt: { type: string, format: date-time }
        status:    { $ref: '#/components/schemas/CustomerStatus' }
```

### 1.2 Lightweight/list projection
- **Schema name:** `Basic{Resource}` (e.g., `BasicCustomer`).
- **Purpose:** used in list responses and when embedded under a parent; **never** includes subresources.
- **Fields:** subset of the main resource's existing fields. The assistant may suggest fields but must not invent ones that don't exist on `{Resource}`.

```yaml
BasicCustomer:
  type: object
  required: [id]
  properties:
    id:        { type: string, format: uuid }
    firstName: { type: string }
    lastName:  { type: string }
    status:    { $ref: '#/components/schemas/CustomerStatus' }
```

### 1.3 Create request (POST)
- **Schema name:** `New{Resource}` (e.g., `NewCustomer`).
- **Semantics:** client-settable fields only; no `id/createdAt/updatedAt`. Server always generates `id`.

```yaml
NewCustomer:
  type: object
  required: [firstName, lastName]
  properties:
    firstName: { type: string }
    lastName:  { type: string }
```

### 1.4 Full replace request (PUT)
- **Body schema:** **`New{Resource}`** (same as create).
- **Semantics:** full replacement; missing fields reset to defaults.

### 1.5 Partial update (PATCH)
- **Schema name:** `Update{Resource}` (e.g., `UpdateCustomer`).
- **Semantics:** partial update; all properties optional; unknown fields ignored per global rule.
- **Content-Type:** `application/json`.
- **Tri-state, decided per field:** a property **absent** from the body is untouched; a property **present** carries the field's new value. For collection-typed properties, "the new value" means the complete desired set — see §1.5.1.

```yaml
UpdateCustomer:
  type: object
  additionalProperties: false
  properties:
    firstName: { type: string }
    lastName:  { type: string }
    status:    { $ref: '#/components/schemas/CustomerStatus' }
```

### 1.5.1 Collection properties in `Update{Resource}` — complete-set reconcile

PATCH decides at the **field** level: absent means untouched, present means "here is the new value". What that means for a collection is the part worth spelling out, because the intuitive reading — merge the incoming elements into the stored ones — is **not** the contract.

**A collection property present in the body is the complete desired set. There is no merge mode.**

| Collection kind | Semantics when present in the body |
|---|---|
| Value-object / scalar arrays (tags, metadata, …) | The stored array is **replaced entirely**, not merged. The property `description` must say so. |
| Child-entity collections (arrays of `Update{Child}` backing a `hasMany`) | Identity-based reconcile against the tracked children — see below. |

#### Child-entity reconcile

| Incoming element | Behaviour |
|---|---|
| Carries a **known `id`** | Update that child **in place**. The PK is preserved, so `x-references` FKs pointing at this child from other aggregates stay valid. |
| Carries **no `id`** | Create. The element is validated **as a create** — the child's client-settable required fields are enforced, and a violating element fails the whole PATCH with `400`. |
| Carries an **unknown `id`** | `404`. Never a silent create-with-client-supplied-id. |
| Tracked child **absent from the array** | **Delete, permanently.** |

**Deletion is a hard delete and is not recoverable.** Reconciled children are aggregate-internal state — the same category as the elements of a replaced value-object array — so a project-wide soft-delete convention for top-level resources does **not** extend to reconcile removals. Consumer-facing descriptions must state that omitted children are permanently removed. Getting this wrong in prose is worse than getting it wrong in code: a client that believes omission is recoverable will discover otherwise in production.

**What fences the accidental-deletion risk** is machinery the contract already mandates, not a special case:

- **`If-Match` is required on every PATCH** (§2). That forces read-modify-write, so a client cannot send a partial array without having first read the current one.
- **`?validateOnly=true`** gives a dry run before committing.

#### DTO shape rule

An `Update{Child}` DTO used as an array element inside a parent's `Update{Parent}` MUST expose an **optional** identity property:

```yaml
UpdateOrderLine:
  type: object
  additionalProperties: false
  properties:
    id:
      type: string
      format: uuid
      description: >-
        Identifies an existing line to update in place. Omit to create a new
        line. Lines omitted from the array are permanently deleted.
    quantity: { type: integer }
    note:     { type: string }
```

Omitting `id` from the DTO entirely leaves the server unable to tell an update from a create, and the only available fallback — delete every tracked child and re-add the incoming ones — recreates rows with new PKs on every PATCH. That breaks `x-references` FKs pointing at those children, audit trails, and concurrency tokens. **Delete-then-add is forbidden as a fallback.** Instead:

- **Spec validation raises a WARN** naming the spec file and property path: *child collection reconcile requires an optional `id` on `Update{Child}` — add it*.
- **Generation fails closed** rather than emitting the destructive fallback.

The rule fires **only** on the specific shape — an `Update*` DTO used as an array element inside another `Update*` DTO. A blunt "every `Update*` DTO needs an `id`" rule would be a false-positive storm, since most `Update*` DTOs are the body of a PATCH addressed by URL, where the identity is in the path.

#### Rejected alternatives

Recorded so the convention does not drift back:

| Alternative | Why it was rejected |
|---|---|
| **Upsert-only** — elements present are created/updated, absent children left untouched | Forks the semantics *inside a single PATCH body*: scalar fields would be "present = new value" while collections would be "present = partial merge". It is also inexpressible in OpenAPI, and it leaves no way to remove a child without adding child `DELETE` routes for every collection. |
| **Deletion markers** — `_delete: true` on an element | Violates the property naming rules, pollutes every child DTO with a field that is not part of the model, and has zero OpenAPI expressibility — nothing in the schema says what the flag does. |

### 1.6 Search
- **Schema name:** `{Resource}SearchRequest` (e.g., `CustomerSearchRequest`).
- **Response:** returns `{Resource}List` (below).

```yaml
CustomerSearchRequest:
  type: object
  properties:
    filters:  { type: array, items: { type: object } }
    sort:     { type: array, items: { type: string } }
    page:     { type: integer, minimum: 1 }
    pageSize: { type: integer }
```

### 1.7 Paginated list wrapper
- **Schema name:** `{Resource}List` (e.g., `CustomerList`).
- **Data:** array of `Basic{Resource}` within the standard pagination envelope.

```yaml
CustomerList:
  type: object
  required: [totalItemsCount, pageCount, page, pageSize, data]
  properties:
    totalItemsCount: { type: integer }
    pageCount:       { type: integer }
    page:            { type: integer }
    pageSize:        { type: integer }
    hasPrev:         { type: boolean }
    hasNext:         { type: boolean }
    links:
      type: object
      properties:
        self:  { type: string, format: uri }
        first: { type: string, format: uri }
        prev:  { type: string, format: uri }
        next:  { type: string, format: uri }
        last:  { type: string, format: uri }
    data:
      type: array
      items: { $ref: '#/components/schemas/BasicCustomer' }
```

### 1.8 Endpoint → model mapping
- `GET /{resources}` → `{Resource}List`
- `GET /{resources}/{resourceId}` → `{Resource}`
- `POST /{resources}` (body: `New{Resource}`) → `201` with body `{Resource}` + `Location`
- `PUT /{resources}/{resourceId}` (body: `New{Resource}`) → `200` with body `{Resource}` + `Location`
- `PATCH /{resources}/{resourceId}` (body: `Update{Resource}`) → `200` with body `{Resource}` + `Location`
- `POST /{resources}:search` (body: `{Resource}SearchRequest`) → `{Resource}List`

### 1.9 `required`, `default`, and `readOnly` on a property

`required` and `default` look contradictory — if the caller must send a value, what is a default for? They are not. `required` says the property must be **present in the resource**; `default` says what value to use **when nobody supplied one**. Those are different questions, and `readOnly` changes who "nobody" is.

| Property is | What `default` means |
|---|---|
| `required`, no `default` | The caller must send a value, and nothing suggests one. |
| not `required`, has `default` | The backend applies it on omission, **and** it doubles as a client-side suggestion. |
| `required`, has `default` | **A client-side suggestion only** — prefill a form, seed a request builder. It is not permission to omit the property. |
| `required` + `readOnly`, has `default` | A **persistence** default. `readOnly` removes the property from the `New{Resource}` DTO and from `aiAccess.writableProperties`, so no caller can supply it and the database is the only remaining consumer. |

The last two rows are one rule seen from two sides: a `default` on a `required` property always addresses whoever is able to supply the value, and `readOnly` is what determines that nobody can.

**Do not add a rule forbidding `required` + `default`.** It reads like a contradiction and it is not. One consumer measured 66 such properties across 43 schemas in a single bundled spec — status enums, country codes, priority levels, numeric thresholds — all correct. A validate-time rule against the pair would fail every one of them.

**For enum properties, the default does not go on the property.** Write it on the enum schema, paired with `x-default`, not beside the `$ref` that points at it — OpenAPI 3.0 ignores keywords declared as siblings of a `$ref`, and the generator ignores property-level defaults on a referenced enum (`ENUM_PROPERTY_LEVEL_DEFAULT_IGNORED`). See `Vendor_Extensions.md` §4.6, which is where this is specified.

**This is enforced, so it is worth knowing before the build tells you.** A required enum property with no default anywhere raises `REQUIRED_ENUM_MISSING_DEFAULT` — an entity whose state machine has no starting state. The fix is a default on the enum schema, or making the property required in `New{Resource}` so the client must supply it; `x-skip-default-validation: true` on the property suppresses it deliberately. Present in generator `0.5.7`, the version this kit pins.

> **Row four is intent, not yet behaviour.** No generated stack currently turns a `readOnly` + `required` property's `default` into a persistence default — not EF `HasDefaultValue`, not SQLAlchemy `default=`/`server_default=`, not a C# property initializer. The column lands `NOT NULL` with no database default and no writer able to fill it. A consumer hit both halves of that: the Python path raises on create because the property is correctly outside the writable whitelist, and the C# path silently inserts the CLR zero value — for an enum, a synthetic `UNKNOWN` that is not a literal of the declared enum. Note the asymmetry that makes it a generator bug rather than an authoring one: a *writable* sibling with the same `required` + `default` pair does receive its initializer. Adding `readOnly` loses it.
>
> Tracked in `compatibility.md`, follow-up 22. **If you already have such properties, sweep existing rows** — on the C# path the bad value inserts silently, so the damage predates the diagnosis.

---

## 2) HTTP contract

- **GET** → `200 OK`
- **POST** → `201 Created` (+ `Location` to canonical resource) — synchronous create
- **POST (long-running)** → `202 Accepted` (+ acknowledgment body with `requestId`) — asynchronous, see § "Long-Running Operations" below
- **PUT** → `200 OK` (+ `Location`, body `{Resource}`) — **always 200, never 204**
- **PATCH** → `200 OK` (+ `Location`, body `{Resource}`) — **always 200, never 204**
- **DELETE** → `204 No Content` — **always 204, no body**

### Response Code Policy
- **POST creating a resource synchronously** returns 201 with the canonical resource (or its key) in the body and a `Location` header.
- **POST that triggers a long-running async process** (multi-second algorithm, fan-out, batch) returns 202 with an acknowledgment body and publishes a domain event for the actual outcome — see § "Long-Running Operations".
- **PUT/PATCH operations must always return 200** with the updated resource in the response body and Location header pointing to the canonical resource URI.
- **DELETE operations must always return 204** with no response body.
- This ensures consistent behavior for code generation and client expectations.

### Long-Running Operations (202 Accepted pattern)

When a POST endpoint triggers a process that cannot complete inside a typical request window (multi-second algorithm, fan-out across many entities, batch operations), the operation MUST be exposed as **asynchronous** rather than blocking the client. The endpoint becomes a thin validator that publishes a domain event for the real work, and returns `202 Accepted` immediately.

#### When to use 202 instead of 201

Use 202 if any of these hold:
- The work routinely takes more than ~2 seconds
- The work involves cross-domain reads + writes
- The work fans out to many child entities (e.g., creating one record per line item, one notification per recipient)
- An async worker (`on-*` operation) already exists or is justified for the same work — keeping a synchronous duplicate path on REST creates two sources of truth for the algorithm

Use 201 (synchronous) for simple resource creation: a single insert, validation, no fan-out, no heavy computation.

#### Contract shape

```yaml
post:
  operationId: doSomethingHeavy
  x-emits:
    - event: Something.Requested            # Triggers the async worker
  requestBody: ...
  responses:
    '202':
      description: |
        Validation passed and a Something.Requested event was published.
        Processing runs asynchronously; clients await the resulting
        Something.Completed event or poll the resource list.
      content:
        application/json:
          schema:
            $ref: '../models/SomethingRequestAcknowledgment.yaml'
    '400': ...   # Synchronous validation errors still apply
    '404': ...
    '409': ...
```

#### Acknowledgment body

The 202 response body is a small `{Resource}RequestAcknowledgment` model with at minimum:

```yaml
type: object
required: [requestId, status]
properties:
  requestId:
    type: string
    format: uuid
    description: Correlation identifier echoed in the resulting domain event payload
  status:
    type: string
    enum: [accepted]
    description: Always `accepted` for successful 202 responses
```

The `requestId` MUST be echoed in the payload of the resulting domain event so the client can correlate the async outcome with the original request.

#### Synchronous validations are still required

The endpoint MUST still validate synchronously before publishing the event — referenced entities exist, the caller has permission, no obvious conflict. The async worker should never receive an event that would have failed validation. The endpoint also still emits `400`, `403`, `404`, `409` etc. as appropriate.

#### Cross-spec linkage

- The OpenAPI operation declares `x-emits` referencing the domain event(s) it publishes (handbook AsyncAPI rules apply)
- The corresponding AsyncAPI message describes the event payload, including the `requestId`
- The `on-*` worker that consumes the event is the actual algorithm owner; both REST manual paths and scheduled-job cron paths converge on the same event and the same worker

#### Example

An order-processing endpoint (`POST /tenants/{tenantId}/orders/process`) follows this pattern:
- Returns 202 with `OrderProcessingRequestAcknowledgment` containing `orderId`, `processingStatus`, and `processingRequestedAt`
- Transitions the target Order's `processingStatus` to `pending` (with `processingRequestSource: manualRest`); the predicate auto-emits `Order.ProcessingRequested`
- Cron path (`run-process-pending-orders`) performs the same transition for each eligible Order (with `processingRequestSource: scheduledJob`)
- Both consumed by `on-order-processing-requested` which owns the algorithm; on success the worker sets the status to `completed` (auto-emits `Order.ProcessingCompleted`); each generated artifact fires its own event independently

### Concurrency Control (Optimistic Locking)

Every entity declares whether its writes are protected, via `x-entity.concurrency` (`Vendor_Extensions.md` §1.1). Optimistic concurrency control via ETags is the recommended default for any resource with more than one writer, and `concurrency: optimistic` is what makes it true of an entity — the key is **required with no default**, so an entity that declares nothing is undeclared, not protected.

`concurrency: none` is a legitimate declaration for a genuinely single-writer or append-only resource, and it owes a `reason` whenever the entity also exposes an unsafe write.

> **Two writers is not only an AI-vs-human question.** The rest of this section is written around agents because that is the case where the race is easiest to picture, but any two callers of the same row contend: an employee cancelling a request a manager is approving, two managers editing one roster, a retry racing its own original. Scoping ETags to the AI-reachable surface under-protects everything else — see `Vendor_Extensions.md` §1.1 for how to choose the mode.

#### Why This Matters

**Problem**: Without concurrency control, simultaneous updates cause lost changes:
```
Agent A reads order (status=confirmed)
Agent B reads order (status=confirmed)
Agent A updates to status=submitted
Agent B updates contact email
→ Agent B's update overwrites Agent A's status change (lost update!)
```

**Solution**: ETags ensure updates only succeed if resource hasn't changed:
```
Agent A reads order (ETag: "abc")
Agent B reads order (ETag: "abc")
Agent A updates with If-Match: "abc" → Success (ETag: "def")
Agent B updates with If-Match: "abc" → 412 Conflict (ETag changed to "def")
→ Agent B must fetch current state, merge changes, and retry
```

#### ETag Requirements

- **Format**: Strong validator, quoted hash (e.g., `"a1b2c3d4"`)
- **Generation**: Hash of resource state (implementation-specific: version number, timestamp hash, or content hash)
- **Mandatory**: On an entity declaring `concurrency: optimistic`, all GET responses MUST include the `ETag` header
- **Validation**: On the same entity, all PUT/PATCH requests MUST include the `If-Match` header
- **AI-Friendly**: Conflict responses include current state for intelligent merge

An entity declaring `concurrency: none` emits no `ETag` and requires no `If-Match` — that is what the declaration means. Declare it deliberately, with its `reason`; do not arrive at it by leaving the key off.

#### Behavior

**GET** → Always returns `ETag` header
```http
GET /orders/123
Response: 200 OK
ETag: "a1b2c3d4"
Content-Type: application/json

{ "id": "123", "status": "confirmed", ... }
```

**PUT/PATCH requires If-Match** → Success
```http
PATCH /orders/123
If-Match: "a1b2c3d4"
Content-Type: application/json

{ "contactEmail": "new@example.com" }

Response: 200 OK
ETag: "e5f6g7h8"
Location: /orders/123

{ "id": "123", "contactEmail": "new@example.com", ... }
```

**Missing If-Match** → 428 Precondition Required
```http
PATCH /orders/123
Content-Type: application/json

{ "contactEmail": "new@example.com" }

Response: 428 Precondition Required
Content-Type: application/json

{
  "errors": [{
    "code": "precondition_required",
    "message": "If-Match header is required for update operations",
    "field": null,
    "retryable": true,
    "retryStrategy": "fetch_current_etag"
  }]
}
```

**Stale If-Match** → 412 Precondition Failed with recovery information
```http
PATCH /orders/123
If-Match: "old-etag"
Content-Type: application/json

{ "contactEmail": "new@example.com" }

Response: 412 Precondition Failed
ETag: "current-etag"
Content-Type: application/json

{
  "errors": [{
    "code": "precondition_failed",
    "message": "Resource was modified by another request. Current state included for merge.",
    "field": null,
    "retryable": true,
    "retryStrategy": "fetch_and_merge",
    "currentETag": "current-etag"
  }],
  "currentResource": {
    "id": "123",
    "status": "submitted",
    "contactEmail": "existing@example.com",
    ...
  }
}
```

#### AI Agent Recovery Pattern

When an AI agent encounters a 412 conflict, it should:

1. **Extract current state** from `currentResource` in the 412 response
2. **Merge changes intelligently**:
   - Keep the current state for fields it didn't intend to change
   - Apply its intended changes to the current state
   - Resolve conflicts based on business rules
3. **Retry with new ETag** from the 412 response
4. **Limit retries** to prevent infinite loops (max 3 attempts recommended)

Example agent logic:
```javascript
async function updateOrder(orderId, changes, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    // Get current state
    const current = await GET(`/orders/${orderId}`);
    const etag = current.headers.get('ETag');

    // Apply changes
    const updated = { ...current.body, ...changes };

    // Attempt update
    const response = await PATCH(`/orders/${orderId}`, updated, {
      headers: { 'If-Match': etag }
    });

    if (response.status === 200) return response.body;
    if (response.status === 412) {
      // Merge with current state from response and retry
      const currentState = response.body.currentResource;
      changes = mergeChanges(changes, currentState);
      continue;
    }
    throw new Error(`Update failed: ${response.status}`);
  }
  throw new Error('Max retries exceeded');
}
```

#### Exceptions

**Resources that do NOT require ETags:**
- **Immutable resources** (e.g., Offer, SearchResult): Cannot be modified, no ETag needed
- **Append-only resources** (e.g., AuditLog, Payment): Only support POST, no updates
- **POST operations**: Creating new resources, no If-Match required

#### No-Op Writes

A PUT/PATCH whose payload leaves every tracked field of the entity unchanged is a **semantic no-op**. It MUST:

- return `200` with the current representation
- return the **unchanged** ETag
- leave `updatedAt` untouched
- write no row
- emit no `x-emits` event

**Why `updatedAt` must not move:** where `updatedAt` backs the ETag, bumping it on a no-op invalidates every client's cached `If-Match` and produces spurious `412`s on the next genuine write. The rule at "same resource state = same ETag" (below) is only satisfiable if no-ops are inert.

**Why no event:** `*Created`/`*Updated`/`*Deleted` messages are forbidden from declaring `x-trigger-when` (`AsyncAPI_Handbook.md` §2.2, `Vendor_Extensions.md` §12.2), so subscribers have no declarative way to filter out a `Before == After` delivery. Suppression is producer-side or it does not happen. A no-change event costs every subscriber a full handler run — including metered AI workers.

What counts as "unchanged" is decided by the change-detection rules in `AsyncAPI_Handbook.md` §2.3 — diff the **tracked entity**, not the event snapshot.

#### Implementation Notes

**For API Implementers:**
- Generate ETags consistently (same resource state = same ETag)
- Detect no-op writes before persisting; return the current ETag unchanged (see No-Op Writes)
- Include ETag in all GET responses for mutable resources
- Validate If-Match before processing PUT/PATCH
- Return current ETag in 412 responses
- Consider including `currentResource` in 412 to reduce round-trips

**For API Consumers:**
- Always store ETag when fetching resources
- Always send If-Match with PUT/PATCH
- Handle 412 by fetching current state and merging
- Implement exponential backoff for retries
- Log conflicts for monitoring concurrent access patterns

### Deletion Policy

Soft delete is the recommended default for DELETE operations: it simplifies error management and enables recovery without a database backup restore.

> **This is a convention, not a default.** Whether a given DELETE destroys a row or archives it is decided by `x-entity.delete` on the target entity (`Vendor_Extensions.md` §1.1), and an entity that declares nothing resolves to **`hard`**. Stating the convention here does not make it true of your entities — declaring `delete: soft` does. An entity whose operation description promises retention but carries no declaration is hard-deleting, and the generator's `DELETE_SEMANTICS_UNDECLARED` warning exists to surface exactly that gap.

#### Soft Delete Behavior

An entity that declares `delete: soft` is marked as deleted rather than removed from the database.

**Mechanism:**
- `deletedAt` timestamp recorded — this is the **sole owner** of deletion state
- `deletedByUserId` recorded when the entity declares it
- Returns `204 No Content`
- Resource no longer appears in list/search results by default

> **Do not also carry a `deleted` member in the entity's status enum.** It is a second, independent write of one fact: the two can disagree, and because `deleted` overwrites whatever status preceded it, restoring the record cannot recover the prior state. The generator flags the overlap as `DELETE_SOFT_STATUS_ENUM_OVERLAP` (WARNING). Filter on `deletedAt` instead. Removing an already-published `deleted` member is a breaking change for any client filtering on it — migrate deliberately.

```http
DELETE /orders/123
If-Match: "etag"

Response: 204 No Content
```

**After deletion:**
```http
GET /orders/123
Response: 404 Not Found

GET /orders?filter=id eq '123' and deletedAt ne null
Response: 200 OK
{
  "data": [{
    "id": "123",
    "status": "confirmed",
    "deletedAt": "2024-01-15T10:30:00Z",
    ...
  }]
}
```

#### Retention and Cleanup

- **Retention period**: declared per entity as `x-entity.delete.retention` — an ISO-8601 duration, or `none` to keep the row forever. 30 days (`P30D`) is a reasonable project default; a domain under a legal retention obligation typically declares `none` and hard-deletes only through a manual, audited process.
- **Automatic cleanup**: hard delete after the retention period expires. **Not implemented yet** — `retention` is declared-but-not-enforced until the cleanup worker (`FEAT-2026-0081`) ships. Until then, no soft-deleted row is destroyed automatically, whatever it declares.
- **Audit logs**: Preserved indefinitely regardless of resource deletion

> There is no domain-level or project-level retention default that entities inherit. `retention` is per entity, so a policy such as *"30 days everywhere except `crm`"* is authored as a declaration on each entity, not as one default plus an override. Write the policy sentence once in the domain's documentation and keep the per-entity declarations consistent with it.

#### Cascade Deletion

When a parent aggregate is soft-deleted, child entities are also soft-deleted:

```yaml
# Example: Deleting an Order
DELETE /orders/123
→ Order deletedAt stamped
→ All OrderLines deletedAt stamped
→ All Payments deletedAt stamped
→ All Fulfillments deletedAt stamped
```

**Cascade rules declared in `x-entity`:**
```yaml
Order:
  x-entity:
    type: aggregate
    delete: soft            # what happens to the Order's own row
    cascadeDelete: soft     # what happens to its children
    children:
      - OrderLine
      - Payment
      - Fulfillment
```

`delete` and `cascadeDelete` are separate keys answering separate questions, and are not required to agree. Each child named in `children` must declare its own `delete: soft` for the cascade to be coherent — `cascadeDelete` names the reach of the cascade, not the semantics of the entities it reaches.

#### Deletion Constraints

DELETE operations may fail if business rules prevent deletion:

```http
DELETE /orders/123
Response: 409 Conflict

{
  "errors": [{
    "code": "delete_not_allowed",
    "message": "Cannot delete order in 'submitted' status. Cancel order first.",
    "retryable": false,
    "requiredAction": "transition_to_cancelled"
  }]
}
```

#### Restore Operation

Soft-deleted resources can be restored within the retention period via **restricted internal APIs only** (not exposed in public API).

**Public API behavior:**
- Deleted resources return `404 Not Found`
- Cannot be modified via standard endpoints
- Can be queried using `filter` parameter: `?filter=deletedAt ne null`

Restoring clears `deletedAt` and the record's prior state is intact, which is the practical reason deletion state lives in `deletedAt` alone: a status enum that was overwritten with `deleted` has no prior value left to restore.

**Internal API behavior** (implementation detail):
```http
POST /internal/orders/123:restore
Authorization: Bearer <internal-token>

Response: 200 OK
{ "id": "123", "status": "confirmed", "deletedAt": null, ... }
```

#### Querying Deleted Resources

Use standard filtering to include deleted resources in queries:

```http
# Include deleted resources
GET /orders?filter=deletedAt ne null

# Exclude deleted resources (default behavior)
GET /orders?filter=deletedAt eq null

# Get specific deleted resource
GET /orders?filter=id eq '123' and deletedAt ne null
```

**Note**: Standard GET by ID (`GET /orders/123`) returns `404` for deleted resources. Use filter queries to access deleted resources.

**Note**: `deletedAt` must appear in the entity's `x-entity.filterableProperties` for these queries to be valid — declaring `delete: soft` does not add it implicitly.

#### AI Agent Considerations

**When deleting:**
- Check the target entity's `x-entity.delete` before assuming anything is recoverable — `soft` is reversible within the retention window via internal APIs, `hard` (declared or defaulted) is not
- Check cascade implications (children will also be deleted)
- Verify business rules allow deletion in current state
- Include `If-Match` header for concurrency control

**When receiving 404:**
- Resource may be deleted (not necessarily non-existent)
- Query with `filter=status eq 'deleted'` to confirm
- If deleted, cannot be modified via public API
- Contact system administrator for restoration if needed

**Error handling:**
- `404 Not Found`: Resource deleted or never existed
- `409 Conflict`: Business rules prevent deletion
- `428 Precondition Required`: Missing If-Match header
- `412 Precondition Failed`: Resource modified since last fetch

### Standard error responses (must be documented wherever applicable with predefined components)

Use these **predefined responses** from `components.responses`:

```yaml
components:
  responses:
    UnauthorizedError:   # 401
      description: The error is returned when the authentication token is missing or expired
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

    ForbiddenError:      # 403
      description: >
        This error is returned when a user is trying to call an API endpoint for which she does not
        have the right privileges
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

    NotFoundError:       # 404
      description: The error is returned when a specific element requested does not exist
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

    BadRequestError:     # 400
      description: This error is returned when the user is passing invalid information to the API endpoint
      content:
        application/json:
          schema:
            type: array
            items:
              $ref: '#/components/schemas/Error'
```

**Apply them as follows:**

- **401 Unauthorized** → include `#/components/responses/UnauthorizedError` and set `WWW-Authenticate` header.
- **403 Forbidden** → include `#/components/responses/ForbiddenError` on **all secured operations** where the caller may lack required role/scope/tenant context.
- **404 Not Found** → include `#/components/responses/NotFoundError` on **all operations with `{...Id}` path parameters** (resource or parent not found).
- **400 Bad Request** → include `#/components/responses/BadRequestError` on endpoints with **request bodies** that can fail validation.

**403 vs 404 guidance**
- Use **403** when the resource exists but the caller lacks permission (e.g., wrong tenant scope).
- Use **404** when the resource truly doesn't exist **or** when you intentionally do not disclose existence (prefer 404 to prevent information leaks when ambiguous).

Other errors still apply as per earlier guidance:
- **405 Method Not Allowed** (include `Allow`)
- **406 Not Acceptable**
- **409 Conflict** (business/state conflict, not ETag) — see section 2.1 below
- **412 Precondition Failed** (`If-Match` mismatch/missing)
- **415 Unsupported Media Type**

**Unknown fields in requests**: ignored at all nesting levels; on 2xx responses server may include `X-Ignored-Fields`/`X-Ignored-Params`.

**Idempotency-Key for POST** creates; replay prior result on retries.

### 2.1) 409 Conflict - Business Rule Violations

**409 Conflict** is used for **business rule violations and state conflicts** — NOT for concurrency control (use 412 for ETag mismatches).

#### When to Use 409

**Purpose**: Indicate that a well-formed request cannot be completed due to the current state of the resource or business rules.

**Key distinction**:
- **400 Bad Request** → Request is malformed or has validation errors
- **409 Conflict** → Request is valid but conflicts with current resource state
- **412 Precondition Failed** → ETag mismatch (concurrency control)

#### Recommended Usage by HTTP Method

| Method | 409 Policy | Rationale |
|--------|-----------|-----------|
| **DELETE** | **Recommended** | Business rules commonly prevent deletion (dependencies, state constraints) |
| **PATCH** | **Recommended** | State transitions and business rules often apply |
| **PUT** | **Recommended** | Same as PATCH (full replacement with state constraints) |
| **POST** | **Conditional** | Include only if uniqueness constraints or parent state dependencies exist |
| **GET** | **Never** | Read-only operations cannot have state conflicts |

#### Common 409 Scenarios

**DELETE operations**:
- Resource has dependencies (e.g., template in use by tenants)
- Resource state prevents deletion (e.g., can't delete active order)
- Cascade constraints would violate business rules

**PATCH/PUT operations**:
- Invalid state transitions (e.g., can't cancel fulfilled order)
- Business rules prevent field changes (e.g., can't change tenant while customer has active orders)
- Relationship constraints violated (e.g., can't set status=inactive with pending orders)

**POST operations**:
- Uniqueness constraint violations (e.g., email already exists)
- Duplicate prevention (e.g., customer already enrolled in tenant)
- Parent state prevents creation (e.g., can't create order under suspended tenant)

#### Response Structure

```http
DELETE /templates/123
Response: 409 Conflict
Content-Type: application/json

{
  "errors": [{
    "code": "template_in_use",
    "message": "Cannot delete template - currently used by 5 tenants",
    "field": null,
    "retryable": false,
    "requiredAction": "remove_template_from_tenants"
  }]
}
```

**Required fields**:
- `code`: Machine-readable error code (snake_case)
- `message`: Human-readable explanation
- `retryable`: Usually `false` for business rule violations
- `requiredAction`: Guidance on how to resolve (recommended)

#### Standard Response Patterns

**DELETE operations**:
```yaml
responses:
  '204':
    description: No Content
  '200':
    description: Resource deleted (when includeBody=true)
    content:
      application/json:
        schema:
          $ref: '../models/Resource.yaml'
  '401': { $ref: '#/components/responses/UnauthorizedError' }
  '403': { $ref: '#/components/responses/ForbiddenError' }
  '404': { $ref: '#/components/responses/NotFoundError' }
  '409': { $ref: '#/components/responses/ConflictError' }
  '412': { $ref: '#/components/responses/PreconditionFailedError' }
  '428': { $ref: '#/components/responses/PreconditionRequiredError' }
```

**PATCH/PUT operations**:
```yaml
responses:
  '200':
    description: OK
    headers:
      Location: { $ref: '#/components/headers/Location' }
      ETag: { $ref: '#/components/headers/ETag' }
    content:
      application/json:
        schema:
          $ref: '../models/Resource.yaml'
  '400': { $ref: '#/components/responses/BadRequestError' }
  '401': { $ref: '#/components/responses/UnauthorizedError' }
  '403': { $ref: '#/components/responses/ForbiddenError' }
  '404': { $ref: '#/components/responses/NotFoundError' }
  '409': { $ref: '#/components/responses/ConflictError' }
  '412': { $ref: '#/components/responses/PreconditionFailedError' }
  '428': { $ref: '#/components/responses/PreconditionRequiredError' }
```

**POST operations (with uniqueness constraints)**:
```yaml
responses:
  '201':
    description: Created
    headers:
      Location: { $ref: '#/components/headers/Location' }
    content:
      application/json:
        schema:
          $ref: '../models/Resource.yaml'
  '400': { $ref: '#/components/responses/BadRequestError' }
  '401': { $ref: '#/components/responses/UnauthorizedError' }
  '403': { $ref: '#/components/responses/ForbiddenError' }
  '409': { $ref: '#/components/responses/ConflictError' }
```

#### Validation Rules

The validation script enforces these rules:

**Rule: MISSING_409_ON_DELETE**
- **Type**: WARNING
- **Message**: "DELETE operations should include 409 response for business rule conflicts"
- **Applies to**: All DELETE operations
- **Rationale**: Most DELETE operations can fail due to dependencies or state constraints

**Rule: MISSING_409_ON_PATCH**
- **Type**: WARNING
- **Message**: "PATCH/PUT operations should include 409 if they involve state transitions or business rules"
- **Applies to**: All PATCH/PUT operations
- **Rationale**: State transitions and business rules commonly apply to updates

**Rule: MISSING_409_ON_POST**
- **Type**: SUGGESTION
- **Message**: "POST operations should include 409 if uniqueness constraints exist"
- **Applies to**: POST operations only
- **Rationale**: Only needed when uniqueness or parent state dependencies exist

#### AI Agent Considerations

**When encountering 409**:
1. **Parse the error** - Extract `code`, `message`, and `requiredAction`
2. **Understand the conflict** - The request is valid but state prevents it
3. **Resolve the conflict** - Follow `requiredAction` guidance to change system state
4. **Retry after resolution** - Once state is corrected, retry the original operation
5. **Do not loop** - If conflict persists after resolution attempt, escalate to human

**Example recovery pattern**:
```javascript
async function deleteTemplate(templateId) {
  try {
    await DELETE(`/templates/${templateId}`);
  } catch (error) {
    if (error.status === 409) {
      const conflict = error.body.errors[0];

      if (conflict.code === 'template_in_use') {
        // Resolve conflict: remove template from tenants
        await removeTemplateFromTenants(templateId);

        // Retry deletion
        await DELETE(`/templates/${templateId}`);
      }
    }
    throw error;
  }
}
```

#### Documentation Requirements

When including 409 in an operation spec, document the specific business rules that can cause conflicts:

```yaml
'409':
  description: |
    Business rule conflict prevents operation:
    - `template_in_use`: Template is currently used by one or more tenants
    - `has_active_assignments`: Customer has active assignments
    - `pending_orders_exist`: Tenant has pending orders that must be completed first
  content:
    application/json:
      schema:
        $ref: '#/components/responses/ConflictError'
      examples:
        templateInUse:
          value:
            errors:
              - code: template_in_use
                message: Cannot delete template - currently used by 5 tenants
                retryable: false
                requiredAction: remove_template_from_tenants
```

---

## 3) Pagination (standard envelope)

- Query: `page` (default 1), `pageSize` (default 25, **hard max 2500**), `sort=field[:asc|desc][,field2...]`.
- Response envelope: `totalItemsCount`, `pageCount`, `page`, `pageSize`, `hasPrev`, `hasNext`, `links`, `data` (see 1.7).
- `links` should include `self`, `first`, `prev`, `next`, `last` when applicable.

---

## 4) Versioning & deprecation

- URL versioning: `/v{major}`; only current major served.
- Deprecation headers during 180-day window: `Deprecation`, `Sunset`, `Link`(rel="deprecation").
- After sunset: **410 Gone** if it existed in this major; **404 Not Found** if it never existed.
- Discovery endpoints: `GET /versions`, `GET /changelogs` (path segments follow camelCase rule; here, lowercase is acceptable).

---

## 5) AuthN/AuthZ

- Bearer JWT (RS256). `iss` and `aud` are project-specific (e.g., `iss=https://<tenant>.auth0.com/`, `aud=https://api.{project-host}/`).
- Access token lifetime and rotating refresh window are project-defined (typical defaults: 60-minute access token, ≤ 30-day refresh).
- **Roles**: The project defines its closed role enum (project-specific). Declare it in the project's OpenAPI common enums file (typically `common/enums.yaml`). All secured endpoints declare allowed roles via the `x-roles` vendor extension.
- **Scopes**: Use `<domain>[.<Entity>].<operation>` — a kebab-case domain from `info.x-domains`, an optional PascalCase entity, and one of `read` / `write` / `delete` / `all` (e.g. `customer.Customer.read`, `order.read`). **Not keyed on the endpoint's tag**: tags are many-to-one against domains, so a tag-keyed scope cannot be resolved back to an owning domain. All secured endpoints declare required scopes via the `x-scopes` vendor extension. Full grammar and rules: `Vendor_Extensions.md` §3.2.
- ABAC with a project-specific custom claim namespace (e.g., `https://{project-host}/claims`):
  - Enforce tenant context first; optionally also narrower scope context.
  - Permit self-service flows with appropriate checks.
  - Step-up (MFA/privilege) hooks supported (implementation detail).

---

## 6) Data formats & localization

- Timestamps: ISO-8601 UTC with `Z` (e.g., `2025-09-15T16:05:23Z`). Inputs with offsets are normalized to `Z`.
- Money: integers in minor units `{ amount: 1099, currency: "USD" }`.
- Arrays are never `null` (use `[]`). Omit optional fields when absent.
- `Accept-Language`: localizes human-readable messages; data remains language-agnostic.

---

## 7) Observability

- Echo `X-Request-Id` (generate if missing).
- Support W3C `traceparent` propagation.
- Rate limit headers on rate-limited routes: `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`.
- Include `Retry-After` on `429`/`503`.

---

## 8) Agent-friendly additions

- Return **`Location` on all successful writes** (POST/PUT/PATCH).
- Support **`?validateOnly=true`** on POST/PUT/PATCH/DELETE (full validation, no commit).
- Optional changes feed `/v1/changes` (cursor-based) or webhooks for reconciliation.

### validateOnly Parameter
All write operations (POST/PUT/PATCH/DELETE) must support the `validateOnly` query parameter:
- **Type**: `boolean`
- **Default**: `false`
- **Purpose**: Enables AI agents to test operations without side effects
- **Behavior**: When `true`, perform full validation but do not commit changes
- **Response**: Same as normal operation (200/201/204) but no actual changes made

---

## 9) Vendor extension (Phase #2): `x-entity`

**Where:** only on main, persisted resource schemas (identified by the presence of `x-entity`).

**Structure:**
```json
{
  "x-entity": {
    "domain": "order",
    "type": "aggregate",
    "requiresPagination": true,
    "hasMany": ["OrderLine","Payment"],
    "hasOne": ["ShippingAddress"],
    "belongsTo": ["Tenant","Customer"],
    "filterableProperties": ["status","priority","customerId","createdAt"],
    "searchableProperties": ["notes.en","notes.fr","reference"],
    "encryptedProperties": ["taxId"],
    "aiAccess": {
      "operations": ["read", "update"],
      "writableProperties": ["status", "priority"],
      "reason": "Triage agent adjusts status/priority from incoming signals."
    }
  }
}
```

**Behavior:**
- `domain` (string, required, leads the block): the kebab-case owning domain. MUST be a key in the project's domain registry `info.x-domains` (§0.1) — the closed universe of domains. An unregistered value is an ERROR (`ENTITY_DOMAIN_UNREGISTERED`). Matches the `domains/{domain}/` folder and the shared `x-domain` vocabulary in AsyncAPI/Arazzo. See `Vendor_Extensions.md §1.1`.
- `requiresPagination` (boolean, default: true): indicates if this resource can grow large and requires pagination when returned in collections. When `true`, endpoints returning collections of this resource should use `{Resource}List` wrapper and support `page`, `pageSize`, `sort` parameters. When `false`, endpoints can return simple arrays.
- Assistant may infer cardinality from `hasOne` / `hasMany` / `belongsTo`, but asks if in doubt.
- One-sided declarations are allowed; assistants warn on likely mismatches.
- `filterableProperties` / `searchableProperties` / `encryptedProperties` must reference existing **top-level** fields (no nested paths, except for BilingualText subfields like `title.en`).
- **CRITICAL (filterableProperties)**: All fields usable in OData `filter` expressions MUST be declared in `filterableProperties` (except generic parameters: page, pageSize, sort, search, filter, expand, validateOnly).
- **CRITICAL (searchableProperties)**: All fields included in free-text `search` MUST be declared in `searchableProperties`. For BilingualText fields, reference subfields (e.g., `title.en`, `title.fr`).
- Masking for `encryptedProperties` on reads: **first N chars + `****` + last M chars** (default 2 + `****` + 2 if unspecified).
- Writes accept plaintext; privileged reads may return unmasked (implementation-level).
- `aiAccess` (required on every `x-entity`): declares the AI agent access policy enforced by generated repositories. Absence triggers a validator WARN (`ENTITY_AIACCESS_MISSING`); for entities the AI must not touch, use the canonical Tier 0 form `operations: []` with `reason`. `operations` lists allowed verbs from `[read, create, update, delete]`; an empty array is the Tier 0 declaration. Write verbs require `writableProperties` and a `reason`. Encrypted fields are excluded from implicit read access and must be listed explicitly in `readableProperties` to be AI-readable. Full schema and examples: see `Vendor_Extensions.md` §1.1.1.

---

## 9.1) DDD Architecture & Aggregate Boundaries

Specfuse APIs follow **Domain-Driven Design (DDD)** principles to ensure proper entity relationships and aggregate boundaries.

### 9.1 Entity Classification Rules

**Every entity MUST be classified as either:**

1. **Aggregate Root** (`type: aggregate`):
   - Independent entities that define aggregate boundaries
   - Can be directly accessed and managed
   - Examples: `Tenant`, `Customer`, `Order`, `Catalog`

2. **Entity within Aggregate** (`type: entity` + `belongsTo`):
   - Entities that belong to and are managed by an aggregate root
   - Cannot be accessed without going through their aggregate root
   - Examples: `OrderLine`, `CustomerPreferences`, `CatalogItem`
   - Operationalized by the validator as `ENTITY_MUST_BE_AGGREGATE_WHEN_ORPHAN_ALLOWED`: a `type: entity` whose `belongsTo` admits a fully-null parent FK state at insert (no `belongsTo` block, or pure `optional.*` / `zeroOrMore` clauses) violates this invariant and must be promoted to `aggregate`. See §9.4 → "Entity type by polymorphic shape" for the full rule.

### 9.2 Aggregate Boundary Validation

**CRITICAL RULE**: No entity can exist without proper aggregate classification.

- **Aggregate roots** define consistency and transaction boundaries
- **Aggregates can belong to other aggregates** in this architecture (e.g., Customer belongs to Tenant) to express tenant hierarchy and data isolation
- **Child entities** must declare `belongsTo` to specify their aggregate context
- **Cross-aggregate references** use IDs only, never direct object references
- **Value objects** compose within aggregates using `x-value-object` extension

### 9.3 Aggregate Structure (Illustrative)

The aggregate structure is project-specific. Below is an illustrative shape using the kit's running example (Customer/Order); replace with your project's actual structure.

```yaml
# Independent Aggregates (type: aggregate)
Tenant         → TenantSettings, Customers[], Catalogs[]
Catalog        → CatalogItems[]
Customer       → CustomerPreferences

# Child Aggregates (type: aggregate + belongsTo - tenant hierarchy)
Customer       → belongsTo: Tenant
Order          → belongsTo: Tenant + Customer
Refund         → belongsTo: Tenant + Order

# Child Entities (type: entity + belongsTo)
OrderLine      → belongsTo: Order (required)
Payment        → belongsTo: Order (required)
OrderAttachment → belongsTo: Tenant + optional (Order | Customer | Refund)
```

The project's actual aggregate map lives in an overlay document (commonly `docs/aggregate-map.md` or generated from `x-entity` metadata).

---

## 9.4) Relationship Cardinality

Entities can express complex relationship requirements using nested cardinality constraints in the `belongsTo` property.

### Cardinality Keywords

| Keyword | Meaning | Use Case |
|---------|---------|----------|
| `allOf: [...]` | Entity MUST belong to ALL listed aggregates | Required relationships (e.g., always needs Tenant) |
| `oneOf: [...]` | Entity MUST belong to EXACTLY ONE from list | Mutually exclusive parent aggregates |
| `oneOrMore: [...]` | Entity MUST belong to AT LEAST ONE from list | Flexible but required relationships |
| `optional: {...}` | Wraps nested cardinality that is optional | Optional relationship groups |
| `zeroOrMore: [...]` | Entity MAY belong to zero or more | Fully optional relationships |

### Basic Cardinality Examples

#### Simple Required Relationship
```yaml
# Entity must belong to exactly one aggregate
x-entity:
  type: entity
  belongsTo:
    oneOf: [Tenant, Customer]
```

#### Multiple Required Relationships
```yaml
# Entity must belong to both aggregates
x-entity:
  type: entity
  belongsTo:
    allOf: [Tenant, Customer]
```

#### Fully Optional Relationship
```yaml
# Entity may belong to zero or more aggregates
x-entity:
  type: aggregate                       # ← aggregate, not entity (see
                                        #   "Entity type by polymorphic
                                        #   shape" below)
  belongsTo:
    zeroOrMore: [Order, Refund, Payment]
```

### Nested Cardinality for Complex Scenarios

Combine cardinality constraints to express complex requirements:

#### Required Base + Optional Exclusive Context
```yaml
# OrderAttachment always belongs to Tenant, optionally to one specific entity
OrderAttachment:
  x-entity:
    type: entity
    belongsTo:
      allOf: [Tenant]  # Always required
      optional:
        oneOf: [Order, Customer, Refund]  # May belong to exactly one
```

**Code Generation:**
```csharp
public class OrderAttachment : Entity
{
    // Required: Always populated
    public Guid TenantId { get; set; }  // NOT nullable
    public Tenant Tenant { get; set; } = null!;

    // Optional: Zero or one of these
    public Guid? OrderId { get; set; }
    public Guid? CustomerId { get; set; }
    public Guid? RefundId { get; set; }
}
```

**Validation:**
- `TenantId` must always be populated
- At most one of `OrderId`, `CustomerId`, or `RefundId` may be populated
- Database check constraint enforces this rule

#### Multiple Required + Optional Exclusive
```yaml
# Audit log requires both Tenant and UserAccount, optionally one context
AuditLog:
  x-entity:
    type: entity
    belongsTo:
      allOf: [Tenant, UserAccount]  # Both always required
      optional:
        oneOf: [Order, Customer, Refund]  # Optionally one context
```

#### Required + Multiple Optional Groups
```yaml
# Notification requires Tenant and UserAccount, has multiple optional links
Notification:
  x-entity:
    type: entity
    belongsTo:
      allOf: [Tenant, UserAccount]  # Both required
      optional:
        oneOf: [Order, Customer]  # Optional primary context (exactly one)
      optionalLinks:
        zeroOrMore: [Refund, OrderAttachment]  # Optional references (any number)
```

#### Flexible Optional Relationships
```yaml
# Comment can attach to multiple entities (at least one required)
Comment:
  x-entity:
    type: entity
    belongsTo:
      oneOrMore: [Order, Refund, OrderAttachment]  # Must attach to at least one
```

### Migration from Old Syntax

**Old Syntax (Ambiguous):**
```yaml
# ❌ Unclear: Does entity belong to ALL, ONE, or AT LEAST ONE?
belongsTo: [Tenant, Order, Refund, Customer]
```

**New Syntax (Explicit):**
```yaml
# ✅ Clear: Entity must belong to Tenant + optionally one other
belongsTo:
  allOf: [Tenant]
  optional:
    oneOf: [Order, Refund, Customer]
```

### Database Implementation

Code generators create appropriate database structures based on cardinality:

#### For `allOf` (Required)
```sql
-- Foreign key is NOT NULL
ALTER TABLE OrderAttachments
ADD CONSTRAINT FK_OrderAttachments_Tenant
FOREIGN KEY (TenantId) REFERENCES Tenants(Id);
```

#### For `optional.oneOf` (Optional Exclusive)
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

#### For `oneOf` (Exactly One Required)
```sql
-- Check constraint: exactly one populated
ALTER TABLE SomeEntity
ADD CONSTRAINT CHK_SomeEntity_ExactlyOneOwner
CHECK (
    (CASE WHEN TenantId IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN CustomerId IS NOT NULL THEN 1 ELSE 0 END) = 1
);
```

### REST Route Patterns by Cardinality

The cardinality shape on `x-entity.belongsTo` determines the **shape and number of create routes** for the entity. The validator enforces this mapping with four rules: `MISSING_PARENT_SCOPED_CREATE`, `FORBIDDEN_FLAT_CREATE_ON_REQUIRED_ONEOF`, `MISSING_FLAT_CREATE_ON_OPTIONAL_ONEOF`, and `PARENT_FK_LEAK_IN_NEW_DTO`. A separate rule, `REDUNDANT_JUNCTION_HASMANY`, governs the M:M junction case below.

The governing principle: **the URL is the single source of truth for the parent FK.** The `New{Entity}` DTO never carries parent FK fields when `belongsTo` is polymorphic — the route handler reads `{parentId}` from the URL, asserts the route-auth scope against that parent, and inserts the entity with that exact FK populated. The entity itself keeps the N nullable polymorphic FK columns with a DB CHECK enforcing "exactly one" (`oneOf`) or "at most one" (`optional.oneOf`). This eliminates URL/body disagreement, makes the polymorphic CHECK enforceable deterministically, and lets the code generator route auth and FK assignment without inference.

#### Cardinality → routes table

| Shape on `belongsTo` | Required create routes | Forbidden | DTO carries parent FK? |
|---|---|---|---|
| `allOf: [A]` (single-required, e.g. tenant) | `POST /{As}/{aId}/{entity}s` | — | No |
| `allOf: [A, B]` on a junction (M:M) | Parents reach the entity via the **junction** in `hasMany` (see "M:M Junction Navigation" below) | Direct `hasMany: [OtherParent]` on either parent | N/A |
| `oneOf: [A, B]` (required polymorphic) | `POST /{As}/{aId}/{entity}s` AND `POST /{Bs}/{bId}/{entity}s` (one per parent) | `POST /{entity}s` (flat) | **No** |
| `optional.oneOf: [A, B]` (optional polymorphic) | Per-parent routes AND `POST /{entity}s` (orphan / no-parent) | — | **No** |
| `allOf: [Tenant] + optional.oneOf: [A, B]` (compound) | `POST /{tenants}/{tenantId}/{entity}s` (no sub-parent) AND per-sub-parent routes | Fully-flat `POST /{entity}s` (tenant is required; no true orphan possible) | **No** |

#### Required polymorphic — example: Note

```yaml
# Note.yaml — entity keeps the nullable polymorphic FK columns
x-entity:
  type: entity
  belongsTo:
    oneOf: [Customer, Vendor]   # required: exactly one parent

# NewNote.yaml — NO customerId, NO vendorId
type: object
required: [body]
properties:
  body: ...
  pinned: ...
```

Routes:

```
POST /customers/{customerId}/notes        # createCustomerNote
POST /vendors/{vendorId}/notes            # createVendorNote
# NO POST /notes — forbidden under required shape
# (a flat route has no valid input: the CHECK demands exactly one
# non-null parent FK, and there's no URL parent + no DTO parent)
```

#### Optional polymorphic — example: Attachment

```yaml
# Attachment.yaml
x-entity:
  type: aggregate                  # ← aggregate, not entity (see "Entity type
                                   #   by polymorphic shape" below)
  belongsTo:
    optional:
      oneOf: [Project, Task]       # zero or one parent
```

Routes:

```
POST /projects/{projectId}/attachments     # attach to a known Project
POST /tasks/{taskId}/attachments           # attach to a known Task
POST /attachments                          # orphan / unattached case
```

`NewAttachment` still does not carry `projectId` / `taskId`. The orphan route inserts with both FKs null; the parent-scoped routes set the corresponding FK from the URL.

#### Compound polymorphic (tenant + optional sub-parent) — example: Comment

```yaml
# Comment.yaml
x-entity:
  type: entity
  belongsTo:
    allOf: [Tenant]                          # required tenant
    optional:
      oneOf: [Project, Task, Milestone]      # optional sub-parent
```

Routes:

```
POST /tenants/{tenantId}/comments              # no sub-parent
POST /projects/{projectId}/comments            # sub-parent: Project
POST /tasks/{taskId}/comments                  # sub-parent: Task
POST /milestones/{milestoneId}/comments        # sub-parent: Milestone
# NO flat POST /comments — Tenant is required; no true orphan exists
```

The sub-parent URL carries enough information: the handler resolves the tenant `tenantId` from the sub-parent's own tenant relationship (e.g., `Project.tenantId`). Authoring a fully-flat `POST /comments` would either leave `Tenant` unset (violating `allOf: [Tenant]`) or force the FK back into the DTO (violating `PARENT_FK_LEAK_IN_NEW_DTO`). The `MISSING_FLAT_CREATE_ON_OPTIONAL_ONEOF` rule is gated on `belongsTo.allOf` being empty — compound shapes like this one do **not** need a fully-flat route because the tenant-scoped route already serves the "no sub-parent within tenant" case.

#### Operation IDs are free-form

The validator matches parent-scoped creates by **HTTP method + URL shape** (path-tail equals the entity plural). Operation IDs may use whichever verb fits the semantics — `createX`, `uploadX`, `attachX`, `submitX`, etc. — and binary/multipart payloads are recognized. Sub-action POSTs (e.g. `POST /notes/{noteId}/transcribe`) are correctly excluded because their terminal segment is not the entity plural.

#### Entity type by polymorphic shape

The polymorphic shape on `belongsTo` also constrains the entity's **classification** (`x-entity.type`). This is the entity-side counterpart to the route-side rules above.

**Rule:** if an entity's `belongsTo` admits a **fully-null parent FK state** at insert time — meaning every polymorphic FK column can be null simultaneously — the entity MUST be `type: aggregate`. Otherwise it may be `type: entity`.

`belongsTo` admits a fully-null parent FK state when:
- `belongsTo` is absent entirely (no parent declared), OR
- `belongsTo` has **no `allOf` clause** AND uses only `optional.*` or `zeroOrMore: [...]` constraints

`belongsTo` does NOT admit a fully-null state — and `type: entity` remains valid — when `belongsTo.allOf` declares at least one required parent. The optional sub-parent may be null, but the `allOf` parent FK is always populated at insert.

| `belongsTo` shape | Admits null-parent state? | Valid `type:` |
|---|---|---|
| Absent | yes — no parent at all | `aggregate` only |
| `oneOf: [A, B]` (required) | no — exactly one populated | either |
| `allOf: [A]` | no — A always populated | either |
| `allOf: [A, B]` | no — both populated | either |
| `allOf: [Tenant] + optional.oneOf: [A, B]` | no — tenant always populated | either |
| **`optional.oneOf: [A, B]` only (no allOf)** | **yes — both can be null** | **`aggregate` only** |
| **`zeroOrMore: [A, B]` only** | **yes — both can be null** | **`aggregate` only** |

**Why:** under §9.1, child entities (`type: entity`) "cannot be accessed without going through their aggregate root" — they must always insert under their parent. An entity declared `type: entity` whose `belongsTo` allows a null-parent state contradicts that invariant: the entity has no parent to insert through. At codegen time this manifests as a generated service body that calls `repository.Add(entity)` against the wrong repository (the first parent in `oneOf`), producing non-compiling code because no per-entity repository exists for child entities — they can only be persisted through their aggregate root's repository.

The canonical example is `Attachment` (from the "Optional polymorphic" example above): a file or note whose parent may be a known `Project`, a known `Task`, or neither (orphan upload). Because the "neither" case is reachable at insert, `Attachment` is `type: aggregate` even when it has no children of its own.

**Validator:** `ENTITY_MUST_BE_AGGREGATE_WHEN_ORPHAN_ALLOWED` (ERROR). Resolution: either promote to `type: aggregate`, or add a `belongsTo.allOf` clause with at least one required parent.

This rule is the entity-side counterpart to the four route-side rules above (`FORBIDDEN_FLAT_CREATE_ON_REQUIRED_ONEOF`, `MISSING_FLAT_CREATE_ON_OPTIONAL_ONEOF`, `MISSING_PARENT_SCOPED_CREATE`, `PARENT_FK_LEAK_IN_NEW_DTO`). Together they form a complete contract: the entity classification matches the polymorphic shape, the routes match the classification, and the DTO matches the routes — no path leads to a non-compiling regen.

### M:M Junction Navigation

When two aggregates have a many-to-many relationship through a junction entity, the parents' `hasMany` lists **must reference the junction**, not the other parent directly. This applies whenever a junction declares `belongsTo.allOf: [A, B]` AND neither `A` nor `B` declares the other under `belongsTo` (i.e., the pair is not a parent/child tenancy tier).

**Why:** declaring `hasMany: [OtherParent]` on a parent triggers the code generator's FK-projection rule, which stamps a non-nullable FK column on the other parent's table — producing SQL FK violations at insert time. The junction owns the link; `hasMany: [Junction]` is how consumers navigate (`team.memberships.user`).

```yaml
# ✅ CORRECT — Team ↔ User via Membership junction

# Team.yaml
x-entity:
  type: aggregate
  hasMany: [Membership, Project, ...]    # ← junction, NOT User

# User.yaml
x-entity:
  type: aggregate
  hasMany: [Membership, ApiKey, ...]     # ← junction, NOT Team

# Membership.yaml (the junction)
x-entity:
  type: entity
  belongsTo:
    allOf: [Team, User]                  # both parents
```

```yaml
# ❌ WRONG — direct hasMany on the other parent

# Team.yaml
x-entity:
  hasMany: [User, Project, ...]          # ← back-projects a phantom FK onto User
```

**Validator:** `REDUNDANT_JUNCTION_HASMANY` (ERROR). The discriminator (`neither parent declares the other under belongsTo`) correctly skips parent/child tenancy hierarchies — `Tenant → Customer` with `Customer.belongsTo.allOf: [Tenant]` is unaffected even if `Tenant.hasMany: [Customer]` is present, because there is no separate junction.

### Relationship symmetry, and the two cases exempt from it

`RELATIONSHIP_SYMMETRY` requires a child's `belongsTo Parent` to be matched by a reciprocal `Parent hasMany child`. Two cases are exempt, and in both the exemption is the *intended* shape — **do not add reciprocals to satisfy them.**

**1. Tenancy roots.** When the parent is a declared tenancy root (`tenancy` in the project file — see `Project_File.md` §4.1), no reciprocal `hasMany` is required. A `belongsTo Tenant` on thirty entities is row-level tenant **scoping**, not aggregate **containment**: you never load `tenant.WorkItems` as an aggregate graph, because access is always a query filter. Enumerating every tenant-scoped child under `Tenant.hasMany` turns the tenant root into a god-aggregate and makes the generator emit child collections nothing loads.

**2. `oneOf` and `optional` parents.** The reverse check skips ambiguous parentage by design. A polymorphic `belongsTo.oneOf: [Person, Organization]` requires neither `Person.hasMany` nor `Organization.hasMany` — the generator cannot know which parent a given row has. Only required (`allOf`) non-tenant parents demand the reciprocal.

> **Tooling caveat — validate the project, not a bare bundle.** The freestanding `validate <bundle.yaml>` path has no project context, so it cannot read `tenancy` and **exemption 1 is inactive there**. It reports phantom symmetry errors, one per tenant-scoped child, against a model that is correct. A consumer lost real time to this and briefly "fixed" it by adding reciprocals that then had to be reverted.
>
> Validate through `validate path/to/project.json` (`Project_File.md` §"File Location, Discovery, and CLI Invocation") — the path that carries the tenancy context, and the one code generation itself uses. Treat symmetry findings from a bare-bundle run as unverified until reproduced against the project file.

### Common anti-patterns (and what the rules say about them)

| Anti-pattern | Symptom | Rule that fires |
|---|---|---|
| Flat `POST /{entity}s` with `New{Entity}` carrying `aId` / `bId`, parent shape is `oneOf: [A, B]` (required) | DB CHECK violation at insert; URL/body mismatch impossible to enforce at the gateway | `FORBIDDEN_FLAT_CREATE_ON_REQUIRED_ONEOF` + `PARENT_FK_LEAK_IN_NEW_DTO` |
| Missing per-parent route under `oneOf` / `optional.oneOf` | Some parents have no way to attach the entity at create time | `MISSING_PARENT_SCOPED_CREATE` |
| Missing flat orphan route under pure `optional.oneOf` (no `allOf`) | The "no parent" case is unreachable | `MISSING_FLAT_CREATE_ON_OPTIONAL_ONEOF` |
| `New{Entity}` declares parent-FK fields under any polymorphic shape | Client can send a parent FK that disagrees with the URL; generator can't reconcile | `PARENT_FK_LEAK_IN_NEW_DTO` |
| Parent declares `hasMany: [OtherParent]` next to a junction | Generator stamps a phantom non-nullable FK on the other parent's table → runtime FK violation | `REDUNDANT_JUNCTION_HASMANY` |
| `type: entity` with `belongsTo` that admits a fully-null parent FK state (pure `optional.*` / `zeroOrMore` / absent) | Generated service body calls the wrong repository (no per-entity repo exists); non-compiling code | `ENTITY_MUST_BE_AGGREGATE_WHEN_ORPHAN_ALLOWED` |

---

## 9.5) Relationship classification: owning, association, opaque

`belongsTo` (§9.4) declares **composition** — the entity is a member of the target's aggregate, deletes cascade, and the parent owns the lifecycle. Not every foreign key means that. An entity frequently points at another entity it does not belong to, and the two cases generate very different code.

Since implicit `{Entity}Id` → `belongsTo` inference was retired (kit `0.5.4`), a `format: uuid` property named after an entity carries **no relationship meaning on its own**. Every FK-shaped property is classified explicitly, exactly once:

| Intent | Declaration | Delete behaviour | Aggregate membership |
|---|---|---|---|
| Entity is part of the target's aggregate | `belongsTo: <Target>` on `x-entity` | Cascade | Yes |
| Entity points at the target but is not owned | `x-references: <Target>` on the property | NoAction | No |
| The uuid is not a foreign key at all | `x-references: none` + justifying `description` | n/a | n/a |
| Owning FK under a name that is not `{Entity}Id` | `x-fk-for: <Target>` on the property, bound to a declared `belongsTo` | Cascade | Yes |

Full extension reference: `Vendor_Extensions.md` §1.7 (`x-references`), §1.8 (`x-fk-for`), §1.9 (`x-expand-of` / `x-projection`).

**The markers are mutually exclusive.** `x-references` and `x-fk-for` declare opposite ownership and must never appear on the same property. `x-references: <Target>` must never co-occur with a `belongsTo` naming that same target — there is no precedence rule and no "declaration wins, marker degrades to a hint" fallback. If the entity is owned, use `belongsTo`; if it merely points, use `x-references`; if it is owned under a legacy column name, use `x-fk-for`.

### Read-only projections

An embed that surfaces another entity's data for read convenience is **not owned state** and must say so, or it will be persisted as if it were:

- **`x-expand-of: <twin>`** — a scalar projection of the entity identified by a sibling property (a uuid FK, or a string natural key; either may be optional). Excluded from persistence.
- **`x-projection: true`** — a non-owned array-of-`$ref` collection. Read-only, and never `required`, because a projection is a convenience the server may decline to populate.

Neither marker may appear on `New*` or `Update*` derivatives — a client cannot write a projection.

### Nested routes require ownership

A nested route asserts a containment relationship in the URL:

```
POST /{parents}/{parentId}/{children}
GET  /{parents}/{parentId}/{children}
```

The child MUST declare `belongsTo <Parent>`. An `x-references` association is **not** sufficient: the route says the child lives inside the parent, while the association says it merely points at it, and the two cannot both be true. Model the association as a flat route with a filter (`GET /{children}?parentId=...`) instead.

This is the route-level counterpart of the classification table — the URL shape and the relationship declaration must agree.

### Anti-patterns

| Anti-pattern | Symptom | Why it is wrong |
|---|---|---|
| Unclassified `format: uuid` property named after an entity | No relationship generated; the FK silently becomes a plain column | Inference was retired — absence of a marker is not a default, it is an omission |
| `x-references: <T>` alongside `belongsTo: <T>` | Ambiguous ownership | Composition and association are mutually exclusive per target |
| `x-references` and `x-fk-for` on one property | Contradictory ownership | The two markers mean opposite things |
| `x-fk-for: <T>` with no `belongsTo: <T>` | Looks like a relationship declaration, declares nothing | `x-fk-for` binds an existing declaration; it cannot create one |
| Unmarked projection embed | Projection persisted as owned state | Nothing distinguishes it from real state without a marker |
| `x-projection` property listed in `required` | Client cannot rely on it anyway | The server may decline to populate a projection |
| Nested route whose child only declares `x-references` | Route asserts containment the model denies | Use a flat route with a filter |
| `x-references: none` with no description | Relationship classification suppressed for unstated reasons | Indistinguishable from an author who skipped the question |

---

## 9.2) Query Parameters & Filtering Standards

Specfuse APIs use **standardized query parameters** for consistent filtering, searching, and pagination. Two distinct mechanisms are supported:

1. **Structured Filtering** via `filter` parameter (OData-style) → Uses `filterableProperties`
2. **Free-Text Search** via `search` parameter → Uses `searchableProperties`

### 10.1 Generic Parameters (Excluded from x-entity)

These parameters are **generic** and do NOT need to be declared in `filterableProperties` or `searchableProperties`:

```yaml
genericParameters:
  - page          # Pagination: page number (1-based)
  - pageSize      # Pagination: items per page
  - sort          # Sorting: supports multiple fields and order
  - search        # General free-text search (USES searchableProperties)
  - filter        # OData-style filtering (USES filterableProperties)
  - expand        # Resource expansion (include related data)
  - validateOnly  # Validation-only mode (no side effects)
  - include       # Include specific related resources
```

### 10.2 filterableProperties vs searchableProperties

#### **filterableProperties**
Fields that support **structured OData filtering** via the `filter` query parameter.

**Purpose**: Enable precise, field-specific queries with operators (`eq`, `ne`, `gt`, `lt`, `and`, `or`)

**Example**:
```yaml
x-entity:
  filterableProperties:
    - status
    - priority
    - category
    - assignedToUserId
    - tenantId
    - dueDate
    - systemGenerated
```

**Usage**:
```
GET /tasks?filter=status eq 'pending' and priority eq 'high'
GET /tasks?filter=dueDate lt 2024-02-01T00:00:00Z
GET /tasks?filter=systemGenerated eq true and category eq 'onboarding'
```

#### **searchableProperties**
Fields included in **free-text search** via the `search` query parameter.

**Purpose**: Enable users to search across multiple text fields with a single search term (like a Google search)

**Example**:
```yaml
x-entity:
  searchableProperties:
    - title.en          # For BilingualText fields, reference subfields
    - title.fr
    - description.en
    - description.fr
    - tags
```

**Usage**:
```
GET /tasks?search=inventory
  → Searches across title.en, title.fr, description.en, description.fr, tags
  → Matches tasks with "inventory" in any of those fields

GET /tasks?search=closing
  → Finds any task with "closing" in title or description (any language)
```

#### **Combined Usage**
Both mechanisms can be used together:

```
GET /tasks?search=inventory&filter=status eq 'pending' and priority eq 'high'
  → Free-text search for "inventory" + structured filters on status and priority
```

### 10.3 Entity-Specific Parameters (Legacy Individual Filters)

**DEPRECATED**: Individual query parameters (e.g., `?status=pending&priority=high`) should be avoided in favor of the `filter` parameter. If used for backward compatibility, they MUST be included in `filterableProperties`.

**Examples:**
- `status`, `tags`, `city`, `province` → Must be in `filterableProperties`
- `expiresAfter`, `expiresBefore` → Requires `expiresAt` in `filterableProperties`
- `capacityMin`, `capacityMax` → Requires `capacity` in `filterableProperties`

### 10.4 Parameter Naming Standards

- **General search**: Use `search` (NOT `q`)
- **OData filtering**: Use `filter`
- **Sorting**: Use `sort` (NOT `sortBy` or `sortOrder`)
- **Date ranges** (legacy): Use `{field}After` and `{field}Before` patterns
- **Numeric ranges** (legacy): Use `{field}Min` and `{field}Max` patterns
- **Boolean filters** (legacy): Use descriptive names (`active`, `archived`, `enabled`)

### 10.5 Validation Rules

1. **Structured Filtering**: All fields usable in `filter` expressions MUST be declared in `filterableProperties`
2. **Free-Text Search**: All fields searched by the `search` parameter MUST be declared in `searchableProperties`
3. **BilingualText Fields**: Reference subfields (e.g., `title.en`, `title.fr`) in `searchableProperties`
4. **Range Parameter Mapping**: Legacy range parameters (`*Min`, `*Max`, `*Before`, `*After`) map to base properties in `filterableProperties`
5. **Database Index Guidance**: Both `filterableProperties` and `searchableProperties` guide which fields need database indexes
6. **API Documentation**: Query parameters and entity properties must be synchronized

---

## 10) Vendor extension: `x-sample`

`x-sample` annotates OpenAPI schema properties with declarative data-generation instructions. It tells consumers *how* to produce realistic values for a given property — without hardcoding data or coupling to any runtime language.

### 10.1 Purpose and Consumers

Multiple consumers interpret `x-sample` annotations independently:

| Consumer | How it uses `x-sample` |
|----------|------------------------|
| **Arazzo setup recipes** | Seed realistic tenant data during scenario execution — recipes reference `x-sample` instead of hardcoding values |
| **OpenAPI doc renderers** | Generate realistic request/response examples instead of placeholder strings |
| **Mock servers** | Return locale-aware fake data that matches the schema's business intent |
| **Dev/demo fixture seeding** | Populate development and demo environments with representative data |

### 10.2 Scoping Rules

#### Schemas that SHOULD have `x-sample`

| Schema pattern | Rationale |
|----------------|-----------|
| `New{Resource}` | POST request bodies — the primary target for recipe seed data |
| Shared value objects in `common/common.yaml` | Inherited by all consumers (e.g., `Address`, `EmergencyContact`, `BilingualText`) |
| `{Resource}SearchRequest` | Search fixture generation |

#### Schemas that MUST NOT have `x-sample`

| Schema pattern | Rationale |
|----------------|-----------|
| `{Resource}` (main) | Server owns the full shape — includes server-generated fields |
| `Basic{Resource}` | Read-only projection — never used for data creation |
| `Update{Resource}` | Partial updates — recipes rarely use PATCH for seeding |
| `{Resource}List` | Response envelope — not a data-creation schema |

#### Properties that MUST NOT have `x-sample`

- **Server-generated fields**: `id`, `createdAt`, `updatedAt`, `etag`, or any field the server computes
- **`$ref` properties**: do not annotate — the referenced schema's own properties carry their own `x-sample` annotations. For example, if `NewCustomer` has `address: { $ref: 'Address' }`, do not put `x-sample` on the `address` property — the `Address` schema's `street`, `city`, etc. already have annotations.
- **Foreign key IDs** (e.g., `customerId`, `tenantId`): these are resolved at runtime from recipe step outputs, not generated from faker

#### Properties that MUST have a DTO-local `x-sample` (enum sentinel-first trap)

When a request DTO property `$ref`s an enum schema whose **first declared literal** is a sentinel value the handler will reject (`unknown`, `unspecified`, `none`, `undefined`, `default`, `notSet`, or any domain-specific auto sentinel like `accrual` for a transaction-type enum, `pending` for an update-to-revoke flow, etc.), the property MUST carry a **DTO-local** `x-sample` with `provider: fixed` set to a valid non-sentinel literal.

Why: the C# generator emits the enum's first literal as the field default in the generated request fake. If the handler validates against the sentinel, the happy-path functional test 400s before the work runs. The DTO-local `x-sample` overrides parent-entity inheritance for scalar enum fields (see `provenance.md`).

Canonical-shape examples:
- An enum `AssignmentType: [person, role]` — `AssignRequest.assignmentType` carries `x-sample: { provider: fixed, format: "person" }`.
- An enum whose first literal is an auto sentinel `accrual` (e.g., `TransactionType`) — `NewAccrualTransaction.transactionType` carries `x-sample: { provider: fixed, format: "manualAdjustment" }`.
- An enum `InvitationStatus` whose first literal is `pending`, but the update flow is "revoke" — `UpdateInvitation.status` carries `x-sample: { provider: fixed, format: "revoked" }`.

Authoring checklist for any new `New*`/`Update*`/`*Request` DTO with an enum property:
1. Open the referenced enum schema; check the **first** literal.
2. If the first literal is a sentinel a handler is likely to reject, add a DTO-local `x-sample` with a valid literal.
3. Pick the literal that matches the DTO's most common intent (look at the DTO's `description` for guidance — e.g. "Typically used to revoke" → use `revoked`).
4. Verify the chosen literal exists in the enum (otherwise the C# fake will emit a non-existent enum case; see `provenance.md`).

Sentinel name list to scan against (case-insensitive): `unknown`, `unspecified`, `none`, `undefined`, `default`, `notSet`, `unset`. Also flag domain-specific auto sentinels — the rule is "the value the handler treats as 'not really set,'" not the literal string `unknown`.

### 10.3 Provider Reference

| Provider | When to use | Required fields | Example |
|----------|-------------|-----------------|---------|
| `faker` | Realistic data — names, emails, addresses, dates, numbers | `path` (required), `locale` (optional) | `{ provider: faker, path: person.firstName, locale: en-US }` |
| `fixed` | Enum values, known constants, boolean defaults | `format` (required — the literal value) | `{ provider: fixed, format: "premium" }` |
| `template` | Compound/derived values — formatted codes, composed strings | `format` (required — template with `{faker.path}` interpolation) | `{ provider: template, format: "ORD-{{string.numeric(6)}}" }` |

**JSON Schema**: `schemas/arazzo-extensions/x-sample.schema.json`

**Field summary**:

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `provider` | Yes | `faker` \| `fixed` \| `template` | Data generation strategy |
| `path` | When `provider: faker` | string | Faker method path (dot-notation) |
| `locale` | No | string | Locale override (e.g., `en-US`). Defaults to tenant locale when omitted |
| `format` | When `provider: fixed` or `template` | string | Literal value (`fixed`) or template string (`template`) |

### 10.4 Canonical Faker Path Library

Paths follow the Faker.js dot-notation convention. Code generators map these to their target platform's faker library.

#### Person
| Path | Produces |
|------|----------|
| `person.firstName` | First name |
| `person.lastName` | Last name |
| `person.fullName` | Full name (first + last) |
| `person.prefix` | Title prefix (Mr., Ms., Dr.) |

#### Contact
| Path | Produces |
|------|----------|
| `internet.email` | Email address |
| `internet.url` | Website URL |
| `phone.number` | Phone number |

#### Location
| Path | Produces |
|------|----------|
| `location.streetAddress` | Street address with number |
| `location.secondaryAddress` | Unit / suite / apartment |
| `location.city` | City name |
| `location.state` | State or province |
| `location.zipCode` | ZIP or postal code |
| `location.latitude` | Latitude (decimal degrees) |
| `location.longitude` | Longitude (decimal degrees) |

#### Company
| Path | Produces |
|------|----------|
| `company.name` | Company / business name |
| `company.catchPhrase` | Slogan or tagline |

#### Date/Time
| Path | Produces |
|------|----------|
| `date.past` | Date in the past |
| `date.future` | Date in the future |
| `date.recent` | Recent date |

#### Identifiers
| Path | Produces |
|------|----------|
| `string.uuid` | UUID v4 |
| `string.numeric` | Numeric string |
| `string.alphanumeric` | Alphanumeric string |

#### Text
| Path | Produces |
|------|----------|
| `lorem.sentence` | Single sentence |
| `lorem.paragraph` | Full paragraph |
| `lorem.words` | Space-separated words |

#### Number
| Path | Produces |
|------|----------|
| `number.int` | Integer |
| `number.float` | Floating-point number |

### 10.5 Locale Handling

- **When omitted**, the generator defers to the tenant's locale at generation time — this is the default and preferred behavior for most properties.
- **When present**, forces a specific locale (e.g., `fr-CA` for French-Canadian names and addresses).
- **Use explicit locale** for properties where locale-specific formatting matters: street addresses, phone numbers, postal codes, city names.
- **Omit locale** for properties where any locale works: UUIDs, emails, URLs, numeric values, enum constants.
- The `locale` field is valid on any provider, though it is most commonly used with `faker`.

### 10.6 Examples

#### NewCustomer — faker + fixed providers

```yaml
# domains/customer/models/NewCustomer.yaml
type: object
required: [firstName, lastName]
properties:
  firstName:
    type: string
    maxLength: 100
    description: Customer's first name
    x-sample:
      provider: faker
      path: person.firstName
  lastName:
    type: string
    maxLength: 100
    description: Customer's last name
    x-sample:
      provider: faker
      path: person.lastName
  email:
    type: string
    format: email
    maxLength: 200
    description: Customer's email address
    x-sample:
      provider: faker
      path: internet.email
  phone:
    type: string
    maxLength: 20
    description: Customer's phone number
    x-sample:
      provider: faker
      path: phone.number
  # tenantId — foreign key, no x-sample (resolved from recipe step outputs)
  tier:
    $ref: './CustomerTier.yaml'
    x-sample:
      provider: fixed
      format: "standard"
```

#### NewOrder — all three providers

```yaml
# domains/order/models/NewOrder.yaml (excerpt)
type: object
required: [customerId, currency]
properties:
  currency:
    type: string
    x-sample:
      provider: fixed
      format: "USD"
  reference:
    type: string
    maxLength: 50
    x-sample:
      provider: template
      format: "ORD-{{string.numeric(6)}}"
  placedAt:
    type: string
    format: date-time
    x-sample:
      provider: faker
      path: date.recent
  notes:
    type: string
    x-sample:
      provider: faker
      path: lorem.sentence
  # customerId — foreign key, no x-sample
  # shippingAddress — $ref property, no x-sample here (Address schema has its own annotations)
```

#### Shared value object — Address (in common/common.yaml)

```yaml
Address:
  type: object
  required: [street, city, region, postalCode, country]
  properties:
    street:
      type: string
      x-sample:
        provider: faker
        path: location.streetAddress
    unit:
      type: string
      x-sample:
        provider: faker
        path: location.secondaryAddress
    city:
      type: string
      x-sample:
        provider: faker
        path: location.city
    region:
      type: string
      x-sample:
        provider: faker
        path: location.state
    postalCode:
      type: string
      x-sample:
        provider: faker
        path: location.zipCode
    country:
      type: string
      x-sample:
        provider: fixed
        format: "US"
    # coordinates — $ref property, no x-sample (GeoCoordinates has its own annotations)
```

**See also**: `Vendor_Extensions.md §6.3` (extension contract and rationale), `Arazzo_Handbook.md §7.7` (recipe data source), `schemas/arazzo-extensions/x-sample.schema.json`

---

## 10.5) Vendor extension: `x-test-seed-value`

`x-test-seed-value` opts a specific **non-`*Id`, non-enum string path parameter** into a deterministic, seed-aligned literal in the generator's happy-path functional test. Without it, the generator substitutes `Guid.NewGuid()` for the path param, and any endpoint whose backend transforms the param before lookup (hashing, normalizing, slugifying) will 404 before reaching the resolution code path.

Introduced to fix happy-path tests 404'ing on non-`*Id` string path params whose backend transforms the value before lookup (hash, slugify, normalize). See `provenance.md` for the reference generator's PR history.

### When to add `x-test-seed-value`

Add the extension to a path parameter ONLY if ALL of the following hold:

1. `in: path` and `required: true`
2. `schema.type: string` (or a `$ref` to a string schema)
3. The parameter name does **not** end in `Id`
4. The schema is **not** an enum (no `enum:` field, no `$ref` to an enum schema)
5. The backend does **not** look up by direct equality on a spec-declared property — it transforms the value first (hash, lowercase, slug, etc.)

Typical names: `token`, `code`, `slug`, `inviteCode`, `shareKey`, `magicLink`, `signupCode`, `username` (when hashed or case-normalized).

### When NOT to add it

- `*Id` path params — already resolve via `TestSeed.<EntityName>Id`
- Enum-typed path params — already resolve via enum-literal substitution
- Path params that map one-to-one to a directly-stored, case-sensitive spec property — use the entity's existing `x-sample` instead
- Endpoints with no happy-path test (e.g., always-404 health probes)

### Authoring shape

```yaml
- name: token
  in: path
  required: true
  schema:
    type: string
  description: |
    Invitation token from the magic-link email.
    Backend looks up by hash (column `Invitation.tokenHash`);
    the consumer test fixture must seed `tokenHash` with the backend's
    hash of `x-test-seed-value` for the happy-path test to resolve.
  x-test-seed-value: "test-invitation-token-fixed"
```

### Literal shape convention

`test-<entity>-<param>-fixed` (or `-fixture-<padding>` when length matters — see constraint rule below) — lowercase, hyphen-separated, includes the entity and param name, suffixed with `-fixed` or `-fixture-...` to signal "deterministic test value, not a real production token." Commit to ONE literal per `(entity, param)` tuple so the consumer fixture can mirror it exactly. Embedded quotes are auto-escaped by the generator; an empty string falls back to the legacy `Guid.NewGuid()` behavior.

### Literal MUST satisfy the param's own schema constraints

The literal flows through the HTTP request and is validated by ASP.NET model binding **before** the handler runs. If the literal violates the param's `minLength`, `maxLength`, or `pattern`, the request 400s and the seeded entity is never queried.

**Always cross-check the chosen literal against the path-param schema.** Example: if `Invitation.token` declares `minLength: 32`, `"test-invitation-token-fixed"` (27 chars) fails model validation; a working literal is `"test-invitation-token-fixture-aaaaa"` (35 chars). Pad with repeated letters or a meaningful suffix if needed.

### Mandatory inline lookup-column note

Whenever you add `x-test-seed-value`, document on the same parameter what transformation the backend applies (hash algorithm if known, or just "hash"; lowercase; slug; etc.) and the storage column name. The consumer test fixture relies on this note to wire up the seeded entity so the test actually resolves rather than 404-ing.

### Paired Backend work

Adding `x-test-seed-value` to a spec is necessary but not sufficient. The consumer (backend repo) must seed an entity instance whose lookup column is set to the backend's transformation of the same literal. Open a paired tracking task on the backend repo whenever you add the extension — without the fixture, the generated test compiles but still 404s.

### Generator behavior summary

- Happy-path functional test: emits `var <param> = "<literal>";` instead of `var <param> = Guid.NewGuid();`
- Negative tests (401/Forbidden): keep `Guid.NewGuid()` — those don't need to resolve to seeded data
- Generated tests remain compile-clean whether the extension is present or absent

**See also**: `Vendor_Extensions.md §6.4` (extension contract), `provenance.md` (reference generator PR history)

---

## 10.6) Vendor extension: `x-membership-gated`

`x-membership-gated: true` narrows the generator's happy-path test theory by stripping the highest-privilege role (typically `Admin`) from the `[InlineData]` rows on endpoints whose handler runs a runtime **membership lookup** (channel member, group participant, thread participant, project collaborator, etc.) *after* the role gate. Without it, the privileged role passes `[RoleRequired]` in production but 403s in tests, because the seed fixture has no membership row for the global principal.

Introduced to fix happy-path tests that 403 when the test exercises a privileged role lacking a per-scope membership row in the seed fixture, even though `[RoleRequired]` would let it through in production. See `provenance.md`.

### When to add `x-membership-gated: true`

The handler dereferences a membership repository — `channelRepository.IsActiveMemberAsync`, `groupRepository.HasParticipantAsync`, `projectRepository.IsCollaboratorAsync`, or similar — and returns 403 when missing, *after* `[RoleRequired]` has passed.

Typical route shapes:
- `/channels/{channelId}/...`
- `/messages/{messageId}/...` (handler resolves message → channel → membership)
- `/threads/{threadId}/...`
- `/groups/{groupId}/participants/...`
- `/projects/{projectId}/collaborators/...`

Any operation where the handler asks **"is the caller a member of this thing?"** before doing the work.

### When NOT to add it

- The role gate alone decides — no membership check in the handler.
- Multiple non-privileged roles also lack the membership row in the seed fixture — use `x-self-scoped` to whitelist seeded roles instead of blacklisting the privileged role.
- The principal is identity-resolved (per-user lookup) rather than membership-table-driven — that's `x-self-scoped` (404 failure mode), not `x-membership-gated` (403).
- The privileged role isn't in `x-roles` to begin with — nothing to strip.

### Authoring shape

```yaml
post:
  operationId: sendMessage
  x-roles: [Admin, Manager, Member]
  # Handler verifies caller is an active ChannelMember of {channelId} after the role
  # gate; Admin has no ChannelMember row in the seed fixture, so the test theory
  # strips Admin to avoid a 403 in the happy-path test.
  x-membership-gated: true
  x-scopes: [messaging.Message.write]
```

The accompanying YAML comment is **mandatory** — it documents what the handler dereferences so a reviewer can verify the opt-in is warranted.

### Properties of the extension

- **Test-emission-only.** `x-roles` stays complete (the privileged role remains in the production auth list). The generated `[RoleRequired]` attribute is unchanged. Only the `[InlineData]` rows of the happy-path test theory are narrowed.
- **No paired Backend work.** The seed fixture already populates membership rows for the non-privileged roles; the bug is purely the privileged role's absence.
- **Boolean only.** Setting `x-membership-gated: false` is equivalent to omitting the extension. There's no "off" semantic to express.

**See also**: `Vendor_Extensions.md §6.5` (extension contract), `provenance.md` (reference generator PR history)

---

## 10.7) Vendor extension: `x-self-scoped`

`x-self-scoped: <role>` (or list of roles) narrows the generator's happy-path test theory to roles for which the seed fixture pre-populates a per-principal runtime row (typically the project's "end user" role row — `Customer`, `Member`, `Profile`, etc.; role names are project-specific). Without it, the test theory exercises roles that 404 because the handler calls `userRepository.FindByIdpUserId(...).Then(<RuntimeRow>).FirstOrDefault()` and the seeded user for those roles has no runtime row.

Introduced to fix happy-path tests 404'ing on `/me/*`-style endpoints when the exercised role has no per-principal runtime row in the seed fixture. See `provenance.md`.

### When to add `x-self-scoped`

The handler resolves the caller to a per-principal row (a `Customer`, `Profile`, `Member`, etc.) and throws `NotFoundException` when the principal has none. The canonical shape is `/me/*` endpoints, but the pattern can show up anywhere — "do something on behalf of the caller's `<entity>`."

Typical examples (replace role names with the project's actual seeded role):
- `/me/orders/*` → `x-self-scoped: Customer` (if Customer owns the order list)
- `/me/preferences/*` → `x-self-scoped: Customer` (if backed by a Customer-side preferences table)
- `/me/profile/*` → `x-self-scoped: Customer` (if Customer owns the profile)

The role values are project-specific — pick whichever role(s) the seed fixture pre-populates the runtime row for.

### When NOT to add it

- Endpoint is `/me/<global>` and any authenticated user works (e.g. `/me/logout`). The existing path-based privileged-role strip (automatic for `/me/*` in the reference generator; see `provenance.md`) is sufficient.
- Endpoint is membership-gated rather than identity-resolved — use `x-membership-gated`.
- All roles in `x-roles` have the runtime row seeded — no narrowing needed.
- `x-roles` already lists only the self-scoped role (e.g. `[Customer]`) — nothing to narrow.

### Authoring shape — single seeded role

```yaml
post:
  operationId: cancelMyOrder
  x-roles: [Admin, Manager, Customer]
  # Handler resolves the caller to their Customer row via auth provider's user id
  # and 404s if no row exists; only the Customer-role principal in the seed fixture
  # has a Customer row, so the test theory narrows to Customer.
  x-self-scoped: Customer
  x-scopes: [order.Order.write]
```

### Authoring shape — multiple seeded roles

```yaml
x-self-scoped: [Customer, GuestCustomer]
```

The intersection of `x-roles` and `x-self-scoped` wins. Roles named in `x-self-scoped` but missing from `x-roles` are silently dropped (typo guard). Matching is case-insensitive (`customer` matches `Customer`).

The accompanying YAML comment is **mandatory** — it documents what the handler resolves so a reviewer can verify the opt-in is warranted.

### Properties of the extension

- **Test-emission-only.** `x-roles` stays complete. The generated `[RoleRequired]` attribute is unchanged. Only the `[InlineData]` rows of the happy-path test theory are narrowed.
- **No paired Backend work.** The seed fixture already populates the runtime row for the named role(s); the bug was the test theory exercising other roles that don't get the row.

### Combining with `x-membership-gated`

The two extensions are orthogonal and compose. Apply both when both conditions hold — e.g. a `/me/channels/{channelId}/markRead` op that resolves the caller to a `Customer` AND verifies channel membership:

```yaml
post:
  operationId: markMyChannelRead
  x-roles: [Admin, Manager, Customer]
  x-self-scoped: Customer          # caller must have a Customer row
  x-membership-gated: true         # ...and be a ChannelMember
```

Narrowing applies sequentially: `x-membership-gated` strips the privileged role → `x-self-scoped` keeps only Customer from the rest. Result: theory exercises only Customer.

**See also**: `Vendor_Extensions.md §6.6` (extension contract), `provenance.md` (reference generator PR history)

---

## 10.8) Vendor extension: `x-test-seed`

`x-test-seed` overrides the C# expression used to resolve a **primary-key path parameter** in the generator's happy-path functional test, replacing the default `TestSeed.<Entity>Id` substitution with a consumer-provided seed-helper expression. Add it when several happy-path tests on the same primary-key path parameter have **mutually-exclusive preconditions** on entity fields — one needs `Status=Placed`, another needs `Status=Submitted`, another needs `Status=Cancelled`, etc. The shared `TestSeed.<Entity>` row cannot satisfy multiple incompatible preconditions at once, so the tests beyond the first fail at runtime without an override.

Introduced to support lifecycle-action endpoints on a domain aggregate with state-machine semantics (e.g., `/me/orders/{orderId}/{action}` for submit/cancel/fulfill), where multiple happy-path tests on the same `*Id` path param need mutually-exclusive entity-state preconditions that a single shared seed row cannot satisfy. See `provenance.md`.

### When to add `x-test-seed`

Add the extension on an operation ONLY if ALL of the following hold:

1. The path parameter is a primary key (`*Id`). For non-`*Id` opaque transformed-lookup keys (tokens, slugs, codes), use `x-test-seed-value` (§10.5) instead.
2. The operation has a happy-path test (i.e. at least one role in `x-roles` succeeds in the `AsAllowedRole_ShouldReturn200` theory after any `x-membership-gated` / `x-self-scoped` narrowing).
3. The happy path requires specific entity-field values to pass — not just "row exists."
4. Another operation on the same `*Id` path param requires a **different, mutually-exclusive** set of preconditions, so a single shared seed row cannot serve all of them.

Typical shape: multiple lifecycle actions on the same resource — `/orders/{orderId}/submit`, `/cancel`, `/fulfill`, `/refund` — where each action's handler asserts on `Status` or similar before doing the work.

### When NOT to add it

- A single happy-path test on the path param — `TestSeed.<Entity>Id` is sufficient.
- The action only requires the row to exist (any state works) — no override needed.
- The path param is not a primary key — use `x-test-seed-value` for transformed-lookup keys.
- The path param is an enum — already resolved via enum-literal substitution.

### Authoring shape

```yaml
post:
  operationId: submitMyOrder
  summary: Submit Placed Order
  x-test-seed:
    orderId: SeedOrderForSubmit()
  x-roles: [Admin, Manager, Customer]
  x-self-scoped: Customer
  x-scopes: [order.Order.write]
```

- The key (`orderId`) MUST match an actual path-parameter name declared on the operation. Misspelled keys produce an undefined-variable compile error in the generated test.
- The value (`SeedOrderForSubmit()`) is emitted **verbatim** into the generated test body. It MUST be a syntactically valid C# expression returning the path param's runtime type (typically `Guid`). Convention is a `()`-suffixed helper method call, but any valid expression is accepted.

### Scope of the override

`x-test-seed` applies ONLY to the `AsAllowedRole_ShouldReturn200` happy-path theory. The negative theories on the same operation continue to emit `TestSeed.<Entity>Id`:

- `AsAnonymous_ShouldReturn401` — auth gate fires before the row is loaded; precondition state is irrelevant.
- `WithForbiddenRole_*_ShouldReturn403` — role gate fires before the row is loaded; precondition state is irrelevant.

The shared `TestSeed.<Entity>` row therefore remains the generic reference for negative tests, GET/list reads, and any other endpoint that doesn't need a tailored row.

### Helper-name convention

`Seed<Entity>For<Action>()` — e.g. `SeedOrderForSubmit`, `SeedOrderForCancel`, `SeedOrderForFulfill`, `SeedOrderForRefund`. Commit to one helper per `(entity, action)` tuple so the consumer fixture can mirror the names exactly.

### Consumer contract

The consumer (backend test fixture) MUST provide the helper. It is typically a `protected` method on `ApiTestBase` (or whichever base class exposes seeding utilities) that:

1. **Inserts a fresh row** with the action's required preconditions.
2. **Returns the new row's primary key** so the generated test can use it as the path-param value.
3. **Does NOT mutate the shared `TestSeed.<Entity>` row** — that row stays the generic reference for everything else.

If the helper does not yet exist, the generated test fails to compile (the C# expression refers to an undefined symbol). This is intentional and explicit — the spec is declaring the contract; the consumer fulfills it.

Example helper:

```csharp
protected Guid SeedOrderForSubmit() => SeedOrder(o =>
{
    o.Status = OrderStatus.Placed;
});
```

### Distinction from `x-test-seed-value` (§10.5)

Both extensions belong to the test-seed family but address different problems:

- **`x-test-seed-value`** sits on a **path parameter** (non-`*Id` string — token, slug, code). It overrides the URL literal substituted into the request. The consumer seeds the entity's lookup column with the backend's transformation of the literal. Failure mode without it: 404 on lookup.
- **`x-test-seed`** (this extension) sits on the **operation** and maps primary-key (`*Id`) path params to C# seed-helper expressions. The consumer provides a helper that inserts a precondition-shaped row. Failure mode without it: the handler's precondition assertion fails at runtime.

The two extensions are independent and may coexist on a single operation if it has both a transformed-lookup key AND a primary key with action-specific preconditions.

### Generator behavior summary

- `AsAllowedRole_ShouldReturn200` test → emits `var <param> = <expression>;` instead of `var <param> = TestSeed.<Entity>Id;`
- `AsAnonymous_*` and `WithForbiddenRole_*` tests → keep `TestSeed.<Entity>Id`
- Generated tests remain compile-clean whether the extension is present or absent — but if present, the consumer helper must exist for the test to compile.

**See also**: `Vendor_Extensions.md §6.7` (extension contract), `provenance.md` (reference generator PR history)

---

## 11) Error model

All error responses use a consistent structure with machine-readable codes and human-readable messages.

### Error Response Structure

```yaml
ErrorResponse:
  type: object
  required: [errors]
  properties:
    errors:
      type: array
      items:
        $ref: '#/components/schemas/Error'

Error:
  type: object
  required: [code, message]
  properties:
    id:
      type: string
      format: uuid
      description: Unique identifier for this error instance (for tracking)
    code:
      type: string
      description: Machine-readable error code (snake_case)
      example: invalid_page_size
    message:
      type: string
      description: Human-readable error message (localized via Accept-Language)
      example: pageSize exceeds maximum of 250
    field:
      type: string
      description: Field name that caused the error (for validation errors)
      example: pageSize
    status:
      type: integer
      description: HTTP status code
      example: 400
    retryable:
      type: boolean
      description: Whether this error can be retried
      example: true
    retryAfter:
      type: integer
      description: Seconds to wait before retrying (if retryable)
      example: 60
    details:
      type: object
      description: Additional context-specific error details
    requestId:
      type: string
      description: Request ID for correlation
    timestamp:
      type: string
      format: date-time
      description: When the error occurred
```

### Error Code Categories

| Category | HTTP Status | Retryable | Description |
|----------|-------------|-----------|-------------|
| `validation_error` | 400 | No | Invalid input data |
| `authentication_required` | 401 | No | Missing or invalid authentication |
| `authentication_expired` | 401 | Yes | Token expired, refresh needed |
| `forbidden` | 403 | No | Insufficient permissions |
| `not_found` | 404 | No | Resource doesn't exist |
| `conflict` | 409 | No | Business rule violation |
| `precondition_required` | 428 | Yes | Missing required header (e.g., If-Match) |
| `precondition_failed` | 412 | Yes | Resource modified, retry with new ETag |
| `rate_limit_exceeded` | 429 | Yes | Too many requests |
| `server_error` | 500 | Yes | Unexpected server error |
| `service_unavailable` | 503 | Yes | Temporary unavailability |
| `resource_expired` | 410 | No | Resource expired (e.g., offer) |

### Standard Error Codes

**Validation Errors (400):**
- `invalid_request`: Malformed request
- `invalid_field`: Invalid field value
- `missing_required_field`: Required field missing
- `invalid_page_size`: Page size out of bounds
- `invalid_filter`: Invalid filter expression
- `invalid_sort`: Invalid sort parameter

**Authorization Errors (401/403):**
- `authentication_required`: No authentication provided
- `authentication_expired`: Token expired
- `invalid_token`: Token invalid or malformed
- `forbidden`: Insufficient permissions
- `tenant_mismatch`: Resource belongs to different tenant

**Resource Errors (404/409/410):**
- `not_found`: Resource not found
- `resource_expired`: Resource expired
- `conflict`: State conflict
- `delete_not_allowed`: Deletion not permitted
- `precondition_failed`: ETag mismatch

**Rate Limiting (429):**
- `rate_limit_exceeded`: Rate limit exceeded

**Server Errors (500/503):**
- `internal_error`: Unexpected server error
- `service_unavailable`: Service temporarily unavailable
- `timeout`: Operation timed out

### Example Error Responses

**Validation Error:**
```json
{
  "errors": [{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "code": "invalid_page_size",
    "message": "pageSize exceeds maximum of 250",
    "field": "pageSize",
    "status": 400,
    "retryable": false,
    "details": {
      "maxAllowed": 250,
      "providedValue": 500
    },
    "requestId": "req_abc123",
    "timestamp": "2024-01-15T10:30:00Z"
  }]
}
```

**Conflict with Recovery Info:**
```json
{
  "errors": [{
    "code": "precondition_failed",
    "message": "Resource was modified by another request",
    "status": 412,
    "retryable": true,
    "retryAfter": 0,
    "details": {
      "currentETag": "new-etag-value"
    }
  }],
  "currentResource": { /* current state for merge */ }
}
```

**Rate Limit:**
```json
{
  "errors": [{
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "status": 429,
    "retryable": true,
    "retryAfter": 60,
    "details": {
      "limit": 100,
      "remaining": 0,
      "resetAt": "2024-01-15T10:31:00Z"
    }
  }]
}
```

### AI Agent Error Handling

**For non-retryable errors:**
- Log error details
- Return error to caller or escalate
- Do not retry automatically

**For retryable errors:**
1. Check `retryAfter` field
2. Wait specified duration (or use exponential backoff)
3. Retry with same or updated request
4. Limit retry attempts (max 3 recommended)
5. Log retry attempts for monitoring

**Exponential Backoff Pattern:**
```javascript
async function retryWithBackoff(operation, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      if (!error.retryable || attempt === maxRetries - 1) {
        throw error;
      }

      const delay = error.retryAfter
        ? error.retryAfter * 1000
        : Math.min(1000 * Math.pow(2, attempt), 30000);

      await sleep(delay);
    }
  }
}
```

### Localization

- Error `message` is localized based on `Accept-Language` header
- Error `code` is always in English (machine-readable)
- Default language: English (en)
- Supported languages: project-defined (declare in the project's overlay)

---

## 12) Do / Don't (assistant)

**Do**
- Use exact schema names/suffixes: `{Resource}`, `Basic{Resource}`, `New{Resource}`, `Update{Resource}`, `{Resource}List`, `{Resource}SearchRequest`.
- Keep `Basic{Resource}` as subset of `{Resource}` (no invented fields).
- Keep enums as separate schemas; camelCase values.
- Always include the `x-entity` vendor extension on main resources.
- When generating endpoints, always fully define path variables within the path.
- When generating endpoints, always include all error responses applicable to the endpoint.
- When generating endpoints, always include the `x-roles` vendor extension on secured endpoints.
- Always confirm the appropriate roles to include for secured endpoints.
- When generating endpoints, always include the `x-scopes` vendor extension on secured endpoints.
- When generating endpoints, **cross-check with `samples/endpoint-samples.yaml`** and follow its patterns (verbs, responses, parameters).
- Always define the summary for each endpoint based on the operationId, following this example: operationId `listCustomers` → summary `List Customers`.
- Always include one and only one tag for each endpoint.
- Always include a meaningful description of each endpoint, including relevant business rules and exceptions.
- **Always run the project's validation script after making changes** to ensure compliance with all validation rules.
- **DDD Architecture**: Ensure every entity is either an aggregate root (`type: aggregate`) or belongs to an aggregate (`type: entity` + `belongsTo`).
- **Query Parameters**: All fields usable in OData `filter` expressions MUST be declared in `filterableProperties`. All fields used in free-text `search` MUST be declared in `searchableProperties`.
- **BilingualText**: Reference subfields in `searchableProperties` (e.g., `title.en`, `title.fr`).
- **Parameter Naming**: Use `search` (not `q`) for free-text search, `filter` for OData filtering, `sort` (not `sortBy` or `sortOrder`) for sorting.
- **Relationship classification**: Classify every `format: uuid` FK-shaped property exactly once — `belongsTo` for composition, `x-references: <Entity>` for a non-owning association, `x-references: none` (with a justifying description) for a uuid that is not a foreign key. Inference was retired; an unmarked property is an omission, not a default. See §9.5.
- **Legacy FK names**: When an owning FK cannot be named `{Entity}Id`, bind it with `x-fk-for: <Entity>` alongside the declared `belongsTo`, so composition and Cascade survive the naming exception.
- **Projections**: Mark read-only embeds — `x-expand-of: <twin>` for a scalar projection, `x-projection: true` for a non-owned collection. An unmarked projection embed is persisted as owned state.
- **PATCH collections are complete sets**: a collection property present in an `Update{Resource}` body replaces the stored set — value-object arrays wholesale, child-entity arrays by identity reconcile (known `id` updates in place, no `id` creates, unknown `id` is `404`, omitted children are permanently deleted). Give `Update{Child}` an optional `id`, and say in the property description that omitted children are not recoverable. See §1.5.1.

**Don't**
- Don't inline enums.
- Don't embed subresources unless explicitly asked.
- Don't place `x-entity` on derivatives or simple types.
- Don't use anonymous objects within a resource.
- Don't define path variables as global components.
- **Don't create orphaned entities**: Every entity must be classified as either aggregate root or belong to an aggregate.
- **Don't classify an orphan-allowing entity as `type: entity`**: if `belongsTo` admits a fully-null parent FK state (absent, or pure `optional.*` / `zeroOrMore` with no `allOf`), `type` MUST be `aggregate`. Child entities (`type: entity`) must always insert under their aggregate root. Triggers `ENTITY_MUST_BE_AGGREGATE_WHEN_ORPHAN_ALLOWED` (ERROR). See §9.4 → "Entity type by polymorphic shape".
- **Don't use `q` parameter**: Use `search` for free-text search functionality.
- **Don't use `sortBy` or `sortOrder`**: Use the standardized `sort` parameter that supports multiple fields and order.
- **Don't add filterable fields without updating `filterableProperties`**: All fields usable in `filter` expressions must be declared.
- **Don't forget `searchableProperties` for text search**: All fields included in `search` must be declared.
- **Don't declare both `x-references: <T>` and `belongsTo: <T>`**: composition and association are mutually exclusive per target. There is no precedence rule and no "marker degrades to a hint" fallback. See §9.5.
- **Don't put `x-references` and `x-fk-for` on the same property**: they declare opposite ownership.
- **Don't use `x-fk-for` without a matching `belongsTo`**: it binds an existing declaration, it cannot create one.
- **Don't nest a route under a parent the child only references**: `POST`/`GET /{parents}/{parentId}/{children}` requires the child to `belongsTo <Parent>`. For an association, use a flat route with a filter.
- **Don't mark a projection `required`**: the server may decline to populate it.
- **Don't put projection markers on `New*`/`Update*` derivatives**: a client cannot write a projection.
- **Don't use deletion markers** (`_delete: true` and friends) to remove children in a PATCH: omission from the array is the removal signal. See §1.5.1.
- **Don't document a child collection as upsert-only or absent-means-untouched**: it contradicts the complete-set contract, and prose that disagrees with the server is worse than no prose.
- **Don't omit `id` from an `Update{Child}` used inside a parent collection**: without it the server cannot tell an update from a create, and delete-then-add is forbidden because it recreates rows with new PKs, breaking `x-references` FKs, audit trails, and concurrency tokens.

---

## 13) Example specification

For clarity and consistency, an example OpenAPI file is provided:

- `samples/endpoint-samples.yaml`

This file shows canonical implementations for all HTTP verbs (list, get one, create, search, replace, update, delete) with:

- Correct model usage (`New{Resource}`, `Update{Resource}`, `Basic{Resource}`, `{Resource}List`, `{Resource}SearchRequest`)
- Predefined error responses (400, 401, 403, 404)
- PUT/PATCH → 200 OK with `{Resource}` + Location
- DELETE → 204 No Content

When in doubt, use this file as the **authoritative template** for new resources and endpoints.

---

## 14) Authorization metadata

Every **secured** operation **must** declare:
- `x-roles`: array of allowed role names drawn from the project's closed role enum.
- `x-scopes`: array of OAuth scopes matching `<domain>[.<Entity>].<operation>` (e.g. `customer.Customer.read`, `order.read`). See `Vendor_Extensions.md` §3.2.

The role enum is project-defined; declare it in the project's OpenAPI common enums file (typically `common/enums.yaml`).

**Default policy templates (may be narrowed per endpoint):**
- **Read ops** (GET list/search/get):
  - `x-roles`: privileged + manager-tier roles
  - `x-scopes`: `[<domain>.<Entity>.read]` (e.g. `customer.Customer.read`; drop the entity segment when the operation spans the domain)
- **Write ops** (POST/PUT/PATCH/DELETE):
  - `x-roles`: privileged + administrative roles
  - `x-scopes`: `[<domain>.<Entity>.write]`, or `[<domain>.<Entity>.delete]` for a DELETE — `delete` is a distinct action, not a subset of `write`

> These extensions document intent for reviewers and generators; enforcement occurs in implementation and/or gateway policy.

---

## 15) Value Objects and Storage Patterns

Specfuse APIs use **value objects** to represent complex data structures that are embedded within entities. Value objects are immutable, have no identity of their own, and are stored as part of their parent entity.

### 15.1 Value Object Definition

A **value object** is a schema that:
- Represents a concept with multiple related properties (e.g., `Address`, `Money`, `ValidityWindow`)
- Has no `id`, `createdAt`, or `updatedAt` fields
- Is always used as a property within an entity
- Does NOT have `x-entity` metadata (entities have `x-entity`, value objects do not)

### 15.2 Storage Patterns

Value objects are stored using different strategies based on their complexity and query requirements. The storage pattern is defined in the parent entity's `x-entity.valueObjects` section.

#### Available Storage Patterns:

- **`collection_json`**: Array of value objects stored as JSON
- **`single_json`**: Single value object stored as JSON
- **`flatten`**: Value object properties flattened into parent entity columns
- **`serialized`**: Value object serialized as string/blob
- **`separate_table`**: Value object stored in separate table (for complex cases)

### 15.3 Entity Metadata for Value Objects

Entities that contain value objects must declare them in their `x-entity` metadata:

```yaml
Order:
  type: object
  required: [id, customerId, status]
  x-entity:
    type: aggregate
    belongsTo: [Tenant, Customer]
    hasMany: [OrderLine]
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
  properties:
    tags:
      type: array
      items:
        $ref: '#/OrderTag'
    validityWindow:
      $ref: '#/ValidityWindow'
    shippingPreferences:  # nullable inferred from not being in 'required'
      $ref: '#/ShippingPreferences'
```

#### Value Object Metadata Properties:

- **`storage`** (required): Storage pattern to use
- **`queryable`** (optional): Array of value object fields that need query support
- **`indexHints`** (optional): Array of fields that should be indexed for performance
- **`propertyPrefix`** (optional): Prefix for flattened properties (only for `flatten` storage)
- **`serializer`** (optional): Serialization format (only for `serialized` storage)

### 15.4 Storage Pattern Guidelines

#### Use `collection_json` when:
- Value object appears as an array
- Individual items need to be queryable
- Structure is moderately complex

#### Use `single_json` when:
- Value object appears as single instance
- Rarely queried directly
- Structure is complex with nested objects/arrays

#### Use `flatten` when:
- Value object has 2-4 simple properties
- Properties are frequently queried
- Want optimal query performance

#### Use `serialized` when:
- Value object is opaque to the database
- No query requirements
- Maximum flexibility needed

### 15.5 Implementation Notes

- **Nullability**: Inferred from OpenAPI `required` arrays, not specified in `valueObjects`
- **Schema References**: Already captured in property definitions, not duplicated
- **Column Naming**: Implementation-specific, follows database naming conventions
- **Code Generation**: Templates use `valueObjects` metadata to generate appropriate storage code

---

## 16) AI Agent Integration Framework

Specfuse projects are designed to be **agentic AI ready**, enabling autonomous AI agents to safely and efficiently interact with the API. This section defines patterns and requirements that make the API predictable, safe, and optimized for AI workflows.

### Core Principles for AI Integration

1. **Predictability**: Consistent patterns across all endpoints
2. **Safety**: Validation without side effects (`validateOnly`)
3. **Resilience**: Idempotency and retry mechanisms
4. **Efficiency**: Batch operations and selective responses
5. **Observability**: Comprehensive audit trails and change tracking

---

### Phase 1: Core AI Foundations (Required)

These patterns are **mandatory** for all endpoints and enable basic AI agent functionality:

#### 1. validateOnly Parameter ✅
**Purpose**: Enables AI agents to test operations without side effects.

```yaml
parameters:
  - name: validateOnly
    in: query
    required: false
    schema:
      type: boolean
      default: false
    description: "Run full validation without committing side effects"
```

**Behavior**:
- When `true`: Perform complete validation but make no changes
- Response: Same status code (200/201/204) as normal operation
- Required on: All write operations (POST/PUT/PATCH/DELETE)

#### 2. Idempotency Keys ✅
**Purpose**: Prevents duplicate operations during retries.

```yaml
parameters:
  - name: Idempotency-Key
    in: header
    required: false
    schema:
      type: string
      format: uuid
    description: "Prevents duplicate operations; replay same result on retry"
```

**Behavior**:
- Server stores key + result for 24 hours
- Identical key returns cached result
- Required on: POST operations (recommended on PUT/PATCH)

#### 3. Change Descriptions
**Purpose**: Enables audit trails and explainable AI actions.

```yaml
parameters:
  - name: X-Change-Reason
    in: header
    required: false
    schema:
      type: string
      maxLength: 500
    description: "Human-readable reason for this change"
  - name: X-Agent-Id
    in: header
    required: false
    schema:
      type: string
    description: "Identifier of the AI agent making this change"
```

#### 4. Enhanced Conflict Detection
**Purpose**: Provides detailed conflict information for intelligent resolution.

```yaml
responses:
  '409':
    description: "Conflict - resource was modified by another process"
    content:
      application/json:
        schema:
          type: object
          properties:
            error: { $ref: '#/components/schemas/Error' }
            currentVersion:
              type: string
              description: "Current ETag of the resource"
            conflictingFields:
              type: array
              items: { type: string }
              description: "Fields that have conflicting changes"
            currentResource:
              description: "Current state of the resource"
              # Reference to the actual resource schema
```

---

### Phase 2: Advanced AI Operations (Recommended)

These patterns enable sophisticated AI agent workflows:

#### 5. Batch Operations
**Purpose**: Reduces API calls and ensures atomic operations.

```yaml
paths:
  /{resources}:batch:
    post:
      summary: "Batch operations on {resources}"
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                operations:
                  type: array
                  items:
                    oneOf:
                      - type: object  # Create
                        properties:
                          op: { const: "create" }
                          data: { $ref: '#/components/schemas/New{Resource}' }
                      - type: object  # Update
                        properties:
                          op: { const: "update" }
                          id: { type: string }
                          data: { $ref: '#/components/schemas/Update{Resource}' }
                      - type: object  # Delete
                        properties:
                          op: { const: "delete" }
                          id: { type: string }
                validateOnly: { type: boolean, default: false }
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  results:
                    type: array
                    items:
                      type: object
                      properties:
                        op: { type: string }
                        id: { type: string }
                        status: { enum: ["success", "error"] }
                        resource: { } # The resulting resource
                        error: { $ref: '#/components/schemas/Error' }
```

#### 6. Change Feeds
**Purpose**: Enables AI agents to stay synchronized with data changes.

```yaml
paths:
  /changes:
    get:
      summary: "Get chronological changes across all resources"
      parameters:
        - name: cursor
          in: query
          schema: { type: string }
          description: "Resume from this position in the change stream"
        - name: limit
          in: query
          schema: { type: integer, maximum: 1000, default: 100 }
        - name: resourceTypes
          in: query
          schema:
            type: array
            items: { type: string }
          description: "Filter by resource types: ['Customer', 'Order']"
        - name: since
          in: query
          schema: { type: string, format: date-time }
          description: "Only changes after this timestamp"
      responses:
        '200':
          content:
            application/json:
              schema:
                type: object
                properties:
                  cursor: { type: string }
                  hasMore: { type: boolean }
                  changes:
                    type: array
                    items:
                      type: object
                      properties:
                        id: { type: string }
                        resourceType: { type: string }
                        operation: { enum: ["created", "updated", "deleted"] }
                        timestamp: { type: string, format: date-time }
                        resourceId: { type: string }
                        agentId: { type: string }
                        changeReason: { type: string }
                        data: { } # The resource state after change
```

#### 7. Partial Response/Field Selection
**Purpose**: Optimizes bandwidth and processing for AI agents.

```yaml
parameters:
  - name: fields
    in: query
    schema: { type: string }
    description: "Comma-separated field list: id,name,status"
    example: "id,name,status,createdAt"
  - name: expand
    in: query
    schema: { type: string }
    description: "Expand related resources: tenant,customer"
    example: "tenant,customer.preferences"
```

---

### Phase 3: Enterprise AI Features (Future)

Advanced patterns for enterprise-scale AI integration:

#### 8. Webhook Subscriptions
**Purpose**: Real-time notifications for AI agents.

```yaml
components:
  schemas:
    WebhookSubscription:
      type: object
      properties:
        id: { type: string, format: uuid }
        url: { type: string, format: uri }
        events:
          type: array
          items:
            enum: ["customer.created", "customer.updated", "order.submitted"]
        secret: { type: string, description: "For signature verification" }
        active: { type: boolean, default: true }
        filters:
          type: object
          properties:
            tenantId: { type: string }
            customerId: { type: string }
```

#### 9. Transaction Support
**Purpose**: Multi-step operations with rollback capability.

```yaml
paths:
  /transactions:
    post:
      summary: "Begin a new transaction"
      responses:
        '201':
          content:
            application/json:
              schema:
                type: object
                properties:
                  transactionId: { type: string }
                  expiresAt: { type: string, format: date-time }

  /transactions/{transactionId}:commit:
    post:
      summary: "Commit all operations in the transaction"

  /transactions/{transactionId}:rollback:
    post:
      summary: "Rollback all operations in the transaction"
```

---

### AI Agent Workflow Examples

#### Example 1: Safe Customer Creation
```
1. POST /customers?validateOnly=true (test creation)
2. Review validation results
3. POST /customers (actual creation with Idempotency-Key)
4. Handle conflicts with 409 response details
```

#### Example 2: Bulk Order Updates
```
1. POST /orders:batch?validateOnly=true (test all changes)
2. Review batch validation results
3. POST /orders:batch (commit all changes atomically)
4. Monitor /changes for confirmation
```

#### Example 3: Conflict Resolution
```
1. PUT /customers/123 (fails with 409)
2. Analyze conflictingFields from 409 response
3. GET /customers/123 (fetch current state)
4. Merge changes intelligently
5. PUT /customers/123 with new If-Match header
```

---

### Spectral Rules for AI Integration

The following Spectral rules enforce AI-friendly patterns:

- `specfuse-validate-only-on-writes`: All write operations must support validateOnly
- `specfuse-change-description-headers`: Recommended change tracking headers
- `specfuse-batch-operation-structure`: Validates batch operation schemas
- `specfuse-conflict-response-details`: Ensures 409 responses include conflict details
- `specfuse-idempotency-key-support`: POST operations should support Idempotency-Key

These rules ensure consistent AI integration patterns across all Specfuse APIs.
