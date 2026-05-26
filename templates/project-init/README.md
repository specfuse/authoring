# Project-Init Template

Bootstrap a new Specfuse project from this template. The `init.sh` script copies the skeleton into a target directory, substitutes project-specific placeholders, and wires the kit's Claude Code agents and commands into the new project's `.claude/`.

## Usage

From the kit root:

```bash
./templates/project-init/init.sh <target-directory>
```

You'll be prompted for:

- **Project name** (kebab-case, e.g. `my-app`) — used in the generator config filename, OpenAPI/AsyncAPI titles, and CLAUDE.md.
- **Project token** (lowercase, no dots, e.g. `myapp`) — used as the channel-address prefix (`{token}.events`, `{token}.{domain}.jobs`).
- **Initial domain name** (kebab-case, e.g. `order`) — the first domain folder under `api/specs/v1/domains/`.

Example:

```bash
$ ./templates/project-init/init.sh ~/projects/my-new-project
Project name (kebab-case, e.g. my-app): my-new-project
Project token (lowercase, no dots, e.g. myapp): mynewproject
Initial domain name (kebab-case, e.g. order): customer

✓ Project bootstrapped at /Users/.../my-new-project
  Next steps:
    cd /Users/.../my-new-project
    git init
    Read CLAUDE.md, then start with /design-scenario or /design-async.
```

## What you get

```
<target-directory>/
├── CLAUDE.md                                # Starter — points at kit handbooks
├── <project-name>-project.json              # Generator config (JSON)
├── .gitignore
├── api/
│   ├── docs/                                # Flow docs, AI access matrix, project-specific overlays
│   └── specs/v1/
│       ├── openapi.yaml                     # OpenAPI root (skeleton)
│       ├── asyncapi.yaml                    # AsyncAPI root (skeleton)
│       ├── common/
│       │   ├── enums.yaml                   # Project role enum (starter shape)
│       │   ├── parameters/
│       │   ├── responses/
│       │   ├── headers/
│       │   └── securitySchemes/
│       ├── async-common/
│       │   ├── channels/
│       │   │   └── application-events.yaml  # Shared event topic
│       │   ├── message-traits/
│       │   └── operation-traits/
│       └── domains/
│           └── <initial-domain>/            # Starter domain folder structure
│               ├── models/
│               ├── operations/
│               ├── events/
│               ├── messages/
│               ├── channels/
│               ├── async-operations/
│               └── scenarios/
└── .claude/
    ├── agents/                              # Copied from kit's claude-assets/agents/
    └── commands/                            # Copied from kit's claude-assets/commands/
```

## Refreshing kit assets

To pull updated agents/commands from the kit into an existing project, re-run `init.sh` on the project directory with the `--refresh-assets` flag:

```bash
./templates/project-init/init.sh --refresh-assets <existing-project-directory>
```

This re-copies `.claude/agents/` and `.claude/commands/` from the kit without touching anything else. Your spec files, project config, and CLAUDE.md are left untouched.

## What this template does NOT include

- **Validator scripts** — the project decides which Spectral ruleset and JSON Schema validators to wire up. The kit's `schemas/` directory will eventually ship a canonical Spectral ruleset; until then, the project provides its own.
- **Bundled OpenAPI/AsyncAPI examples** — the skeleton specs are minimal stubs. See `samples/endpoint-samples.yaml`, `samples/message-samples.yaml`, etc., in the kit for canonical patterns to copy into the project's domain folders.
- **Generator invocation** — the `<project>-project.json` file is the generator's input; running the generator is project-specific tooling.
- **CI configuration** — add your own GitHub Actions / GitLab CI / Buildkite config under `.github/workflows/` (or equivalent).

## How the template handles placeholders

Files with the `.template` suffix in this directory are processed during bootstrap: the suffix is stripped and three placeholders are substituted:

| Placeholder | Replacement |
|---|---|
| `{ProjectName}` | The kebab-case project name (e.g. `my-app`) |
| `{project}` | The lowercase project token (e.g. `myapp`) |
| `{initial-domain}` | The first domain name (e.g. `order`) |

Files without the `.template` suffix (e.g. `.gitkeep`) are copied as-is.
