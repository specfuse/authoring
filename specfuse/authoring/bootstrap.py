"""Project bootstrap for specfuse-authoring.

  * init    -> prompt name/token/domain, lay down the project skeleton from the
               project-init template, scaffold the authoring contract into
               .specfuse/authoring/, and wire the specfuse-authoring Claude Code
               plugin into .claude/settings.json.
  * refresh -> re-sync .specfuse/authoring/ from the installed package and
               re-assert the plugin config in an existing project.

Claude assets (skills + agents) are distributed via the `specfuse` Claude Code
plugin marketplace (github: specfuse/specfuse), NOT copied per project. `init`
registers that marketplace and enables the `specfuse-authoring@specfuse` plugin;
the skills read the contract scaffolded under .specfuse/authoring/.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from . import kit_root

NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")  # kebab-case
TOKEN_RE = re.compile(r"^[a-z][a-z0-9]*$")  # lowercase alnum, no dots/hyphens

# Claude Code plugin wiring (shared `specfuse` marketplace; our plugin key).
MARKETPLACE_KEY = "specfuse"
MARKETPLACE_VALUE = {"source": {"source": "github", "repo": "specfuse/specfuse"}}
PLUGIN_KEY = "specfuse-authoring@specfuse"

# The authoring contract the skills read at runtime, scaffolded into the project.
CONTRACT_DIRS = ("handbooks", "samples")
SCAFFOLD_SUBDIR = Path(".specfuse") / "authoring"


def scaffold_contract(target: Path) -> None:
    """Copy the authoring contract (handbooks/, samples/) into
    <target>/.specfuse/authoring/. Overwrites — this is a version-sync."""
    root = kit_root()
    dest_base = target / SCAFFOLD_SUBDIR
    for sub in CONTRACT_DIRS:
        src = root / sub
        if not src.is_dir():
            sys.exit(f"Error: kit content missing: {src}")
        dst = dest_base / sub
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def wire_plugin(target: Path) -> list[str]:
    """Parse-merge-rewrite <target>/.claude/settings.json to assert the
    specfuse-authoring plugin config. Idempotent; returns the changed keys.

    - extraKnownMarketplaces["specfuse"] = the github source (overwrite on drift)
    - enabledPlugins["specfuse-authoring@specfuse"] = true (restore if removed)
    All other settings are preserved untouched.
    """
    claude_dir = target / ".claude"
    settings_path = claude_dir / "settings.json"
    if settings_path.exists():
        data = json.loads(settings_path.read_text())
    else:
        data = {}

    changed: list[str] = []
    marketplaces = data.setdefault("extraKnownMarketplaces", {})
    if marketplaces.get(MARKETPLACE_KEY) != MARKETPLACE_VALUE:
        marketplaces[MARKETPLACE_KEY] = MARKETPLACE_VALUE
        changed.append(f"extraKnownMarketplaces.{MARKETPLACE_KEY}")
    plugins = data.setdefault("enabledPlugins", {})
    if plugins.get(PLUGIN_KEY) is not True:
        plugins[PLUGIN_KEY] = True
        changed.append(f"enabledPlugins.{PLUGIN_KEY}")

    if changed:
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return changed


def refresh(target: Path) -> int:
    if not target.is_dir():
        sys.exit(f"Error: target directory does not exist: {target}")
    print(f"Refreshing authoring contract + plugin config in: {target}")
    scaffold_contract(target)
    changed = wire_plugin(target)
    print("✓ Synced .specfuse/authoring/ (handbooks, samples)")
    print(
        f"✓ Re-asserted plugin config: {', '.join(changed)}"
        if changed else "✓ Plugin config already current"
    )
    print("  Pull the latest skills in Claude Code: /plugin update specfuse-authoring@specfuse")
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

    # Copy template tree, excluding any bootstrap script/README at the template root.
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

    print("Scaffolding authoring contract + wiring the plugin...")
    scaffold_contract(target)
    wire_plugin(target)

    print(
        f"\n✓ Project bootstrapped at {target}\n\n"
        "  Next steps:\n"
        f"    cd {target}\n"
        "    git init && git add . && git commit -m 'Initial bootstrap from specfuse-authoring'\n\n"
        "  Install the authoring skills (one-time, in Claude Code):\n"
        "    /plugin marketplace add specfuse/specfuse\n"
        "    /plugin install specfuse-authoring@specfuse\n"
        "  (init already registered the marketplace and enabled the plugin in\n"
        "   .claude/settings.json — the commands above are the manual equivalent.)\n\n"
        "  Then design with /specfuse-authoring:design-scenario or :design-async.\n"
        "  After a kit update, re-sync the contract + plugin config with:\n"
        f"    specfuse-authoring refresh {target}\n"
    )
    return 0
