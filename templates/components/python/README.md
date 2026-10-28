# {{Dir}}

Python services for **{{ProjectName}}**. The libraries under `libs/` are generated from the API specifications in [`{{SpecRepo}}`](../{{SpecRepo}}). That repo must be checked out next to this one.

## Layout

| Library | Package | Generated (`_generated/`) |
|---|---|---|
| `libs/contracts` | `{{ContractsPackage}}` | SQLAlchemy models, enums, value objects, events, event builders, snapshots |
| `libs/core` | `{{CorePackage}}` | repositories, unit of work, session, event outbox and emitters |

Every `_generated/` folder is rewritten by every regen: **never edit it**. Put hand-written code beside it: subclass or wrap the generated classes in your own modules. Services and workers that use these libraries go in new workspace members (add them to `[tool.uv.workspace]`).

## Set up and test

```bash
uv sync --all-packages
uv run pytest
```

## Regenerate

From `../{{SpecRepo}}`, on a branch of this repo with no uncommitted changes:

```bash
./scripts/specfuse/generate.sh {{Groups}}
```

Review and merge the regen here first. Then advance the spec repo's baseline with `./scripts/specfuse/advance-state.sh`.

## Where this came from

`specfuse authoring add-component` seeded the workspace, the `pyproject.toml` files and this README once, for generator {{GeneratorVersion}}. They're yours to change, and the kit never rewrites them.
