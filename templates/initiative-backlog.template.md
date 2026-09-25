# Initiative ideation backlog

The pre-intake fuzzy front end. Candidate initiatives live here while they are
shaped — *before* an `INIT-YYYY-NNNN` is minted. This is the one lifecycle stage
upstream of the initiative registry: an idea is captured, shaped to `ready`, and
then **graduates** via the specs agent's `initiative-intake` skill, which mints
the `INIT-` id and starts the `drafting → validating → planning` lifecycle. On
graduation the row flips to `minted` and links its INIT — the row stays as a
breadcrumb; the registry and roadmap take over from there.

This file is the **thin index**. Each idea's real shaping material — the
considerations, references, constraints, bundling, and mint plan — lives in a
**per-idea dossier** under `docs/product/backlog/IDEA-NNN-<slug>.md`
([dossier template](initiative-idea-dossier.template.md)). The index row carries
only what you need to scan and prioritize; the dossier is where the thinking
happens. One fact, one home: the row owns *state + pointer*, the dossier owns
*content*.

This file lives in the **specs repo** (`docs/product/`) because product ideation
happens here. Created and maintained by the **specs agent** via three skills:
`ideation-capture` (append a row + stub dossier), `ideation-shape` (work the
dossier to `ready`), `ideation-groom` (periodic triage). The orchestrator's
`features/INIT-*.md` registries and `roadmap.md` are downstream and never read
this file — the seam is the human running intake on a `ready` (or bundled) item.

| Idea     | Title    | State | Repos     | Dossier | INIT |
|----------|----------|-------|-----------|---------|------|
| IDEA-001 | <title>  | idea  | <repos?>  | [`backlog/IDEA-001-<slug>.md`](backlog/IDEA-001-<slug>.md) | — |

State: `idea` → `shaping` → `ready` → `specified` → `minted` (or `delivered` /
`parked` / `dropped`). `ready` means the dossier's readiness checklist is fully
checked — only then is it cleared to have its specs authored. **`specified`, not
`ready`, is the intake-eligible state.** A bundled idea shows the lead's INIT
once the bundle is minted.

## IDEA-001 — <title>

<One-line summary — what this idea is, in a single sentence. Everything else lives
in the dossier.>

**Dossier:** [`backlog/IDEA-001-<slug>.md`](backlog/IDEA-001-<slug>.md) · **State:** idea

## Notes

- **Backlog IDs (`IDEA-NNN`) are transient.** Not correlation IDs — they exist only
  until an idea graduates, when the minted `INIT-YYYY-NNNN` becomes the durable
  identity. Allocate sequentially; do not reuse retired IDs.
- **One idea ↔ one dossier ↔ one row.** Several ideas can fold into one initiative:
  the lead dossier declares `bundles: [IDEA-NNN, …]`; at mint, every bundled row
  flips to `minted` pointing at the same `INIT-`. Bundling is decided in
  `ideation-shape`, recorded in the dossier — never inferred.
- **Capture is cheap; shaping is where the work is.** A one-line `idea` row with a
  stub dossier is a valid, encouraged state — the backlog's job is to lose no idea.
- **`parked`** = good idea, wrong time (keep, revisit at groom). **`dropped`** =
  decided against (keep the row + dossier with a one-line why, so it isn't
  re-proposed).
- **`specified` means the specs exist and a decision is owed.** A loop feature
  authored them under gates, `prepare-handoff` published a manifest, and the
  dossier records both (`graduated_to`, `handoff`). It is a **waypoint, never a
  terminus**: an aging `specified` row means nobody has decided, which is an
  unambiguous signal precisely because the state carries no second meaning.
- **`delivered` is the terminal for spec-only work.** Some ideas' whole
  deliverable IS the spec tree; minting an `INIT-` no component repo will
  implement invents a registry entry that does nothing. `delivered` is a
  deliberate act a human records, not a state a row decays into — which is why
  it is separate from `specified` rather than folded into it. It is the
  backlog's `done`: every other lifecycle here separates parked-and-resumable
  from ended, and before this the only *successful* ending was `minted`.
- **Why authoring the specs is not a backlog state.** It happens in a loop
  feature, inside the gate cycle — human work-unit review at `arm-gate`, the
  validation oracle, the whole-tree-validates and structural-assertion rules
  (`.specfuse/docs/methodology.md` §10, spec front-end `authored`). A backlog
  state offers none of that. `graduated_to` records *that* a feature is doing
  it; the feature is *how*.
- **Graduation is `initiative-intake`, not a backlog skill.** When an item is
  `specified`, the human/specs agent runs intake; intake reads the dossier(s) —
  and the handoff manifest when there is one — mints the INIT, and this row (and
  any bundled rows) flip to `minted`. The backlog never mints.
- **Specs before the mint, by default.** Decomposing an initiative into per-repo
  features is a function of the spec surface: which entities, operations, events
  and scopes exist. None of that is knowable at mint time from a dossier, so
  minting first makes the orchestrator's opening move rediscovering a shape that
  could have been authored upstream under gates. The older order — mint, then
  draft specs inside the `INIT-` — stays legal and stays right where the specs
  are small relative to the implementation. What is never right is dispatching
  implementation against specs that do not exist.
