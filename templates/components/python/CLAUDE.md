# {{Dir}}: instructions for coding agents

## Generated code: never edit

- Every `_generated/` folder under `libs/` is generated from `../{{SpecRepo}}` by the Specfuse generator. The next regen overwrites it.
- If a task seems to need a change in generated code, stop. The fix belongs in the API spec (in `../{{SpecRepo}}`) or in the generator. Say so, and note that a regen is required.
- Before writing a model, enum, event or repository by hand, check `{{ContractsPackage}}` and `{{CorePackage}}`. It probably exists already.

## Where hand-written code goes

- Beside `_generated/`, never inside it. Subclass or wrap the generated classes.
- New services and workers go in their own workspace members, depending on `{{ContractsDist}}` / `{{CoreDist}}`.
