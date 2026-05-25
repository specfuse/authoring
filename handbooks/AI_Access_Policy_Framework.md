# AI Access Policy Framework

This handbook defines the **framework** every Specfuse project uses to decide what AI agents can do with each entity. The project's concrete tier assignments — which specific entities sit in which tier — live in a project-local overlay (see `templates/ai-access-policy-template.md` for the starter shape).

The framework drives the `aiAccess` block on `x-entity` (see [`Vendor_Extensions.md §1.1.1`](./Vendor_Extensions.md) for the schema). The generator emits AI-scoped repositories, field allow-lists, and audit hooks from those blocks.

---

## 1) Why a Framework

A consistent four-tier framework keeps AI access decisions:

- **Auditable** — every entity has a documented tier with a stable shape (`operations`, `ownedBy`, `writableProperties`, `reason`). Reviewers compare like-for-like.
- **Defaulted to safety** — absence of `aiAccess` means no access. Broadening is explicit; revoking is removal.
- **Easy to classify new entities** — three questions (read? write? system of record?) place every entity in exactly one tier.
- **Stable as agents evolve** — adding a new agent doesn't require revisiting every entity, only the ones whose access surface changes.

The alternative — ad-hoc `aiAccess` blocks per entity — produces drift, surprises in production, and review fatigue.

---

## 2) The Four Tiers

| Tier | Name | `operations` | `ownedBy` | Criteria |
|------|------|-------------|-----------|----------|
| **0** | No access | *(omit `aiAccess`)* | n/a | Security/legal-sensitive, admin-only, or no agent needs it |
| **1** | Reference read | `[read]` | n/a | AI needs it for context/decisions but must never modify it |
| **2** | Collaborative | varies | `shared` | AI and humans both edit; last-writer-wins with audit |
| **3** | AI-owned | `[read, create, update]` | `ai` | AI is the system of record; backend writes are reconciled |

### 2.1 Tier 0 — No Access

The entity has no `aiAccess` block at all. Generated AI-facing repositories do not expose this entity in any form — agents cannot read, write, list, or even discover it.

**When to use:**
- The entity participates in an authentication or authorization flow that must remain free of AI influence (invitation tokens, password reset records, OAuth state).
- The entity is an append-only accounting ledger (payment transactions, audit logs, financial reconciliation rows) where AI presence would compromise integrity guarantees.
- The entity is operationally orthogonal to AI agents (display screens, integration plumbing).
- No agent has a plausible reason to read it.

**Implementation:** simply omit the `aiAccess` block. The `x-entity` block remains; only `aiAccess` is absent.

### 2.2 Tier 1 — Reference Read

The agent may read every non-encrypted top-level property of the entity, but cannot create, update, or delete it.

```yaml
aiAccess:
  operations: [read]
```

**When to use:**
- Reference/master data the agent needs as context (tenants, customers, policies, templates).
- Human-owned data the agent must understand but never edit (employment records, preferences, time-off requests).
- Anything an agent reads to make decisions about *other* entities (e.g., the agent reads a tenant config to decide how to triage a work item, but never writes the tenant itself).

**Encrypted-field default:** when `readableProperties` is omitted, the agent reads every top-level property *except* those listed in `encryptedProperties`. To grant read access to an encrypted field, list it explicitly (see §4 below).

**No write access whatsoever.** Tier 1 is purely read-only. If the agent needs to write *any* property, the entity is tier 2 or 3.

### 2.3 Tier 2 — Collaborative (`ownedBy: shared`)

Both AI and humans may write. Conflicts are resolved last-writer-wins with audit trail.

```yaml
aiAccess:
  operations: [read, create, update]  # subset varies per entity
  writableProperties:
    - status
    - priority
    - notes
    # ... only the fields the agent is allowed to write
  immutableOnUpdate:
    - tenantId
    - customerId
  ownedBy: shared
  reason: >
    Triage agent classifies and prioritizes incoming items;
    humans curate the queue and adjust outcomes.
```

**When to use:**
- Operational entities where the agent assists but doesn't replace humans (work items, comments, activity logs, attachments).
- Configuration entities the agent helps initialize during onboarding but humans subsequently maintain (settings, templates, schedules).
- Entities where AI detects state changes and humans react, or vice versa.

**The shared write contract:**
- `writableProperties` is always an explicit allow-list. There is no "all fields" shortcut. Every field the agent is allowed to write must be enumerated.
- `immutableOnUpdate` is a subset of `writableProperties` covering fields the agent may set on create but never change on update. **Foreign keys to tenant/scope are always immutable on update** — AI must never re-parent a record across tenants.
- `reason` describes the business need in product language, not implementation language. ("Triage agent classifies incoming items" — not "the triage handler in `TriageWorker.cs` sets the status field").
- `ownedBy: shared` is the explicit declaration. The default would be inferred but writing it out keeps the tier visible at the point of use.

**Operations subset:** tier 2 uses whatever subset of `[read, create, update]` matches the agent's actual needs. Some entities are read+create only (the agent creates new records but never modifies existing ones); some are read+update only (the agent only annotates existing rows). Tailor the subset to the use case.

### 2.4 Tier 3 — AI-Owned (`ownedBy: ai`)

The AI agent is the system of record for the entity. Backend writes are advisory and reconciled against agent state.

```yaml
aiAccess:
  operations: [read, create, update]
  writableProperties:
    - status
    - confidence
    - reasoning
    - dataPoints
    # ... full owned surface
  immutableOnUpdate:
    - tenantId
  ownedBy: ai
  reason: >
    AI artifact. The recommendation agent generates suggestions
    end-to-end based on demand forecasting; humans accept or reject
    but do not author.
```

**When to use:**
- AI-generated artifacts that humans consume but don't author: suggestions, predictions, classifications, generated plans, model outputs.
- Entities whose business semantics are "the AI's view of the world" — overriding from the backend means the AI was wrong, not that humans were.
- Entities the agent owns end-to-end through their lifecycle (created by AI, transitioned by AI, archived by AI).

**The AI-owned contract:**
- `ownedBy: ai` declares the conflict-resolution authority. When a backend write contradicts agent state, the agent's view wins on reconciliation.
- The agent's `writableProperties` is typically broader than tier 2 — closer to the full editable surface of the entity — because the agent is the legitimate author of every field except scope/identity.
- `immutableOnUpdate` still includes scope foreign keys for the same tenant-isolation reason.
- `reason` makes the ownership explicit: "AI artifact" or "AI owns generation/lifecycle of this entity."

**Tier 3 is rare.** Most entities are tier 0, 1, or 2. Tier 3 is reserved for entities whose existence is justified by the agent's work.

---

## 3) Cross-Cutting Rules

These rules apply across all tiers and override per-entity convenience.

### 3.1 No `delete` for any tier

Soft-delete is the only delete in a Specfuse project (see [`API_Handbook.md §2`](./API_Handbook.md) deletion policy). Revoking records is a human decision: a soft-delete is reversible within the retention window via privileged internal APIs, and hard-delete only happens automatically after retention expires.

`aiAccess.operations` MUST NOT include `delete`. If an agent's job is "mark as deleted," express that as `update` on the `status` field (or whichever soft-delete marker the entity uses).

### 3.2 Encrypted fields excluded from implicit read

When `readableProperties` is omitted on a tier 1+ entity, the agent reads every top-level property *except* fields listed in `encryptedProperties` (or fields carrying `x-classification: [encrypted]`).

To grant AI read access to an encrypted field, list it explicitly in `readableProperties`:

```yaml
Customer:
  x-entity:
    encryptedProperties: [taxId]
    aiAccess:
      operations: [read]
      readableProperties:
        - firstName
        - lastName
        - email
        - phone
        - taxId   # Explicitly granted — not auto-included
      reason: >
        Tax-reconciliation agent needs the tax ID to match
        external accounting system records.
```

Masking rules on the wire still apply — encrypted fields surface masked unless the caller has the elevated privilege to see plaintext.

### 3.3 Foreign keys are always `immutableOnUpdate`

For any tier 2 or tier 3 entity, foreign-key scope fields (`tenantId`, parent-aggregate IDs, etc.) MUST appear in `immutableOnUpdate`. AI must never re-parent a record across tenants or move it under a different parent aggregate — that's a structural change that requires explicit human action.

Even if `writableProperties` includes a tenant scope field (so the agent can set it on create), `immutableOnUpdate` blocks the agent from changing it on update.

### 3.4 `reason` describes business need, not technology

The `reason` string surfaces in:
- Generated doc-comments on the AI repository class
- The project's AI manifest (audit reference)
- PR review diffs

It MUST describe the **business reason** the agent needs this access. It MUST NOT reference:
- Specific class names, files, modules, or namespaces ("the `TriageWorker.cs` handler sets...")
- Target language idioms ("the C# repository calls...")
- Specific AI provider, model, or agent implementation ("the GPT-4 prompt in `triage.prompt.md`...")

**Good:** "Triage agent creates work items from detected operational issues and updates status through the lifecycle."

**Bad:** "The `TriageHandler` Java class calls `WorkItemRepository.save()` after the Claude prompt returns."

The reason should still be true in five years even after the implementation changes three times.

### 3.5 Write requires `writableProperties` + `reason`

Whenever `operations` contains any of `create`, `update`, or `delete` (well — `delete` is forbidden per §3.1, so realistically `create` or `update`), both:
- `writableProperties` (non-empty) — explicit allow-list
- `reason` (non-empty, ≥ ~40 chars of business rationale)

…are required. The Spectral validator enforces this. There is no "all fields" write shortcut; every field must be enumerated.

### 3.6 `aiAccess` only on `x-entity` schemas

`aiAccess` may only appear on schemas that carry `x-entity` — i.e., main resource schemas (aggregates and entities). It must NOT appear on:
- Derivative schemas: `Basic{Resource}`, `New{Resource}`, `Update{Resource}`, `{Resource}List`, `{Resource}SearchRequest`
- Value-object schemas (`x-value-object`)
- Anonymous inline schemas

The same placement rules as other entity-level metadata.

---

## 4) `ownedBy` Semantics

`ownedBy` records the system of record when both AI and backend can write. It does not change *what* can write — only *who wins* when both do.

| Value | Conflict Resolution |
|-------|---------------------|
| `shared` (default) | Last-writer-wins with audit. The runtime logs both writes; the latest one persists. |
| `ai` | AI agent is authoritative. Backend writes are reconciled against agent state on the next agent pass. |
| `backend` | Backend is authoritative. AI writes are advisory and may be overridden by subsequent backend writes. |

### 4.1 When to use `shared`

The default for tier 2. Use when:
- Both AI and humans legitimately edit the entity in normal operation.
- No clear authority hierarchy — the more recent write reflects the more recent decision.
- The cost of a missed update is reversible (status revert, comment edit, tag change).

### 4.2 When to use `ai`

Use when:
- The entity exists because the agent produces it.
- A backend write that contradicts agent state is more likely to be wrong than the agent's view.
- The agent has a reconciliation loop that re-applies its intended state on the next pass.

Tier 3 entities almost always use `ownedBy: ai`. Tier 2 entities rarely do.

### 4.3 When to use `backend`

Use when:
- The backend is the canonical source (e.g., a system the agent has only advisory access to).
- AI suggestions should appear in the entity but be considered overridable by any backend write.
- The agent intentionally writes "best-effort" data the backend may correct.

This is uncommon. Most tier 2 entities use `shared`; if the backend is fully authoritative, the entity is likely tier 1 (read-only for AI) instead.

---

## 5) Future: Per-Agent Scoping

The single `aiAccess` block treats "AI" as monolithic. When a project has multiple agents with different trust levels (a low-trust triage agent and a high-trust orchestration agent both touching `WorkItem`, for example), this becomes a limitation.

The framework will extend to allow `aiAccess` keyed by agent role — without breaking the single-block form — when the need surfaces in production usage. Until then, the recommendation is to keep access conservative: the policy reflects the *least-trusted* agent that touches the entity, and the runtime enforces additional restrictions on more-restricted agents at the agent layer rather than the data layer.

If your project hits this limitation early, file a kit issue with the specific scenario — it shapes the extension design.

---

## 6) How to Classify a New Entity

Three questions, applied in order:

1. **Does any plausible AI capability need to *read* this entity?**
   - No → **Tier 0** (omit `aiAccess`)
   - Yes → continue

2. **Does any plausible AI capability need to *write* it?**
   - No → **Tier 1** (`operations: [read]`)
   - Yes → continue

3. **Is the AI the system of record?**
   - No → **Tier 2** (`ownedBy: shared`)
   - Yes → **Tier 3** (`ownedBy: ai`)

### 6.1 When in doubt, start more restrictive

Broadening access later is cheap (add fields to `writableProperties`, expand `operations`, raise the tier). Revoking access after agents depend on it is not — agents will have built workflows on top of the access, and removing it breaks them.

Default to:
- Tier 0 if you're unsure whether *any* agent will ever need it.
- Tier 1 if you know an agent will read it but you're unsure about writes.
- Tier 2 with the narrowest possible `writableProperties` if writes are needed.

The flowchart is biased toward restriction by design.

### 6.2 Edge cases

**The agent reads the entity to make decisions about another entity.** → Tier 1. Reading another entity to inform a write doesn't elevate this entity's tier.

**The agent creates the entity but never updates it.** → Tier 2 with `operations: [read, create]` (no `update`). The shared-write contract still applies, but `writableProperties` lists only the fields the agent populates on create.

**The agent creates suggestions that other code converts into "real" entities.** → The suggestion entity is tier 3 (`ownedBy: ai`). The downstream entity is tier 2 or whatever its independent classification dictates. They are separate decisions.

**An entity has both an AI-owned subset and a human-owned subset of fields.** → Tier 2 with `writableProperties` restricted to the AI-owned subset. The framework doesn't have a "tier 2.5" — explicit `writableProperties` is the lever.

**An entity is read by AI for now, but the project plans to add write access in six months.** → Tier 1 now. Revisit when the write access is actually needed. Don't pre-grant write capability "because we'll need it later" — the framework's safety stance is least-privilege at all times.

---

## 7) Relationship to Other Extensions

| Extension | Relationship |
|---|---|
| `x-entity` | `aiAccess` is a property of `x-entity`. See [`Vendor_Extensions.md §1.1.1`](./Vendor_Extensions.md). |
| `encryptedProperties` / `x-classification: [encrypted]` | Encrypted fields are excluded from the implicit read surface (§3.2). |
| `x-classification: [pii \| sensitive]` | PII/sensitive fields are not auto-excluded from AI read, but they trigger snapshot acknowledgement rules (`x-snapshot-pii-acknowledged`) when included in event snapshots. See `AsyncAPI_Handbook.md §2.3`. |
| `x-ai-safe` (operations) | Operates at the HTTP operation level — whether an AI agent may invoke a specific endpoint without approval. `aiAccess` operates at the entity/repository level — what the AI may touch via generated data-access code. The two are complementary; a tier 2 entity may still have endpoints that are not `x-ai-safe`. |
| `x-ai.entities` (AsyncAPI workers) | When an AsyncAPI worker declares `x-ai.entities.{reads,creates,updates,deletes}`, every listed entity MUST have a matching `aiAccess` block granting the corresponding operation. The cross-spec validator enforces this. See `AsyncAPI_Handbook.md §4.3`. |
| `filterableProperties` / `searchableProperties` | Govern HTTP query surfaces, not AI repository methods. AI filtering/search allow-lists are derived separately from `readableProperties`. |

---

## 8) Where to Find the Project's Tier Assignments

This handbook defines the framework. The project's concrete per-entity tier assignments live in a project-local document, typically `api/docs/{project}-ai-access-matrix.md` or similar — the kit provides a starter in [`templates/ai-access-policy-template.md`](../templates/ai-access-policy-template.md) which the project copies and fills in.

The matrix document lists every entity in the project and assigns it to a tier, with the YAML `aiAccess` block that gets added to its `x-entity`. It is the team-visible reference for what AI agents can do; the framework above is how those tiers are reasoned about.

When a new entity is added to the project, the team:
1. Applies the classification flowchart (§6) to pick a tier.
2. Updates the matrix document with the entity, its tier, and rationale.
3. Adds the corresponding `aiAccess` block to the entity's `x-entity` in the OpenAPI spec.
4. The Spectral validator enforces that the tier-shape and aiAccess-block-shape are consistent.

---

*This handbook is loaded as mandatory reading via `CLAUDE.md`. All `aiAccess` blocks in OpenAPI specs must comply with the framework defined here.*
