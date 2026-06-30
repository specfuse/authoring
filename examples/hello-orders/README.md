# hello-orders

A tiny, complete Specfuse example project bundled inside the [spec-authoring-kit](https://github.com/Specfuse/authoring). Its job is two-fold:

1. **Pedagogical** — show, in one place, what a minimum-but-real Specfuse project looks like across OpenAPI, AsyncAPI, and Arazzo.
2. **Regression net** — the kit's CI workflow re-validates this example on every PR; if a handbook change breaks the example, the PR fails.

## What this demonstrates

| Surface | What's here |
|---|---|
| Domains | `customer`, `order` |
| Entities | `Customer` (aggregate), `Order` (aggregate), `OrderLine` (entity under Order) |
| REST operations | List/Get/Create/Update on Customer & Order, lifecycle `placeOrder`, plus List/Add on OrderLine — 11 operations total |
| Events | `Customer.Created`, `Customer.Updated`, `Order.Created`, `Order.Updated`, `Order.Placed` (state transition), `OrderLine.Created` |
| Snapshots | `CustomerSnapshot`, `OrderSnapshot`, `OrderLineSnapshot` |
| Scenarios | One cross-domain scenario — `place-order` (customer adds a line item to a draft order and places it) |
| Recipes | `minimal-customer` (root) + `customer-with-draft-order` (extends) |
| AI access policy | One entity per tier (1, 2) plus an empty tier 0/3 — covers the matrix shape |
| Flow docs | One Mermaid sequence diagram for the place-order flow |

## How to read it

Start at the spec roots and follow the `$ref` graph:

```
api/specs/v1/openapi.yaml     ← REST root; references domains/{customer,order}/operations/*.yaml
api/specs/v1/asyncapi.yaml    ← AsyncAPI root; references async-common/channels + per-domain async-operations
api/specs/v1/scenarios/cross-domain/place-order.arazzo.yaml
                              ← the one scenario, references the two recipes below
api/specs/v1/scenarios/setup-recipes/foundational/
  minimal-customer.recipe.yaml
  customer-with-draft-order.recipe.yaml
```

The handbooks at `<kit>/handbooks/` are the authoritative rules; this example is a worked-out application of them.

## What's deliberately NOT here

The example is intentionally tiny. Out of scope:

- **No `Tenant` entity.** `tenantId` is the ambient scope — it appears as a path parameter and on snapshots but no Tenant entity is defined or has its own operations.
- **No replace/delete operations.** PATCH only — no PUT, no DELETE.
- **No payment, shipping, fulfillment, or refund flows.** Order has `draft` and `placed` states; everything past `placed` is out of scope.
- **No scheduled jobs.** Async-operations folder contains `on-*` / `emit-*` only, no `run-*`.
- **No tier 0 or tier 3 entities** with detailed blocks — the policy matrix shows them as empty rows for completeness.
- **No `createUser`, `createTenant`, or auth flows.** The recipe takes a fixed `tenantId` input.

When the kit grows new authoring patterns (search endpoints, scheduled jobs, AI workers, etc.), this example will grow alongside.

## Role as the kit's CI regression net

`.github/workflows/example-regen.yml` validates this example on every PR to the kit. The validation today is YAML-only (every `.yaml` file under `api/` must parse). When the kit ships Spectral rulesets and generator integration, that workflow will grow to run Spectral + a full generator regeneration.

When a handbook or sample change forces a structural change here, regenerate the example in the same PR. The diff against the previous version is the proof that the change is non-breaking (or, intentionally, the visible cost of a breaking change).
