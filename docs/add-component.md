<!--
Copyright 2026 Specfuse Contributors
Licensed under the Apache License, Version 2.0. See LICENSE.
-->

# Seeding a component repo

`specfuse authoring add-component` creates a component repo **beside the spec repo**: a C# backend or a Python services workspace, ready to receive generated code. It also adds that component's groups to the project file. Run it from the spec repo:

```bash
specfuse authoring add-component csharp Backend
specfuse authoring add-component python my-app-ai
```

| Option | Effect |
|---|---|
| `-n`, `--dry-run` | Print the groups it would add and the directory it would create. Write nothing. |
| `--group-prefix P` | Prefix the new group names, when the project file already has a `Domain` / `Api` / … group. |
| `--namespace N` | C# root namespace. Default: the project name in PascalCase (`hello-orders` → `HelloOrders`). |
| `--project FILE` | The project file, when the spec repo has more than one. |
| `--no-generate` | Seed only. Otherwise `scripts/specfuse/generate.sh` runs for the new groups if the project has it. |

## Seeded once, then yours

The command writes the host around the generated code: solution and project files, package manifests, the composition root, and the hand-written seams that generated code calls by name. **It writes them once.** They aren't in the scaffold manifest, `upgrade` never touches them, and the generator never writes them. They're project files, and they evolve with the project.

It refuses a directory that already exists and isn't empty, and a group name the project file already uses.

## C#

```
Backend/
├── <Ns>.slnx
├── Directory.Build.props            compiles src/ and gen-src/ in every project
├── <Ns>.Domain/<Ns>.Domain.csproj
├── <Ns>.Infrastructure/…csproj      references Domain
├── <Ns>.Api/…csproj                 Web SDK; references Domain and Infrastructure
│   └── src/
│       ├── Program.cs               wires the generated registrations
│       ├── Utils/UserHelper.cs      claims → the caller the generated controllers expect
│       └── Filters/ExceptionFilter.cs   generated domain exceptions → HTTP status + Error list
├── README.md, CLAUDE.md, .gitignore
```

It adds three groups (`Domain`, `Infrastructure`, `Api`) whose artifact sets compile together. After generating, `dotnet build` passes and `dotnet run --project <Ns>.Api` serves on an in-memory database. Set `ConnectionStrings__Default` to use SQL Server.

A `tenancy` block (`handbooks/Project_File.md` §4.1) is optional. Without one, the generator emits a do-nothing tenancy contract for the event runtime, so a single-tenant project compiles its services (from generator 0.20.0, [clabonte/generator#2883](https://github.com/clabonte/generator/issues/2883)).

## Python

```
my-app-ai/
├── pyproject.toml                    uv workspace over libs/*
├── libs/contracts/pyproject.toml     <abbr>_contracts: models, enums, value objects, events, snapshots
├── libs/core/pyproject.toml          <abbr>_core: repositories, unit of work, outbox, emitters
├── README.md, CLAUDE.md, .gitignore
```

It adds two groups (`PythonContracts`, `PythonCore`). After generating, `uv sync --all-packages && uv run pytest` passes.

The package roots must be the ones the generator derives from the project name, because generated code imports across the two libraries by those names. A name with capitals gives their lowercased initials (`HelloOrders` → `ho_contracts`). A name without capitals is snake-cased, with every run of other characters folded to one `_` (`hello-orders` → `hello_orders_contracts`); a leading digit gets a `_` prefix. The distribution names are the same roots with hyphens (`hello-orders-contracts`).

## Package versions and drift

The seeded package references are the ones the kit's pinned generator compiles against. CI seeds both components from `examples/hello-orders`, generates them with the pinned generator, and then builds and runs them on every pin change. So a pin that needs a new package fails in the kit's CI before release.

Projects that seeded earlier own their copies. When a generator upgrade needs a new package, its `compatibility.md` row says so, and the build names it.

If the project pins its own generator (`.specfuse/generator.lock`), the command warns that the seed was verified with the kit's pin.
