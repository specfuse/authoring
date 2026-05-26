# hello-orders

This is the bundled Specfuse example project inside the [spec-authoring-kit](https://github.com/clabonte/spec-authoring-kit). It exists for two reasons: (1) a worked-out reference of a minimum-but-real Specfuse project across OpenAPI + AsyncAPI + Arazzo, and (2) the kit's CI regression net — every PR to the kit re-validates this example.

---

## Authoritative rules

All API, async, scenario, and AI-access design here MUST comply with the Specfuse spec-authoring kit. The kit's handbooks are the source of truth; this `CLAUDE.md` only documents conventions specific to `hello-orders`.

When designing specs, read the relevant handbook first:

| Topic | Handbook |
|---|---|
| REST API design (paths, models, HTTP contract, errors) | `<kit>/handbooks/API_Handbook.md` |
| AsyncAPI events, scheduled jobs, snapshots, workers | `<kit>/handbooks/AsyncAPI_Handbook.md` |
| Arazzo scenarios and setup recipes | `<kit>/handbooks/Arazzo_Handbook.md` |
| Vendor extensions (`x-entity`, `x-emits`, `x-label`, etc.) | `<kit>/handbooks/Vendor_Extensions.md` |
| AI agent access policy (tier framework) | `<kit>/handbooks/AI_Access_Policy_Framework.md` |

Canonical samples to copy from:

- `<kit>/samples/endpoint-samples.yaml`
- `<kit>/samples/message-samples.yaml`
- `<kit>/samples/scenario-samples.yaml`
- `<kit>/samples/recipe-samples.yaml`

Since `hello-orders` lives inside the kit, `<kit>` resolves to `../../` (the kit root).

---

## Project-specific overlays

### Project token

Channel addresses in this project use the prefix `helloorders` (no hyphen — the project token must be a single dot-segment). The shared event topic is `helloorders.events`.

### Domain list

Active domains:

- `customer` — owns the Customer aggregate. Read/write CRUD + the `Customer.Created` / `Customer.Updated` events.
- `order` — owns the Order aggregate and its OrderLine child entity. CRUD + the lifecycle action `placeOrder` (state transition draft→placed) + line-item add. Emits `Order.Created`, `Order.Updated`, `Order.Placed`, `OrderLine.Created`.

There is intentionally no `tenant` domain. `tenantId` is the ambient scope — it appears as a path parameter and on snapshots, but no Tenant entity is defined.

### Role enum

Defined in [`api/specs/v1/common/enums.yaml#/Role`](api/specs/v1/common/enums.yaml).

- `Admin` — full access
- `Manager` — tenant-level manager
- `Customer` — end-user self-service
- `Authenticated` — pre-business-role flows (not used by any operation in this example)

`x-roles` rule of thumb here:
- Reads: `[Admin, Manager, Customer]`
- Writes: `[Admin, Manager]`

### AI access policy

See [`api/docs/hello-orders-ai-access-policy.md`](api/docs/hello-orders-ai-access-policy.md). The example uses tier 1 (Customer, read-only) and tier 2 (Order + OrderLine, collaborative). Tier 0 and tier 3 are intentionally empty.

### Flow documentation

[`api/docs/flows/order/overview.md`](api/docs/flows/order/overview.md) — Mermaid sequence diagram for the place-order flow.

---

## Project structure

```
api/
├── docs/
│   ├── hello-orders-ai-access-policy.md
│   └── flows/order/overview.md
└── specs/v1/
    ├── openapi.yaml
    ├── asyncapi.yaml
    ├── common/                            # Shared OpenAPI components
    │   ├── enums.yaml
    │   ├── parameters/{path,pagination}.yaml
    │   ├── responses/errors.yaml
    │   ├── headers/common.yaml
    │   └── securitySchemes/auth.yaml
    ├── async-common/                      # Shared async components
    │   ├── channels/application-events.yaml
    │   ├── message-traits/common.yaml
    │   └── operation-traits/common.yaml
    ├── domains/
    │   ├── customer/                      # 4 ops, 2 events, 1 snapshot
    │   └── order/                         # 7 ops, 4 events, 2 snapshots
    └── scenarios/
        ├── cross-domain/place-order.arazzo.yaml
        └── setup-recipes/foundational/
            ├── minimal-customer.recipe.yaml
            └── customer-with-draft-order.recipe.yaml
```

---

## What's deliberately out of scope

Out of scope for the example (kept tiny on purpose):

- No Tenant entity, no auth/user/login operations
- No PUT, no DELETE, no `:search` endpoints
- No scheduled jobs (no `run-*` operations)
- No payment / shipping / refund flows
- No AI worker (no `x-ai` blocks on async-operations)

When the kit grows new patterns, add them here.

---

## CI regression net

`.github/workflows/example-regen.yml` (at the kit root) validates every `.yaml` under `api/` on every PR. When the kit ships Spectral rulesets and the generator, that workflow will grow.

---

*Last updated: project bootstrap*
