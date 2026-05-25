# Specfuse Spec-Authoring Kit

The upstream contract for [Specfuse](https://github.com/Specfuse) projects. Defines the conventions, vendor extensions, and authoring workflows that the Specfuse code generator consumes to produce backend, frontend, and worker artifacts from OpenAPI + AsyncAPI + Arazzo specifications.

## What this kit provides

- **Handbooks** (`handbooks/`) — authoritative rules for REST, async, and behavioral spec authoring.
- **Samples** (`samples/`) — canonical YAML templates for endpoints, messages, scenarios, and recipes.
- **Schemas** (`schemas/`) — Spectral lint rules and JSON schemas for validation.
- **Templates** (`templates/`) — `project-init/` skeleton for bootstrapping new Specfuse projects, plus an AI Access Policy template.
- **Claude assets** (`claude-assets/`) — Claude Code agents, commands, and skills that automate authoring workflows.
- **Bundled example** (`examples/hello-orders/`) — a small, complete, generic Specfuse project demonstrating the full surface and serving as the kit's regression net.

## Status

**Private, incubating.** This kit is currently hosted under `clabonte/spec-authoring-kit` while the first generalization pass is audited for leakage from its source project (RestoManager). It will transfer to `Specfuse/spec-authoring-kit` once the first external consumer has bootstrapped successfully and no source-project artifacts remain.

## Relationship to other Specfuse repos

```
spec-authoring-kit  ◄── this repo (rules, samples, templates)
       ▲
       │ consumes
       │
   ┌───┴────────────────┐
   │                    │
generator           orchestrator
(Java/Kotlin —      (filesystem-based
 produces code      multi-agent workflow
 from specs)        coordination)
```

The kit is upstream of both: it defines *what* a Specfuse spec must look like. The generator consumes those specs to emit code. The orchestrator coordinates the multi-agent authoring workflow that produces those specs.

## Quick start (placeholder — populated in Phase 5)

```bash
# Clone the kit
git clone git@github.com:clabonte/spec-authoring-kit.git
# Bootstrap a new project from templates/project-init/
# (init.sh to be added in Phase 5)
```

See `compatibility.md` for the kit ↔ generator version matrix.
