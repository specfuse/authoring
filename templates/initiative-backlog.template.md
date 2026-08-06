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
dossier to `ready`), `backlog-groom` (periodic triage). The orchestrator's
`features/INIT-*.md` registries and `roadmap.md` are downstream and never read
this file — the seam is the human running intake on a `ready` (or bundled) item.

| Idea     | Title    | State | Repos     | Dossier | INIT |
|----------|----------|-------|-----------|---------|------|
| IDEA-001 | <title>  | idea  | <repos?>  | [`backlog/IDEA-001-<slug>.md`](backlog/IDEA-001-<slug>.md) | — |

State: `idea` → `shaping` → `ready` → `minted` (or `parked` / `dropped`).
`ready` means the dossier's readiness checklist is fully checked — only then is it
intake-eligible. A bundled idea shows the lead's INIT once the bundle is minted.

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
- **Graduation is `initiative-intake`, not a backlog skill.** When an item is
  `ready`, the human/specs agent runs intake; intake reads the dossier(s), mints
  the INIT, and this row (and any bundled rows) flip to `minted`. The backlog
  never mints.
