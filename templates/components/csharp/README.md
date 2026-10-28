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

Every generated operation that declares `x-roles` requires an authenticated caller: anonymous requests get 401. `Program.cs` uses JWT bearer; for a local token, use the .NET SDK's `user-jwts` (the `roles` claim carries the role, `sub` the user id):

```bash
TOKEN=$(dotnet user-jwts create --project {{Prefix}}.Api --name dev --claim roles=Admin --audience {{Prefix}} --output token)
ASPNETCORE_ENVIRONMENT=Development dotnet run --project {{Prefix}}.Api
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/...
```

In production, configure `Authentication:Schemes:Bearer` (authority, audience) for your identity provider.

## Regenerate

From `../{{SpecRepo}}`, on a branch of this repo with no uncommitted changes:

```bash
./scripts/specfuse/generate.sh {{Groups}}
```

Review and merge the regen here first. Then advance the spec repo's baseline with `./scripts/specfuse/advance-state.sh`.

## Where this came from

`specfuse authoring add-component` seeded the solution, project files, `Directory.Build.props`, this README and the `src/` files once, for generator {{GeneratorVersion}}. They're yours to change, and the kit never rewrites them. When a generator upgrade needs a new package, its release notes and a failing build will say which one.
