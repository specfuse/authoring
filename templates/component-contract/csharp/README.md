# Starter generated-code contract for a C# component repo

The files here are the mechanical half of a C# component's generated-code bar,
ready to seed into a repo that receives Specfuse-generated C#. They are seeded
**once** and owned by the component from then on; the kit never rewrites them
(the decision record is [specfuse/authoring#171](https://github.com/specfuse/authoring/issues/171),
and `add-component` will seed them automatically once
[#181](https://github.com/specfuse/authoring/issues/181) lands).

| File | Lands at | What it is |
|---|---|---|
| `gen-contract.yml` | repo root | 16 starter rules: markers, layering, host wiring, extension-point adoption. Every rule green on a fresh seed. |
| `scripts/gen_contract_checks.py` | `scripts/` | The two project-specific checks the generic engine cannot express: `generated_base_adopted` and `generated_handler_interface_implemented_directly`. |
| `scripts/check-gen-contract.sh` | `scripts/` | Runs the contract through the shared engine (`specfuse.loop.gen_contract`, specfuse-loop 0.30+). |
| `scripts/test-gen-contract.sh` | `scripts/` | Mutation test: breaks the tree one rule at a time and asserts the rule reports it. |
| `scripts/apply-gen-patches.sh` | `scripts/` | Re-applies the tracked temporary patches in `gen-patches/` after a regen; `--check` is the gate that they are all in place. |
| `gen-patches/README.md` | `gen-patches/` | The index of active and retired patches, and how to make and retire one. |
| `docs/generated-code-expectations.md` | `docs/` | The prose half, with the five section names the generator's QA reviewer reads. |
| `verification.snippet.yml` | merge into `.specfuse/verification.yml` | The `code` gate set: contract, build, tests. |
| `.github/workflows/gen-contract.yml` | `.github/workflows/` | CI: contract plus mutation test on every PR, no .NET SDK needed. |

## Seeding by hand

From the component repo root, with `<Prefix>` the solution's root namespace
(`HelloOrders` for `HelloOrders.Domain` / `.Infrastructure` / `.Api`):

```bash
# This folder ships in every spec repo the kit set up, at
# .specfuse/authoring/templates/component-contract/csharp (refreshed by upgrade).
# From a component repo checked out beside its spec repo:
KIT=../<spec-repo>/.specfuse/authoring/templates/component-contract/csharp
cp "$KIT/gen-contract.yml" .
mkdir -p scripts docs .github/workflows
cp "$KIT/scripts/"* scripts/
cp "$KIT/docs/generated-code-expectations.md" docs/
cp "$KIT/.github/workflows/gen-contract.yml" .github/workflows/
sed -i.bak 's/__Prefix__/HelloOrders/g' gen-contract.yml docs/generated-code-expectations.md && rm -f *.bak docs/*.bak
mkdir -p gen-patches && cp "$KIT/gen-patches/README.md" gen-patches/
chmod +x scripts/check-gen-contract.sh scripts/test-gen-contract.sh scripts/apply-gen-patches.sh
python3 -m pip install 'specfuse-loop>=0.30'     # or: pipx install specfuse
./scripts/check-gen-contract.sh                  # must be green
./scripts/test-gen-contract.sh                   # every rule must bite
```

Then paste the `code:` block of `verification.snippet.yml` into
`.specfuse/verification.yml`. The full walkthrough, with what each rule
protects and how to extend the contract, is
[`docs/csharp-component-guide.md`](../../../docs/csharp-component-guide.md)
§6.

## Extending the contract

Add a rule when a review finding recurs. The bar for a new rule:

1. Green on the default branch the day it lands, or shipped with a
   `waived_until:` block that freezes today's count and names the event that
   ends it.
2. A case in `scripts/test-gen-contract.sh` proving it bites.
3. A `why:` that says what breaks in production, not what a style guide says.
   The `why` is printed with every violation; it is what makes a finding
   actionable without a conversation.

The engine's own reference (check kinds, `waived_until`, `allow_empty`, the
`builtins:` module) is the module docstring:
`python3 -c "import specfuse.loop.gen_contract as m; print(m.__doc__)"`.
