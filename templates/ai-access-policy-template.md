# {ProjectName} AI Access Policy

> **Template instructions:** Copy this file into your project (typical location: `api/docs/{project-name}-ai-access-policy.md`), replace `{ProjectName}` with your project name, delete this admonition, and fill in the entity tables and per-domain `aiAccess` blocks below. The framework that drives tier semantics is in `handbooks/AI_Access_Policy_Framework.md` — read that first. The empty matrix and per-domain skeleton below are scaffolding; each row/block becomes a concrete tier assignment as you classify each entity.

This document defines the AI agent access policy for all {ProjectName} entities. It is consumed by the code generator (via the `aiAccess` property on `x-entity`) and serves as the team-visible reference for what AI agents can and cannot do with each entity.

For the tiering framework, `ownedBy` semantics, encrypted-field rules, and the classification flowchart, see [`handbooks/AI_Access_Policy_Framework.md`](../handbooks/AI_Access_Policy_Framework.md). For the full `aiAccess` schema, see [`handbooks/Vendor_Extensions.md §1.1.1`](../handbooks/Vendor_Extensions.md).

---

## Entity Classification Matrix

Every entity in the project is classified into one of four tiers (see framework §2 for the criteria). List every `x-entity` schema in the matrix below; the tier sums must reconcile against the project's full entity count.

### Tier 0 — No access (omit `aiAccess`)

Security/legal-sensitive entities, admin-only entities, or entities no agent needs.

| Entity | Domain | Rationale |
|--------|--------|-----------|
| `{EntityName}` | `{domain}` | {one-line reason this entity has no AI access} |
| ... | ... | ... |

**Total: {N} entities**

### Tier 1 — Reference read

Entities the agent reads for context/decisions but never modifies.

| Entity | Domain | Rationale |
|--------|--------|-----------|
| `{EntityName}` | `{domain}` | {one-line reason this entity is read-only for AI} |
| ... | ... | ... |

**Total: {N} entities**

### Tier 2 — Collaborative (`ownedBy: shared`)

Entities where AI and humans both edit, with last-writer-wins resolution.

| Entity | Domain | AI operations | Rationale |
|--------|--------|--------------|-----------|
| `{EntityName}` | `{domain}` | read, create, update | {one-line reason AI and humans share write authority} |
| ... | ... | ... | ... |

**Total: {N} entities**

### Tier 3 — AI-owned (`ownedBy: ai`)

Entities where the AI is the system of record; backend writes are reconciled against agent state.

| Entity | Domain | AI operations | Rationale |
|--------|--------|--------------|-----------|
| `{EntityName}` | `{domain}` | read, create, update | {one-line reason AI owns this entity end-to-end} |
| ... | ... | ... | ... |

**Total: {N} entities**

### Summary

| Tier | Count | % |
|------|-------|---|
| 0 — No access | {N} | {pct}% |
| 1 — Reference read | {N} | {pct}% |
| 2 — Collaborative | {N} | {pct}% |
| 3 — AI-owned | {N} | {pct}% |
| **Total** | **{N}** | **100%** |

---

## Detailed `aiAccess` Blocks by Domain

Below are the exact `aiAccess` blocks to add to each entity's `x-entity`. Group by domain; entities in tier 0 are omitted (no `aiAccess` means no access). The skeleton below shows the four shapes — copy and adapt per entity.

### {domain-name}

#### {EntityName} (tier 0)
*(no `aiAccess` — omit entirely)*

#### {EntityName} (tier 1)
```yaml
aiAccess:
  operations: [read]
```

#### {EntityName} (tier 1, with explicit encrypted-field grant)
```yaml
aiAccess:
  operations: [read]
  readableProperties:
    - firstName
    - lastName
    - email
    - phone
    - {encryptedFieldName}   # Explicitly granted — not auto-included
  reason: >
    {Business reason the agent needs this encrypted field. Should not
    reference the agent implementation or target language.}
```

#### {EntityName} (tier 2)
```yaml
aiAccess:
  operations: [read, create, update]    # or any subset
  writableProperties:
    - {field1}
    - {field2}
    - {field3}
    - tenantId                          # FK scope, will be locked on update
  immutableOnUpdate:
    - tenantId
    # ...any other fields settable on create but not on update
  ownedBy: shared
  reason: >
    {Business reason in product language — what the agent does with
    this entity and why humans also need to edit it. Should not
    reference target language, file paths, or agent implementation.}
```

#### {EntityName} (tier 3)
```yaml
aiAccess:
  operations: [read, create, update]
  writableProperties:
    - {field1}
    - {field2}
    - {field3}
    - tenantId
  immutableOnUpdate:
    - tenantId
  ownedBy: ai
  reason: >
    {Business reason explaining why this entity is AI-owned —
    typically "AI artifact" or "Agent owns end-to-end generation
    and lifecycle of this entity."}
```

### {next-domain-name}

(...repeat per domain...)

---

## Rollout Plan

A phased rollout keeps risk low. Each phase produces a reviewable diff in the AI manifest.

### Phase 1 — Tier 0 + Tier 1 (safe, no write surface)

Add `aiAccess: { operations: [read] }` to all tier 1 entities. Tier 0 entities get nothing. Mechanical and low-risk — gives AI agents a complete read surface immediately with no production exposure.

**Entities touched:** {tier 1 count}

### Phase 2 — Tier 3 (AI-owned, focused review)

Add the tier 3 blocks. These carry `ownedBy: ai` and need careful review of `writableProperties` against the agent's actual needs. Usually a small set of entities — review each one individually.

**Entities touched:** {tier 3 count}

### Phase 3 — Tier 2 (collaborative, domain-by-domain)

Add the tier 2 blocks one domain at a time. Each introduces a shared-write contract that deserves scrutiny. PRs grouped by domain keep review surface manageable.

**Entities touched:** {tier 2 count}

### Phase 4 — Generator integration

Run the generator against updated specs. Validate the AI manifest. Smoke-test that generated AI repositories compile and that no entity outside tier 0 accidentally exposes more than intended. Cross-check `x-ai.entities` declarations on AsyncAPI workers against the matching `aiAccess` blocks (the generator enforces this — confirm zero validation errors).

---

## Maintenance Guidelines

### Adding a new entity

1. Apply the framework's classification flowchart (`AI_Access_Policy_Framework.md §6`).
2. Default to tier 0 or 1 — never start with write access unless the use case is clear and the writable surface is well-understood.
3. Add the entity to the matrix above with its tier, domain, and rationale.
4. Add the `aiAccess` block to the entity's `x-entity` in the OpenAPI spec.
5. Document the `reason` with the business need, not the implementation.
6. Run the validator to ensure `writableProperties` and `immutableOnUpdate` reference real top-level properties on the entity.

### Broadening access

- Moving from tier 0 to tier 1 is low-risk (read-only). One-line matrix entry + one-line `aiAccess` block.
- Moving to tier 2 or 3 requires:
  - An explicit `reason` describing the business need.
  - An enumerated `writableProperties` allow-list (no "all fields" shortcut).
  - Review of `immutableOnUpdate` to ensure tenant-scope foreign keys stay locked on update.
- Every broadening should produce a visible AI-manifest diff in the PR. Reviewers compare the diff against the matrix update for consistency.

### Revoking access

- Remove `aiAccess` entirely to revoke all access (back to tier 0).
- The AI manifest will reflect the change, and generated AI-scoped repository methods will be removed on the next generation run.
- If the entity has dependent AsyncAPI workers (declared in `x-ai.entities`), update them in the same PR — the cross-spec validator will fail the build if a worker still claims access to a now-tier-0 entity.

### Migrating between tiers

| Move | Risk | Action |
|------|------|--------|
| Tier 0 → 1 | Low | Add `aiAccess: { operations: [read] }`. No code impact. |
| Tier 1 → 2 | Medium | Add `writableProperties`, `immutableOnUpdate`, `ownedBy: shared`, `reason`. Review with the team. |
| Tier 1 → 3 | High | Same as 1 → 2 but with `ownedBy: ai`. Justify why AI is the system of record. |
| Tier 2 → 3 | Medium | Change `ownedBy: shared` → `ai`. Confirm backend writes are tolerant of reconciliation. |
| Tier 2 → 1 | High | Remove write surface. Audit agent code for write paths and migrate them or remove the agent. |
| Tier 3 → 2 | High | Same as 2 → 1 in scope: the agent's authority drops; reconciliation logic that assumed AI-ownership may break. |
| Any → 0 | Highest | Removes all AI access. Confirm no agent depends on any read or write path before removing. |

---

*This document is the team-visible reference for AI access. The framework that defines tier semantics is in `handbooks/AI_Access_Policy_Framework.md` — keep both in sync.*
