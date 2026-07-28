# Contributing to the Specfuse Spec-Authoring Kit

The spec-authoring kit is part of the Specfuse methodology suite, alongside
`specfuse/loop` and the Specfuse generator. The kit is the **upstream
contract**: it defines what a valid Specfuse spec must look like, which vendor
extensions exist, and how projects are authored. The generator consumes that
contract; the loop drives the authoring workflow. Each project is independently
adoptable — contributions should keep the kit usable on its own.

## Ground rules

- **Open-source hygiene from every commit.** No consumer-product names, no
  private-organization names, no internal URLs, no fixtures containing
  sensitive data. The kit was extracted from a real project; brand names and
  domain-specific role/enum values from that source do **not** belong in
  handbooks, samples, schemas, or comments. Write every commit message and code
  comment as if a stranger will read it. Apache 2.0 license headers belong on
  source files from the first commit.
- **The handbooks are the contract.** `handbooks/` is the authoritative
  spec-authoring reference. A change that alters a generator-contract rule (a
  new `x-*` extension, a naming convention, a validation rule) is a contract
  change — it must be paired with a generator-side commit and a row in
  `compatibility.md`. See "Versioning" below.
- **Samples and the example mirror the handbooks.** `samples/` and
  `examples/hello-orders/` must always pattern-match the current handbook
  rules. If you change a rule, update the samples and the example in the same
  PR.
- **Extension shape changes and the ruleset move together.** The Spectral rules
  that validate `x-entity`, `x-value-object` and friends are hand-maintained
  mirrors of those extensions' shapes, and `specfuse-xentity-shape` is
  `additionalProperties: false`. So a new entity-level property that lands in
  the handbooks without a matching ruleset update does not merely go
  unvalidated — it makes the shape rule **reject every entity that uses it**.
  Adding or renaming a property inside any `x-*` block therefore requires
  updating `schemas/spectral/` **in the same PR**. This has drifted before: a
  required property once shipped across dozens of entities with no ruleset
  update and sat broken for months. A hand-maintained mirror will drift; the
  only question is how long before anyone notices.
- **Boring beats clever.** Markdown, YAML, JSON Schema, Spectral, a thin Python
  CLI. Every piece individually replaceable.
- **An extension nothing consumes is a false guarantee.** Readers reasonably
  assume a declared constraint is enforced somewhere. Before adding one, name
  what reads it — a generator output, a Spectral rule, a documented lint
  exemption. If nothing does, either wire it up or document it explicitly as
  declared-but-unenforced, and say so where authors will see it.

## What requires a version bump

Bump the kit version and add a `compatibility.md` row on any change to:

- Handbook content that changes a generator-contract rule (new `x-*`
  extension, naming-convention change, validation rule).
- Sample YAML structure (the templates the generator consumes).
- Spectral schemas in `schemas/`.
- The pinned generator in `generator.lock`.

Pair the kit bump with the generator commit that implements the corresponding
parser/validator change.

The Claude Code authoring assets (skills + design agents) live in the
`specfuse-authoring` plugin in the `specfuse/specfuse` marketplace, not in this
repo. The kit ships the CLI plus the handbooks, samples, schemas, and
templates. Workflow assets (`templates/project-init/`) and the
`specfuse-authoring` CLI do **not** require generator-side coordination and do not
need a matrix bump — but a CLI change still bumps the package version.

## Before you push

- **`hello-orders` is the regression net.** Every PR re-validates the bundled
  example (`.github/workflows/example-regen.yml`). If your change touches the
  contract, regenerate/re-validate `examples/hello-orders/` and confirm it
  still passes.
- **A rule change must be verified in both directions.** Confirm the rule still
  fires on a genuine violation, not only that the error count went down. A rule
  that stops misfiring by never running looks identical to a fixed one from the
  finding count alone, and the same is true of a lint gate that silently stops
  gating. `schemas/spectral/fixtures/` holds the fixtures that pin this for the
  null-tolerance and `mutability` behaviours; add one when you fix a rule.
- **Build the package.** `python -m build --wheel` must succeed, and a wheel
  installed in a clean environment must run `specfuse-authoring init` correctly
  (the wheel bundles handbooks, samples, templates, and schemas under the
  `specfuse/authoring/_kit/` path; Claude assets resolve from the plugin, not the wheel).
- **Re-run the leak check.** Confirm no source-project brand names leaked back
  in:
  `grep -rinE 'restomanager|restaurant|<your-source-brand>' . | grep -v '.git/'`

## PR conventions

- **Branch from `main`** with a descriptive name (`fix/spectral-batch-rule`,
  `feat/x-new-extension`).
- **Reference an issue.** For contract-touching changes, open the issue first
  and discuss before coding.
- **One change per PR.** A PR that changes a handbook rule *and* the CLI is two
  PRs.

## Reporting

Use the issue tracker for bugs and design discussion. For anything touching the
shared contract (handbooks, vendor extensions, schemas), say so explicitly in
the issue title so it can be coordinated with the generator and the other
Specfuse projects. For security issues, see [`SECURITY.md`](SECURITY.md).
