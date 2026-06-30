<!--
Copyright 2026 Specfuse Contributors
Licensed under the Apache License, Version 2.0. See LICENSE.
-->

# Getting started

This guide takes you from zero to a generated backend: install the kit, bootstrap a project, author your first domain, validate it, and run the generator.

## 1. Prerequisites

| Tool | Why | Check |
|---|---|---|
| **Python 3.10+** | runs the `specfuse-kit` CLI | `python3 --version` |
| **[uv](https://docs.astral.sh/uv/)** or **[pipx](https://pipx.pypa.io/)** | runs the CLI without a global install | `uvx --version` / `pipx --version` |
| **Java 17+ (JRE)** | the code generator is a Java binary | `java -version` |
| **[Claude Code](https://claude.com/claude-code)** (optional) | the `/design-*` authoring commands | — |
| **GitHub access token** | only needed to run `generate` (pulls the private generator) | see §6 |

You do **not** need to clone this repo. The CLI ships every kit asset (handbooks, samples, templates, Claude assets) inside the package.

## 2. Bootstrap a project

```bash
uvx specfuse-kit init ~/projects/my-app
```

You'll be prompted for three things (or pass them as flags for non-interactive use):

| Prompt | Flag | Example | Rules |
|---|---|---|---|
| Project name | `--name` | `my-app` | kebab-case |
| Project token | `--token` | `myapp` | lowercase alphanumeric, no dots — used as the channel-address prefix (`myapp.events`) |
| Initial domain | `--domain` | `order` | kebab-case |

```bash
uvx specfuse-kit init ~/projects/my-app --name my-app --token myapp --domain order
```

This creates a complete project skeleton: the `api/specs/v1/` tree, a `{name}-project.json` generator config, a `CLAUDE.md`, and a `.claude/` folder with the kit's design agents and slash commands.

```bash
cd ~/projects/my-app
git init && git add . && git commit -m "Initial bootstrap from spec-authoring-kit"
```

## 3. Author your first domain

The [handbooks](../handbooks/) are the authoritative spec-authoring contract. Start here:

| To design… | Read | Command |
|---|---|---|
| An entity or endpoint | [`API_Handbook.md`](../handbooks/API_Handbook.md) + [`samples/endpoint-samples.yaml`](../samples/endpoint-samples.yaml) | author by hand |
| An async event / scheduled job | [`AsyncAPI_Handbook.md`](../handbooks/AsyncAPI_Handbook.md) | `/design-async` |
| A cross-domain scenario | [`Arazzo_Handbook.md`](../handbooks/Arazzo_Handbook.md) | `/design-scenario` |
| A setup recipe | [`Arazzo_Handbook.md`](../handbooks/Arazzo_Handbook.md) §7 | `/design-recipe` |
| AI agent access policy | [`AI_Access_Policy_Framework.md`](../handbooks/AI_Access_Policy_Framework.md) | copy the template |

The slash commands run inside Claude Code in your project directory. The bundled [`examples/hello-orders/`](../examples/hello-orders/) is a complete worked reference — pattern-match against it.

> **`aiAccess` is required on every entity.** Each `x-entity` must declare an `aiAccess` block. For entities the AI must not touch, use the canonical Tier 0 form `operations: []` with a `reason`. See `Vendor_Extensions.md` §1.1.1.

## 4. Validate

Inside Claude Code, the kit's commands validate your specs against the handbook rules:

```
/validate            # OpenAPI surface
/validate-async      # AsyncAPI messages and operations
/validate-scenarios  # Arazzo scenarios and recipes
```

## 5. Generate code

The generator turns your validated specs into backend, frontend, and worker artifacts:

```bash
uvx specfuse-kit generate <args>
```

On first run the CLI resolves the generator pinned for your kit version (see [`generator.lock`](../generator.lock)), downloads it, **verifies its SHA-256**, caches it under `~/.specfuse/jars/`, and runs it. Subsequent runs use the cache.

## 6. Generator access (token setup)

The generator is distributed as a private release asset. To pull it, the CLI needs **one** of:

- **GitHub CLI** — install [`gh`](https://cli.github.com/) and `gh auth login`. The CLI uses it transparently. *(recommended)*
- **A token** — export a GitHub token with read access to the generator-distribution repo:
  ```bash
  export SPECFUSE_TOKEN=ghp_xxx
  ```

Your kit maintainer issues the access. Revoking the token revokes the generator; the kit itself stays usable. The cache and config live under `~/.specfuse/` (override with `$SPECFUSE_HOME`). Full setup, CI tokens, and troubleshooting: [`generator-access.md`](generator-access.md).

If no generator is pinned yet for your kit version, `generate` exits with a clear message — upgrade the kit once a generator-bearing release is available.

## 7. Keep assets current

When the kit ships an update, refresh your project's design agents and commands:

```bash
uvx specfuse-kit refresh ~/projects/my-app
```

This re-copies `.claude/agents/` and `.claude/commands/` from the installed kit. Your specs are never touched.

## Where to go next

- [`README.md`](../README.md) — kit overview and asset map
- [`handbooks/`](../handbooks/) — the full authoring contract
- [`examples/hello-orders/`](../examples/hello-orders/) — a complete worked project
- [`compatibility.md`](../compatibility.md) — kit ↔ generator version matrix
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — contributing back to the kit
