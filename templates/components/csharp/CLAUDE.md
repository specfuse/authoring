# {{Dir}}: instructions for coding agents

## Generated code: never edit

- `*/gen-src/**` and every `*.g.cs` file are generated from `../{{SpecRepo}}` by the Specfuse generator. The next regen overwrites them.
- If a task seems to need a change under `gen-src/`, stop. The fix belongs in the API spec (in `../{{SpecRepo}}`) or in the generator. Say so, and note that a regen is required.
- Before writing a model, DTO, repository, mapper or controller by hand, check `gen-src/`. It probably exists already.

## Where hand-written code goes

- `src/` in each project. Extend generated types with `partial` classes, or derive from the generated `*Base` classes.
- `{{Prefix}}.Api/src/Program.cs` wires the generated registrations. `Utils/UserHelper.cs` maps claims to the caller the generated controllers expect, and `Filters/ExceptionFilter.cs` maps domain exceptions to HTTP.

## The guide

- `../{{SpecRepo}}/.specfuse/authoring/docs/csharp-component-guide.md` is the full reference for this repo: layout, build wiring, the seams generated code calls by name, extension patterns, the generated-code contract, the regen flow, and an audit checklist (§10). The kit refreshes it on every `upgrade` of the spec repo. Read it before changing build wiring or adding a seam.

## Layering

- `{{Prefix}}.Domain` depends on nothing in this solution.
- `{{Prefix}}.Infrastructure` depends on Domain only.
- `{{Prefix}}.Api` depends on Domain. It references Infrastructure only to wire it up in `Program.cs`.
