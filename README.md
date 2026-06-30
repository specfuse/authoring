# Specfuse Spec-Authoring Kit

The upstream contract for [Specfuse](https://github.com/Specfuse) projects. Defines the conventions, vendor extensions, and authoring workflows that the Specfuse code generator consumes to produce backend, frontend, and worker artifacts from OpenAPI 3.0.3 + AsyncAPI 3.0.0 + Arazzo 1.0.1 specifications.

## Quick start

Bootstrap a new Specfuse project with the kit's CLI:

```bash
uvx specfuse-kit init ~/projects/my-new-project
# or: pipx run specfuse-kit init ~/projects/my-new-project
```

You'll be prompted for the project name, the project token (channel-address prefix), and the initial domain. The CLI substitutes placeholders, copies the kit's Claude Code agents and commands into the new project's `.claude/`, and prints next steps. Pass `--name`/`--token`/`--domain` to run non-interactively.

To refresh agents and commands in an existing project after a kit update:

```bash
uvx specfuse-kit refresh ~/projects/existing-project
```

(The legacy `templates/project-init/init.sh` bash bootstrap still works for git-clone workflows.)

See [`templates/project-init/README.md`](templates/project-init/README.md) for the full bootstrap reference and [`examples/hello-orders/`](examples/hello-orders/) for a complete worked example.

## What's in the kit

| Asset | Contents |
|---|---|
| **Handbooks** ([`handbooks/`](handbooks/)) | 6 authoritative documents: REST API, AsyncAPI, Arazzo, vendor extensions, AI access policy framework, and the generator's project file. Together these define the full spec-authoring contract. |
| **Samples** ([`samples/`](samples/)) | 4 canonical YAML templates — endpoints, async messages, scenarios, recipes — that every authored file should pattern-match against. |
| **Schemas** ([`schemas/`](schemas/)) | *(Forthcoming.)* Spectral lint rules and JSON Schemas for validation. |
| **Templates** ([`templates/`](templates/)) | The `project-init/` skeleton with `init.sh` bootstrap script, plus the AI Access Policy template. |
| **Claude assets** ([`claude-assets/`](claude-assets/)) | 5 Claude Code sub-agents and 20 slash commands (`/design-scenario`, `/design-async`, `/design-recipe`, etc.) that automate spec design. Copied into each project on bootstrap. |
| **Bundled example** ([`examples/hello-orders/`](examples/hello-orders/)) | A 61-file complete Specfuse project — 2 domains, 3 entities, 1 state-transition event, 1 cross-domain scenario, 2 setup recipes, filled AI access policy, CI workflow. Serves as the kit's regression net. |

## Where to start

| You want to… | Read first | Then run |
|---|---|---|
| Bootstrap a new project | [`templates/project-init/README.md`](templates/project-init/README.md) | `init.sh <target-dir>` |
| Design your first scenario | [`handbooks/Arazzo_Handbook.md`](handbooks/Arazzo_Handbook.md) | `/design-scenario` |
| Author a new entity or endpoint | [`handbooks/API_Handbook.md`](handbooks/API_Handbook.md) + [`samples/endpoint-samples.yaml`](samples/endpoint-samples.yaml) | (no kit command yet — author by hand) |
| Design an async event or scheduled job | [`handbooks/AsyncAPI_Handbook.md`](handbooks/AsyncAPI_Handbook.md) + [`samples/message-samples.yaml`](samples/message-samples.yaml) | `/design-async` |
| Add a setup recipe | [`handbooks/Arazzo_Handbook.md`](handbooks/Arazzo_Handbook.md) §7 + [`samples/recipe-samples.yaml`](samples/recipe-samples.yaml) | `/design-recipe` |
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

**Incubating** (`v0.3`), Apache-2.0. Handbooks, samples, claude-assets, the `project-init` template, the bundled `hello-orders` example, and the `specfuse-kit` CLI are all in place. Generator-side alignment items are tracked in [`compatibility.md`](compatibility.md#outstanding-generator-side-follow-ups).

The kit is distributed on PyPI as `specfuse-kit` and hosted under [`Specfuse/spec-authoring-kit`](https://github.com/Specfuse/spec-authoring-kit). The code generator it drives is distributed separately as a pinned, checksum-verified release asset (see [`generator.lock`](generator.lock)); `specfuse-kit generate` resolves, verifies, and runs it on demand.

## Additional references

- [`compatibility.md`](compatibility.md) — kit ↔ generator version matrix and outstanding generator-side follow-ups.
- [`provenance.md`](provenance.md) — bug-and-PR history that motivated each vendor extension. Kit-maintainer audit trail; external consumers do not need the referenced PRs to resolve.
