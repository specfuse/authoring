# {{Dir}}

C# backend for **{{ProjectName}}**. Most of the code is generated from the API specifications in [`{{SpecRepo}}`](../{{SpecRepo}}). That repo must be checked out next to this one.

## Layout

| Project | Generated (`gen-src/`) | Hand-written (`src/`) |
|---|---|---|
| `{{Prefix}}.Domain` | entities, value objects, enums, domain services, exceptions, events and snapshots | `partial` classes that extend the generated types |
| `{{Prefix}}.Infrastructure` | EF Core `DbContext`, entity configurations, repositories, event runtime | your own infrastructure (external services, custom queries) |
| `{{Prefix}}.Api` | controllers, API models, mappers, authorization | `Program.cs`, `Utils/UserHelper.cs`, `Filters/ExceptionFilter.cs`, middleware |

`Directory.Build.props` compiles both roots of every project. `gen-src/` is rewritten by every regen: **never edit it**. Extend generated types with `partial` classes or by deriving from the generated `*Base` classes, in `src/`.

## Run

```bash
dotnet build
dotnet run --project {{Prefix}}.Api
```

Without `ConnectionStrings__Default`, the API runs on an in-memory database.

## Regenerate

From `../{{SpecRepo}}`, on a branch of this repo with no uncommitted changes:

```bash
./scripts/specfuse/generate.sh {{Groups}}
```

Review and merge the regen here first. Then advance the spec repo's baseline with `./scripts/specfuse/advance-state.sh`.

## Where this came from

`specfuse authoring add-component` seeded the solution, project files, `Directory.Build.props`, this README and the `src/` files once, for generator {{GeneratorVersion}}. They're yours to change, and the kit never rewrites them. When a generator upgrade needs a new package, its release notes and a failing build will say which one.
