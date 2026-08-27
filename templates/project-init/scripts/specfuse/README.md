# `scripts/specfuse/`

Tooling the Specfuse authoring skills invoke. **This whole directory is owned by
the kit**: `specfuse authoring upgrade` replaces its contents wholesale so fixes
reach every project. Editing a file in place works until the next upgrade, which
will overwrite it and tell you it did. Send changes upstream instead — see the
kit's `CONTRIBUTING.md`.

**The subdirectory is the boundary, and it is the only thing the kit touches.**
`scripts/` itself is yours: your own tooling, and anything shipped by a contract
other than this one, live beside `specfuse/` and are never read, rewritten or
pruned by an upgrade. The shared substrate's `validate-event.py` and
`validate-frontmatter.py` (authoring #26) are the standing example — they sit at
`scripts/`, not here.

Before kit `0.10.0` these files landed directly in `scripts/`, which meant the
kit claimed about twenty generic filenames (`validate-specs.sh`, `bundle-spec.sh`,
`serve-docs.sh`) in a directory most repos already use. A project file colliding
with one of those was overwritten on upgrade — warned about on stderr, which in
CI is where warnings go unread. The move makes the boundary structural rather
than conventional.

## Validation

| Script | What it checks |
|---|---|
| `validate-specs.sh` | Runs every layer below in order. The one to run before a commit. |
| `validate-structure.sh` | Domain-based file layout of the OpenAPI tree. |
| `validate-redocly.sh` | OpenAPI parses and bundles cleanly. |
| `validate-spectral.sh` | OpenAPI against the kit's Spectral ruleset. |
| `validate-async-structure.sh` | AsyncAPI file layout and flow docs. |
| `validate-async-spectral.sh` | AsyncAPI against the kit's Spectral ruleset. |
| `validate-arazzo.sh` | Arazzo scenarios and recipes — structural + cross-spec. |
| `validate-arazzo-spectral.sh` | Arazzo against the kit's Spectral ruleset. |
| `validate-openapi-generator.sh` | The spec is consumable by openapi-generator. |
| `check-extension-vocabulary.py` | The rulesets' closed vendor-extension guards still cover the generator's vocabulary — run by `validate-spectral.sh` before it lints. |
| `spectral-overlay-diff.py` | Which of *your* Spectral rules the kit now owns. Not part of `validate-specs.sh` — run it by hand when adopting or re-adopting the kit's rulesets. |

**Why the vocabulary check exists.** Several rules validate a vendor extension
with `additionalProperties: false`. That is a closed schema over a vocabulary
the *generator* owns, so when the generator adds a key the ruleset does not
know about, the consequence is not a missed warning — the first spec that
declares the key fails lint outright, and the error names your spec rather than
the ruleset. `check-extension-vocabulary.py` reads the key literals out of the
pinned generator jar and fails when the generator knows a key no guard accepts.
It is deliberately one-way: keys a ruleset accepts but the jar never mentions
are reported and never fatal, because the generator reaches some keys through
indirect constants that leave no literal behind.

With no generator jar cached it skips **loudly** and exits 0 — a developer who
has never run `generate` should not be blocked. CI should pass `--require-jar`
so the skip cannot become the normal state. `SPECFUSE_GENERATOR_JAR` points it
at a specific jar. A generator key that legitimately belongs to a different
surface goes in `.specfuse/authoring/vocabulary-exceptions.yaml` with a reason —
declared, not silently tolerated.

**Why the overlay diff exists.** If your `.spectral.yaml` was copied from
another Specfuse project rather than written against the kit, it is a *fork* of
the kit's own rules under older ids (`rm-*` rather than `specfuse-*`). Extending
the kit on top of that double-reports every shared rule — two ids, two findings,
one violation — and the natural reaction is to back the change out. The script
classifies every rule as redundant / diverged / project-specific / kit-only-new,
matching ids through `.specfuse/authoring/schemas/spectral/rule-renames.yaml`,
so the deletion is a decision rather than a guess:

```bash
pip install PyYAML   # its only dependency
python3 scripts/specfuse/spectral-overlay-diff.py \
  --kit-ruleset     .specfuse/authoring/schemas/spectral/specfuse-openapi.yaml \
  --project-ruleset api/spectral.myproject.yaml
```

Exit `0` nothing redundant, `1` redundant rules found, `2` could not run — and
it treats a wrong file pair or a stale map as could-not-run rather than reporting
a clean bill of health for a comparison that never happened. The full procedure,
including the order that keeps the gate on throughout, is in
`.specfuse/authoring/schemas/README.md` §"Reducing an overlay that forked from
the kit". Once the overlay is reduced the script exits `0` and is worth leaving
in CI: it then fails the day someone re-adds a rule the kit already owns.

The Spectral validators lint against the rulesets delivered into
`.specfuse/authoring/schemas/spectral/`, so they follow the kit rather than a
copy that drifts. Keep it that way: a second, project-local copy of a ruleset
is the same drift problem wearing a different hat, and the copy CI does not run
is the one that rots. The vocabulary check flags ruleset files no script names,
for exactly that reason — one ruleset, one runner. Each resolves the spec version by looking for the newest
`api/specs/v*` directory; pass one explicitly to override
(`./scripts/specfuse/validate-spectral.sh v1`).

"Nothing to check" is a pass, not an error — a project with no Arazzo scenarios
yet exits 0.

## Bundling and docs

| Script | Purpose |
|---|---|
| `bundle-spec.sh` | Bundle OpenAPI into a single file for generation. |
| `bundle-async-spec.sh` | Same for AsyncAPI, plus a post-bundle dedup pass. |
| `dedupe-async-bundle.py` | Dedup helper — called by `bundle-async-spec.sh`. |
| `serve-docs.sh` | Redocly preview server for the OpenAPI docs (default port 8081). |
| `serve-async-docs.sh` | Preview server for the AsyncAPI docs. |
| `generate-scenario-docs.sh` | Bundle, then generate scenario + technical-reference docs. |
| `generate-scenario-index.sh` | Build the scenario index — called by the above. |
| `build-prompt-index.sh` | Reverse index of `api/docs/implementation-prompts/`, for `/prepare-handoff`. |

`generate-scenario-docs.sh` drives the generator through
`specfuse authoring generate`, which resolves and checksum-verifies the version
pinned in the kit's `generator.lock`. There is no jar to keep in this directory.
(The script falls back to the deprecated flat `specfuse-authoring` command when
the suite CLI is not installed, and `SPECFUSE_AUTHORING` overrides both.)

## External dependencies

Not bundled — install what you use:

```bash
npm install -g @redocly/cli                        # bundling, preview, validate-redocly
npm install -g @stoplight/spectral-cli             # the Spectral validators
npm install -g @openapitools/openapi-generator-cli # validate-openapi-generator
npm install -g @asyncapi/cli                       # serve-async-docs
pipx install specfuse                              # generation (the whole Specfuse suite)
pip install PyYAML                                 # bundle-async-spec (dedup pass), spectral-overlay-diff
```

Each script checks for what it needs and prints the install command if it is
missing, so you only need the ones you actually run.
