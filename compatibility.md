# Kit ↔ Generator Compatibility

This file tracks which Specfuse generator commits are known compatible with each kit version. Breaking changes to vendor extensions require coordinated releases on both sides — the generator implements the contract that the kit defines.

## Current

| Kit version | Generator commit | Notes |
|---|---|---|
| `v0.1` (incubating) | `0a812e46` (`Bug #457: Add x-test-seed operation extension`) | Initial bootstrap. Kit content not yet populated; pin reflects the generator state at the moment of kit creation. |

## How to update this matrix

Bump the kit version on every change to:
- Handbook content that changes a generator-contract rule (new `x-*` extension, naming convention change, validation rule)
- Sample YAML structure (templates the generator consumes)
- Spectral schemas in `schemas/`

Pair the kit bump with the generator commit that implements the corresponding parser/validator change, and add a row above.

Workflow assets (`claude-assets/`, `templates/project-init/init.sh`) do not require generator-side coordination and do not need a matrix bump.
