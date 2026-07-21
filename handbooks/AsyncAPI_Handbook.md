# AsyncAPI Handbook

> **Version:** 2.1.0
> **Spec Format:** AsyncAPI 3.0.0
> **Reference Transport:** Azure Service Bus (AMQP 1.0) — the patterns generalize to any pub-sub transport with topic/subscription semantics (Kafka, NATS, Google Pub/Sub, RabbitMQ). Examples use ASB terminology; consult the Specfuse generator's runtime adapter docs for transport-specific bindings.
> **Status:** Authoritative — all async specifications in a Specfuse project MUST comply with this handbook.

This handbook defines the rules, conventions, and patterns for designing asynchronous process specifications in a Specfuse project. It is the async counterpart to the [API Handbook](./API_Handbook.md) and shares the same philosophy: spec-driven, code-generated, strictly validated.

**The v2.1 model is deliberately minimal.** Only two message categories exist (`event` and `scheduledJob`), only two channel types (`event-topic` and `scheduled-trigger`), and the entire architecture is pub-sub. v2.1 adds snapshot-based event payloads, suffix-driven action classes, and derived subscription filters on top of the v2 baseline (see §0.9 for the v2 → v2.1 design summary). Read [Section 1: Architectural Principles](#1-architectural-principles) before adding anything that doesn't fit — deviations require explicit user approval.

---

## Table of Contents

0. [Conventions](#0-conventions)
1. [Architectural Principles](#1-architectural-principles)
2. [Message Categories](#2-message-categories)
3. [Channel Design](#3-channel-design)
4. [Vendor Extensions Reference](#4-vendor-extensions-reference)
5. [Patterns Catalog](#5-patterns-catalog)
6. [Cross-Reference Rules](#6-cross-reference-rules)
7. [Code Generation Contract](#7-code-generation-contract)
8. [Do NOT](#8-do-not)
9. [Flow Documentation](#9-flow-documentation)
10. [Future Phases](#10-future-phases)

---

## 0) Conventions

### 0.1 Spec Version

All async specifications use **AsyncAPI 3.0.0**. The root entry point is `api/specs/v1/asyncapi.yaml`.

### 0.2 File Organization

```
api/specs/v1/
├── asyncapi.yaml                    # Root entry (references all domains)
├── async-common/                    # Shared async components
│   ├── message-traits/
│   │   └── common.yaml              # Correlation, tenant, timestamp headers
│   ├── operation-traits/
│   │   └── common.yaml              # Delivery guarantees, retry policies
│   └── bindings/
│       └── transport.yaml           # Protocol-specific bindings (e.g., azure-service-bus.yaml)
└── domains/
    └── {domain}/
        ├── models/                  # API-shaped resources — SHARED with OpenAPI (do not duplicate)
        ├── events/                  # Event-shaped resources — snapshots, contexts (see §2.3)
        ├── channels/                # Channel definitions
        ├── async-operations/        # Operation definitions
        └── messages/                # Message (event) definitions
```

**Rules:**
- One channel per file under `domains/{domain}/channels/`
- One message per file under `domains/{domain}/messages/`
- One async operation per file under `domains/{domain}/async-operations/`
- One snapshot per event-emitting entity under `domains/{domain}/events/{Entity}Snapshot.yaml`; one Context shape per state-transition that needs transient metadata (`{Entity}{Action}Context.yaml`). See §2.3.
- The root `asyncapi.yaml` uses ONLY `$ref` to point to domain files — no inline definitions

### 0.3 File Naming

| File Type | Folder | Convention | Example |
|-----------|--------|------------|---------|
| Channel | `channels/` | kebab-case, descriptive topic name | `order-events.yaml` |
| Message | `messages/` | PascalCase, matching the message `name` | `OrderSubmitted.yaml` |
| Async Operation | `async-operations/` | kebab-case with verb prefix | `on-order-submitted.yaml` |

### 0.4 Verb Prefixes for Async Operations

| Prefix | Action | `x-worker` | Use Case |
|--------|--------|------------|----------|
| `on-` | `receive` | **Required** | Event handlers — reacting to a domain event on a topic. These are workers. |
| `run-` | `send` | **Required** | Scheduled job dispatchers — triggered by a cron timer, publish events to a topic. These are workers. |
| `emit-` | `send` | **Forbidden** | Event publishing declarations — declares what an `on-*` worker publishes as a side effect. These are NOT workers. |

**How to distinguish `run-*` from `emit-*`:** both are `action: send`, but `run-*` is an independently triggered worker (cron schedule via `x-scheduled-job` on its message) with `x-worker`, while `emit-*` is a publishing declaration owned by an `on-*` receive operation (linked via `x-emits`) and has no `x-worker`.

**How `on-*` workers link to their `emit-*` declarations:** the `on-*` operation declares `x-emits` listing the event(s) it publishes on completion. Each `x-emits` entry uses the `{Entity}.{Action}` format matching the emitted message's `x-label`. This is the same pattern used on OpenAPI write operations, reused here for async-to-async links.

The legacy `execute-*` and `dispatch-*` prefixes no longer exist. Commands and point-to-point dispatch are not part of the v2 architecture.

### 0.5 Tags (Domain Grouping on Operations)

Async operations MUST declare exactly **one tag** identifying their domain — consistent with the OpenAPI convention.

```yaml
tags:
  - name: Order
```

Tags must be PascalCase and match the domain name. All tags used in operations must be declared in the root `asyncapi.yaml` under `info.tags`.

Channels do not support tags in AsyncAPI 3.0 — use `x-domain` instead.

### 0.6 Naming & Casing

| Element | Convention | Example |
|---------|-----------|---------|
| Event message names | Past tense PascalCase | `OrderSubmitted`, `CustomerCreated` |
| Scheduled job message names | Verb phrase + `Job` suffix | `AutoArchiveStaleOrdersJob` |
| Channel addresses | Dot-separated lowercase | `{project}.order.events` |
| Payload properties | camelCase | `orderId`, `submittedAt` |
| Subscription names | kebab-case | `on-order-submitted` |

The spec **does not** dictate generated class names, namespaces, file layout, or target language. Those are the code generator's concern, derived from `x-domain` plus language-specific conventions.

### 0.7 Channel Address Convention

**Event topics share a single address across the entire system:**

```
{project}.events
```

Where `{project}` is a short literal token chosen per project (e.g., `acme`, `hello-orders`) and configured once in the project's overlay. All domain event messages are published to this one topic. Routing between consumers is done by subscription filters over the Label property (see §0.8), not by topic splitting. The shared topic is defined in `api/specs/v1/async-common/channels/application-events.yaml` and referenced by every event-publishing operation and every event-receiving operation.

**Scheduled-trigger addresses remain per-domain:**

```
{project}.{domain}.jobs
```

Where `{domain}` is the kebab-case domain name (e.g., `order`, `customer`). Scheduled-trigger channels are logical identifiers (the real trigger is the cron expression on the message); per-domain grouping keeps the file tree tidy and does not impact the transport.

Examples (with `{project}` = `acme`):
```
acme.events                  # every event message, all domains
acme.order.jobs              # cron-triggered jobs for the order domain
acme.notification.jobs       # cron-triggered jobs for the notification domain
```

The rationale for the single shared event topic is documented in §1.5 and §3.2. Splitting events across multiple topics is forbidden without explicit user approval (§8, item 14).

### 0.8 Message Label Convention

Every message sent to the message bus sets the `Label` property (Azure Service Bus terminology; Kafka uses headers, NATS uses subjects — the generator's transport adapter handles the mapping) using exactly two segments:

```
{Entity}.{Action}
```

Examples:
```
Order.Submitted
Customer.Created
NotificationJob.Created
```

Where:
- `{Entity}` is the PascalCase aggregate/entity name from `x-label.entity` — MUST match a schema with `x-entity` in OpenAPI
- `{Action}` is the PascalCase past-tense action verb from `x-label.action`

**Tenancy lives in the envelope, not the label.** `tenantId` and any other tenant routing fields are stamped as ApplicationProperties (headers) on every event by the producer pipeline (see the universal envelope contract documented in the project's event-contract overlay; defaults emit `eventId`, `correlationId`, `aggregateId`, `aggregateType`, `eventVersion`, `producedAt`, and `tenantId`). Tenant-scoped subscribers AND-merge `user.tenantId = '<guid>'` into the derived label filter via `x-subscription.requiredHeaders` (see §4.3).

**Why two-segment labels:**

1. **Stable public contract.** Labels never carry tenant identity, so a message published in 2026 still routes correctly when the tenant is migrated, deleted, or merged.
2. **Filters become predicates over `Label = '<E.A>'`** (or `Label LIKE '<E>.%'` for entity-wildcard) — no `LIKE 'X.%.%'` traps, no SQL-LIKE-vs-dots confusion.
3. **Per-tenant subscribers are header-based**, not label-based — easier to add, remove, or deactivate without changing message metadata.

**Subscription filter patterns:**

```sql
-- Standard: single-action subscriber
Label = 'Order.Submitted'

-- All actions for one entity
Label LIKE 'Order.%'

-- Multi-action subscriber (subset of one entity's actions)
Label = 'Order.Submitted' OR Label = 'Order.Cancelled'

-- Multi-entity subscriber (one worker covering several aggregates)
Label LIKE 'Customer.%' OR Label LIKE 'Order.%' OR Label LIKE 'Refund.%'

-- Tenant-scoped subscriber (header-driven, AND-merged with derived label filter)
Label = 'Order.Submitted' AND user.tenantId = '550e8400-e29b-41d4-a716-446655440000'

-- Channel-aware subscriber for promoted-header values (see x-envelope-promote)
Label = 'NotificationJob.Created' AND user.channel = 'email'
```

**Authors do not write filters.** The generator derives the filter from the operation's `messages:` list as an OR-chain over `Label =` (or `LIKE '<E>.%'` for entity-wildcard patterns), then AND-merges any `requiredHeaders` declared on `x-subscription`. The legacy authored `filter` field is forbidden — see `Vendor_Extensions.md §12.3`.

### 0.9 v2.1 Design Summary

v2.1 settled three design questions that earlier v2 specs left open. The handbook reflects all three:

| # | Question | Resolution |
|---|---|---|
| 1 | **Snapshot embedding** on `*Updated` and state-transition events | **Full snapshots.** Every `*Updated` and state-transition event ships full `before` + `after` snapshots `$ref`-ed from `domains/{domain}/events/{Entity}Snapshot.yaml`. Bandwidth is managed via the snapshot guardrails (size cap + PII acknowledgement, see §2.3). The earlier "events carry only what consumers need" rule is superseded. |
| 2 | **First-appearance naming** vs domain-specific creation verbs | **`*Created` is the default** for any event that marks an entity's first appearance. The "manner of creation" moves to a snapshot field (e.g., `creationSource: 'imported' \| 'manual'`). The Spectral rule `specfuse-async-first-appearance-uses-created` enforces this at error severity. Outcome events of cross-aggregate state transitions (e.g., a worker processing `Tenant.OnboardingRequested` creates Customer aggregates) emit standard `Customer.Created` events per child entity. |
| 3 | **Fan-out collapse** for multi-channel notifications | **One event per business action, multiplexed via `x-envelope-promote`.** Channel-specific dispatchers (email, SMS, push) subscribe to a single `NotificationJob.Created` event and discriminate via `requiredHeaders: { channel: <X> }`. Avoids `*QueuedFor{Email,Sms,Push}` proliferation. |

These choices favor consumer self-sufficiency (snapshots), naming uniformity (`*Created`), and small event surface area (header-based fan-out) over per-handler payload minimization. The size and PII guardrails (§2.3) catch the bandwidth/privacy edge cases.

---

## 1) Architectural Principles

The v2 async architecture follows **five hard rules**. They exist to keep the system simple, predictable, and easy to reason about. Deviations require explicit user approval (Rule 1.4).

### 1.1 Pub-Sub Is the Only Transport Model

Every message is published to a topic. Every consumer subscribes to the messages it cares about. There are no direct command queues, no point-to-point sends, no request/reply semantics.

If handler A needs handler B to do something, A publishes an event; B subscribes to that event. The event/command distinction is conceptual, not structural — on the wire both are just messages with routing metadata. Eliminating the distinction collapses several layers of ceremony (command messages, dispatcher operations, `x-dispatches` metadata, thin-dispatcher-of-commands pattern) without losing any real capability.

**Implication:** the handler that reacts to an event does the actual work directly. It does NOT dispatch a command to another handler for the same domain.

### 1.2 Event Payloads Use Snapshots — Shaped by Action Class

Event payload shape is determined by **action class**, which is inferred from the message-name suffix (see §2.2 for the full table):

- `*Created` events carry the aggregate ID + an `after` snapshot of the just-created entity.
- `*Updated` events carry the aggregate ID + `before` + `after` snapshots so consumers can compute deltas.
- `*Deleted` events carry the aggregate ID + a `before` snapshot of the entity at the moment of removal.
- State-transition events (anything else, e.g., `*Approved`, `*Archived`, `*Submitted`) carry the aggregate ID + `before` + `after` snapshots, plus an optional `context` for transient transition metadata that does not live on the entity.

A snapshot is a frozen, versioned record of the entity's scalar columns and owned value objects (NOT navigation properties, NOT child collections). One snapshot per entity, reused across all events for that entity (see §2.3 for snapshot rules and the `events/` folder convention).

**This is a deliberate choice over the earlier "events carry only what consumers need, never the full aggregate" stance.** The rationale for embedding full snapshots:

1. **Consumer self-sufficiency** — downstream handlers compute deltas, build projections, and emit notifications without round-tripping back to the source service. Round-trips couple consumers to the producer's REST availability and add latency to every event.
2. **Schema evolution clarity** — the snapshot is the public schema; entities are not. Breaking entity changes that don't affect the snapshot stay private to the producer.
3. **Generator-friendly typing** — typed snapshot records (`CustomerSnapshot`, etc.) eliminate the "what does this event payload actually look like" guesswork on every consumer.

**Bandwidth and cost are managed via**:

- **Snapshot size cap** (default 25 scalar fields, soft Spectral warning) — bloat indicates an entity doing too much; explicit waiver via `x-snapshot-size-acknowledged: true`.
- **PII acknowledgement** (Spectral rule) — fields classified `pii`/`sensitive` (see `Vendor_Extensions.md §1.5`) require per-field justification in `x-snapshot-pii-acknowledged` before they may appear in a snapshot.
- **Optional `context` field** (state-transition only) for transient metadata that should not be persisted on the entity (e.g., a cancellation reason, an external trigger source).

### 1.3 Scheduled Jobs Are Thin Fan-Out Dispatchers

A scheduled job (cron-triggered worker) MUST:

1. Query the database to identify work items matching its criteria
2. Publish one **event** per work item to a topic — one that other subscribers already handle (or that you are adding a subscriber for)

The job itself does NO heavy processing. Separate subscribers handle each event independently with proper isolation, retry, and DLQ support.

**Rationale:** if a job archives 200 stale records and record #47 fails, you don't want the whole batch to die or retry from the beginning. Per-item events mean per-item failure isolation, retry, DLQ visibility, and independent observability.

**Narrow exception:** jobs that produce a single output (e.g., "nightly metrics snapshot published as one event") or jobs where there are no per-item semantics (e.g., "regenerate a materialized view") can do the work directly. The exception must be obvious from context; when in doubt, default to fan-out and ask.

### 1.4 When to Deviate

If, while designing async specs, you want to do any of the following, **stop and escalate**:

- Define a command message (single-consumer semantics, request/reply, imperative naming)
- Introduce a point-to-point queue
- Define a saga or multi-step orchestration
- Have a scheduled job do heavy processing directly (beyond the narrow exception in 1.3)
- Use a message category or channel type not listed in this handbook

Explain to the user *why* the simpler model is insufficient for the specific scenario. Wait for explicit approval before proceeding. Do not silently introduce new extensions, new message categories, or new patterns.

### 1.5 All Domain Events Share One Topic

Every event message is published to the single shared topic `{project}.events` (§0.7). There is no per-aggregate or per-domain event topic. Consumers subscribe with SQL-like filters over the `Label` property (§0.8) to receive only the events they care about.

**Multi-entity subscribers are a first-class pattern.** A single `on-*` operation can list multiple message `$ref`s and compose an OR-chain SQL filter (e.g., `Label LIKE 'Customer.%' OR Label LIKE 'Order.%' OR Label LIKE 'Refund.%'`). This is preferred over splitting the same logical worker into multiple sibling operations; it keeps cross-aggregate logic (projection rebuilds, sync workers, notification orchestrators) in one cohesive handler with one subscription, one DLQ, and one retry budget.

**Rationale:**

- The two-segment `Label` convention (`{Entity}.{Action}`) plus envelope ApplicationProperties (`tenantId`, plus `x-envelope-promote` opt-ins) plus the transport's SQL-style filters already provide all the routing fidelity needed — down to the individual tenant or channel if required. Adding a second axis of routing (topic splitting) duplicates that capability at the broker level without adding any expressiveness.
- One topic means one publishing endpoint, one client configuration, one set of permissions. New event types cost a message file and a one-line entry on the shared channel's `messages` map — no new infrastructure resources, no IaC changes, no deployment coordination.
- Cross-aggregate handlers (which routinely touch several aggregates) would otherwise need to subscribe to N topics or hold N client connections. With the shared topic they subscribe once.
- Splitting topics later is non-breaking. Payload shape and label format are transport-agnostic, so moving a subset of events onto their own topic is a pure infrastructure change if throughput or blast-radius isolation ever demands it. See §3.2 (sharding escape hatch).

**Scope limit:** this rule applies to event topics only. Scheduled-trigger channels remain per-domain logical identifiers (§3.3) because they carry no transport semantics — the cron is the trigger.

If a specific flow seems to need event topic splitting (e.g., a high-cardinality projection flood, a compliance isolation boundary), **stop and escalate per Rule 1.4.** The sharding escape hatch is available, but it is not a default.

---

## 2) Message Categories

Every message MUST declare `x-message-category`. Only two values are valid:

- `event` — a domain event published to a topic
- `scheduledJob` — a cron-triggered job parameter payload

### 2.1 Domain Events (`event`)

Domain events signal that something has already happened. They are facts — immutable notifications of state changes.

**Naming:** Past tense, PascalCase. Examples: `OrderSubmitted`, `CustomerCreated`, `RefundApproved`.

**Required extensions:**
- `x-message-category: event`
- `x-label` with `entity` (PascalCase aggregate name) and `action` (PascalCase past-tense verb)
- `x-version` with `current` and `status`
- Message `traits` referencing `auditableEvent` from `async-common/message-traits/common.yaml` — supplies the canonical envelope (eventId, correlationId, aggregateId, aggregateType, eventVersion, producedAt, etc.)

**Required when applicable:**
- `x-trigger-when` on state-transition events (anything not `*Created`/`*Updated`/`*Deleted`) — see §2.2 and `Vendor_Extensions.md §12.2`

**Optional extensions:**
- `x-partition-key` when ordered delivery is required for the same aggregate

**Payload rules** (see §2.2 for the full action-class table):
- Always include the aggregate ID (e.g., `orderId`) as a required scalar
- Include `before` / `after` snapshot references per the action class
- Snapshots are `$ref`-ed from `domains/{domain}/events/{Entity}Snapshot.yaml` (see §2.3)
- Tenant routing fields (`tenantId`) belong in the snapshot, not as separate required payload fields — the envelope ApplicationProperties carry them for routing

**Example** (`*Updated`, the most common shape):
```yaml
name: OrderUpdated
title: Order Updated
summary: Emitted when an order's tracked fields change without a state transition.
contentType: application/json
traits:
  - $ref: '../../../async-common/message-traits/common.yaml#/auditableEvent'
x-message-category: event
x-label:
  entity: Order
  action: Updated
x-version:
  current: 1
  status: stable
x-partition-key:
  property: orderId
  scope: aggregate
payload:
  type: object
  required: [orderId, before, after]
  properties:
    orderId:
      type: string
      format: uuid
    before:
      $ref: '../events/OrderSnapshot.yaml'
    after:
      $ref: '../events/OrderSnapshot.yaml'
```

**Example** (state transition, e.g., `Submitted`):
```yaml
name: OrderSubmitted
x-message-category: event
x-label: { entity: Order, action: Submitted }
x-version: { current: 1, status: stable }
x-trigger-when: "After.status == 'submitted' && Before.status != 'submitted'"
payload:
  type: object
  required: [orderId, before, after]
  properties:
    orderId: { type: string, format: uuid }
    before: { $ref: '../events/OrderSnapshot.yaml' }
    after:  { $ref: '../events/OrderSnapshot.yaml' }
```

### 2.2 Event Action Classes (Suffix-Driven Inference)

The action class of an event is **inferred from its message-name suffix** — there is no `x-action-class` extension, and authors do not declare it. The Spectral rule `specfuse-async-event-name-action-class` validates that the suffix and payload shape align.

| Suffix | Action class | Required payload fields | `x-trigger-when` |
|---|---|---|---|
| `*Created` | created | `<aggregateId>`, `after` | Forbidden |
| `*Updated` | updated | `<aggregateId>`, `before`, `after` | Forbidden |
| `*Deleted` | deleted | `<aggregateId>`, `before` | Forbidden |
| **anything else** (e.g., `*Approved`, `*Archived`, `*Submitted`, `*Published`) | stateTransition | `<aggregateId>`, `before`, `after`, optional `context` | **Required** |

Where `<aggregateId>` is a required scalar payload field whose name matches the entity's primary-key field (e.g., `orderId` for `Order.*` events). The Specfuse rule `ASYNC_PAYLOAD_AGGREGATE_ID_MISSING` enforces it.

**State-transition events require `x-trigger-when`** — a pure boolean predicate over `Before.*`/`After.*` snapshot fields that determines when the event fires. See `Vendor_Extensions.md §12.2` for the full grammar; in short:

```yaml
x-trigger-when: "After.status == 'archived' && Before.status != 'archived'"
```

The predicate is evaluated by generator-emitted service code against `EntityEntry.OriginalValues` (Before) and `EntityEntry.CurrentValues` (After) before `SaveChangesAsync`. When matched, the transition event fires AND the corresponding `*Updated` is suppressed (mutual exclusivity rule). Multiple matching transitions on one save fire as siblings — same `correlationId`/`causationId`/`aggregateVersion`, distinct `eventId`s, no guaranteed emit order.

**First-appearance events use `*Created`**: events that mark an entity's first appearance MUST use the `*Created` suffix even when the domain has its own creation verb. The "manner of creation" moves to a snapshot field (e.g., `creationSource: 'imported' | 'manual'`). The Spectral rule `specfuse-async-first-appearance-uses-created` flags non-`*Created` events whose `x-trigger-when` references no `Before.*` fields. **Exception:** events that fire as the *outcome* of a state transition on a different aggregate (e.g., a worker that processes `Tenant.OnboardingRequested` creates Customer aggregates) emit standard `Customer.Created` events per child aggregate — the parent state transition is a separate concern from the per-aggregate creation.

**Optional `context` field** (state-transition only): for transitions whose metadata genuinely should not persist on the entity (cancellation reason, external trigger source), a `context: { $ref: '../events/{Entity}{Action}Context.yaml' }` field may appear in the payload. When `context` is present, the message MUST declare `x-trigger-mode: explicit` and an `x-method-name` (the imperative verb for the generated service method); the generator then emits that explicit service method taking the context as a parameter and suppresses the auto-emission path for the event (see `Vendor_Extensions.md §12.2` for both extensions). `x-trigger-when` is still required — it documents the semantic transition AND prevents the auto-path from emitting `*Updated` per the mutual-exclusivity rule. The owning OpenAPI operation MUST also declare `x-context-justification` (see `Vendor_Extensions.md §6.3`).

### 2.3 Snapshots — One Per Entity, Reused Across All Events

Each event-emitting entity has exactly one `{Entity}Snapshot` definition, **reused across all of its events** (Created/Updated/Deleted/state transitions). Snapshots live in a dedicated `events/` folder peer to `models/`:

```
api/specs/v1/domains/{domain}/
├── models/                                # API-shaped resources
├── events/                                # event-shaped resources (snapshots, contexts)
│   ├── {Entity}Snapshot.yaml              # one per event-emitting entity
│   └── {Entity}{Action}Context.yaml       # opt-in per state transition (§2.3 context field)
├── messages/                              # event message declarations
├── channels/
└── async-operations/
```

**Why `events/` not `models/`:** snapshots are the public schema of the event stream; OpenAPI models are the public schema of REST surfaces. The folder boundary makes the distinction explicit and leaves room for other event-only types (e.g., `Context` shapes).

**The snapshot contains:**
- All scalar columns of the entity
- All owned value objects (serialized via the same converter as on the entity)
- Foreign-key scalars to parent entities (`tenantId`, etc.)

**The snapshot does NOT contain:**
- Navigation properties
- Child collections (children have their own events and snapshots)
- Computed/non-stored fields
- Audit fields already present on the envelope (`producedAt`, `userId`, `correlationId`, etc.)

**Change detection diffs the tracked entity, never the snapshot.**

The snapshot is the wire payload. It is not the diff source. Because it deliberately omits navigation properties, child collections, and computed fields, a snapshot-level diff reports "identical" for a write that mutated only an omitted field — and, combined with the no-op suppression rule (`API_Handbook.md` §Concurrency Control → No-Op Writes), silently swallows a real persisted change while publishing nothing and raising no error. Data moves, the event stream stays quiet, nothing fails. That is the expensive shape to debug.

Diff `EntityEntry.OriginalValues` against `EntityEntry.CurrentValues` before `SaveChangesAsync` — the same source `x-trigger-when` predicates evaluate against (`Vendor_Extensions.md` §12.2).

Accepted consequence: a write touching only snapshot-omitted fields emits an `*Updated` whose `before` and `after` are byte-identical, so subscribers cannot tell what moved. The intended remedy is to add the field to the snapshot if consumers need it; a `changedFields` map on the envelope was considered and rejected (§5.3 — consumers compute deltas from `(before, after)`).

**Array-valued properties compare as sets.**

For change detection, scalar-array properties compare order-insensitively: `[a, b]` → `[b, a]` is not a change and MUST NOT trigger a write or an event. Sorting or hashing members before comparison is fine. Where authored sequence carries meaning, declare an explicit ordering property and sort on it — array position in a JSON column MUST NOT carry semantics implicitly. (This concerns scalar arrays only; child collections are excluded from snapshots and have their own events.)

**Snapshot guardrails:**

| Rule | Severity | Override |
|---|---|---|
| Snapshot has > 25 scalar fields | warn | `x-snapshot-size-acknowledged: true` on the snapshot file |
| Snapshot includes a property whose source entity field carries `x-classification: [pii \| sensitive]` | error | `x-snapshot-pii-acknowledged: { propertyName: "justification ≥ 20 chars" }` on the snapshot file |
| Snapshot field name does not exist on the source entity | error | (no override — fix the snapshot or the entity) |

**Snapshot version cascade:** breaking changes to a snapshot (renamed/typed/new-required field, removed required field) bump `x-version.current` on every event message that `$ref`s that snapshot. Non-breaking changes (new optional field) require no bump anywhere. The Specfuse generator emits the impact graph at build time so cascades are visible at PR review.

**Snapshot dual-version coexistence:** when a breaking change forces a bump, the previous snapshot shape stays available so deprecated event messages can still deserialize. The convention (rename existing → `*V1.yaml`, author new under canonical name; deprecated event messages flip `$ref` to the versioned file; delete both after `removalDate`) is documented in `Vendor_Extensions.md §12.2 x-version`.

**Example** (`api/specs/v1/domains/customer/events/CustomerSnapshot.yaml`):

```yaml
type: object
description: Frozen snapshot of a Customer at the moment of an event.
required: [id, tenantId, status]
properties:
  id:           { type: string, format: uuid }
  tenantId:     { type: string, format: uuid }
  userId:       { type: string, format: uuid, nullable: true }
  firstName:    { type: string }
  lastName:     { type: string }
  email:        { type: string, format: email, nullable: true }
  phone:        { $ref: '../models/PhoneNumber.yaml' }
  status:       { $ref: '../models/CustomerStatus.yaml' }
  tier:         { $ref: '../models/CustomerTier.yaml' }
  archivedAt:   { type: string, format: date-time, nullable: true }
```

### 2.4 Scheduled Jobs (`scheduledJob`)

Scheduled jobs are time-triggered background tasks. They follow the **thin fan-out dispatcher** pattern (Rule 1.3) by default.

**Naming:** Verb phrase + `Job` suffix, PascalCase. Examples: `AutoArchiveStaleOrdersJob`, `RecomputeCustomerTiersJob`.

**Required extensions:**
- `x-message-category: scheduledJob`
- `x-label` with `entity` and `action`
- `x-version` with `current` and `status`
- `x-scheduled-job` with `cron`, optional `timezone`, `overlap`, `scope`

**Payload rules:**
- For `perTenant` scope: include `tenantId` (the dispatcher runs once per tenant)
- For project-specific narrower scopes (e.g., `perCustomer`): include the matching scoping field(s)
- For `global` scope: payload may be empty or carry only config parameters (e.g., thresholds)

**Overlap strategies:**
- `skip` (default): if a previous run is still executing, skip the new trigger
- `queue`: queue the new trigger to run after the current one completes
- `cancelPrevious`: cancel the running instance and start fresh

**Example:**
```yaml
name: AutoArchiveStaleOrdersJob
title: Auto-Archive Stale Orders Job
summary: Runs weekly to fan out archive events for stale draft orders
contentType: application/json
traits:
  - $ref: '../../../async-common/message-traits/common.yaml#/commonHeaders'
x-message-category: scheduledJob
x-label:
  entity: Order
  action: AutoArchiveStale
x-version:
  current: 1
  status: stable
x-scheduled-job:
  cron: '0 2 * * 1'
  timezone: America/New_York
  overlap: skip
  scope: perTenant
payload:
  type: object
  required: [tenantId]
  properties:
    tenantId:
      type: string
      format: uuid
    staleThresholdDays:
      type: integer
      default: 30
```

### 2.5 The Closed Universe: No Open Maps in Event Payloads

Event payloads live in a **closed universe** — the same principle that governs the domain registry (`API_Handbook.md §0.1`) applies to the *shape* of every payload. Each field of a snapshot, a `context` object, or a job payload MUST resolve to a **named, typed schema**: a scalar with a declared `format`, an enum, a snapshot `$ref`, or a value object (`x-value-object`, `Vendor_Extensions.md §1.2`). What is forbidden is the **open map** — a free-form `object` with `additionalProperties: true` (or `additionalProperties: { }`) standing in for "some set of keys we don't want to enumerate."

**Why open maps are banned:**

- **No generated types.** An open map generates as `Dictionary<string, object>` / `Map<String, Object>` / `dict[str, Any]` — the consumer self-sufficiency and typed-payload guarantees of §1.2 evaporate. Every consumer re-invents parsing and re-guesses the value type.
- **No validation, no evolution signal.** Nothing constrains the keys, so nothing flags a producer that renames one. The snapshot-version cascade (§2.3) cannot see inside an open map, so a breaking change ships silently.
- **No audit surface.** PII/classification rules (§2.3, `Vendor_Extensions.md §1.5`) key off declared fields. Data hidden in an open map bypasses `x-snapshot-pii-acknowledged` entirely.

**The remodel:** when the data is genuinely heterogeneous (a variable set of extracted values, per-line annotations, arbitrary tags), do not reach for a map keyed by strings. Model it as an **array of self-describing value objects** — each element names its own kind via a discriminator and carries a typed value. The set of kinds is itself a closed enum, so the universe stays closed.

#### Worked example: `DocumentExtractedContext`

A `Document.Extracted` state-transition event (`x-trigger-when: "After.status == 'extracted' && Before.status != 'extracted'"`) carries a `context` describing the fields an extraction worker pulled out of the document. The first cut modeled that context as an open map of field-name → value.

**Before — open map (rejected):**

```yaml
# events/DocumentExtractedContext.yaml  ❌
type: object
description: Fields extracted from the document, keyed by field name.
additionalProperties: true        # <-- open map: any string key, any value
# e.g. { "invoiceNumber": "INV-42", "total": 128.5, "issuedOn": "2026-07-01" }
```

Problems: the key set is unbounded, the value type is `object`, and neither `total` (a money amount) nor `invoiceNumber` (an identifier) carries type, confidence, or provenance. Generated consumers get `Dictionary<string, object>`.

**After — array of self-describing value objects (correct):**

```yaml
# events/DocumentExtractedContext.yaml  ✅
type: object
required: [fields]
description: Fields extracted from the document, as a closed set of typed value objects.
properties:
  fields:
    type: array
    items:
      $ref: './ExtractedField.yaml'
```

```yaml
# events/ExtractedField.yaml  ✅  (self-describing value object)
type: object
x-value-object:
  defaultStorage: 'single_json'
  immutable: true
required: [kind, value, confidence]
properties:
  kind:                            # discriminator — the closed set of extractable fields
    $ref: './ExtractedFieldKind.yaml'
  value:                           # typed, normalized value
    type: string
  confidence:
    type: number
    minimum: 0
    maximum: 1
  source:                          # provenance: where on the document it was found
    type: string
    nullable: true
    description: e.g. page/region locator; null when the extractor cannot attribute it.
```

```yaml
# models/ExtractedFieldKind.yaml  ✅  (closed enum — the universe of kinds)
type: string
enum: [invoiceNumber, total, issuedOn, vendorName, currency]
```

Now every extracted field is a first-class, typed, versioned VO drawn from a closed enum of `kind`s. Adding a new extractable field is a one-line enum edit that the version cascade and Spectral rules can see — the universe stays closed. `additionalProperties: true` anywhere in an event payload is an ERROR; the escape hatch (a genuinely opaque blob) is a single scalar `type: string, format: byte` field with a documented content type, never a keyed map.

---

## 3) Channel Design

### 3.1 Channel Types

Every channel MUST declare `x-channel-type`:

| Type | Protocol Mechanism | Fan-out | Use Case |
|------|-------------------|---------|----------|
| `event-topic` | Pub-sub topic (e.g., ASB Topic, Kafka topic, NATS subject) | Yes (subscriptions) | Domain events — multiple consumers can subscribe |
| `scheduled-trigger` | Timer (not a real transport) | N/A | Scheduled jobs — triggered by cron, modelled as a channel for structural parallelism |

### 3.2 Topic Design

**Core rule:** All event messages are published to the single shared topic `{project}.events`. Consumers subscribe with SQL filters over the `Label` property (see §0.8). Per-aggregate topic splitting is an optional sharding escape hatch if throughput or blast-radius isolation ever demands it — payload and label formats are transport-agnostic so splitting later is non-breaking.

**Rules:**

- Every event-publishing operation (`on-*` with `x-emits`, `run-*` scheduled-trigger publishers that produce events, and every `emit-*` sibling) binds to the shared channel `async-common/channels/application-events.yaml`.
- Every event-receiving `on-*` operation binds to that same shared channel.
- Consumers isolate themselves with the derived subscription filter — one subscription per `on-*` operation, generated from the operation's `messages:` list and any `requiredHeaders` / `filterOverride` (authors never write the filter directly; see §4.3).
- The shared channel's `messages` map must list every event message referenced by any operation bound to it. This is an authoring-time invariant enforced by the Spectral rule `asyncapi-channel-message-completeness`.
- Multi-entity workers list multiple message `$ref`s in `messages:`; the generator composes the OR-chain over `Label` equality. See §4.3 for filter modes and §4.5 for the per-filter entity-pattern cap.

**Sharding escape hatch (not a default):**

If operational evidence later shows that a specific subset of events needs its own topic (e.g., very high throughput swamping unrelated subscribers, or a compliance isolation boundary that cannot be expressed as a filter), the migration is purely infrastructure-side:

1. Add a new channel file for the split topic.
2. Move the subset of message `$ref`s from `application-events.yaml` to the new channel's `messages` map.
3. Repoint the relevant operations' channel reference.

No message payload, no `x-label`, no consumer filter logic needs to change. Do NOT split topics preemptively — wait for concrete evidence and escalate per Rule 1.4.

**Scheduled-trigger exemption:** scheduled-trigger channels are per-domain (§3.3). The single-topic rule applies to event messages only.

### 3.3 Scheduled-Trigger Channels

Scheduled-trigger channels group all cron-triggered jobs for a domain. One channel per domain, e.g., `{project}.order.jobs`.

A scheduled-trigger channel has no transport semantics — its `address` is purely a logical identifier. The actual trigger is the cron expression declared on each message's `x-scheduled-job`. Modeling it as a channel keeps the spec structurally parallel with event topics so the generator can walk the same tree.

### 3.4 Dead-Letter Channels

Dead-letter channels are NOT explicitly defined in the spec — they are infrastructure concerns handled by the transport's configuration. The spec focuses on the happy path.

### 3.5 Channel File Structure

**Shared event channel** — the one channel every event-topic operation binds to:

`api/specs/v1/async-common/channels/application-events.yaml`:

```yaml
address: '{project}.events'
description: |
  Single shared topic for every domain event. Consumers subscribe with
  SQL filters over the Label property. See handbook §1.5 and §3.2 for
  the rationale.
messages:
  orderSubmitted:
    $ref: '../../domains/order/messages/OrderSubmitted.yaml'
  customerCreated:
    $ref: '../../domains/customer/messages/CustomerCreated.yaml'
  notificationJobCreated:
    $ref: '../../domains/notification/messages/NotificationJobCreated.yaml'
  # ...one entry per event message file in the repo
x-domain: shared
x-channel-type: event-topic
```

The `messages` map MUST list every event message referenced by any operation bound to this channel. When authoring a new event message, add a one-line `$ref` here at the same time. This completeness invariant is enforced at authoring time by the Spectral rule `asyncapi-channel-message-completeness` (no generator magic, no implicit discovery).

**Scheduled-trigger channel** — one per domain, under `domains/{domain}/channels/`:

```yaml
address: '{project}.{domain}.jobs'
description: |
  Scheduled-trigger channel for the {domain} domain
messages:
  autoArchiveStaleOrdersJob:
    $ref: '../messages/AutoArchiveStaleOrdersJob.yaml'
x-domain: {domain}
x-channel-type: scheduled-trigger
```

---

## 4) Vendor Extensions Reference

### 4.1 Channel Extensions

#### `x-domain` (required on all channels)

The domain this channel belongs to. Must match the domain folder name. The active domain list is defined by the project's overlay (location is project-specific; the validator loads it at lint time).

```yaml
x-domain: order
```

**Type:** kebab-case string

#### `x-channel-type` (required on all channels)

```yaml
x-channel-type: event-topic
```

**Valid values:** `event-topic`, `scheduled-trigger`

### 4.2 Message Extensions

#### `x-message-category` (required on all messages)

```yaml
x-message-category: event
```

**Valid values:** `event`, `scheduledJob`

#### `x-label` (required on all messages)

Declares the Label segments used for message-bus routing. The runtime Label is exactly two segments: `{entity}.{action}` — tenancy moves to envelope ApplicationProperties (see §0.8).

```yaml
x-label:
  entity: Order
  action: Submitted
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `entity` | Yes | PascalCase string | Aggregate/entity name. MUST match a schema with `x-entity` in OpenAPI specs. |
| `action` | Yes | PascalCase past-tense verb | Action verb (e.g., `Created`, `Submitted`, `Archived`). Imperative verbs (`Create`, `Submit`) are not events — they are commands, which v2 architecture does not support. |

**Deriving entity and action from the message name:**
- Events: `OrderSubmitted` → entity: `Order`, action: `Submitted`
- Jobs: `AutoArchiveStaleOrdersJob` → entity: `Order`, action: `AutoArchiveStale`

The `x-label.entity` field **is** the aggregate link. There is no separate `x-source-aggregate` or `x-event.aggregateType` — the validator reads `x-label.entity` and confirms it matches a PascalCase aggregate schema in OpenAPI.

**Labels are public contract.** Once a label has been published to a topic that has live consumers, it cannot be renamed. To change semantics, mark the existing message `x-version.status: deprecated` with `replacedBy`, author the new message under the new label, and run both in parallel for the deprecation window.

#### `x-version` (required on all messages)

```yaml
x-version:
  current: 1
  status: stable
```

| Field | Required | Type | Values | Description |
|-------|----------|------|--------|-------------|
| `current` | Yes | integer | >= 1 | Current schema version number |
| `status` | Yes | string | `draft`, `stable`, `deprecated` | Lifecycle status |
| `deprecatedAt` | When `status: deprecated` | string | ISO date | When this version was deprecated |
| `replacedBy` | When `status: deprecated` | string | PascalCase | Successor message name |
| `removalDate` | No | string | ISO date | Optional target date for removing the deprecated version |

The same `x-version` shape is used across all three spec pillars (OpenAPI, AsyncAPI, Arazzo). Deprecation metadata lives inside `x-version`; there is no separate `x-deprecated` extension.

**Evolution rules:**

Within the same version (non-breaking):
- Add new **optional** properties
- Add new enum values (consumers must handle unknown values gracefully)
- Relax a constraint (e.g., increase maxLength)

Requires a **new version** (breaking):
- Remove or rename a property
- Change a property's type
- Make an optional property required
- Change the meaning of an existing property or enum value

**Version lifecycle:**
1. `draft` — Schema is under development, not yet consumed in production
2. `stable` — Schema is in production; evolution rules apply
3. `deprecated` — Schema is being phased out; `replacedBy` must point to the successor

#### `x-scheduled-job` (required on `scheduledJob` messages)

```yaml
x-scheduled-job:
  cron: '0 2 * * 1'
  timezone: America/New_York
  overlap: skip
  scope: perTenant
```

| Field | Required | Type | Values | Description |
|-------|----------|------|--------|-------------|
| `cron` | Yes | string | Standard cron | Cron schedule expression |
| `timezone` | No | string | IANA timezone | Default: UTC |
| `overlap` | No | string | `skip`, `queue`, `cancelPrevious` | Default: `skip` |
| `scope` | No | string | `global`, `perTenant`, project-defined narrower scopes | Default: `perTenant` |

The `scope` enum is project-tunable. Generator accepts arbitrary kebab/camelCase values and emits one job instance per scope row.

#### `x-partition-key` (optional, on events requiring ordered delivery)

```yaml
x-partition-key:
  property: orderId
  scope: aggregate
```

| Field | Required | Type | Values | Description |
|-------|----------|------|--------|-------------|
| `property` | Yes | camelCase string | — | Payload property used as partition key |
| `scope` | No | string | `aggregate`, `tenant`, project-defined narrower scopes | Default: `aggregate` |

**When to use ordered delivery:**
- State-change events for the same aggregate that must be applied in sequence
- Per-tenant batch operations with sequential guarantees

**When NOT to use:**
- Events consumed by idempotent, order-independent handlers
- Scheduled jobs (always dispatched in parallel)

**Impact on consumers:**
- The receiving operation's `x-subscription` should set `requiresSession: true`
- The transport uses the partition key as the session ID, guaranteeing FIFO within a session
- Concurrency is limited to one message per session (multiple sessions process in parallel)

#### `x-trigger-when` (required on state-transition messages, forbidden on `*Created`/`*Updated`/`*Deleted`)

Pure boolean predicate over `Before`/`After` snapshot fields. The generator-emitted service code evaluates the predicate against `EntityEntry.OriginalValues` and `EntityEntry.CurrentValues` before `SaveChangesAsync`; on a match, the transition event fires AND the corresponding `*Updated` is suppressed (mutual exclusivity).

```yaml
x-trigger-when: "After.status == 'archived' && Before.status != 'archived'"
```

See `Vendor_Extensions.md §12.2` for the full predicate grammar (allowed constructs, forbidden constructs, error message format from the Specfuse type-checker).

**Two enforcement surfaces:** Spectral catches authoring-time syntax violations (`specfuse-async-trigger-when-coherence`); Specfuse type-checks against the snapshot at build time (unknown fields, type mismatches, invalid enum literals).

#### `x-envelope-promote` (optional on snapshot field schemas)

Marks a snapshot scalar property that should also be stamped as an envelope ApplicationProperty so subscription filters can target it without inspecting the payload.

```yaml
# In NotificationJobSnapshot.yaml
properties:
  channel:
    type: string
    enum: [email, sms, push]
    x-envelope-promote: true
```

The dispatcher reads the promoted value from the snapshot and stamps `message.ApplicationProperties[channel] = "email"` on the outbound message. Subscribers reference the promoted header via `x-subscription.requiredHeaders` (see §4.3). Total promoted-header bytes per message MUST stay ≤ 1 KB.

#### `x-snapshot-size-acknowledged` (opt-in, on snapshot files only)

Boolean. Waives the soft size warning when a snapshot exceeds the cap (default 25 scalar fields). Records an explicit team decision that the size is intentional.

```yaml
# At the root of TenantSettingsSnapshot.yaml
x-snapshot-size-acknowledged: true
```

#### `x-snapshot-pii-acknowledged` (required on snapshot files that include PII/sensitive fields)

Per-field justification block listing properties whose source entity field carries `x-classification: [pii]` or `[sensitive]` and which the snapshot intentionally retains. Without an entry, the snapshot fails Spectral validation.

```yaml
# At the root of CustomerSnapshot.yaml
x-snapshot-pii-acknowledged:
  email: "invitation worker needs recipient address"
  phone: "SMS notification worker dispatches via the SMS provider"
```

Each entry must carry a justification ≥ 20 chars. The acknowledgement is reviewed at PR time; the justification surfaces in generated audit logs.

### 4.3 Operation Extensions

#### `x-worker` (required on `receive` operations and `run-*` scheduled jobs)

Behavioral contract and runtime configuration for the handler. Language-specific details (class name, namespace, file location) are NOT part of the spec — the generator derives them.

**`x-worker` is required on operations that ARE workers — i.e., operations that the code generator scaffolds as standalone handler classes:**
- `on-*` operations (`action: receive`) — event handlers
- `run-*` operations (`action: send`) — cron-triggered scheduled job dispatchers

**`x-worker` is FORBIDDEN on `emit-*` operations.** An `emit-*` operation is a publishing declaration, not a worker. It declares what message an `on-*` or `run-*` worker publishes. The generator wires the publish call into the owning worker — it does not create a separate class for it.

```yaml
x-worker:
  name: order-enrichment
  idempotent: true
  inboxDedup: true
  concurrency: 5
  timeout: 30s
  settingsPrefix: OE
  tunables:
    - name: enrichment_batch_size
      type: int
      default: 10
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | No | kebab-case string | Overrides the worker identity stem derived from the operation key. Controls folder name, handler class name, worker class name, settings class name, and module/package name. Default: when absent, the stem is derived by stripping the operation prefix (`on-`/`run-`/`emit-`) from the operation key. |
| `idempotent` | No | boolean | Default: `true`. Whether processing the same message twice produces the same outcome. |
| `inboxDedup` | No | boolean | Default: `true`. When `true`, the generated handler base inserts an inbox-claim row keyed on `(eventId, handlerName)` before invoking `HandleCoreAsync`. Set `false` only for handlers with no DB writes and no externally-visible side effects (cache invalidator, metrics emitter). Coherence with `idempotent` and the operation's delivery-trait `guarantee` is enforced by `specfuse-async-worker-inbox-dedup-coherence`. |
| `concurrency` | No | integer | Default: `1`. Max concurrent handler instances. |
| `timeout` | No | string (duration) | Hard execution cap (e.g., `30s`, `5m`). |
| `settingsPrefix` | No | string | Overrides the auto-derived environment-variable prefix for the worker's generated settings class. Default: first letter of each kebab segment of `x-worker.name` (or the derived stem), uppercased (e.g., `order-enrichment` → `OE`). Only set when the auto-derived prefix conflicts with another worker. |
| `tunables` | No | array of objects | Worker-specific configuration fields emitted as typed fields on the generated settings class. Each field becomes an environment-variable-configurable setting prefixed with the worker's env prefix (e.g., `OE_ENRICHMENT_BATCH_SIZE=10`). See schema below. |

**`tunables[]` entry schema:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | snake_case string | Field name on the generated settings class (e.g., `enrichment_batch_size`). |
| `type` | No | string | One of `int`, `float`, `bool`, `str`. Default: `str`. |
| `default` | No | any | Default value. Omit to declare the field as required (no default; must be supplied via environment). |

**When to use `name`:** the operation key describes *what event triggers the worker* (e.g., `on-customer-created`), while `x-worker.name` describes *what the worker does* (e.g., `customer-profile-setup`). Set `name` when the two diverge — for example, when a single trigger event fans out to a worker whose purpose is better expressed by its downstream responsibility.

**When to use `settingsPrefix`:** only when the auto-derived prefix would collide with another worker's prefix (for example, two workers whose kebab-segment initials produce the same acronym). Otherwise leave it unset — the generator's derivation rule keeps prefixes predictable.

**When to use `tunables`:** declare configuration knobs the worker needs at runtime that are not part of the event payload — thresholds, limits, feature toggles, external-service parameters. They appear on the generated settings class and are overridable via environment variables at deploy time.

**What's NOT here and why:**
- `type` — derived from the operation's `action` (`send`/`receive`) and the channel's `x-channel-type`
- `handlerName` — derived from the operation key (or `name` when set) by the generator
- `namespace` — language-specific; derived from `x-domain` using the generator's convention

`name` is NOT a replacement for the forbidden subfields above. It only controls the identity stem; `type`, `handlerName`, and `namespace` remain fully derived by the generator.

#### `x-emits` (on `on-*` receive operations that publish events)

Links a receive operation to the `emit-*` send operations it publishes on completion. Uses the same `{Entity}.{Action}` format as OpenAPI `x-emits`, matching the emitted message's `x-label`.

```yaml
# on-customer-created.yaml (receive operation)
x-emits:
  - event: CustomerProfile.Enriched
    description: Published when AI-driven profile enrichment finishes
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `event` | Yes | string | `{Entity}.{Action}` matching the emitted message's `x-label` |
| `description` | No | string | Brief explanation of when/why this event is published |

**Rules:**
- Required on every `on-*` receive operation that publishes events via `emit-*` send operations
- The generator uses `x-emits` to wire publish calls into the handler class
- The cross-spec validator resolves `x-emits` entries to their matching `emit-*` operations via `x-label` matching
- `run-*` scheduled jobs do NOT use `x-emits` — they publish directly via their channel reference

#### `x-subscription` (required on `receive` operations from `event-topic` channels)

```yaml
x-subscription:
  name: on-order-submitted           # MUST equal the operation file stem
  requiredHeaders:                   # Optional: declarative header equality, AND-merged with the derived label filter
    channel: email
  maxDeliveryCount: 10
  lockDuration: 30s
  requiresSession: false
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | kebab-case string | MUST equal the operation file name minus `.yaml`. Validated by `specfuse-async-subscription-name-mismatch`. |
| `requiredHeaders` | No | object | Declarative envelope-header equality map. Each `(key, value)` becomes `AND user.{key} = '{value}'` in the generated filter. Keys must be camelCase ApplicationProperty names that the universal envelope (`tenantId`, `aggregateType`, `eventId`, etc.) or `x-envelope-promote` declarations actually publish. |
| `filterOverride` | No | string | Raw SQL filter string. Mutually exclusive with `requiredHeaders`. Requires a `description` justification ≥ 40 chars on the operation explaining why derivation is insufficient. |
| `maxDeliveryCount` | No | integer | Max delivery attempts before dead-lettering. Default: `10` |
| `lockDuration` | No | string (duration) | Lock duration during processing. Default: `30s` |
| `requiresSession` | No | boolean | Set to `true` when the referenced message has `x-partition-key`. Default: `false` |

**The legacy authored `filter` field is forbidden.** Filters are derived from the operation's `messages:` list — Spectral rejects any operation declaring `filter` directly.

**Rules:**
- `x-subscription` is required on all `receive` operations from `event-topic` channels
- `x-subscription` is NOT used on scheduled-trigger channels (no transport subscription)
- The subscription name MUST equal the operation's file stem (renaming is the only remediation)
- `requiredHeaders` and `filterOverride` are mutually exclusive

**Three filter modes:**

| Mode | Author writes | Generator emits |
|---|---|---|
| **Derived (default)** | `messages: [E1.Created.yaml, E2.Updated.yaml]` only | `Label = 'E1.Created' OR Label = 'E2.Updated'` |
| **`requiredHeaders`** | `messages:` list + `requiredHeaders: { channel: email }` | `<derived> AND user.channel = 'email'` |
| **`filterOverride`** | Raw SQL + `description` justification | The override verbatim |

**Filter patterns the generator will produce:**

| Subscriber shape | What you write | Resulting filter |
|---|---|---|
| Single-action subscriber | `messages: [OrderSubmitted.yaml]` | `Label = 'Order.Submitted'` |
| Wildcard-all-actions on one entity | `messages: [*.yaml for that entity]` (or `filterOverride: "Label LIKE 'Order.%'"`) | `Label LIKE 'Order.%'` |
| Multi-entity subscriber | `messages:` list spanning entities | `Label LIKE 'Customer.%' OR Label LIKE 'Order.%' OR ...` |
| Tenant-scoped subscriber | `messages:` list + `requiredHeaders: { tenantId: '<guid>' }` | `<derived> AND user.tenantId = '<guid>'` |
| Channel-aware subscriber (uses `x-envelope-promote`) | `messages: [NotificationJobCreated.yaml]` + `requiredHeaders: { channel: email }` | `Label = 'NotificationJob.Created' AND user.channel = 'email'` |

**Multi-entity subscribers compose an OR chain** — there is no shorter form. Keep under the cap in §4.5.

#### `x-observability` (recommended on all async operations)

```yaml
x-observability:
  criticality: high
  sla:
    maxProcessingTime: 5s
    maxAge: 60s
  metrics:
    - orderEnrichmentDuration
  alertOnDlq: true
  tracing: full
```

| Field | Required | Type | Values | Description |
|-------|----------|------|--------|-------------|
| `criticality` | Yes | string | `low`, `medium`, `high`, `critical` | Business impact if this worker fails |
| `sla` | No | object | See below | Processing SLA thresholds |
| `sla.maxProcessingTime` | No | string (duration) | — | Alert if a single message takes longer |
| `sla.maxAge` | No | string (duration) | — | Alert if a message sits in the queue longer than this before pickup |
| `metrics` | No | array | camelCase strings | Custom business metrics to emit |
| `alertOnDlq` | No | boolean | Default: `true` | Whether DLQ arrivals trigger alerts |
| `tracing` | No | string | `full`, `minimal`, `none` | OpenTelemetry span detail. Default: `full` |

**Criticality levels** (standard four-level severity matching alerting infrastructure conventions):

| Level | Meaning | Alerting |
|-------|---------|----------|
| `critical` | System unusable if this worker fails | Page on-call immediately |
| `high` | Core feature degraded | Alert within 5 minutes |
| `medium` | Non-core feature affected | Alert within 30 minutes |
| `low` | Cosmetic or deferrable impact | Daily digest |

The legacy value `normal` (used in early v2 specs) is no longer accepted — migrate to `medium`.

**Relationship with `x-worker.timeout`:** `timeout` is the hard cap (kill the handler); `sla.maxProcessingTime` is the soft warning target. The timeout should always be >= the SLA.

#### `x-ai` (on operations requiring AI/LLM capabilities)

Identifies workers that use AI/LLM functionality. Determines which code generation template is used and what AI infrastructure is wired up.

```yaml
x-ai:
  enabled: true
  task: recommendation
  model: claude-sonnet
  promptTemplate: order/enrich-order
  capabilities:
    - structuredOutput
    - toolUse
  estimatedTokens:
    input: 8000
    output: 3000
  maxLatency: 30s
  fallback: queue
  entities:
    reads: [Order, Customer]
    creates: [OrderRecommendation]
    updates: [Order]
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `enabled` | Yes | boolean | `true` to mark as AI-powered |
| `task` | Yes | string | One of: `generation`, `classification`, `extraction`, `summarization`, `analysis`, `translation`, `validation`, `recommendation` |
| `entities` | When `enabled: true` | object | Declares every entity the worker reads/writes (see below) |
| `model` | No | string | Preferred model (informational) |
| `promptTemplate` | No | string | Path relative to `prompts/` |
| `capabilities` | No | array | One or more of: `structuredOutput`, `toolUse`, `rag`, `vision`, `streaming`, `multiTurn`, `batchProcessing` |
| `estimatedTokens` | No | object | `{input, output}` |
| `maxLatency` | No | string (duration) | Max acceptable latency for the AI call |
| `fallback` | No | string | `skip`, `queue`, `default`. Default: `queue` |

**`entities` field:**

Declares the complete data surface of the AI worker for cross-spec validation and audit. Each entity name must be PascalCase and match a schema with `x-entity` in OpenAPI.

| Sub-field | Type | Description |
|-----------|------|-------------|
| `reads` | string[] | Entities the worker reads for context. Each must have `aiAccess.operations` containing `read`. |
| `creates` | string[] | Entities the worker creates. Each must have `aiAccess.operations` containing `create`. |
| `updates` | string[] | Entities the worker modifies. Each must have `aiAccess.operations` containing `update`. |
| `deletes` | string[] | Entities the worker deletes. Each must have `aiAccess.operations` containing `delete`. |

At least one of the four arrays must be non-empty. The trigger entity (from the incoming message's `x-label.entity`) must appear in at least `reads`. The code generator validates each entity against its `aiAccess` in the OpenAPI spec and fails the build on mismatches.

The code generator uses `x-ai` to decide whether the worker needs AI infrastructure (prompt management, structured-output validation, token budgeting). The target language is chosen by the generator, not the spec.

### 4.4 Delivery Traits

#### `x-delivery` (on operation traits)

Applied via operation traits in `async-common/operation-traits/common.yaml`. Workers reference a trait to pick up delivery guarantees.

```yaml
x-delivery:
  guarantee: atLeastOnce
  maxRetries: 5
  retryBackoff: exponential
  deadLetterOnFailure: true
```

| Field | Required | Type | Values | Description |
|-------|----------|------|--------|-------------|
| `guarantee` | Yes | string | `atLeastOnce`, `atMostOnce`, `exactlyOnce` | Delivery guarantee |
| `maxRetries` | No | integer | — | Default: `3` |
| `retryBackoff` | No | string | `linear`, `exponential` | Retry strategy |
| `deadLetterOnFailure` | No | boolean | — | Default: `true` |

---

### 4.5 Mitigation Rules (Single Shared Topic)

The single shared event topic (§1.5, §3.2) is the system's default. It concentrates routing into the `Label` convention + subscription filters. The following rules guard the corners that concentration would otherwise expose. They are mandatory; each has a specific enforcement surface (handbook, Spectral, cross-spec validator, generator, runtime).

| # | Rule | Enforcement |
|---|------|-------------|
| 1 | Session-ID namespacing | Generator (Specfuse) |
| 2 | Subscription filter entity-pattern cap (≤10) | Spectral + Specfuse |
| 3 | Per-subscription DLQ alerting | Handbook + runtime config |
| 4 | `x-label.entity` ↔ OpenAPI `x-entity` 1:1 | Cross-spec validator (blocking) |
| 5 | Sharding escape hatch documented | Handbook (§3.2) |
| 6 | Scheduled-trigger exemption | Handbook (§0.7, §3.2, §3.3) |
| 7 | Post-bundle reference validation | Bundle step + Specfuse |
| 8 | Telemetry dimension tagging | Generator (Specfuse) |

#### 4.5.1 Session-ID namespacing under `x-partition-key`

Pub-sub transport sessions are scoped to a topic. With every aggregate publishing to the one shared topic, two messages with the same raw partition-key value but different entities (e.g., an `Order` whose `orderId` happens to collide with a `Refund`'s `refundId` — unlikely with UUIDs, guaranteed with any integer-like key) would serialize into the same session and tank throughput.

When a message declares `x-partition-key`, the generator MUST prefix the runtime session ID with `{x-label.entity}:`. For example, a message with `x-label.entity: Order` and `x-partition-key.property: orderId` publishes with:

```
SessionId = "Order:{orderId}"
```

Consumers using `requiresSession: true` see the same prefixed session IDs. Authors do not write the prefix in the spec — it is an artifact of the generator and documented here for contract clarity.

#### 4.5.2 Subscription filter entity-pattern cap

The effective filter on a subscription (derived from the operation's `messages:` list, plus any `requiredHeaders` / `filterOverride`) may reference **at most 10 distinct entity patterns** — counted as distinct `Label = '<Entity>.'` clauses in the derived OR-chain or distinct `LIKE '<Entity>.` prefixes inside a `filterOverride`. More than 10 is a smell: the worker is probably doing too much and should be split along a natural seam. The cap also keeps filters well under the transport's filter-size limit (e.g., 2048 chars on ASB).

Recall that authors do NOT write a raw `filter` field directly (forbidden — see §4.3); the rule operates on the derived filter the generator produces.

Enforced by Spectral rule `asyncapi-subscription-filter-entity-cap` (error severity) and mirrored in the Specfuse validator.

#### 4.5.3 Per-subscription DLQ alerting

Because every topic has only one address (`{project}.events`), topic-level DLQ alerts are meaningless — every failure across every worker would fire the same alert. Alerting MUST be configured per-subscription.

- `x-observability.alertOnDlq: true` (the default) applies to the subscription named on `x-subscription.name`.
- Dashboards and runbooks must key on subscription name, not topic name.
- A DLQ alert for subscription `on-notification-job-dispatch-push` is meaningful; a DLQ alert for topic `{project}.events` is noise.

#### 4.5.4 `x-label.entity` ↔ OpenAPI `x-entity` 1:1 (blocking)

With the `Label` as the only router, entity-name collisions silently misroute messages. The cross-spec validator treats the following as a **blocking error** (not a warning):

- An `x-label.entity` that has zero matching `x-entity` schemas in OpenAPI
- An `x-label.entity` that matches more than one `x-entity` schema (two domains defining the same aggregate name)

This check runs on every validation invocation and fails the build. Renaming is the only remediation; there is no allowlist.

#### 4.5.5 Sharding escape hatch

The single-topic decision is deliberate and reversible. Payload shape, `x-label` format, subscription filter syntax, and operation structure are all transport-agnostic. If operational evidence (throughput, blast-radius isolation, regulatory boundary) justifies splitting, see §3.2 for the migration recipe. Splitting MUST NOT be done preemptively.

#### 4.5.6 Scheduled-trigger exemption

§0.7, §3.2, and §3.3 exempt `scheduled-trigger` channels from the single-topic rule. Cron-triggered channels carry no transport semantics — their address is a logical identifier. Grouping them per domain keeps the file tree ergonomic without changing runtime behavior.

#### 4.5.7 Post-bundle reference validation

In addition to the authoring-time Spectral rule, the bundled AsyncAPI document (output of the project's `bundle-async-spec` step) is re-validated by Specfuse: every `messages: [$ref: ...]` entry on every operation MUST resolve to a message declared in that operation's bound channel's `messages` map. A dangling reference fails the code generation build. This belt-and-suspenders catches the case where Spectral is skipped, misconfigured, or an authored workaround slips past it.

#### 4.5.8 Telemetry dimension tagging

Per-topic observability is useless when everyone shares one topic. The generator MUST tag every publish and receive span with OpenTelemetry attributes derived from the message's `x-label`:

- `event.entity` — the `x-label.entity` value
- `event.action` — the `x-label.action` value

Metrics emitted by the generator (publish count, receive count, handler duration, DLQ rate) MUST carry the same two labels as Prometheus dimensions. Dashboards slice on these dimensions, not on topic name. Projects may apply a custom prefix to the attribute names (e.g., `{project}.event.entity`) via the generator's configuration; the unprefixed form is the default. This is a generator-side contract; authors do not configure it per operation.

---

## 5) Patterns Catalog

### 5.1 Event Notification Pattern

The default pattern. An API operation changes state and emits a domain event. One or more handlers react asynchronously. Each handler does its own work directly — no intermediate dispatch layer.

```
[API] POST /orders/{id}/submit
  └─ emits → Order.Submitted (event-topic)
       ├─ handler 1 → reserves inventory (does the work)
       ├─ handler 2 → sends confirmation notifications
       └─ handler 3 → updates dashboard metrics
```

Each handler is an `on-*` operation with `action: receive` and `x-subscription` on the topic.

**When to use:** whenever an API operation has side effects that can happen asynchronously.

### 5.2 Scheduled Job Fan-Out (Default for All Scheduled Work)

A cron timer triggers a **thin dispatcher**. The dispatcher queries for work items and publishes one event per item. Separate subscribers handle each event independently with their own retry and DLQ.

```
CRON: '0 2 * * 1' (weekly Monday 2 AM)
  └─ triggers → AutoArchiveStaleOrdersJob (thin dispatcher, action: send)
       ├─ queries DB → finds N stale orders
       └─ publishes N × Order.ArchiveRequested (one per order)
            └─ each → subscriber that archives the order (action: receive)
                 ├─ success → order archived (optionally emits Order.Archived)
                 └─ failure → DLQ (isolated, individually retryable)
```

**Scheduled jobs use `action: send`** because they are not receiving messages — they are independently triggered by a cron timer and their primary purpose is publishing events to a topic. The `x-scheduled-job` extension on their message carries the cron expression. Unlike `emit-*` declarations, `run-*` operations ARE workers and require `x-worker`.

**The job handler MUST:**
1. Query the database to identify work items matching its criteria
2. Publish one event per work item to its channel
3. Complete quickly (its timeout should reflect query + publish, not processing)

**The subscriber MUST:**
1. Process exactly one work item per event
2. Be idempotent
3. Have its own retry policy, DLQ, and observability

**Benefits over inline processing:**
- Failure archiving order #47 doesn't block orders #48–#200
- Failed items are individually visible in the DLQ with full context
- Subscribers can run with high concurrency (e.g., `concurrency: 10`)
- Each work item has its own retry cycle and metrics

**When the narrow exception applies:** jobs producing a single output (snapshot, view refresh, aggregate recompute) that have no per-item semantics may do the work directly. When in doubt, default to fan-out and ask.

### 5.3 Event-Carried State Transfer

An event carries enough state for consumers to update their local projections without querying the source service. In v2.1 this is realized via the snapshot model (§2.3): every event carries the appropriate `before`/`after` snapshot for its action class, and consumers compute deltas locally.

```
CustomerUpdated event payload:
  - customerId
  - before: CustomerSnapshot   # entity state before the save
  - after:  CustomerSnapshot   # entity state after the save
```

Consumers compute deltas from `(before, after)` rather than receiving a hand-curated `changedFields` map.

**When to use:** when consumers maintain read models of data from other domains. The snapshot model gives them everything they need without round-trips. Bandwidth is managed via snapshot guardrails (size cap, PII acknowledgement) — see §2.3.

> **Note**: earlier v2 guidance recommended hand-curated payloads with `changedFields`/`currentValues` and explicitly warned against embedding the full aggregate. v2.1 supersedes that policy in favor of snapshots — see §0.9.

### 5.4 Outbox Pattern (Infrastructure)

The outbox pattern ensures reliable event publishing alongside database transactions. This is an **infrastructure concern** not explicitly defined in specs, but the design supports it:

- Event payloads are serializable to JSON
- Each event includes aggregate ID for outbox deduplication
- `x-emits` on OpenAPI operations links events to their source API call, enabling the generator to wire up outbox publishing at the REST layer

---

## 6) Cross-Reference Rules

### 6.1 Reuse OpenAPI Models

**ALWAYS reference existing OpenAPI models** for types shared between sync and async specs. Never duplicate a schema.

```yaml
# CORRECT — reference existing model
status:
  $ref: '../models/OrderStatus.yaml'

# WRONG — duplicated definition
status:
  type: string
  enum: [placed, submitted, fulfilled, cancelled]
```

### 6.2 When to Define New Schemas in Messages

Define a new schema inside a message file ONLY when the payload property is unique to the async context:
- Event envelope properties (`eventId`, `occurredAt`)
- Job configuration parameters (`staleThresholdDays`) — unique to job triggers

Everything else should `$ref` into `domains/{domain}/models/`.

### 6.3 Linking Events via `x-emits`

`x-emits` is used in two contexts to create machine-readable links between event producers and the events they publish:

#### OpenAPI → AsyncAPI (REST write operations)

Every OpenAPI write operation (POST/PUT/PATCH/DELETE) declares `x-emits` with the events it publishes on success:

```yaml
# api/specs/v1/domains/order/operations/submit-order.yaml
post:
  operationId: submitOrder
  x-emits:
    - event: Order.Submitted
      description: Emitted when the order is submitted
```

#### AsyncAPI → AsyncAPI (async receive operations)

Every `on-*` receive operation that publishes events via `emit-*` send operations declares `x-emits` to link them:

```yaml
# api/specs/v1/domains/customer/async-operations/on-customer-created.yaml
x-emits:
  - event: CustomerProfile.Enriched
    description: Published when AI-driven profile enrichment finishes
```

This tells the code generator to wire the publish call for `CustomerProfileEnriched` into the `on-customer-created` handler class.

#### Common rules

The `event` value (`{Entity}.{Action}`) must match an AsyncAPI event message's `x-label` (`{entity}.{action}`).

**The cross-spec validator:**
1. For every `x-emits.event` in OpenAPI, finds the matching AsyncAPI message — fails if missing
2. For every `x-emits.event` on an `on-*` async operation, finds the matching `emit-*` send operation via `x-label` — fails if missing
3. For every AsyncAPI event message, identifies the OpenAPI operations that emit it (reverse lookup) — informational only. Events can also be published by scheduled jobs or other workers, so having no OpenAPI emitter is valid.

**There is no `triggerOperation` field on the AsyncAPI side.** The link is computed from `x-emits`, not duplicated.

**`run-*` scheduled jobs do NOT use `x-emits`** — they publish directly via their channel reference. The generator knows they are publishers from the `action: send` + `x-worker` + `x-scheduled-job` combination.

### 6.4 Aggregate References

Every message's `x-label.entity` MUST correspond to a PascalCase schema with `x-entity` defined in the OpenAPI specs. The validator enforces this link. There is no separate `x-source-aggregate` or `x-target-aggregate` — `x-label.entity` is authoritative.

### 6.5 Shared Enums

Reference enums from `common/enums.yaml` or domain-specific model files:

```yaml
currency:
  $ref: '../../../common/enums.yaml#/CurrencyCode'
```

---

## 7) Code Generation Contract

### 7.1 Generated Artifacts

| Source | Artifact |
|--------|----------|
| Event message | Typed event record/class |
| Scheduled job message | Typed job parameter record/class |
| `on-*` operation (`action: receive`, has `x-worker`) | Event handler skeleton + subscription wiring |
| `run-*` operation (`action: send`, has `x-worker`) | Scheduled worker skeleton + cron registration + publish wiring |
| `emit-*` operation (`action: send`, no `x-worker`) | Publish method wired into the owning `on-*` worker (resolved via `x-emits`) |
| Per-domain | Worker registration (DI wiring) |
| Global | Worker service collection / startup |

### 7.2 What the Generator Derives (Not in the Spec)

- **Handler/class name** — from the operation file name (e.g., `on-order-submitted.yaml` → `OrderSubmittedHandler` in C#, equivalent in other languages)
- **Namespace / package** — from `x-domain` plus the target language's convention
- **Worker type classification** — from verb prefix, `action`, and `x-worker` presence:
  - `on-*` (`action: receive`, has `x-worker`) → event subscriber worker
  - `run-*` (`action: send`, has `x-worker`, message has `x-scheduled-job`) → scheduled job worker
  - `emit-*` (`action: send`, no `x-worker`) → publish method wired into the owning worker
- **Linking `emit-*` to its owning worker** — the generator resolves `x-emits` on `on-*` operations to find which `emit-*` declarations belong to which worker. For `run-*` operations, the publish target is the channel referenced directly on the operation.
- **Project layout** — decided by the generator config per language

### 7.3 Cross-Spec Wiring

- Every OpenAPI write operation with `x-emits` → publish call generated at the end of the REST handler (outbox-compatible)
- Every `on-*` async operation with `x-emits` → publish call wired into the handler class (resolved via matching `emit-*` operations)
- Every `run-*` async operation → publish call wired directly from the channel reference
- Every AsyncAPI event message → subscribe binding in the worker project
- The `x-label` drives the message-bus Label at send time and the subscription filter at receive time

### 7.4 Project Configuration

The Workers group in the project's generator configuration file (a JSON file at the project root, consumed by the Specfuse generator) specifies the target language and output directory. The spec itself remains language-agnostic.

---

## 8) Do NOT

1. **Do NOT duplicate OpenAPI models.** If a type exists in `models/`, use `$ref`. Never copy enum values, value objects, or entity schemas into message files.

2. **Do NOT use `publish`/`subscribe` terminology.** AsyncAPI 3.0 uses `send` and `receive` via the `action` property. The old terms are from AsyncAPI 2.x.

3. **Do NOT put multiple unrelated message types on one channel.** A channel should carry messages from the same aggregate or bounded context (with the documented exception of the shared event topic — see §3.2).

4. **Do NOT embed raw entity types in event payloads.** Use snapshots (`$ref` to `events/{Entity}Snapshot.yaml`). Snapshots include scalar columns and owned value objects only — never navigation properties or child collections. See §2.3.

5. **Do NOT define inline objects or enums in message payloads.** Same rule as OpenAPI: use `$ref` to separate schema files.

6. **Do NOT define path variables or parameters as global components.** Channel parameters, if any, are defined inline on the channel.

7. **Do NOT mix sync (REST) and async (worker) operations in the same file.** REST operations go in `operations/`, async operations go in `async-operations/`.

8. **Do NOT create a message without a corresponding async operation.** Every message must be consumed by at least one `receive` operation (or produced by a `send` operation).

9. **Do NOT introduce commands, sagas, point-to-point queues, or other patterns outside the v2 architecture** without explicit user approval. See Rule 1.4.

10. **Do NOT declare any of these removed extensions:**
    - `x-source-aggregate`, `x-target-aggregate` (use `x-label.entity`)
    - `x-event` (derived from `x-message-category` + `x-label` + OpenAPI `x-emits`)
    - `x-command`, `x-target-aggregate` (commands removed)
    - `x-saga` (sagas removed)
    - `x-dispatches` (replaced by native `send` operations)
    - `x-worker.type`, `x-worker.handlerName`, `x-worker.namespace` (derived by generator)

11. **Do NOT put language-specific fields in specs** (class names, namespaces, package paths, file paths). The code generator owns all language decisions.

12. **Do NOT make breaking changes within the same `x-version.current`** — bump the version and keep the old one alive until all consumers migrate.

13. **Do NOT have scheduled jobs do heavy work directly.** They must be thin fan-out dispatchers (Rule 1.3). The narrow exception (single-output jobs with no per-item semantics) must be obvious from context; when in doubt, ask.

14. **Do NOT split events across multiple topics.** The single shared event topic `{project}.events` is deliberate (see §1.5 and §3.2). Do not introduce per-domain or per-aggregate event topics as a convenience. The sharding escape hatch exists but requires explicit approval per Rule 1.4 and concrete operational evidence, not stylistic preference.

15. **Do NOT author raw `x-subscription.filter` strings.** Filters are derived from the operation's `messages:` list. Use `x-subscription.requiredHeaders` for declarative header equality (e.g., tenant scoping, channel filtering). Use `x-subscription.filterOverride` only as a justified escape hatch with a `description` ≥ 40 chars explaining why derivation is insufficient. See §4.3.

16. **Do NOT include a three-segment `Label` (`{Entity}.{Action}.{tenantId}`).** Labels are exactly two segments — tenancy lives in envelope ApplicationProperties. AND-merge `user.tenantId = '<guid>'` via `requiredHeaders` for tenant-scoped subscribers. See §0.8.

17. **Do NOT declare `x-trigger-when` on `*Created`/`*Updated`/`*Deleted` events.** It is required only on state-transition events (anything else). See §2.2.

18. **Do NOT declare `x-action-class`.** Action class is inferred from the message-name suffix. See `Vendor_Extensions.md §12.5`.

    **DO declare `x-trigger-mode: explicit` when (and only when) the payload carries a `context` field.** It is REQUIRED there — the message also needs a `description` ≥ 40 chars on the `context` property AND an `x-method-name` (PascalCase imperative verb for the generated service method, e.g. `CancelOrder`; generator-enforced via `MISSING_METHOD_NAME`). Enforced by Spectral `specfuse-async-context-coherence` and the generator's AsyncAPI validator. `explicit` makes the generator emit a typed service method and suppress the auto-dispatcher. Omit `x-trigger-mode` on messages with no `context` (defaults to `auto`). Valid values: `auto | explicit`.

19. **Do NOT use the legacy `criticality: normal` value on `x-observability`.** The four-level enum is `low | medium | high | critical`. Migrate `normal` → `medium`.

20. **Do NOT use the per-field `x-pii: true` / `x-sensitive: true` flags.** Use `x-classification: [pii | sensitive | encrypted | exposed]` on the entity property schema instead. See `Vendor_Extensions.md §1.5`.

---

## 9) Flow Documentation

Every domain with async specifications SHOULD have corresponding flow documentation. Flow docs are the primary resource for product managers and developers to understand how the system works end-to-end.

**Rules:**
- When adding or modifying async specs, the corresponding flow doc should be created or updated
- Each flow doc covers one end-to-end process (trigger → final outcome)
- Flow docs use Mermaid sequence diagrams for visual clarity
- The `/specfuse-authoring:design-async` skill (from the `specfuse-authoring` plugin) enforces flow doc creation as part of the design process

Project-specific location and template are decided by the project — typical layout is `api/docs/flows/{domain}/`.

---

## 10) Future Phases

The v2 model covers current needs. The following are explicitly **not** part of v2 but may be reintroduced if concrete use cases emerge. Each requires a design discussion and handbook update before use.

### 10.1 Commands / Point-to-Point Messaging
Reintroduced only if a scenario genuinely requires single-consumer semantics or request/reply that pub-sub can't express. Until then, every message is an event.

### 10.2 Sagas and Multi-Step Orchestration
Multi-step distributed workflows with compensation logic (`x-saga`, saga channels, saga step messages). Not currently needed — current flows are simple pub-sub chains.

### 10.3 Dead-Letter Queue Handling
Standardized DLQ processing: operations that consume dead-lettered messages, automated retry/replay, manual review queue, DLQ monitoring dashboards.

### 10.4 Resilience Patterns
Circuit breakers, bulkhead isolation, per-dependency fallback strategies beyond `x-ai.fallback`.
