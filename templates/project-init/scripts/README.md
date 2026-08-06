# `scripts/`

Tooling the Specfuse authoring skills invoke. **These files are owned by the
kit**: `specfuse-authoring upgrade` replaces them wholesale so fixes reach every
project. Editing one in place works until the next upgrade, which will overwrite
it and tell you it did. Send changes upstream instead — see the kit's
`CONTRIBUTING.md`.

Project-specific tooling belongs in a directory the kit does not own (`bin/`,
`tools/`, anywhere but here).

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

The Spectral validators lint against the rulesets delivered into
`.specfuse/authoring/schemas/spectral/`, so they follow the kit rather than a
copy that drifts. Each resolves the spec version by looking for the newest
`api/specs/v*` directory; pass one explicitly to override
(`./scripts/validate-spectral.sh v1`).

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
`specfuse-authoring generate`, which resolves and checksum-verifies the version
pinned in the kit's `generator.lock`. There is no jar to keep in this directory.

## External dependencies

Not bundled — install what you use:

```bash
npm install -g @redocly/cli                        # bundling, preview, validate-redocly
npm install -g @stoplight/spectral-cli             # the Spectral validators
npm install -g @openapitools/openapi-generator-cli # validate-openapi-generator
npm install -g @asyncapi/cli                       # serve-async-docs
pipx install specfuse-authoring                    # generation
pip install PyYAML                                 # bundle-async-spec (dedup pass)
```

Each script checks for what it needs and prints the install command if it is
missing, so you only need the ones you actually run.
