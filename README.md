# Specfuse Spec-Authoring Kit

The upstream contract for [Specfuse](https://github.com/Specfuse) projects. Defines the conventions, vendor extensions, and authoring workflows that the Specfuse code generator consumes to produce backend, frontend, and worker artifacts from OpenAPI 3.0.3 + AsyncAPI 3.0.0 + Arazzo 1.0.1 specifications.

## Quick start

Bootstrap a new Specfuse project with the Specfuse CLI:

```bash
pipx install specfuse                # the whole suite; no extras, no flags
#   (or: uv tool install specfuse)
specfuse authoring init ~/projects/my-new-project
```

The kit is one component of the Specfuse suite, and the suite is driven through
the single `specfuse` command — `specfuse authoring …` is this kit. Installing
`specfuse` brings the kit with it, and `pipx upgrade specfuse` (or `uv tool
upgrade specfuse`) pulls every component's new release.

> **Standalone use.** `pip install specfuse-authoring` still works if you want
> the kit alone or as a library, and its flat `specfuse-authoring` command is
> kept as a deprecated alias until 1.0.0 — drop the `specfuse ` prefix from
> every command below. Do not install both ways: the two installs provide the
> same flat command name, so whichever claimed `~/.local/bin` first is what
> runs, and upgrading the other changes nothing. `specfuse doctor` reports which
> install owns each command.

You'll be prompted for the project name, the project token (channel-address prefix), and the initial domain. The CLI substitutes placeholders, scaffolds the authoring contract (handbooks + samples + Spectral schemas) into `.specfuse/authoring/`, wires the `specfuse-authoring` Claude Code plugin into `.claude/settings.json`, and prints next steps. Pass `--name`/`--token`/`--domain` to run non-interactively.

The Claude Code authoring assets (skills + agents) ship as the `specfuse-authoring` plugin in the shared `specfuse` marketplace. `init` auto-wires the plugin, but you install it once in Claude Code with:

```
/plugin marketplace add specfuse/specfuse
/plugin install specfuse-authoring@specfuse
```

To pull a kit update into an existing project — handbooks, samples, schemas and the `scripts/` tooling:

```bash
specfuse authoring upgrade ~/projects/existing-project
specfuse authoring upgrade ~/projects/existing-project --dry-run   # preview first
```

Your specs are never touched. `upgrade` tracks what it wrote (`.specfuse/authoring/.scaffold-manifest`), so it replaces kit files, warns before overwriting one you edited, and never deletes a file it did not create. (`refresh` is a deprecated alias.)

Pull newer skills with `/plugin update specfuse-authoring@specfuse`.

See [`examples/hello-orders/`](examples/hello-orders/) for a complete worked example.

## What's in the kit

| Asset | Contents |
|---|---|
| **Handbooks** ([`handbooks/`](handbooks/)) | 6 authoritative documents: REST API, AsyncAPI, Arazzo, vendor extensions, AI access policy framework, and the generator's project file. Together these define the full spec-authoring contract. |
| **Samples** ([`samples/`](samples/)) | 4 canonical YAML templates — endpoints, async messages, scenarios, recipes — that every authored file should pattern-match against. |
| **Schemas** ([`schemas/`](schemas/)) | Working Spectral rulesets and custom functions for validation under `schemas/spectral/`. CI lints the bundled example against them. [`schemas/README.md`](schemas/README.md) also covers how to run Spectral so a crash cannot pass as a clean spec, and how to turn the ruleset on against specs that predate it. |
| **Templates** ([`templates/`](templates/)) | The `project-init/` skeleton, plus the AI Access Policy template. |
| **Claude assets** | 5 Claude Code sub-agents and 20 authoring skills (`/specfuse-authoring:design-scenario`, `/specfuse-authoring:design-async`, `/specfuse-authoring:design-recipe`, etc.) that automate spec design. Distributed as the `specfuse-authoring` plugin in the `specfuse/specfuse` marketplace; `init` wires the plugin and scaffolds the contract the skills read into `.specfuse/authoring/`. |
| **Bundled example** ([`examples/hello-orders/`](examples/hello-orders/)) | A 61-file complete Specfuse project — 2 domains, 3 entities, 1 state-transition event, 1 cross-domain scenario, 2 setup recipes, filled AI access policy, CI workflow. Serves as the kit's regression net. |

## Where to start

| You want to… | Read first | Then run |
|---|---|---|
| Bootstrap a new project | [`docs/getting-started.md`](docs/getting-started.md) | `specfuse authoring init <target-dir>` |
| Design your first scenario | [`handbooks/Arazzo_Handbook.md`](handbooks/Arazzo_Handbook.md) | `/specfuse-authoring:design-scenario` |
| Author a new entity or endpoint | [`handbooks/API_Handbook.md`](handbooks/API_Handbook.md) + [`samples/endpoint-samples.yaml`](samples/endpoint-samples.yaml) | (no kit command yet — author by hand) |
| Design an async event or scheduled job | [`handbooks/AsyncAPI_Handbook.md`](handbooks/AsyncAPI_Handbook.md) + [`samples/message-samples.yaml`](samples/message-samples.yaml) | `/specfuse-authoring:design-async` |
| Add a setup recipe | [`handbooks/Arazzo_Handbook.md`](handbooks/Arazzo_Handbook.md) §7 + [`samples/recipe-samples.yaml`](samples/recipe-samples.yaml) | `/specfuse-authoring:design-recipe` |
| Configure AI agent access | [`handbooks/AI_Access_Policy_Framework.md`](handbooks/AI_Access_Policy_Framework.md) + [`templates/ai-access-policy-template.md`](templates/ai-access-policy-template.md) | (copy template into project) |
| Look up a `x-*` extension | [`handbooks/Vendor_Extensions.md`](handbooks/Vendor_Extensions.md) | — |
| Configure the generator project file | [`handbooks/Project_File.md`](handbooks/Project_File.md) | — |
| See a complete worked example | [`examples/hello-orders/README.md`](examples/hello-orders/README.md) | — |

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

## Status

**Incubating** (`v0.7.0`), Apache-2.0. Handbooks, samples, schemas, the `project-init` template, the bundled `hello-orders` example, the `specfuse-authoring` plugin (in the `specfuse/specfuse` marketplace), and the `specfuse authoring` CLI are all in place. Generator-side alignment items are tracked in [`compatibility.md`](compatibility.md#outstanding-generator-side-follow-ups).

The kit is distributed on PyPI as `specfuse-authoring` and hosted under [`Specfuse/authoring`](https://github.com/Specfuse/authoring). The code generator it drives is distributed separately as a pinned, checksum-verified release asset (see [`generator.lock`](generator.lock)); `specfuse authoring generate` resolves, verifies, and runs it on demand.

## Additional references

- [`compatibility.md`](compatibility.md) — kit ↔ generator version matrix and outstanding generator-side follow-ups.
- [`provenance.md`](provenance.md) — bug-and-PR history that motivated each vendor extension. Kit-maintainer audit trail; external consumers do not need the referenced PRs to resolve.
