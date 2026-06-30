<!--
Copyright 2026 Specfuse Contributors
Licensed under the Apache License, Version 2.0. See LICENSE.
-->

# Releasing `specfuse-authoring`

Releases are **tag-driven**. Pushing a `vX.Y.Z` tag triggers
[`.github/workflows/release.yml`](.github/workflows/release.yml): it builds the
wheel + sdist, smoke-tests the **built artifact** (clean-install bootstrap, not
the source tree), checks the tag matches the package version, and—on a tag—
publishes to PyPI via **OIDC trusted publishing** (no API token).

## One-time operator setup (before the first release)

1. **Create the PyPI project + trusted publisher.** On PyPI →
   *Your projects → Publishing → Add a pending publisher* for project
   **`specfuse-authoring`**:
   - Owner: `Specfuse`  ·  Repository: `authoring`
   - Workflow: `release.yml`  ·  Environment: `pypi`
2. **Create the `pypi` environment** in the GitHub repo
   (*Settings → Environments → New environment → `pypi`*). Optionally add
   required reviewers so a human approves each publish.
3. **Make the repo public** before (or at the same time as) the first publish.
   PyPI's links point at `github.com/Specfuse/authoring`, and the wheel exposes
   the handbooks/samples anyway, so a published package + private repo is
   inconsistent. The leakage scrub (the gate for going public) is already done.

## Per-release checklist

1. **Decide the version** `X.Y.Z` (semver). Bump on any handbook contract
   change, sample/schema change, generator pin, or CLI change.
2. **Bump the version in all three places** (the workflow enforces agreement):
   - `pyproject.toml` → `project.version`
   - `specfuse/authoring/__init__.py` → `__version__`
   - `generator.lock` → `kit_version`
   - (and the `README.md` Status line, for humans)
3. **Update `compatibility.md`** — add/adjust the row for this kit version
   (and the generator version it pins), if the contract or pin changed.
4. **Sanity-check locally:**
   ```bash
   python -m build
   pipx run --spec "$(ls dist/*.whl)" specfuse-authoring --version   # or install in a venv
   ```
   Confirm `examples/hello-orders/` still lints (CI does this on push, too).
5. **Commit** the version bump on `main` and push.
6. **Tag and push the tag:**
   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
7. **Watch the `release` workflow.** build-test must pass; `publish` then runs
   (approve it if you set required reviewers on the `pypi` environment).
8. **Verify on PyPI:** `pip index versions specfuse-authoring` shows `X.Y.Z`, and
   `pipx install specfuse-authoring==X.Y.Z` works from a clean machine.
9. **Cut a GitHub Release** for the tag with notes (optional but recommended).

## Notes

- `workflow_dispatch` runs build + smoke **without** publishing (no tag) — use it
  to dry-run the pipeline.
- A version mismatch between the tag and the package version **fails the build**
  before publish — the tag is the source of truth.
- The **generator jar** is released separately (see
  [`.claude/skills/bump-generator-pin`](.claude/skills/bump-generator-pin/SKILL.md)
  and `scripts/bump-generator-pin.py`); a generator release is a no-op for
  clients until a kit patch re-pins it and ships here.
- The **Claude assets** (skills + agents) are released from the
  [`specfuse/specfuse`](https://github.com/specfuse/specfuse) plugin marketplace,
  not from this package — bump the plugin's `plugin.json` version there.
