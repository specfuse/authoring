# Arazzo Handbook

> **Version:** 1.0.0
> **Spec Format:** Arazzo 1.0.1
> **Status:** Authoritative -- all Arazzo specifications in a Specfuse project MUST comply with this handbook.

This handbook defines the rules, conventions, and patterns for authoring Arazzo scenario and recipe specifications in a Specfuse project. It is the behavioral counterpart to the [API Handbook](./API_Handbook.md) (REST) and the [AsyncAPI Handbook](./AsyncAPI_Handbook.md) (async workers). Together, the three handbooks form Specfuse's spec-first architecture.

Arazzo scenarios and recipes are **machine-readable behavioral specifications**. They describe multi-step API workflows -- what actors do, in what order, with what assertions -- and are consumed by documentation generators, test generators, UI automation, and the Specfuse orchestrator.

---

## Table of Contents

1. [Purpose and Relationship to OpenAPI/AsyncAPI](#1-purpose-and-relationship-to-openapiasyncapi)
2. [Granularity Rule](#2-granularity-rule)
3. [File Organization](#3-file-organization)
4. [Workflow-Level Extensions](#4-workflow-level-extensions)
5. [Step-Level Extensions](#5-step-level-extensions)
6. [Async Step Modeling](#6-async-step-modeling)
7. [Setup Recipes](#7-setup-recipes)
8. [Expression Reference](#8-expression-reference)
9. [Cross-Spec Source-of-Truth Rule](#9-cross-spec-source-of-truth-rule)
10. [Versioning and Deprecation](#10-versioning-and-deprecation)
11. [MCP Exposure](#11-mcp-exposure)
12. [Canonical Examples](#12-canonical-examples)
13. [Do / Do NOT](#13-do--do-not)
14. [Authoring Path](#14-authoring-path)
15. [Testing Pyramid Position and CI Integration](#15-testing-pyramid-position-and-ci-integration)
16. [Specfuse Contract](#16-specfuse-contract)

---

## 1) Purpose and Relationship to OpenAPI/AsyncAPI

### 1.1 The Three Pillars

A Specfuse project's spec-first architecture rests on three pillars:

| Pillar | Spec Format | Describes | Source of Truth For |
|--------|------------|-----------|---------------------|
| REST API | OpenAPI 3.0.3 | Endpoints, schemas, authorization | What the API accepts and returns |
| Async Workers | AsyncAPI 3.0.0 | Events, scheduled jobs, channels | What happens asynchronously |
| Behavioral Scenarios | Arazzo 1.0.1 | Multi-step workflows, actor interactions | How the system is used end-to-end |

OpenAPI and AsyncAPI are **canonical** -- they define the structural contracts. Arazzo is the **behavioral layer** -- it describes how those contracts compose into real use cases. Arazzo never invents operations, schemas, or events that don't exist in the other two pillars.

### 1.2 What Arazzo Replaces

Arazzo replaces procedural Mermaid-based flow documentation. Conceptual content (domain overviews, aggregate maps, state machines) is retained in hand-authored `overview.md` files per domain. Generated scenario documentation lives alongside them in `scenarios/`.

### 1.3 What Arazzo Drives

- **Documentation generation** -- Mermaid sequence diagrams, step-by-step guides, tutorial prose
- **Integration test generation** -- executable tests against a disposable tenant
- **UI test generation** -- Playwright regression and LLM-driven exploratory tests
- **MCP tool exposure** -- scenarios exposed as callable tools for AI orchestrators
- **Specfuse task planning** -- scenario decomposition for the orchestrator

### 1.4 Arazzo 1.0.1 Native Concepts Used

Arazzo natively provides:

- **`sourceDescriptions`** -- references to the OpenAPI spec(s) that define the operations used in workflows
- **`workflows`** -- ordered sequences of steps with inputs, outputs, and control flow
- **Steps** -- individual API calls (`operationId`) or sub-workflow invocations (`workflowId`)
- **`successCriteria`** -- assertions on step responses (all must pass; AND logic)
- **`onSuccess` / `onFailure`** -- control flow actions (`end`, `goto`, `retry`)
- **`components`** -- reusable parameters, inputs, success/failure actions
- **Runtime expressions** -- `$inputs`, `$steps.<id>.outputs`, `$response.body`, `$statusCode`, etc.
- **`tags`** -- free-form workflow tags for categorization

Specfuse extends these with vendor extensions (`x-*`) documented in Sections 4-11.

---

## 2) Granularity Rule

Getting the right granularity -- not too coarse, not too fine -- is critical. The wrong granularity produces either monolithic mega-scenarios that are hard to maintain or an explosion of trivially different micro-scenarios.

### 2.1 The Core Principle

**One file = one use case.** A use case is a business-meaningful interaction with a clear trigger, a clear outcome, and a coherent actor set.

Within a file:
- **Multiple workflows** model step-sequence or actor-set variants of the same use case (e.g., "agent approves refund" vs. "agent rejects refund")
- **Input parameters** model data-only variants (e.g., different order priorities, different item counts)

### 2.2 The Mermaid Diagram Test

> **If two scenarios would produce the same Mermaid sequence diagram (same actors, same steps in the same order, same decision points), they should be one scenario with input parameters for data variation.**

Conversely, if two scenarios produce meaningfully different diagrams (different steps, different actors, different branching), they belong in separate files.

### 2.3 Mechanical Overlap Floor (Spectral-Enforced)

The Spectral rule `arazzo-scenario-step-overlap` enforces a mechanical floor:

| Overlap (Jaccard on ordered operationId sequence) | Action |
|---|---|
| < 60% | Fine -- clearly distinct scenarios |
| 60-80% | Surfaced by the `scenario-reviewer` sub-agent for human sign-off |
| >= 80% | **Spectral error** -- must be consolidated or consciously overridden |

The >= 80% threshold forces a conscious decision: "yes, this really needs to be a separate scenario." The reviewer agent handles the ambiguous 60-80% zone.

### 2.4 Examples

**Correct granularity:**
- `request-refund.arazzo.yaml` -- one use case (refund request) with workflows for the happy path, rejection, and cancellation
- `submit-order.arazzo.yaml` -- one use case (order submission) with input parameters for different order sizes

**Too coarse:**
- `all-order-operations.arazzo.yaml` -- combines unrelated use cases (placing, refunding, archiving) into one file

**Too fine:**
- `submit-order-with-priority.arazzo.yaml` and `submit-order-standard.arazzo.yaml` -- data variants that produce identical Mermaid diagrams; should be one scenario with a `priority` input parameter

---

## 3) File Organization

### 3.1 Directory Structure

```
api/specs/v3/
├── openapi.yaml
├── asyncapi.yaml
├── domains/
│   └── {domain}/
│       ├── models/                          # Shared with OpenAPI (never duplicate)
│       ├── operations/                      # REST operations
│       ├── channels/                        # AsyncAPI channels
│       ├── async-operations/                # AsyncAPI operations
│       ├── messages/                        # AsyncAPI messages
│       └── scenarios/                       # Arazzo scenarios
│           └── *.arazzo.yaml
└── scenarios/                               # Cross-cutting scenarios
    ├── cross-domain/
    │   └── *.arazzo.yaml
    └── setup-recipes/
        ├── foundational/
        │   ├── minimal-tenant.recipe.yaml
        │   ├── minimal-customer.recipe.yaml
        │   └── basic-orders.recipe.yaml
        └── domain-specific/
            └── {domain}/
                └── *.recipe.yaml
```

Domain folder names follow the project's domain naming convention (kebab-case, one folder per bounded context). The active domain list is defined by the project (typically in `.specfuse/project.yaml` or an equivalent overlay).

### 3.2 File Naming

| File Type | Location | Convention | Example |
|-----------|----------|------------|---------|
| Domain scenario | `domains/{domain}/scenarios/` | kebab-case + `.arazzo.yaml` | `request-refund.arazzo.yaml` |
| Cross-domain scenario | `scenarios/cross-domain/` | kebab-case + `.arazzo.yaml` | `onboard-customer-full-flow.arazzo.yaml` |
| Foundational recipe | `scenarios/setup-recipes/foundational/` | kebab-case + `.recipe.yaml` | `minimal-tenant.recipe.yaml` |
| Domain-specific recipe | `scenarios/setup-recipes/domain-specific/{domain}/` | kebab-case + `.recipe.yaml` | `submitted-order.recipe.yaml` |

### 3.3 File-Level Homogeneity Rule

**All workflows in a single file must share the same category** -- either all recipes or all scenarios. A file is either 100% recipes or 100% scenarios. Mixing is a validator error.

**Rationale:** file purpose is obvious from its path (`scenarios/` vs `setup-recipes/`), and tooling can classify files without parsing workflow contents.

**Discriminator:** the presence of `x-recipe` on a workflow marks it as a recipe; absence marks it as a scenario. There is no separate `x-category` field.

---

## 4) Workflow-Level Extensions

Every Arazzo workflow in a Specfuse project carries a set of vendor extensions that provide taxonomy, documentation, actor binding, and lifecycle metadata. This section is the authoritative schema reference.

### 4.1 Root Document Structure

```yaml
arazzo: "1.0.1"
info:
  title: "Request refund for an order"
  version: "1.0.0"

sourceDescriptions:
  - name: apiSpec
    url: ../../../openapi.yaml
    type: openapi

x-version:
  current: 1
  status: draft

x-domain: order

tags:
  - critical-path
  - order-management

x-doc:
  summary: "A customer requests a refund for a completed order. A support agent reviews the request and approves or rejects it; the customer is notified at each step."
  personas: [customer, support-agent]
  businessOutcome: "Reduces friction in refund handling and provides a documented audit trail."

x-mcp:
  exposed: false

x-actors:
  customer:
    role: Customer
    description: "The customer who placed the original order"
    ref: $setup.outputs.customerId
  agent:
    role: SupportAgent
    description: "The support agent who reviews the refund request"
    ref: $setup.outputs.agentId

x-setup:
  recipe: completed-order-with-customer
  inputs:
    orderPlacedDate: "@today-7d"

workflows:
  - workflowId: happy-path
    # ... steps
```

### 4.2 `x-version` (required on all workflows)

Lifecycle and status metadata. Unified shape shared across all three spec pillars (OpenAPI, AsyncAPI, Arazzo). There is no separate `x-deprecated` extension -- deprecation metadata lives inside `x-version`.

```yaml
x-version:
  current: 1
  status: stable
```

| Field | Required | Type | Values | Description |
|-------|----------|------|--------|-------------|
| `current` | Yes | integer | >= 1 | Schema version number |
| `status` | Yes | string | `draft`, `stable`, `deprecated` | Lifecycle status |
| `deprecatedAt` | When deprecated | string | ISO date | When this version was deprecated |
| `replacedBy` | When deprecated | string | — | Successor scenario/recipe file name |
| `removalDate` | No | string | ISO date | Target date for removing the deprecated version |

**Deprecation example:**

```yaml
x-version:
  current: 1
  status: deprecated
  deprecatedAt: "2026-06-01"
  replacedBy: request-refund-v2
  removalDate: "2026-12-01"
```

### 4.3 `x-domain` (required on all workflows)

Identifies the owning domain. Must be a kebab-case domain name drawn from the project's active domain list, or the reserved value `cross-domain`.

```yaml
x-domain: order
```

**Conventions:**
- Domain names are kebab-case, one domain per bounded context.
- The project defines its domain list in an overlay file (typically `.specfuse/project.yaml`); the validator loads that list at lint time.
- The reserved value `cross-domain` is only valid for files under `scenarios/cross-domain/`. The validator enforces this constraint.

### 4.4 `tags` (optional, native Arazzo)

Free-form tags for categorization. Uses the native Arazzo `tags` array -- there is no parallel `x-tags` extension.

```yaml
tags:
  - critical-path
  - order-management
```

**Rationale:** Arazzo already defines `tags` on workflows; a parallel `x-tags` would duplicate the concept.

The `critical-path` tag has special meaning: scenarios tagged `critical-path` run as blocking checks on PRs in CI (see Section 15).

### 4.5 `x-doc` (optional)

Documentation metadata consumed by the doc generator and tutorial renderer.

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

`x-doc` is also valid at the step level (see Section 5.4).

### 4.6 `x-actors` (required on scenario workflows, forbidden on recipes)

Declares the actors who perform steps in the scenario. Each actor is bound to a role from the project's closed role set and optionally to an entity seeded by a setup recipe.

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
| `.role` | Yes | string | Role from the project's closed role set (see below) |
| `.description` | No | string | Human-readable description |
| `.ref` | No | expression | Binds the actor to a recipe-seeded entity via `$setup.outputs.X` |

**Role enum (project-defined, closed set):**

The role values are project-specific. The project defines its role enum in its OpenAPI `x-roles` extension (see the API Handbook), and the Arazzo validator enforces that every `x-actors.*.role` is a member of that set. The illustrative roles used throughout this handbook (`Customer`, `SupportAgent`, `SupportManager`, `Admin`, `Authenticated`) are examples only -- replace them with your project's actual role values.

**Recommended convention:** projects that distinguish pre-business-role flows (e.g., self-service signup, invitation acceptance, where the user has a valid auth token but no assigned role yet) should include an `Authenticated` role for that case.

**Why recipes don't have `x-actors`:** recipes execute as an implicit `$system` actor mapped to the project's highest-privileged role (typically `Admin`), which has broad enough permissions to create any fixture the API permits. Scenarios authenticate their own actors against recipe-seeded entities via `x-actors.<name>.ref: $setup.outputs.X`. This is the only coupling between recipe execution identity and scenario execution identity.

**Scheduled-job (system-initiated) scenarios:** Cron-triggered scenarios have no human actor that initiates the workflow -- the job runs as the system. These scenarios still require `x-actors`, but the actor serves as an **observer** who verifies the outcome after the job runs, not as an initiator. Use a role with sufficient read access to inspect results. Apply `x-as: $observer` on the verification steps.

Arazzo has no native concept of "trigger a cron job" -- every step must reference an OpenAPI `operationId`. Scheduled-job scenarios model **observable outcomes**, not job triggers:

1. Create preconditions that will be acted upon by the job (e.g., a stale draft entity)
2. Use `x-async.await` to observe the event the job publishes
3. Use `x-async.poll` to verify the final REST state
4. The test runtime is responsible for triggering the job between setup and observation steps

### 4.7 `x-setup` (optional on scenario workflows, forbidden on recipes)

Declares which setup recipe must run before this scenario to provision the required test fixtures.

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
| `inputs` | No | object | Values passed to the recipe's workflow `inputs`. Supports date tokens (see Section 8.3). |

The recipe's `outputs` become available in the scenario via the `$setup.outputs.X` expression root.

### 4.8 `x-mcp` (optional on scenario workflows)

Declares whether this scenario is exposed as an MCP tool for AI orchestrators.

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
| `exposed` | Yes | boolean | Explicit opt-in. Default: `false` |
| `toolName` | When exposed | string | kebab-case tool name, **globally unique** across all scenarios in the repo |
| `description` | When exposed | string | MCP-facing description of what the tool does |
| `requiresActorAuth` | No | boolean | Whether the tool requires actor authentication context. Default: `true` |
| `safeForAutoInvoke` | No | boolean | Whether an AI agent can invoke this without human confirmation. Default: `false` |

**Inputs and outputs are derived** from the workflow's `inputs` and `outputs` -- they are not redeclared in `x-mcp`.

**Global uniqueness of `toolName`** is enforced by a Spectral rule from Phase 0 onward. This prevents conflict accumulation while the MCP runtime consumer (Phase 7) is still deferred.

---

## 5) Step-Level Extensions

Steps in Arazzo workflows use `operationId` to reference real OpenAPI operations. Specfuse extends steps with actor binding, async assertions, UI automation hints, and documentation metadata.

### 5.1 `x-as` (required on all scenario steps)

Identifies which actor performs this step. The value must reference an actor defined in `x-actors`.

```yaml
steps:
  - stepId: create-refund-request
    x-as: $customer
    operationId: requestRefund
    requestBody:
      payload:
        orderId: $setup.outputs.orderId
        reason: "Item arrived damaged"
    successCriteria:
      - condition: $statusCode == 201
    outputs:
      refundId: $response.body#/id
```

The `$` prefix is conventional (mirrors the expression syntax) but the validator resolves the actor key from `x-actors`. For example, `$customer` resolves to the actor defined at `x-actors.customer`.

**Recipes do not use `x-as`** -- recipe steps execute as the implicit `$system` actor.

### 5.2 `x-async` (on steps involving asynchronous behavior)

Models event-driven interactions within a scenario step. See Section 6 for the full reference.

### 5.3 `x-ui` (optional, on steps with user-facing interactions)

Provides UI automation hints consumed by the LLM-driven exploratory runner and the Playwright test generator. Each step may declare the user-facing actions, expected visual outcomes, and optional Playwright selectors.

```yaml
steps:
  - stepId: create-refund-request
    x-as: $customer
    operationId: requestRefund
    x-ui:
      platform: web
      page: /orders/history
      actions:
        - id: open-order
          text: "Click the order from last week"
        - id: open-refund-dialog
          text: "Click 'Request refund' button"
        - id: select-reason
          text: "Select 'Item arrived damaged' from the reason dropdown"
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
| `platform` | No | string | `web`, `mobile`, `any`. Default: `any` |
| `page` | No | string | The page/route where this step takes place |
| `actions` | Yes | array | Ordered list of user-facing actions |
| `actions[].id` | Yes | string | Stable identifier for this action (kebab-case) |
| `actions[].text` | Yes | string | Natural-language description for LLM agent and tutorial prose |
| `expect` | No | string[] | Expected visual outcomes after the step completes |
| `selectors` | No | array | Optional Playwright selector hints |
| `selectors[].for` | Yes | string | Must reference an existing `actions[].id` in the same step |
| `selectors[].playwright` | Yes | string | Playwright selector string |
| `captureScreenshot` | No | boolean | Whether to capture a screenshot after this step. Default: `false` |

**Binding rule:** every `selectors[].for` value MUST match an `actions[].id` in the same step. Dangling selector references are a Spectral error. This makes selectors rename-safe and validator-enforceable.

**Two-mode consumption:**
- **LLM-driven mode** reads `actions[].text` and `expect` as natural-language instructions
- **Playwright mode** reads `selectors[].playwright` as concrete element locators; falls back to LLM-derived selectors when a selector is not provided for an action

### 5.4 `x-doc` (optional, at step level)

Step-level documentation metadata for tutorial generation.

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

### 5.5 Failure Handling: `failureActions` vs `onFailure`

Arazzo provides two complementary failure-handling mechanisms at different scopes. Both are native Arazzo concepts (not vendor extensions).

**`failureActions`** (workflow-level): a list of failure actions that apply as **defaults to all steps** in the workflow. Useful for workflow-wide policies like "end on any failure."

**`onFailure`** (step-level): an array of failure actions that apply to a **single step**. Overrides workflow-level actions by name.

#### Precedence

1. Step-level `onFailure` **overrides** same-named actions from the workflow-level `failureActions`. A step-level action with the same `name` replaces the workflow-level behavior for that step only.
2. A step **cannot remove** a workflow-level failure action -- only override it.
3. Steps without `onFailure` inherit all workflow-level `failureActions`.
4. When neither is defined, the default behavior on step failure is to **end the workflow and return**.

#### Action types

| Type | Behavior |
|------|----------|
| `end` | The workflow ends and returns applicable outputs to the caller |
| `retry` | The current step is retried, constrained by `retryAfter` and `retryLimit` |
| `goto` | One-way transfer of control to a `workflowId` or `stepId` |

#### When to use each

- **`failureActions` only** -- when all steps share the same failure behavior. Avoids repetition.
- **`onFailure` only** -- when only one or two steps need failure handling (e.g., negative tests). Keeps the intent local to the step.
- **Both** -- when most steps share a default but specific steps need overrides. The workflow sets the baseline; steps override by name.

#### Example: negative-test step with step-level `onFailure`

```yaml
# This step is EXPECTED to fail (testing validation error).
# Step-level onFailure handles the expected failure; no workflow-level
# failureActions needed since the failure is local to this step.
- stepId: submit-empty-order
  x-as: $customer
  operationId: submitOrder
  parameters:
    - name: orderId
      in: path
      value: $steps.create-empty-order.outputs.emptyOrderId
  successCriteria:
    - condition: $statusCode == 400
  onFailure:
    - name: unexpected-success
      type: end
      criteria:
        - condition: $statusCode == 200
```

#### Example: workflow default with step-level override

```yaml
workflows:
  - workflowId: multi-step-with-default-failure
    summary: "Most steps end on failure; one step retries"

    # Default: any unhandled step failure ends the workflow
    failureActions:
      - name: end-on-failure
        type: end

    steps:
      - stepId: create-resource
        x-as: $agent
        operationId: createCustomer
        # ... (no onFailure -- inherits workflow default: end on failure)

      - stepId: call-flaky-service
        x-as: $agent
        operationId: syncExternalReference
        # Override the workflow default for this step: retry instead of ending
        onFailure:
          - name: end-on-failure
            type: retry
            retryAfter: 2
            retryLimit: 3

      - stepId: verify-result
        x-as: $agent
        operationId: getCustomer
        # ... (no onFailure -- inherits workflow default: end on failure)
```

---

## 6) Async Step Modeling

Arazzo 1.0.1 natively supports REST API calls but has no built-in async/event primitives. Specfuse bridges this gap with `x-async`, which provides three verbs for modeling event-driven behavior within scenario steps.

### 6.1 Event Identity

Events are identified by `{Entity}.{Action}` format (both segments PascalCase), matching the `x-label` convention in the AsyncAPI specs. For example, `Order.Placed` resolves to the AsyncAPI message with `x-label: { entity: Order, action: Placed }`.

**Channel derivation:** authors never write channel addresses in Arazzo files. The validator derives the channel from the resolved message using the project's channel naming convention (defined in the AsyncAPI handbook -- typically `{project}.events` for event messages and `{project}.{domain}.jobs` for scheduled-job messages).

### 6.2 The Three Verbs

#### `emit` -- Assert that the step publishes event(s)

The step triggers an API call that publishes events. The validator asserts that the declared events were observed on the message bus.

```yaml
steps:
  - stepId: create-refund-request
    x-as: $customer
    operationId: requestRefund
    requestBody:
      payload:
        orderId: $setup.outputs.orderId
        reason: "Item arrived damaged"
    successCriteria:
      - condition: $statusCode == 201
    outputs:
      refundId: $response.body#/id
    x-async:
      emit:
        - event: Refund.Requested
          expect:
            customerId: $setup.outputs.customerId
          timeout: PT10S
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `emit` | — | array | One or more events the step is expected to publish |
| `emit[].event` | Yes | string | `{Entity}.{Action}` matching an AsyncAPI message's `x-label` |
| `emit[].expect` | No | object | Partial payload match -- key/value pairs to assert on the event payload |
| `emit[].timeout` | No | string | ISO 8601 duration. Max wait time for the event to appear. Default: `PT10S` |

#### `await` -- Passively wait for an event

The step waits for an asynchronous event matching specified criteria. Typically used after a step triggers an async workflow (e.g., an AI worker) and the scenario needs to observe the outcome.

```yaml
steps:
  - stepId: wait-for-profile-enrichment
    x-as: $agent
    x-async:
      await:
        event: CustomerProfile.Enriched
        match:
          customerId: $steps.create-customer.outputs.customerId
        timeout: PT60S
        outputs:
          enrichmentStatus: $message.payload.status
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `await` | — | object | Wait for a single event |
| `await.event` | Yes | string | `{Entity}.{Action}` |
| `await.match` | No | object | Key/value pairs the event payload must match. Values may use expressions. |
| `await.timeout` | Yes | string | ISO 8601 duration. Max wait time. |
| `await.outputs` | No | object | Named outputs extracted from the matched event. Values use `$message.*` expressions. |

Note: `await` steps do not declare `operationId` -- they are purely event-driven. They still require `x-as` and `stepId`.

#### `poll` -- Poll a REST endpoint until a condition is met

The step repeatedly calls a REST endpoint until a success condition evaluates to true or the timeout expires. Useful when the system has no observable event for a state change, or when asserting final REST state is more meaningful than intercepting an event.

```yaml
steps:
  - stepId: poll-refund-status
    x-as: $customer
    x-async:
      poll:
        operationId: getRefund
        parameters:
          refundId: $steps.create-refund-request.outputs.refundId
        until: $response.body#/status == 'validated'
        interval: PT2S
        timeout: PT30S
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `poll` | — | object | Poll a REST endpoint |
| `poll.operationId` | Yes | string | The OpenAPI operation to call repeatedly |
| `poll.parameters` | No | object | Parameters for each poll request |
| `poll.until` | Yes | string | Arazzo simple condition that must evaluate to true for polling to stop |
| `poll.interval` | No | string | ISO 8601 duration between poll attempts. Default: `PT2S` |
| `poll.timeout` | Yes | string | ISO 8601 duration. Max total polling time. |

**Limitation -- same-status transitions:** The `until` condition works best when the observable change is a status field transition (e.g., `draft` → `submitted`). When async processing leaves the status unchanged (e.g., a draft entity is regenerated but stays `draft`), the `until` condition is trivially true from the first poll. In these cases, pair `poll` with a preceding `await` to ensure the async processing has completed before polling, or accept the poll as a "wait then verify" step and document the limitation with `x-doc.tutorialNote`.

### 6.3 Combining Verbs

A single step may combine `emit` with either `await` or `poll` when the step both triggers an event and waits for a downstream outcome. However, `await` and `poll` are mutually exclusive within the same `x-async` block.

```yaml
steps:
  - stepId: submit-order
    x-as: $customer
    operationId: submitOrder
    successCriteria:
      - condition: $statusCode == 200
    x-async:
      emit:
        - event: Order.Submitted
          timeout: PT10S
      await:
        event: Order.Validated
        match:
          orderId: $steps.submit-order.outputs.orderId
        timeout: PT60S
```

### 6.4 AI Worker Observability

AI-driven workers (those with `x-ai: { enabled: true }` in AsyncAPI) are **opaque to step-level introspection** but **fully observable via outcomes**.

**Never assert (opaque internals):**
- Prompt content, model choice, token counts
- Intermediate reasoning or internal tool calls
- Worker execution timing details

**Must assert for critical-path AI flows (observable outcomes):**
- The terminal event the worker emits (via `x-async.await`)
- The resulting REST resource state (via `x-async.poll`)

```yaml
# Correct: assert the AI worker's observable outcome
steps:
  - stepId: wait-for-ai-enrichment
    x-as: $agent
    x-async:
      await:
        event: CustomerProfile.Enriched
        match:
          customerId: $steps.create-customer.outputs.customerId
        timeout: PT120S
        outputs:
          recommendationsCount: $message.payload.recommendationsCount

  - stepId: verify-enrichment-result
    x-as: $agent
    operationId: getCustomer
    parameters:
      customerId: $steps.create-customer.outputs.customerId
    successCriteria:
      - condition: $response.body#/enrichmentStatus == 'completed'
```

**Rationale:** treating AI workers as black boxes for internals while anchoring on observable results gives deterministic regression coverage without binding the test suite to prompt or model specifics.

### 6.5 Arazzo 1.1.0 Migration Path

When Arazzo 1.1.0 ships with native AsyncAPI support, the migration is mechanical:

| Current (1.0.1 via `x-async`) | Future (1.1.0 native) |
|---|---|
| `x-async.emit` | Native `channel` + `action: send` |
| `x-async.await` | Native `channel` + `action: receive` |
| `x-async.poll` | Stays (REST polling, not native async) |

The Specfuse parser will support both extension-based (1.0.1) and native (1.1.0) syntax in parallel during the transition. Because `x-async` is nested and self-contained (not scattered across the file), the codemod is mechanical.

---

## 7) Setup Recipes

Recipes are Arazzo workflows that provision test fixtures using real OpenAPI operations. They are infrastructure -- not business scenarios.

### 7.1 Discriminator

The presence of `x-recipe` on a workflow marks it as a recipe. Absence marks it as a scenario. There is no separate `x-category` field.

**Rationale:** one field instead of two; no enum to maintain; avoids naming collision with `x-operation.category` in OpenAPI.

### 7.2 `x-recipe` Schema

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
| `purpose` | Yes | string | `test-fixture`, `demo-fixture`, `dev-fixture` | What the recipe is for |
| `extends` | No | string[] | Recipe file stems | Single-inheritance composition chain |
| `idempotent` | No | boolean | — | Whether running the recipe twice produces the same result. Default: `true` |
| `estimatedDurationMs` | No | integer | — | Estimated execution time (informational, for test scheduling) |
| `scope` | No | string | `scenario`, `session` | Lifetime of the fixture. Default: `scenario`. Session scope deferred to Phase 5+. |

### 7.3 Composition via `extends`

Recipes compose through single-inheritance chains. A recipe that extends another inherits all the parent's outputs and can build on them.

```yaml
# minimal-customer.recipe.yaml
x-recipe:
  purpose: test-fixture
  extends: [minimal-tenant]
  idempotent: true

workflows:
  - workflowId: setup
    inputs:
      type: object
      properties:
        customerName:
          type: string
          default: "Acme Co."
    dependsOn: []  # Parent runs first via extends
    steps:
      - stepId: create-customer
        operationId: createCustomer
        requestBody:
          payload:
            tenantId: $steps.parent-setup.outputs.tenantId
            name: $inputs.customerName
        outputs:
          customerId: $response.body#/id
    outputs:
      tenantId: $steps.parent-setup.outputs.tenantId
      customerId: $steps.create-customer.outputs.customerId
```

**Composition rules:**
- **Max depth: 6.** Deeper chains indicate over-engineering. The validator enforces this. The limit accommodates state-machine fixture progressions (e.g., `minimal-tenant` → `minimal-customer` → `basic-orders` → `submitted-order` → `paid-order` → `fulfilled-order`), where each level represents a meaningful, reusable business state. Chains that grow purely as wrapper indirection (each level wrapping a single API call without adding a named state) are still over-engineering and should be flattened.
- **No cycles.** A recipe cannot extend itself or form a circular chain.
- **No output namespace collisions.** If a parent and child both declare an output with the same name, the validator emits an error. The flat output namespace keeps `$setup.outputs.X` unambiguous.
- **Single-inheritance only.** The `extends` array expresses an ordered chain, not multiple parents. Each entry extends the previous.

### 7.4 Recipe Actor Context

**Recipes do not declare `x-actors`.** The Specfuse runtime executes recipe steps as an implicit `$system` actor mapped to the project's highest-privileged role -- broad enough to create any fixture the API permits.

**Recipes do not use `x-as` on steps** -- every step runs as `$system`.

**Recipes cannot reference `$setup`** -- only scenarios reference recipes via `$setup`. A recipe referencing another recipe uses `extends`, not `$setup`.

### 7.5 Output Contract

A recipe's `outputs` map is its public contract. Scenarios reference recipe outputs via `$setup.outputs.X`. When modifying a recipe, adding outputs is safe; removing or renaming outputs is a breaking change that requires updating all dependent scenarios.

**Output inheritance in `extends` chains:** When recipe B extends recipe A, all outputs from A's workflow are automatically available to consumers of B via `$setup.outputs.X`. Recipe B does not need to re-declare parent outputs -- the runtime merges outputs from the full `extends` chain into a single flat namespace. If a parent and child both declare an output with the same name, the validator emits an error (no silent shadowing). Inside the child recipe's workflow, parent outputs are accessed via `$steps.parent-setup.outputs.X` (see §8.1).

### 7.6 Foundational Recipes

Each project defines a small set of foundational recipes that form the base of its composition chain. For example:

| Recipe | Provides | Extends |
|--------|----------|---------|
| `minimal-tenant` | `tenantId`, `adminUserId` | (none) |
| `minimal-customer` | `customerId` + parent outputs | `minimal-tenant` |
| `basic-orders` | `orderId1`, `orderId2`, `agentId` + parent outputs | `minimal-customer` |

Domain-specific recipes extend foundational ones to add domain fixtures (e.g., `submitted-order` extends `basic-orders` and finalizes one of the orders).

### 7.7 Data Source

Recipe step payloads reference `x-sample` annotations on OpenAPI model properties for realistic data generation (see the Vendor Extensions handbook for `x-sample`). Recipes should not hardcode data values that `x-sample` can provide.

---

## 8) Expression Reference

Scenarios and recipes use the Arazzo 1.0.1 runtime-expression grammar (prefix `$`) extended with two Specfuse-specific roots. This section is the authoritative reference for all valid expression roots and the date-token grammar.

### 8.1 Expression Roots

| Root | Scope | Resolved By | Description |
|------|-------|-------------|-------------|
| `$inputs.X` | Workflow input parameters | Arazzo native | Access workflow input values |
| `$steps.<stepId>.outputs.X` | Prior step outputs within the same workflow | Arazzo native | Access outputs from earlier steps. Supports JSON Pointer suffix: `$steps.foo.outputs.bar#/nested/field` |
| `$response.body.X`, `$response.header.X`, `$response.status` | Current REST step's response | Arazzo native | Available in the owning step's `outputs` and `successCriteria` only |
| `$statusCode` | Current REST step's HTTP status | Arazzo native | Shorthand for the response status code |
| `$setup.outputs.X` | Outputs published by the recipe declared in `x-setup.recipe` | Specfuse extension | Available in scenario workflows only (not in recipes) |
| `$steps.parent-setup.outputs.X` | Outputs from the parent recipe in an `extends` chain | Specfuse extension | Available inside recipe workflows that declare `extends`. The `parent-setup` pseudo-step resolves to the parent recipe's workflow outputs. |
| `$message.payload.X`, `$message.headers.X` | Message captured inside `x-async.await` | Specfuse extension | Available inside the `x-async.await` block's `outputs` and `match` only |

### 8.2 Scope Rules (Validator-Enforced)

- **`$response`** and **`$statusCode`** are only valid inside the owning step's `outputs` and `successCriteria` blocks.
- **`$message`** is only valid inside the owning `x-async.await` block's `outputs` and `match`.
- **`$setup`** is only valid in scenario workflows (files without `x-recipe`). Recipes cannot reference `$setup`.
- **`$steps.parent-setup`** is only valid inside recipe workflows that declare `extends`. It provides access to the parent recipe's workflow outputs. Recipes without `extends` cannot reference `$steps.parent-setup`.
- **`$inputs`** and **`$steps`** follow Arazzo native scoping (workflow-local).

### 8.3 Date-Token Grammar

Date tokens provide human-readable relative dates that are resolved at runtime by the Specfuse executor.

**Syntax:** `@<anchor>[+/-<offset>][@<IANA-timezone>]`

**Anchors:**
- `@now` -- current ISO 8601 datetime
- `@today` -- current date at 00:00 UTC

**Offsets:** `[+-]<number><unit>`, chainable. Units: `y` (year), `mo` (month), `w` (week), `d` (day), `h` (hour), `m` (minute), `s` (second).

**Timezone suffix:** `@<IANA-timezone>` (e.g., `@America/New_York`)

**Examples:**

| Token | Resolves To |
|-------|-------------|
| `@now` | `2026-04-21T14:30:00Z` |
| `@today` | `2026-04-21T00:00:00Z` |
| `@today+3d` | `2026-04-24T00:00:00Z` |
| `@now-1h30m` | `2026-04-21T13:00:00Z` |
| `@today+2w@America/New_York` | `2026-05-05T00:00:00-04:00` |

### 8.4 Date-Token Allowed Locations (Restricted)

Date tokens are resolved in a restricted set of fields only. Tokens appearing anywhere else are a validator error.

**Allowed locations:**
- `x-setup.inputs.*` values
- Workflow `inputs.*` default values
- Step `requestBody.payload.*` values
- Step `parameters.*` values (inside the payload, not in path expressions)

**Rationale:** restricting the resolution surface keeps the runtime resolver simple and predictable.

---

## 9) Cross-Spec Source-of-Truth Rule

### 9.1 The Rule

**OpenAPI and AsyncAPI are canonical. Arazzo is behavioral. Arazzo assertions that contradict the canonical specs fail validation.**

This means:
- If an Arazzo step asserts `$statusCode == 200` for a POST operation, but the OpenAPI spec defines that operation as returning `201`, the validator flags the contradiction.
- If an `x-async.emit` references an event `Customer.Promoted`, but no AsyncAPI message has `x-label: { entity: Customer, action: Promoted }`, the validator flags the missing event.
- If a step uses `operationId: deleteCustomer`, but that operationId doesn't exist in the OpenAPI spec, the validator flags it.

### 9.2 What the Validator Checks (Cross-Spec)

| Check | Source | Target | Severity |
|-------|--------|--------|----------|
| `operationId` exists | Arazzo step | OpenAPI `operationId` | Error |
| Event `{Entity}.{Action}` exists | `x-async.emit` / `x-async.await` | AsyncAPI message `x-label` | Error |
| Status code assertions don't contradict OpenAPI response codes | `successCriteria` | OpenAPI operation responses | Error |
| Actor `role` in closed set | `x-actors.*.role` | Project's OpenAPI `x-roles` enum | Error |
| `x-domain` value valid | `x-domain` | Project's active domain list + `cross-domain` | Error |
| `cross-domain` only in `scenarios/cross-domain/` | File path + `x-domain` | Directory structure | Error |
| `$setup.outputs.X` resolves | Expression | Recipe `outputs` map | Error |
| Step graph acyclic; all inputs satisfied | Workflow steps | Internal | Error |
| Recipe `extends` chain valid, depth <= 6, no cycles | Recipe | Other recipes | Error |
| No output namespace collisions in recipe chains | Recipe outputs | Parent recipe outputs | Error |
| `x-mcp.toolName` globally unique | All scenarios | All scenarios | Error |

### 9.3 Violation Example

```yaml
# OpenAPI defines: POST /customers -> 201 Created
# Arazzo scenario:
steps:
  - stepId: create-customer
    operationId: createCustomer
    successCriteria:
      - condition: $statusCode == 200    # WRONG: OpenAPI says 201
```

The validator reports: `Source-of-truth violation: operation 'createCustomer' returns 201 per OpenAPI, but successCriteria asserts 200.`

### 9.4 AI Worker Access

The Arazzo validator does NOT re-check AI worker `aiAccess` alignment. The AsyncAPI cross-spec validator already enforces `x-ai.entities` against `aiAccess` at the source. Arazzo trusts that verdict -- duplicating checks would create two maintenance points for the same rule.

---

## 10) Versioning and Deprecation

### 10.1 Unified Shape

Arazzo uses the same `x-version` shape as AsyncAPI messages and (eventually) OpenAPI. Deprecation metadata lives inside `x-version`; there is no standalone `x-deprecated` extension.

See Section 4.2 for the full schema.

### 10.2 Lifecycle

1. **`draft`** -- scenario is under development; not yet consumed by test generation or documentation
2. **`stable`** -- scenario is in production; changes follow evolution rules
3. **`deprecated`** -- scenario is being phased out; `deprecatedAt` and `replacedBy` are required; `removalDate` is optional

### 10.3 Evolution Rules

**Within the same version (non-breaking):**
- Add new steps to a workflow
- Add new workflows to a file
- Add new input parameters with defaults
- Add new outputs
- Relax assertions (e.g., widen a timeout)

**Requires a new version (breaking):**
- Remove or rename a workflow, step, or output
- Change the required inputs
- Change `x-setup.recipe` to a recipe with a different output contract
- Tighten assertions in ways that would fail previously-passing tests

### 10.4 Semver on `info.version`

The `info.version` field uses semantic versioning for the Arazzo document itself. The `x-version.current` integer tracks the schema/content version for tooling consumption. Both are maintained.

---

## 11) MCP Exposure

### 11.1 Contract

The `x-mcp` extension on scenario workflows declares opt-in exposure as MCP tools. See Section 4.8 for the full schema.

### 11.2 Design Principles

- **Explicit opt-in:** `exposed: false` is the default. Scenarios are not MCP tools unless explicitly marked.
- **Derived I/O:** MCP tool inputs and outputs are derived from the workflow's `inputs` and `outputs` -- never redeclared in `x-mcp`. This avoids drift.
- **Global uniqueness:** `toolName` must be unique across all scenarios in the repo. Enforced by Spectral from Phase 0.
- **Safety default:** `safeForAutoInvoke: false` means an AI agent must confirm with a human before running the tool. Only mark `true` for read-only, low-risk scenarios.

### 11.3 Example

```yaml
x-mcp:
  exposed: true
  toolName: get-order-status
  description: "Check the current status of a customer's order"
  requiresActorAuth: true
  safeForAutoInvoke: true   # Read-only, safe for auto-invocation
```

The MCP runtime (Phase 7) consumes this metadata. Phase 0 establishes the contract and uniqueness enforcement.

---

## 12) Canonical Examples

Full-length canonical examples are provided in separate files for easy reference and cross-checking:

- **Scenario template:** `samples/scenario-samples.yaml` -- a complete scenario file demonstrating all extensions, actor binding, async assertions, and UI hints
- **Recipe template:** `samples/recipe-samples.yaml` -- a complete recipe file demonstrating composition via `extends`, output contracts, and fixture provisioning

These files are the authoritative templates for new scenarios and recipes. When in doubt about structure or conventions, consult them first.

---

## 13) Do / Do NOT

### Do

- **Do** use real `operationId` values from the OpenAPI spec. Never invent operations.
- **Do** use `{Entity}.{Action}` PascalCase format for event references in `x-async`, matching AsyncAPI `x-label`.
- **Do** declare `x-version` on every workflow with an accurate `status`.
- **Do** include `x-as` on every scenario step to identify the acting user.
- **Do** bind actors to recipe-seeded entities via `x-actors.<name>.ref: $setup.outputs.X`.
- **Do** assert at least one observable outcome (event or REST state) for critical-path AI worker flows.
- **Do** use the `critical-path` tag on scenarios that must block PR merges.
- **Do** follow the Mermaid diagram test (Section 2.2) when deciding whether to split or merge scenarios.
- **Do** use date tokens (`@today+3d`) instead of hardcoded dates in recipe inputs and step payloads.
- **Do** keep recipe output contracts stable -- adding outputs is safe; removing/renaming is breaking.
- **Do** declare `x-doc.summary` on every scenario for documentation generation.

### Do NOT

1. **Do NOT use top-level `x-emits` in Arazzo files.** The Arazzo assertion is `x-async.emit` (nested under `x-async`). Top-level `x-emits` is reserved for OpenAPI operations and AsyncAPI `on-*` receive operations. Using it in Arazzo creates a naming collision. The validator rejects `x-emits` as a top-level Arazzo field.

2. **Do NOT write channel addresses in `x-async`.** Channel derivation is automatic: the validator resolves the channel from the event's `x-label`. Authors never specify which topic or channel an event belongs to.

3. **Do NOT invent `operationId` values.** Every `operationId` in a step must exist in the referenced OpenAPI spec. If the operation doesn't exist yet, design it first (OpenAPI is canonical).

4. **Do NOT invent event names.** Every `{Entity}.{Action}` in `x-async` must match an AsyncAPI message's `x-label`. If the event doesn't exist yet, design it first (AsyncAPI is canonical).

5. **Do NOT mix recipes and scenarios in the same file.** All workflows in a file must be the same category. The file-level homogeneity rule is enforced by the validator.

6. **Do NOT declare `x-actors` on recipe workflows.** Recipes execute as the implicit `$system` actor (mapped to the project's highest-privileged role). Actor declarations on recipes are a validator error.

7. **Do NOT use `x-as` in recipe steps.** Recipe steps run as `$system`. The `x-as` extension is for scenarios only.

8. **Do NOT reference `$setup` inside recipe files.** Recipes compose via `extends`, not `$setup`. The `$setup` root is only valid in scenario workflows. Using it in a recipe is a validator error.

9. **Do NOT exceed recipe composition depth of 6.** If a recipe chain goes deeper than 6 levels, it indicates over-engineering. Flatten or restructure. The 6-level ceiling accommodates state-machine fixture progressions (draft → submitted → paid → fulfilled, layered on a foundational base); chains beyond that are typically wrapper indirection without distinct business states.

10. **Do NOT create output namespace collisions in recipe chains.** If a parent recipe outputs `tenantId` and a child recipe also outputs `tenantId`, the validator flags the collision. Rename one of them.

11. **Do NOT assert AI worker internals.** Never write assertions about prompt content, model choice, token counts, or intermediate reasoning. Assert observable outcomes only (terminal events or resulting REST state).

12. **Do NOT use `x-category`, `x-tags`, or `x-deprecated` as standalone extensions.** Category is determined by `x-recipe` presence; tags use the native Arazzo `tags` array; deprecation lives inside `x-version`.

13. **Do NOT hardcode absolute dates in scenarios or recipes.** Use date tokens (`@today+3d`, `@now-1h`) to keep scenarios time-independent.

14. **Do NOT place date tokens outside the allowed locations.** Date tokens resolve only in `x-setup.inputs`, workflow `inputs` defaults, step `requestBody.payload`, and step `parameters` values. Tokens elsewhere are a validator error.

15. **Do NOT put language-specific references in Arazzo files.** No class names, namespaces, package paths, file paths, or target-language identifiers. The code generator owns all language decisions.

16. **Do NOT create scenarios with >= 80% step-sequence overlap.** The Spectral rule `arazzo-scenario-step-overlap` flags this as an error. Consolidate into one scenario with input parameters or workflows for variants.

17. **Do NOT make `x-mcp.toolName` collide with another scenario's `toolName`.** Global uniqueness is enforced by Spectral. Choose descriptive, domain-prefixed names (e.g., `order-submit`, not `submit`).

18. **Do NOT use `x-mcp` on recipe workflows.** Recipes are infrastructure, not user-facing tools.

---

## 14) Authoring Path

### 14.1 LLM-Only Authoring

Arazzo scenarios are authored exclusively through Claude Code using the `/design-scenario` skill. Hand-authoring YAML is not expected or recommended.

**Rationale:** the cross-spec dependency surface (operationIds, event names, actor roles, recipe outputs, expression scoping) is too tight for safe hand-authoring. The authoring agents validate in real-time, cross-reference against OpenAPI and AsyncAPI specs, and catch issues that a human editing YAML would miss.

### 14.2 Claude Code Commands

| Command | Audience | Purpose |
|---------|----------|---------|
| `/design-scenario` | PM | Interactive scenario creation from intent |
| `/update-scenario` | PM, dev | Modify existing scenario; handles operationId renames, version bumps |
| `/design-recipe` | Architect | New setup recipe |
| `/validate-scenarios` | All | Run Layer 1 static validator |
| `/review-scenario` | Reviewer | Pre-merge checklist via `scenario-reviewer` sub-agent |
| `/impact-scenarios` | Dev | Reverse lookup: scenarios referencing a given operationId/event |
| `/list-scenarios` | PM | Browse by domain / actor / tag |
| `/deprecate-scenario` | Dev | Mark deprecated; cascade to test suite; generate migration note |

### 14.3 Sub-Agents

| Agent | Role | Key Constraint |
|-------|------|---------------|
| `scenario-architect` | Translates PM intent into valid Arazzo YAML | Never invents operationIds, events, or roles -- stops and asks |
| `scenario-validator` | Runs cross-spec checks, returns structured diagnostics | Pure function of specs; no network |
| `scenario-reviewer` | Independent second opinion for `/review-scenario` | Never sees the original PM prompt -- reviews YAML on its own merits. Enforces granularity rule (Section 2). |
| `impact-analyzer` | Given git diff, finds affected scenarios | Used by CI and `/impact-scenarios` |

### 14.4 Interactive Flow (`/design-scenario`)

1. Gather intent in plain language
2. Map to domain (confirm with user)
3. Scan OpenAPI/AsyncAPI for candidate operations and events
4. Confirm actor set from the project's closed role list
5. Walk through steps one at a time; confirm each
6. Elicit failure modes explicitly
7. Collect `x-ui` natural-language actions and expected outcomes
8. Generate YAML
9. Run Layer 1 validator; auto-repair mechanical issues; surface what requires judgment
10. Render as Mermaid sequence diagram for human sanity check
11. Write file and regenerate scenario markdown documentation

---

## 15) Testing Pyramid Position and CI Integration

### 15.1 Pyramid Position

Arazzo-generated tests sit at the **top of the testing pyramid** -- integration/E2E level. They exercise critical paths through the real API against a disposable tenant. They are not a replacement for unit tests or service-level tests.

```
     /\        Arazzo scenario tests (critical paths, slow, high-fidelity)
    /  \
   /    \      Service/integration tests (domain-level, moderate speed)
  /      \
 /________\   Unit tests (fast, numerous, foundational)
```

### 15.2 Execution Environment

- **Tenant isolation:** fresh disposable tenant provisioned per CI session. No shared state between runs.
- **Setup:** recipes use real OpenAPI operations to create fixtures. No database seeding or backdoors.
- **Actor auth:** seeded via the identity API using recipe-provisioned user entities.

### 15.3 CI Integration

**PR-scoped (on every pull request):**

- Only scenarios impacted by changed `operationId`s or events run (determined by the `impact-analyzer` sub-agent)
- **Blocking** for scenarios tagged `critical-path` -- PR cannot merge if these fail
- **Report-only** for other scenarios -- failures are surfaced but don't block

**Nightly:**

- Full `critical-path` suite runs
- Recent-changed scenario set runs
- Results feed into flake-rate tracking

### 15.4 Flake Budget

Target scenario test flake rate: < 2%. Scenarios that exceed this threshold are flagged for review -- the cause is typically a timing issue (tight `x-async` timeouts) or a test data collision.

---

## 16) Specfuse Contract

> **Status:** Stub -- to be fleshed out as Specfuse evolves.

This section pins the interface between a Specfuse project's specifications and the Specfuse tooling platform. Its purpose is to ensure that spec-schema changes and Specfuse releases can be coordinated without surprises.

### 16.1 What Specfuse Reads

- Bundled OpenAPI spec (`output/openapi-bundled.yaml`)
- Bundled AsyncAPI spec (`output/asyncapi-bundled.yaml`)
- Arazzo scenario and recipe files (`**/*.arazzo.yaml`, `**/*.recipe.yaml`)
- JSON Schemas for all vendor extensions (source of validation truth)

### 16.2 What Specfuse Produces

| Phase | Artifact |
|-------|----------|
| Phase 1 | Layer 1 diagnostics (static validation results) |
| Phase 3 | Scenario markdown + Mermaid sequence diagrams |
| Phase 5 | Integration test code (target language chosen by generator config) |
| Phase 6 | Playwright test code + LLM exploratory runner scripts |

### 16.3 Versioning Discipline

Specfuse versions against the handbooks. A breaking change in an extension schema (new required field, changed semantics, removed field) requires a paired Specfuse release. Additive changes (new optional fields, new extensions) are non-breaking and absorbed by Specfuse at its own pace.

### 16.4 Change Propagation

1. Handbook change lands in the kit (PR merged)
2. If breaking: paired Specfuse PR opened simultaneously
3. If additive: Specfuse issue created for adoption at next convenient release
4. JSON Schema for the changed extension updated in both repos

---

*This handbook is loaded as mandatory reading via `CLAUDE.md`. All Arazzo specifications must comply with the rules defined here. If any request conflicts with this handbook, pause and ask for approval before deviating.*
