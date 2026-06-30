"""Project bootstrap — Python port of templates/project-init/init.sh.

Faithful to the bash original:
  * init    -> prompt name/token/domain, copy template tree, rename the
               {initial-domain} dir, substitute placeholders in *.template
               files, rename the project json, copy claude-assets.
  * refresh -> re-copy claude-assets agents + commands into an existing
               project's .claude/.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from . import kit_root

NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")  # kebab-case
TOKEN_RE = re.compile(r"^[a-z][a-z0-9]*$")  # lowercase alnum, no dots/hyphens


def _claude_assets_src() -> Path:
    assets = kit_root() / "claude-assets"
    if not (assets / "agents").is_dir() or not (assets / "commands").is_dir():
        sys.exit(f"Error: kit claude-assets incomplete at {assets}")
    return assets


def copy_claude_assets(target: Path) -> None:
    """Copy agents/ and commands/ markdown into target/.claude/ (mirrors init.sh)."""
    src = _claude_assets_src()
    for sub in ("agents", "commands"):
        dst = target / ".claude" / sub
        dst.mkdir(parents=True, exist_ok=True)
        for md in sorted((src / sub).glob("*.md")):
            shutil.copy2(md, dst / md.name)


def refresh(target: Path) -> int:
    if not target.is_dir():
        sys.exit(f"Error: target directory does not exist: {target}")
    print(f"Refreshing claude-assets in: {target}")
    copy_claude_assets(target)
    print("✓ Refreshed .claude/agents/ and .claude/commands/")
    return 0


def _prompt(label: str, pattern: re.Pattern[str], err: str, value: str | None) -> str:
    if value is not None:
        if not pattern.match(value):
            sys.exit(f"Error: {err}")
        return value
    raw = input(label).strip()
    if not pattern.match(raw):
        sys.exit(f"Error: {err}")
    return raw


def init(
    target: Path,
    *,
    name: str | None = None,
    token: str | None = None,
    domain: str | None = None,
    assume_yes: bool = False,
) -> int:
    if target.exists() and not target.is_dir():
        sys.exit(f"Error: {target} exists and is not a directory.")
    if target.is_dir() and any(target.iterdir()):
        if not assume_yes:
            confirm = input(
                f"Target directory {target} is not empty. Continue and overwrite? [y/N] "
            ).strip().lower()
            if confirm != "y":
                print("Aborted.")
                return 1

    project_name = _prompt(
        "Project name (kebab-case, e.g. my-app): ",
        NAME_RE,
        "project name must be kebab-case (lowercase letters, digits, hyphens; start with a letter).",
        name,
    )
    project_token = _prompt(
        "Project token for channel addresses (lowercase, no dots, e.g. myapp): ",
        TOKEN_RE,
        "project token must be lowercase letters and digits only (no hyphens, no dots).",
        token,
    )
    initial_domain = _prompt(
        "Initial domain name (kebab-case, e.g. order): ",
        NAME_RE,
        "domain name must be kebab-case.",
        domain,
    )

    template_root = kit_root() / "templates" / "project-init"
    if not template_root.is_dir():
        sys.exit(f"Error: project-init template not found at {template_root}")

    target.mkdir(parents=True, exist_ok=True)
    target = target.resolve()
    print(f"\nBootstrapping Specfuse project.\n  Kit:    {kit_root()}\n  Target: {target}\n")

    # Copy template tree, excluding init.sh and README.md (mirrors init.sh).
    for src in template_root.rglob("*"):
        if not src.is_file():
            continue
        if src.name in ("init.sh", "README.md"):
            continue
        dest = target / src.relative_to(template_root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    # Rename the initial domain folder.
    placeholder_domain = target / "api" / "specs" / "v1" / "domains" / "{initial-domain}"
    if placeholder_domain.is_dir():
        placeholder_domain.rename(placeholder_domain.with_name(initial_domain))

    # Process *.template files: strip suffix and substitute placeholders.
    subs = {
        "{ProjectName}": project_name,
        "{project}": project_token,
        "{initial-domain}": initial_domain,
    }
    for tmpl in list(target.rglob("*.template")):
        text = tmpl.read_text()
        for k, v in subs.items():
            text = text.replace(k, v)
        tmpl.with_suffix("").write_text(text)  # drops the .template suffix
        tmpl.unlink()

    # Rename the project config file to the actual project name.
    proj_json = target / "{project-name}-project.json"
    if proj_json.is_file():
        proj_json.rename(target / f"{project_name}-project.json")

    print("Copying claude-assets...")
    copy_claude_assets(target)

    print(
        f"\n✓ Project bootstrapped at {target}\n\n"
        "  Next steps:\n"
        f"    cd {target}\n"
        "    git init && git add . && git commit -m 'Initial bootstrap from spec-authoring-kit'\n\n"
        "  Then read CLAUDE.md and start designing with /design-scenario or /design-async.\n"
        "  Refresh agents/commands after a kit update with:\n"
        f"    specfuse-authoring refresh {target}\n"
    )
    return 0
