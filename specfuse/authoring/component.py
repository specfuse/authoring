"""`add-component` — seed a component repo beside the spec repo, once.

A component repo (a C# backend, a Python services workspace) receives generated
code from the spec repo through each group's `destination`. The generator
writes only the generated trees. The host around them (solution and project
files, package manifests, the composition root, the hand-written seams the
generated code calls by name) is project code. It is seeded here, ONCE, and is
the project's from then on: it is never in the scaffold manifest, and `upgrade`
never touches it. Seeding it from the generator instead would overwrite local
changes on every regen.

What this does, from the spec repo:

  1. creates `../<dir>` (refusing a non-empty one) and `git init`s it,
  2. renders `templates/components/<lang>/` into it,
  3. appends the component's groups to the project file,
  4. runs `scripts/specfuse/generate.sh` for those groups when the project has it,
     otherwise prints the commands to run.

The seeded package versions are the ones the kit's pinned generator compiles
against. CI (`example-regen.yml`) seeds, generates and builds on every pin
change, so a stale template fails there rather than in an adopter's first build.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import kit_root

LANGUAGES = ("csharp", "python")

# Artifact sets per C# layer: what the generated tree needs to compile together.
# The event runtime is always registered: at generator 0.19.0 the `service`
# artifact references IEventCollector whether or not the spec emits events
# (clabonte/generator#2883), and the runtime in turn needs the project-level
# `tenancy` block.
_CSHARP_DOMAIN = [
    "domainProject", "domainValidation", "domainExceptions", "valueObject", "entity",
    "enum", "domainModel", "serviceInterface", "repositoryInterface", "service",
    "asyncEvent", "tenancyMarker", "eventRuntime", "snapshot", "snapshotContext",
]
_CSHARP_INFRASTRUCTURE = [
    "entityTypeConfiguration", "valueObjectConverter", "dbContext", "repository",
    "infrastructureProject", "eventRuntimeImpl",
]
_CSHARP_API = [
    "apiProject", "apiMapper", "apiModel", "apiController", "applicationServiceInterface",
    "authorizationRuntime",
]

_PYTHON_CONTRACTS = ["aiEntity", "enum", "valueObject", "snapshot", "snapshotContext", "event", "eventBuilder"]
_PYTHON_CORE = ["aiRepository", "eventOutbox", "defaultEventEmitter"]

# Template files whose published name differs from their name in the kit.
# Dotfiles are stored without the dot so no packaging step can drop them.
_RENAMES = {"gitignore": ".gitignore"}

_TOKEN = re.compile(r"\{\{(\w+)\}\}")


class ComponentError(RuntimeError):
    pass


def render(text: str, values: dict) -> str:
    """Replace each `{{Key}}`. An unknown key is a template bug and fails loudly
    instead of rendering as empty text."""
    def token(m: re.Match) -> str:
        key = m.group(1)
        if key not in values:
            raise ComponentError(f"template uses unknown key {{{{{key}}}}}")
        return str(values[key])

    return _TOKEN.sub(token, text)


def pascal_case(name: str) -> str:
    """`hello-orders` → `HelloOrders`; an already PascalCase name is kept as is."""
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", name) if p]
    return "".join(p[:1].upper() + p[1:] for p in parts)


def python_abbreviation(project_name: str) -> str:
    """The package-root prefix the generator derives for Python (`PythonProfile.projectAbbreviation`).

    The generator imports across Python libraries by `<abbr>_contracts` /
    `<abbr>_core`, so the seeded packages must use exactly its derivation:
    the lowercased capitals of the project name (`RestoManager` → `rm`), else
    the name itself, snake-cased.
    """
    caps = "".join(c.lower() for c in project_name if c.isupper())
    if caps:
        return caps
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", project_name).lower()


def _find_project_file(spec_dir: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        if not explicit.is_file():
            raise ComponentError(f"project file not found: {explicit}")
        return explicit
    found = sorted(spec_dir.glob("*-project.json"))
    if len(found) != 1:
        raise ComponentError(
            f"expected one <name>-project.json in {spec_dir}, found {len(found)}; pass --project"
        )
    return found[0]


def _generator_version(spec_dir: Path) -> tuple[str, str | None]:
    """(kit-pinned version, project-pinned version or None)."""
    kit = json.loads((kit_root() / "generator.lock").read_text())["generator"]["version"]
    project_lock = spec_dir / ".specfuse" / "generator.lock"
    project = None
    if project_lock.is_file():
        try:
            project = json.loads(project_lock.read_text()).get("generator", {}).get("version")
        except json.JSONDecodeError:
            project = None
    return kit, project


def _groups(lang: str, config: dict, dir_name: str, values: dict, group_prefix: str) -> list[dict]:
    dest = f"../{dir_name}/"
    if lang == "csharp":
        prefix = values["Prefix"]
        return [
            {
                "name": f"{group_prefix}Domain",
                "language": "C#",
                "basePackage": f"{prefix}.Domain",
                "destination": dest,
                "cleanGenerated": True,
                "artifacts": list(_CSHARP_DOMAIN),
            },
            {
                "name": f"{group_prefix}Infrastructure",
                "language": "C#",
                "basePackage": f"{prefix}.Infrastructure",
                "destination": dest,
                "cleanGenerated": True,
                "artifacts": list(_CSHARP_INFRASTRUCTURE),
            },
            {
                "name": f"{group_prefix}Api",
                "language": "C#",
                "basePackage": f"{prefix}.Api",
                "destination": dest,
                "cleanGenerated": True,
                "artifacts": list(_CSHARP_API),
            },
        ]
    return [
        {
            "name": f"{group_prefix}PythonContracts",
            "language": "python",
            "basePackage": values["ContractsPackage"],
            "destination": f"{dest}libs/contracts/src",
            "cleanGenerated": True,
            "artifacts": list(_PYTHON_CONTRACTS),
        },
        {
            "name": f"{group_prefix}PythonCore",
            "language": "python",
            "basePackage": values["CorePackage"],
            "destination": f"{dest}libs/core/src",
            "cleanGenerated": True,
            "artifacts": list(_PYTHON_CORE),
        },
    ]


def _values(lang: str, config: dict, spec_dir: Path, dir_name: str, namespace: str | None) -> dict:
    project_name = config.get("name") or ""
    kit_version, project_version = _generator_version(spec_dir)
    values = {
        "Dir": dir_name,
        "ProjectName": project_name,
        "SpecRepo": spec_dir.name,
        "GeneratorVersion": kit_version,
        "ProjectGeneratorVersion": project_version or "",
    }
    if lang == "csharp":
        prefix = namespace or pascal_case(project_name)
        if not re.fullmatch(r"[A-Z][A-Za-z0-9]*(\.[A-Z][A-Za-z0-9]*)*", prefix or ""):
            raise ComponentError(
                f"cannot derive a C# namespace from project name {project_name!r}; pass --namespace"
            )
        if not config.get("tenancy"):
            raise ComponentError(
                "a C# component needs a project-level `tenancy` block (handbooks/Project_File.md §4.1).\n"
                "  At this generator, generated services always use the event runtime, and the event\n"
                "  runtime requires tenancy, so a single-tenant project cannot compile them yet\n"
                "  (clabonte/generator#2883). Add a `tenancy` block naming your tenant entity, then rerun."
            )
        values.update(Prefix=prefix)
    else:
        abbr = python_abbreviation(project_name)
        if not abbr.isidentifier():
            raise ComponentError(
                f"the generator derives the Python package root '{abbr}_contracts' from project "
                f"name {project_name!r}, which is not a valid Python identifier.\n"
                "  Generated Python imports across its libraries by that derived name, so the\n"
                "  packages cannot be renamed here. Until the generator derives a valid root from\n"
                "  kebab-case names (clabonte/generator#2882), set the project file's `name` to PascalCase (e.g. "
                f"{pascal_case(project_name)!r}), which yields "
                f"'{python_abbreviation(pascal_case(project_name))}_contracts'."
            )
        values.update(
            ContractsPackage=f"{abbr}_contracts",
            CorePackage=f"{abbr}_core",
            ContractsDist=f"{abbr.replace('_', '-')}-contracts",
            CoreDist=f"{abbr.replace('_', '-')}-core",
        )
    return values


def _render_tree(src: Path, dest: Path, values: dict) -> list[Path]:
    written: list[Path] = []
    for path in sorted(src.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(src).as_posix().replace("__Prefix__", str(values.get("Prefix", "")))
        parts = rel.split("/")
        parts[-1] = _RENAMES.get(parts[-1], parts[-1])
        out = dest.joinpath(*parts)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(path.read_text(encoding="utf-8"), values), encoding="utf-8")
        written.append(out)
    return written


def add_component(
    lang: str,
    dir_name: str,
    *,
    spec_dir: Path | None = None,
    project_file: Path | None = None,
    namespace: str | None = None,
    group_prefix: str = "",
    generate: bool = True,
    dry_run: bool = False,
) -> int:
    try:
        return _add_component(
            lang, dir_name, spec_dir=(spec_dir or Path.cwd()).resolve(), project_file=project_file,
            namespace=namespace, group_prefix=group_prefix, generate=generate, dry_run=dry_run,
        )
    except ComponentError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _add_component(
    lang: str, dir_name: str, *, spec_dir: Path, project_file: Path | None, namespace: str | None,
    group_prefix: str, generate: bool, dry_run: bool,
) -> int:
    if lang not in LANGUAGES:
        raise ComponentError(f"unsupported language {lang!r}; choose one of {', '.join(LANGUAGES)}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", dir_name):
        raise ComponentError(f"{dir_name!r} is not a plain directory name (it is created beside the spec repo)")

    config_path = _find_project_file(spec_dir, project_file)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    target = spec_dir.parent / dir_name
    if target.exists() and any(target.iterdir()):
        raise ComponentError(f"{target} already exists and is not empty; seeding never overwrites")

    values = _values(lang, config, spec_dir, dir_name, namespace)
    groups = _groups(lang, config, dir_name, values, group_prefix)
    taken = {g.get("name", "").lower() for g in config.get("groups", [])}
    clash = [g["name"] for g in groups if g["name"].lower() in taken]
    if clash:
        raise ComponentError(
            f"the project file already has group(s) {', '.join(clash)}; pass --group-prefix to name these apart"
        )
    values["Groups"] = " ".join(f'"{g["name"]}"' if " " in g["name"] else g["name"] for g in groups)

    print(f"Seeding a {lang} component at {target}")
    for g in groups:
        print(f"  + group {g['name']} [{g['language']}] {g['basePackage']} -> {g['destination']}")
    if values["ProjectGeneratorVersion"] and values["ProjectGeneratorVersion"] != values["GeneratorVersion"]:
        print(
            f"Warning: the project pins generator {values['ProjectGeneratorVersion']}; the seeded "
            f"package versions were verified with {values['GeneratorVersion']}. A failing first "
            "build names what to adjust.",
            file=sys.stderr,
        )
    if dry_run:
        print("Dry run: nothing written.")
        return 0

    written = _render_tree(kit_root() / "templates" / "components" / lang, target, values)
    if shutil.which("git"):
        subprocess.run(["git", "init", "-q", str(target)], check=False)

    config.setdefault("groups", []).extend(groups)
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(written)} file(s) and added {len(groups)} group(s) to {config_path.name}.")

    names = [g["name"] for g in groups]
    script = spec_dir / "scripts" / "specfuse" / "generate.sh"
    if generate and script.is_file():
        print(f"\nGenerating {', '.join(names)}. The new repo's seed is not committed yet, so")
        print("generate.sh runs with --allow-dirty and will flag it.")
        rc = subprocess.run(["bash", str(script), *names, "--allow-dirty"], cwd=spec_dir).returncode
        if rc != 0:
            print(f"Generation failed (exit {rc}). The seed and the groups stay; fix and rerun generate.sh.",
                  file=sys.stderr)
            return rc
    else:
        print("\nGenerate the new groups from the spec repo:")
        print("  ./scripts/specfuse/bundle-spec.sh && ./scripts/specfuse/bundle-async-spec.sh")
        for n in names:
            print(f'  specfuse authoring generate generate --group "{n}" {config_path.name}')

    build = "dotnet build" if lang == "csharp" else "uv sync --all-packages && uv run pytest"
    print(f"\nNext, in {target}:")
    print(f"  {build}")
    print("  git add -A && git commit -m 'Seed component and first regen'")
    print(f"Then commit the {config_path.name} change in the spec repo.")
    return 0
