---
idea_id: IDEA-NNN
slug: <kebab-slug>
state: idea          # idea | shaping | ready | minted | parked | dropped
target_repos: []     # owner/repo guesses; must be non-empty to reach `ready`
autonomy_guess: review   # auto | review | supervised — becomes intake's autonomy_default
bundles: []          # IDEA-NNN ids folded INTO this one (this is the lead); else empty
bundled_into: null   # set on a follower: the lead IDEA-NNN this folds into
minted_init: null    # set on graduation: the INIT-YYYY-NNNN this became
---

# IDEA-NNN — <title>

> Per-idea shaping dossier. The thinking workspace for turning this idea (alone or
> bundled with others) into a mintable initiative. The backlog index
> (`../INITIATIVE_BACKLOG.md`) carries only this idea's row + one-liner; everything
> substantive lives here. Worked by `ideation-shape`; read by `initiative-intake`
> at graduation. Fill what you can, leave honest placeholders for the rest — a thin
> dossier is a valid `idea`-state dossier.

## Context & motivation

<Where this came from and why it matters. The deeper why behind the one-liner — the
pain/opportunity, who raised it, what triggered it. More than the index summary.>

## Value & outcome

<The user-observable outcome if built. Who benefits, how, and the one signal that
would tell us it worked.>

## Considerations

<The open design space — approaches to weigh, tradeoffs, alternatives, "what to
think about" before this is mintable. This is the heart of the dossier: the
judgment calls a future drafter/PM should not have to rediscover. Bullets fine.>

## References & sources to use

<What material to pull when this graduates to `drafting`. Link them now so they're
not re-hunted later:>

- Business/domain narratives: `docs/business/…`, `docs/product/…`
- Existing specs that overlap or constrain: `/product/…` (OpenAPI/AsyncAPI/Arazzo)
- Prior art / external references / tickets / conversations
- Any handoff manifest or scenario this would extend

## Constraints

<Hard boundaries the initiative must respect: tenancy, security/AI-access policy,
compliance, technical limits, dependencies on not-yet-built surfaces. The things
that would make a naive plan wrong.>

## Affected domains & repos

<Which product domains this touches and which component repos it would span (the
basis for the registry's `involved_repos`). Surface-level guesses, not an
operation inventory — that's `drafting`'s job.>

## Related ideas & bundling

<Relationships to other backlog ideas. If this idea should be minted *together*
with others as one initiative, name them and say why the bundle is one initiative
and not several. Set `bundles:`/`bundled_into:` in the frontmatter to match. If it
stands alone, say so.>

## Sizing & risk

<Rough size (small / medium / large initiative). The scary parts — what's hardest to
spec, verify, or get right. What could make this balloon.>

## Out of scope (rough)

<The boundary — what this explicitly does not cover, so the eventual initiative stays
bounded enough to mint and decompose.>

## Open questions

<Unknowns. Mark each **[blocking]** (must resolve before `ready`) or **[carry]**
(can ride into `drafting`). A `ready` dossier has no `[blocking]` left open.>

## Readiness (all four → `ready`)

- [ ] Problem stated (a real pain/opportunity, not a solution in disguise)
- [ ] Value clear (one-sentence user-observable outcome)
- [ ] Rough scope + boundary (in and out, coarse but bounded)
- [ ] Target repos named (which components it spans)

## Mint plan

<The bridge to `initiative-intake` — what intake will consume when this graduates.
Keep it in intake's own input shape so the handoff is mechanical:>

- **Proposed title:** <free-form initiative title>
- **`involved_repos`:** <list — mirrors `target_repos` once settled>
- **`autonomy_default`:** <auto | review | supervised>
- **Scope sentence:** <one sentence intake can seed the registry Description with>
- **Bundled ideas folded in:** <IDEA-NNN list, or none>

## Decision log

<Dated shaping decisions, newest last, so the reasoning is auditable when this is
minted weeks later. e.g. `2026-06-07 — folded IDEA-004 in; both are one rostering
surface.`>
