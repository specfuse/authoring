---
name: bump-generator-pin
description: Kit-side half of a generator release — pin a newly published generator jar into generator.lock, then walk the maintainer through the kit version bump, compatibility.md row, and PyPi publish. Trigger when a new generator version has been released to Specfuse/generator-dist and you have its version + SHA-256. Maintainer-only (not copied into client projects).
---

# bump-generator-pin

Pins a released generator jar in the kit and completes the kit-side lockstep so
`specfuse authoring generate` resolves and verifies the new jar.

Use this **after** the generator's own release script has published
`specfuse-generator-<X.Y.Z>.jar` to `Specfuse/generator-dist` (tag `v<X.Y.Z>`)
and printed a version + SHA-256.

## Inputs

- `<version>` — the released generator semver (e.g. `1.4.0`)
- `<sha256>` — the 64-hex SHA-256 the release printed (also in the release's
  `.jar.sha256` sidecar asset)
- the intended **kit** version for this patch (the kit bump that ships the new pin)

If any are missing, ask for them. Do not guess a SHA-256.

## Steps

1. **Dry-run the pin first** (irreversible-ish: it edits a committed contract
   file, so preview before writing):
   ```bash
   python3 scripts/bump-generator-pin.py --version <version> --sha256 <sha256> --dry-run
   ```
   Show the diff. Confirm `asset`, `release_tag`, and `release_repo` look right
   (`specfuse-generator-<version>.jar`, `v<version>`, `Specfuse/generator-dist`).

2. **Apply the pin:**
   ```bash
   python3 scripts/bump-generator-pin.py --version <version> --sha256 <sha256>
   ```

3. **Bump the kit version** to the agreed kit patch version, in all three places
   that carry it:
   - `pyproject.toml` (`project.version`)
   - `generator.lock` (`kit_version`)
   - `README.md` Status line (if it names the version)

4. **Add a compatibility.md row** under `## Current`, mapping this kit version to
   generator `<version>`. Write a one-line note describing what changed in the
   contract (or "no contract change — generator bugfix only"). Match the existing
   row format.

5. **Check the extension vocabulary against the new jar — this is a gate, not a
   nicety.** The kit's Spectral rules close several vendor extensions with
   `additionalProperties: false`, over a vocabulary the generator owns. A pin
   bump is the moment that vocabulary changes, and it is the last moment the
   drift is cheap: after release, the first spec that declares a new key fails
   lint with an `additionalProperties` error naming the spec, and the generator
   feature cannot be adopted until someone patches the ruleset by hand. That has
   happened three times on `x-entity` alone (`domain`, `concurrency`, `delete`).

   ```sh
   SPECFUSE_GENERATOR_JAR=~/.specfuse/jars/specfuse-generator-<version>.jar \
     python3 templates/project-init/scripts/specfuse/check-extension-vocabulary.py --require-jar
   ```

   Run it from the repo root against `schemas/spectral/` (the kit's own copies —
   the same files the overlay delivers). If it reports keys the generator knows
   and the rulesets reject:

   - Add each key to the guard's schema **in this same PR**, with its value
     constraint from the generator's release notes, and add a fixture case in
     both directions to `schemas/spectral/fixtures/xentity-shape-keys.yaml` (or
     the equivalent fixture for that guard).
   - Update the handbook section that documents the extension. A key the ruleset
     accepts but no handbook describes is undiscoverable by spec authors.
   - If a key belongs to a different surface than the guard covers, record it in
     `vocabulary-exceptions.yaml` with a reason rather than leaving it unexplained.

   Do not proceed to the commit with a red check. A pin that ships with an
   unpatched ruleset ships a blocked feature.

6. **Verify** the pin resolves: run the resolver in dry mode if practical, or at
   minimum confirm `generator.lock` is valid JSON and the SHA-256 matches what the
   release published.

7. **Commit** on a branch (one change per PR):
   `Pin generator <version>; bump kit to <kit-version>`.

8. **Remind the maintainer** of the final, outward-facing step (do NOT do it
   automatically): publish the kit patch to PyPi
   (`python -m build && twine upload dist/*`). Until that lands, clients still
   resolve the previously-pinned jar.

## Guardrails

- Never invent or commit a token or SHA-256. If the SHA isn't supplied, stop and ask.
- This skill lives in the kit repo's `.claude/` and is maintainer-only — it is
  **not** part of the `specfuse-authoring` plugin and must never reach client projects.
- A generator release without this kit-side bump is a no-op for clients; a kit
  bump pointing at a SHA that doesn't match the published jar makes `generate`
  abort on every client. Keep version, asset, tag, and SHA-256 mutually consistent.
