<!--
Copyright 2026 Specfuse Contributors
Licensed under the Apache License, Version 2.0. See LICENSE.
-->

# Getting started

This guide takes you from zero to a generated backend: install the kit, bootstrap a project, author your first domain, validate it, and run the generator.

## 1. Prerequisites

| Tool | Why | Check |
|---|---|---|
| **Python 3.10+** | runs the `specfuse-authoring` CLI | `python3 --version` |
| **[pipx](https://pipx.pypa.io/)** | installs the CLI as an isolated app | `pipx --version` |
| **Java 17+ (JRE)** | the code generator is a Java binary | `java -version` |
| **[Claude Code](https://claude.com/claude-code)** (optional) | the `/specfuse-authoring:*` authoring skills | — |
| **GitHub access token** | only needed to run `generate` (pulls the private generator) | see §6 |

You do **not** need to clone this repo. The CLI ships every kit asset (handbooks, samples, templates, schemas) inside the package, and the Claude Code authoring assets ship as the `specfuse-authoring` plugin in the `specfuse/specfuse` marketplace.

## 2. Install the CLI and bootstrap a project

```bash
pipx install specfuse-authoring     # recommended (isolated CLI app)
#   (or, inside a venv you control: python3 -m pip install specfuse-authoring)
specfuse-authoring init ~/projects/my-app
```

> A bare `pip install` into a system Python is blocked on PEP-668 externally-managed environments (Debian/Ubuntu, Homebrew). Use `pipx` (then `pipx upgrade specfuse-authoring`) or a virtualenv.

> **If you already run the `specfuse` umbrella CLI, install the kit through it instead:** `pipx install --force --include-deps 'specfuse[all]'`. The umbrella's `authoring` extra and this standalone package both provide a `specfuse-authoring` command, and pipx refuses to point one venv's shim at another's — it warns `File exists at ~/.local/bin/specfuse-authoring and points to … Not modifying.` and moves on. The result is a command that silently keeps running the install you *didn't* just upgrade. Run `specfuse doctor` (umbrella 0.9.4+) to see which install owns each command.

You'll be prompted for three things (or pass them as flags for non-interactive use):

| Prompt | Flag | Example | Rules |
|---|---|---|---|
| Project name | `--name` | `my-app` | kebab-case |
| Project token | `--token` | `myapp` | lowercase alphanumeric, no dots — used as the channel-address prefix (`myapp.events`) |
| Initial domain | `--domain` | `order` | kebab-case |

```bash
specfuse-authoring init ~/projects/my-app --name my-app --token myapp --domain order
```

This creates a complete project skeleton: the `api/specs/v1/` tree, a `{name}-project.json` generator config, a `CLAUDE.md`, the authoring contract (handbooks + samples) scaffolded into `.specfuse/authoring/`, and a `.claude/settings.json` wired to the `specfuse-authoring` plugin.

```bash
cd ~/projects/my-app
git init && git add . && git commit -m "Initial bootstrap from spec-authoring-kit"
```

### Install the authoring plugin

The design and validation skills (and the 5 design sub-agents) ship as the `specfuse-authoring` plugin in the shared `specfuse` marketplace. `init` auto-wires the plugin into `.claude/settings.json`, but install it once in Claude Code with:

```
/plugin marketplace add specfuse/specfuse
/plugin install specfuse-authoring@specfuse
```

The skills read the authoring contract from `.specfuse/authoring/` (scaffolded by `init`).

## 3. Author your first domain

The [handbooks](../handbooks/) are the authoritative spec-authoring contract. Start here:

| To design… | Read | Command |
|---|---|---|
| An entity or endpoint | [`API_Handbook.md`](../handbooks/API_Handbook.md) + [`samples/endpoint-samples.yaml`](../samples/endpoint-samples.yaml) | author by hand |
| An async event / scheduled job | [`AsyncAPI_Handbook.md`](../handbooks/AsyncAPI_Handbook.md) | `/specfuse-authoring:design-async` |
| A cross-domain scenario | [`Arazzo_Handbook.md`](../handbooks/Arazzo_Handbook.md) | `/specfuse-authoring:design-scenario` |
| A setup recipe | [`Arazzo_Handbook.md`](../handbooks/Arazzo_Handbook.md) §7 | `/specfuse-authoring:design-recipe` |
| AI agent access policy | [`AI_Access_Policy_Framework.md`](../handbooks/AI_Access_Policy_Framework.md) | copy the template |

The skills run inside Claude Code in your project directory. The bundled [`examples/hello-orders/`](../examples/hello-orders/) is a complete worked reference — pattern-match against it.

> **`aiAccess` is required on every entity.** Each `x-entity` must declare an `aiAccess` block. For entities the AI must not touch, use the canonical Tier 0 form `operations: []` with a `reason`. See `Vendor_Extensions.md` §1.1.1.

## 4. Validate

Inside Claude Code, the kit's skills validate your specs against the handbook rules:

```
/specfuse-authoring:validate            # OpenAPI surface
/specfuse-authoring:validate-async      # AsyncAPI messages and operations
/specfuse-authoring:validate-scenarios  # Arazzo scenarios and recipes
```

## 5. Generate code

The generator turns your validated specs into backend, frontend, and worker artifacts:

```bash
specfuse-authoring generate <args>
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

When the kit ships an update, pull it into your project:

```bash
specfuse-authoring upgrade ~/projects/my-app
```

Add `--dry-run` to see what would change before anything is written.

This overlays the kit-owned files from the installed package — the handbooks, samples and Spectral schemas under `.specfuse/authoring/`, plus the `scripts/` tooling the skills call — and re-asserts the plugin config in `.claude/settings.json`. **Your specs are never touched**: `api/`, `CLAUDE.md`, your project file and `.gitignore` are seeded once at `init` and owned by you thereafter.

### What upgrade will and will not do

`upgrade` records a sha256 of every file it writes in `.specfuse/authoring/.scaffold-manifest`. That record is what lets it tell three otherwise identical-looking files apart:

| Situation | What happens |
|---|---|
| Kit file, untouched | Replaced silently |
| Kit file you edited | Replaced, with a warning naming the file |
| File the kit never wrote, sitting in a kit directory | **Kept**, with a note — never deleted |
| Kit file dropped from a newer release | Removed, but only because the manifest proves the kit wrote it |

So edits to shipped handbooks or scripts do not survive an upgrade — that is the contract, and the warning tells you which file lost changes. Send improvements upstream instead (see [`CONTRIBUTING.md`](../CONTRIBUTING.md)).

A project scaffolded by a **newer** kit than the one installed is refused rather than rolled back:

```
Error: refusing downgrade: … was scaffolded by kit 0.6.0, but the installed kit is 0.5.5.
Upgrade the CLI first: pipx upgrade specfuse-authoring
```

Projects created before the overlay existed have no manifest. They are adopted on first `upgrade` — it reports `kit unversioned -> <version>`, writes everything, and stays quiet about pre-existing edits it has no baseline for.

To pull newer skills themselves, run `/plugin update specfuse-authoring@specfuse` inside Claude Code.

## Where to go next

- [`README.md`](../README.md) — kit overview and asset map
- [`handbooks/`](../handbooks/) — the full authoring contract
- [`examples/hello-orders/`](../examples/hello-orders/) — a complete worked project
- [`compatibility.md`](../compatibility.md) — kit ↔ generator version matrix
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — contributing back to the kit
