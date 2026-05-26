# hello-orders AI Access Policy

This document defines the AI agent access policy for all entities in the `hello-orders` example project. It is consumed by the code generator (via the `aiAccess` property on `x-entity`) and serves as the team-visible reference for what AI agents can and cannot do with each entity.

For the tiering framework, `ownedBy` semantics, encrypted-field rules, and the classification flowchart, see [`<kit>/handbooks/AI_Access_Policy_Framework.md`](../../../handbooks/AI_Access_Policy_Framework.md). For the full `aiAccess` schema, see [`<kit>/handbooks/Vendor_Extensions.md §1.1.1`](../../../handbooks/Vendor_Extensions.md).

---

## Entity Classification Matrix

`hello-orders` has 3 entities. Tier 0 and tier 3 are intentionally empty — the matrix shows them for completeness.

### Tier 0 — No access (omit `aiAccess`)

Security/legal-sensitive entities, admin-only entities, or entities no agent needs.

| Entity | Domain | Rationale |
|--------|--------|-----------|
| _(none in this example)_ | — | — |

**Total: 0 entities**

### Tier 1 — Reference read

Entities the agent reads for context/decisions but never modifies.

| Entity | Domain | Rationale |
|--------|--------|-----------|
| `Customer` | `customer` | Order-management agents read customer profiles for context when reviewing or annotating orders. No write surface. |

**Total: 1 entity**

### Tier 2 — Collaborative (`ownedBy: shared`)

Entities where AI and humans both edit, with last-writer-wins resolution.

| Entity | Domain | AI operations | Rationale |
|--------|--------|--------------|-----------|
| `Order` | `order` | read, create, update | Agents draft orders, annotate them, and may promote drafts to placed on behalf of the customer; humans (managers, customers) remain authoritative. |
| `OrderLine` | `order` | read, create | Agents add line items to draft orders on behalf of the customer; no update path. |

**Total: 2 entities**

### Tier 3 — AI-owned (`ownedBy: ai`)

Entities where the AI is the system of record; backend writes are reconciled against agent state.

| Entity | Domain | AI operations | Rationale |
|--------|--------|--------------|-----------|
| _(none in this example)_ | — | — | — |

**Total: 0 entities**

### Summary

| Tier | Count | % |
|------|-------|---|
| 0 — No access | 0 | 0% |
| 1 — Reference read | 1 | 33% |
| 2 — Collaborative | 2 | 67% |
| 3 — AI-owned | 0 | 0% |
| **Total** | **3** | **100%** |

---

## Detailed `aiAccess` Blocks by Domain

The `aiAccess` blocks below are duplicated from each entity's `x-entity` for human review. The OpenAPI files are the authoritative source.

### customer

#### Customer (tier 1)
```yaml
aiAccess:
  operations: [read]
  # readableProperties omitted → every non-encrypted top-level field
  reason: >
    Order-management agents read customer profiles to provide context
    when reviewing or annotating orders. No write surface.
```

### order

#### Order (tier 2)
```yaml
aiAccess:
  operations: [read, create, update]
  writableProperties:
    - status
    - notes
    - currency
    - customerId
    - tenantId
  immutableOnUpdate:
    - customerId
    - tenantId
  ownedBy: shared
  reason: >
    Order-management agents draft orders, annotate them, and may promote
    drafts to placed on behalf of the customer. Humans (managers, customers)
    remain authoritative; tenant and customer scope cannot be reparented.
```

#### OrderLine (tier 2)
```yaml
aiAccess:
  operations: [read, create]
  writableProperties:
    - description
    - quantity
    - unitPriceMinor
    - orderId
  immutableOnUpdate:
    - orderId
  ownedBy: shared
  reason: >
    Order-management agents add line items to draft orders on behalf of
    the customer. No update or delete — once added, a line is replaced
    by deleting and re-adding (out of scope for this example).
```

---

## Rollout Plan

Not applicable in this example — there are no live agents and no production exposure. In a real project the four-phase rollout (Tier 0+1 → Tier 3 → Tier 2 by domain → Generator integration) from the framework's §Rollout Plan would apply.

---

## Maintenance Guidelines

See the [template](../../../templates/ai-access-policy-template.md) for the full set. For this example, the key constraints:

- Adding a new tier-2 or tier-3 entity requires `writableProperties` (enumerated, no wildcards), `immutableOnUpdate` containing all FK scope fields, and a `reason` ≥ 40 characters of business language.
- Foreign keys (`tenantId`, `customerId`, `orderId`) are always `immutableOnUpdate` for tier 2+ entities.
- `aiAccess` only appears on schemas with `x-entity` — never on derivatives (`Basic*`, `New*`, `Update*`, `*List`).

---

*This document is the team-visible reference for AI access in the hello-orders example. The framework that defines tier semantics lives in the kit's handbook.*
