"""Versioned overlay for kit-owned files in an existing project.

`init` copies the project template once, at creation. Nothing re-delivered it
afterwards, so a kit release could never reach a project that already existed —
`refresh` re-copied only handbooks and samples, blindly, with no record of what
it had written and no way to tell a kit file from one the project had edited.

This module is the delivery mechanism. It mirrors the scaffold overlay in
`specfuse/loop` (`specfuse/loop/scaffold.py`), deliberately: same VERSION stamp,
same sha256 manifest as the ownership record, same manifest-scoped prune, same
refusal to downgrade. Two components solving one problem the same way is worth
more than either solving it cleverly.

The central idea is the **manifest**. `.specfuse/authoring/.scaffold-manifest`
records the sha256 of every file the last init/upgrade wrote, keyed by
project-relative path. That record is what lets an upgrade distinguish three
otherwise identical-looking files:

  - one we wrote and nobody touched      -> overwrite silently
  - one we wrote and the project edited  -> overwrite, but say so
  - one we never wrote                   -> never delete it; keep it, loudly

Without the manifest all three look the same on disk, and the only safe
behaviours are "clobber everything" or "touch nothing".

What the overlay owns is kit content only: the handbooks, samples and schemas
under `.specfuse/authoring/`, plus the `scripts/` tooling at the project root.
The project's own specs (`api/`), its `CLAUDE.md`, its project file and its
`.gitignore` are seeded once by `init` and never touched again — they are the
user's, and an upgrade that rewrote them would destroy the actual work.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

from . import __version__, kit_root

SCAFFOLD_SUBDIR = Path(".specfuse") / "authoring"
MANIFEST_FILE = SCAFFOLD_SUBDIR / ".scaffold-manifest"
VERSION_FILE = SCAFFOLD_SUBDIR / "VERSION"

# Kit source directory -> destination, relative to the project root.
#
# `scripts` lands at the project root because that is where the plugin skills
# look for it (`./scripts/serve-docs.sh`). Everything else is contract material
# and lives under .specfuse/authoring/.
# A source may be a directory (copied recursively) or a single file.
#
# `templates/` is NOT overlaid wholesale: `templates/project-init/` is the
# scaffold source that `init` expands, and shipping it into a project would drop
# a second, unexpanded copy of the skeleton on top of the real one.
OVERLAY: tuple[tuple[str, str], ...] = (
    ("handbooks", ".specfuse/authoring/handbooks"),
    ("samples", ".specfuse/authoring/samples"),
    ("schemas", ".specfuse/authoring/schemas"),
    (
        "templates/ai-access-policy-template.md",
        ".specfuse/authoring/templates/ai-access-policy-template.md",
    ),
    (
        "templates/initiative-backlog.template.md",
        ".specfuse/authoring/templates/initiative-backlog.template.md",
    ),
    (
        "templates/initiative-idea-dossier.template.md",
        ".specfuse/authoring/templates/initiative-idea-dossier.template.md",
    ),
    ("templates/project-init/scripts", "scripts"),
)

# Destination roots whose contents are pruned when the kit stops shipping a
# file. Scoped by the manifest — see prune logic in `upgrade`. Single-file
# entries contribute their parent directory.
PRUNE_DIRS: tuple[str, ...] = tuple(
    dict.fromkeys(
        dest if "." not in Path(dest).name else Path(dest).parent.as_posix()
        for _, dest in OVERLAY
    )
)


class DowngradeError(RuntimeError):
    """The project was scaffolded by a newer kit than the one installed."""


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_version(v: str) -> tuple[int, ...]:
    parts = v.strip().split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"invalid version: {v!r}")
    return tuple(int(p) for p in parts)


# Build residue that must never be delivered into a project. The overlay copies
# source directories wholesale, so anything a maintainer generates in the kit
# tree — running the bundled Python helper is enough — would otherwise ship.
_JUNK_DIRS = frozenset({"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"})
_JUNK_SUFFIXES = (".pyc", ".pyo")
_JUNK_NAMES = frozenset({".DS_Store"})


def _is_junk(path: Path) -> bool:
    return (
        path.name in _JUNK_NAMES
        or path.suffix in _JUNK_SUFFIXES
        or any(part in _JUNK_DIRS for part in path.parts)
    )


def overlay_files() -> list[tuple[str, bytes]]:
    """Every kit-owned file as (project-relative path, content)."""
    root = kit_root()
    out: list[tuple[str, bytes]] = []
    for src_rel, dest_rel in OVERLAY:
        src = root / src_rel
        if src.is_file():
            out.append((dest_rel, src.read_bytes()))
            continue
        if not src.is_dir():
            # A kit that does not ship this source yet is not an error; the
            # overlay may be declared ahead of the content it will carry.
            continue
        for path in sorted(src.rglob("*")):
            if not path.is_file() or _is_junk(path):
                continue
            rel = f"{dest_rel}/{path.relative_to(src).as_posix()}"
            out.append((rel, path.read_bytes()))
    return out


def read_manifest(target: Path) -> dict[str, str]:
    """Ownership record from the previous init/upgrade; {} when absent.

    Malformed content degrades to {} rather than raising: the callers then
    behave as if ownership is unprovable, which errs toward keeping files.
    """
    path = target / MANIFEST_FILE
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}


def write_manifest(target: Path, entries: dict[str, str]) -> None:
    path = target / MANIFEST_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(sorted(entries.items())), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_version(target: Path) -> None:
    path = target / VERSION_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(__version__ + "\n", encoding="utf-8")


def scaffold_version(target: Path) -> str | None:
    """The kit version that last wrote this project's overlay, if recorded."""
    path = target / VERSION_FILE
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip() or None


def detect_modified(target: Path) -> list[str]:
    """Kit-owned files whose content no longer matches what we wrote.

    Empty when there is no manifest — an unmanaged tree has no baseline to
    differ from, and reporting every file as modified would be noise.
    """
    manifest = read_manifest(target)
    modified = [
        rel
        for rel, expected in manifest.items()
        if (target / rel).exists() and _sha256_hex((target / rel).read_bytes()) != expected
    ]
    return sorted(modified)


def stamp(target: Path) -> None:
    """Record the current kit version and file hashes without changing content.

    Called at the end of `init`, so a freshly created project starts out
    upgradeable. Without this the first upgrade would see no manifest and treat
    every kit file as unowned.
    """
    entries = {
        rel: _sha256_hex(content)
        for rel, content in overlay_files()
        if (target / rel).exists()
    }
    write_manifest(target, entries)
    write_version(target)


def upgrade(target: Path, *, dry_run: bool = False) -> int:
    """Overlay the installed kit's files onto an existing project.

    Overwrites kit-owned files, prunes ones the kit no longer ships (only where
    the manifest proves we wrote them), and leaves everything else alone.
    """
    if not target.is_dir():
        sys.exit(f"Error: target directory does not exist: {target}")
    target = target.resolve()

    recorded = scaffold_version(target)
    if recorded is not None:
        try:
            if _parse_version(recorded) > _parse_version(__version__):
                raise DowngradeError(
                    f"refusing downgrade: {target} was scaffolded by kit {recorded}, "
                    f"but the installed kit is {__version__}. "
                    f"Upgrade the CLI first: pipx upgrade specfuse "
                    f"(or `pipx upgrade specfuse-authoring` on a standalone install)"
                )
        except ValueError:
            print(
                f"specfuse authoring upgrade: WARNING — malformed {VERSION_FILE}: "
                f"{recorded!r}. Proceeding as if unversioned.",
                file=sys.stderr,
            )

    old_manifest = read_manifest(target)
    files = overlay_files()
    if not files:
        sys.exit(f"Error: kit content missing under {kit_root()}")

    written: list[str] = []
    clobbered: list[str] = []
    manifest: dict[str, str] = {}

    for rel, content in files:
        dest = target / rel
        shipped_sha = _sha256_hex(content)
        manifest[rel] = shipped_sha

        if dest.exists():
            on_disk = _sha256_hex(dest.read_bytes())
            if on_disk == shipped_sha:
                continue  # already current
            # Warn only when there is a manifest to judge against. On a legacy
            # tree every file would warn, and the signal would drown.
            if old_manifest:
                owned = old_manifest.get(rel)
                if owned is None:
                    print(
                        f"specfuse authoring upgrade: WARNING — overwriting {rel}: "
                        "not written by a prior init/upgrade (project-authored?).",
                        file=sys.stderr,
                    )
                elif on_disk != owned:
                    print(
                        f"specfuse authoring upgrade: WARNING — overwriting locally-"
                        f"modified {rel}. Kit files are replaced on upgrade; send "
                        "changes upstream rather than editing in place.",
                        file=sys.stderr,
                    )
                clobbered.append(rel)

        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            if rel.startswith("scripts/") and rel.endswith(".sh"):
                dest.chmod(0o755)
        written.append(rel)

    shipped = {rel for rel, _ in files}
    pruned: list[str] = []
    kept: list[str] = []
    for prune_dir in PRUNE_DIRS:
        dir_path = target / prune_dir
        if not dir_path.is_dir():
            continue
        for existing in sorted(dir_path.rglob("*")):
            if not existing.is_file():
                continue
            rel = existing.relative_to(target).as_posix()
            if rel in shipped:
                continue
            # Delete only what the manifest proves the kit wrote — a file the
            # kit shipped once and has since dropped. Anything else is the
            # project's, including every file on a pre-manifest tree.
            if rel in old_manifest:
                if not dry_run:
                    existing.unlink()
                pruned.append(rel)
            else:
                kept.append(rel)

    if not dry_run:
        write_manifest(target, manifest)
        write_version(target)

    prefix = "Would upgrade" if dry_run else "Upgraded"
    from_ver = recorded or "unversioned"
    print(f"{prefix} {target}")
    print(f"  kit {from_ver} -> {__version__}")
    print(f"  {len(written)} file(s) written, {len(pruned)} removed")
    if clobbered:
        print(f"  {len(clobbered)} locally-modified or unowned file(s) overwritten (see warnings above)")
    for rel in kept:
        print(
            f"  kept {rel}: not shipped by this kit and not written by a prior "
            f"init/upgrade — delete it manually if it is stale.",
            file=sys.stderr,
        )
    if dry_run:
        print("  (dry run — nothing was written)")
    return 0


def legacy_refresh_paths(target: Path) -> list[str]:
    """Kit dirs a pre-overlay `refresh` created, for the deprecation notice."""
    return [
        d for d in (".specfuse/authoring/handbooks", ".specfuse/authoring/samples")
        if (target / d).is_dir()
    ]


def clean_orphans(target: Path) -> None:
    """Remove the empty dirs a prune can leave behind."""
    for prune_dir in PRUNE_DIRS:
        root = target / prune_dir
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                shutil.rmtree(path, ignore_errors=True)
