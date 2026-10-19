"""Generator launcher — download-on-demand, pinned, checksummed jar.

The generator is a closed-source Java binary distributed as a private GitHub
Release asset. The public kit never contains the jar; it contains only the
pin (generator.lock) and the expected SHA-256. On `generate`, the launcher:

  1. reads the pin: the project's `.specfuse/generator.lock` when one exists
     (searched upward from the working directory, stopping at the repo root),
     otherwise the one shipped with the installed kit version,
  2. uses the cached jar if its checksum matches,
  3. otherwise downloads the pinned release asset (gh CLI, or HTTPS + token),
  4. verifies SHA-256 against the pin (aborts on mismatch),
  5. runs `java -jar <jar> <args...>`.

`SPECFUSE_GENERATOR_JAR=/path/to.jar` skips all of the above and runs that jar
as-is: no pin, no checksum. It exists for generator development and is
reported as unpinned on every run.

Access is gated entirely by the client's ability to pull the private release
(a GitHub token). Revoke the token -> revoke the generator; the kit is
unaffected.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from . import kit_root

CACHE_DIR = Path(os.environ.get("SPECFUSE_HOME", Path.home() / ".specfuse")) / "jars"
TOKEN_ENV = "SPECFUSE_TOKEN"  # GitHub token with read access to the dist repo
JAR_ENV = "SPECFUSE_GENERATOR_JAR"  # unpinned local jar; same name the project scripts honour
PROJECT_LOCK = Path(".specfuse") / "generator.lock"


def _load_kit_pin() -> dict:
    lock = kit_root() / "generator.lock"
    if not lock.is_file():
        sys.exit(f"Error: generator.lock not found at {lock}")
    return json.loads(lock.read_text())


def find_project_lock(start: Path | None = None) -> Path | None:
    """The nearest `.specfuse/generator.lock` at or above `start`.

    The search stops at the first directory holding `.git`, so a project never
    picks up a pin from an unrelated checkout that happens to enclose it.
    """
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        if (d / PROJECT_LOCK).is_file():
            return d / PROJECT_LOCK
        if (d / ".git").exists():
            return None
    return None


def _project_pin(lock: Path, kit_pin: dict) -> dict:
    """A project pin, with unset fields defaulted from the generator's release conventions.

    Only `version` and `sha256` are required. `asset`, `release_tag` and
    `release_repo` follow the dist repo's naming, so a project bumping its pin
    writes two values, not five.
    """
    try:
        pin = json.loads(lock.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"Error: {lock} is not valid JSON: {e}")
    gen = pin.get("generator")
    if not isinstance(gen, dict) or not gen.get("version") or not gen.get("sha256"):
        sys.exit(
            f"Error: {lock} must set generator.version and generator.sha256, e.g.\n"
            '       {"generator": {"version": "0.19.0", "sha256": "<64 hex chars>"}}'
        )
    version = gen["version"]
    kit_gen = kit_pin.get("generator", {})
    gen.setdefault("asset", f"specfuse-generator-{version}.jar")
    gen.setdefault("release_tag", f"v{version}")
    gen.setdefault("release_repo", kit_gen.get("release_repo", "Specfuse/generator-dist"))
    pin.setdefault("min_java", kit_pin.get("min_java", 21))
    return pin


def _load_pin() -> tuple[dict, str]:
    """The effective pin and a short label naming where it came from."""
    kit_pin = _load_kit_pin()
    lock = find_project_lock()
    if lock is not None:
        pin = _project_pin(lock, kit_pin)
        kit_version = kit_pin.get("generator", {}).get("version")
        if pin["generator"]["version"] != kit_version:
            print(
                f"Warning: {lock} pins generator {pin['generator']['version']}; this kit "
                f"({kit_pin.get('kit_version', '?')}) is tested with {kit_version}. "
                "See compatibility.md.",
                file=sys.stderr,
            )
        return pin, f"project pin {lock}"
    gen = kit_pin.get("generator", {})
    if gen.get("sha256") in (None, "", "PENDING"):
        sys.exit(
            "Error: no generator is pinned for this kit version yet.\n"
            "       This kit release predates a published generator jar.\n"
            "       Upgrade the kit once a generator-bearing release is available."
        )
    return kit_pin, "kit pin"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_java(min_java: int) -> None:
    if shutil.which("java") is None:
        sys.exit(f"Error: 'java' not found on PATH. The generator needs JRE {min_java}+.")
    # Best-effort version check; never block on a parse failure.
    try:
        out = subprocess.run(
            ["java", "-version"], capture_output=True, text=True, check=False
        ).stderr
        # e.g. 'openjdk version "17.0.10"' or '"1.8.0_xxx"'
        ver = out.split('"', 2)[1] if '"' in out else ""
        major = int(ver.split(".")[0]) if not ver.startswith("1.") else int(ver.split(".")[1])
        if major < min_java:
            sys.exit(f"Error: Java {major} found; generator needs JRE {min_java}+.")
    except (IndexError, ValueError):
        print("Warning: could not parse Java version; proceeding.", file=sys.stderr)


def _download(pin: dict, dest: Path) -> None:
    gen = pin["generator"]
    repo = gen["release_repo"]
    tag = gen["release_tag"]
    asset = gen["asset"]
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Prefer the gh CLI — it handles private-repo auth transparently.
    if shutil.which("gh"):
        print(f"Downloading {asset} ({tag}) via gh from {repo}...")
        subprocess.run(
            ["gh", "release", "download", tag,
             "--repo", repo, "--pattern", asset,
             "--output", str(dest), "--clobber"],
            check=True,
        )
        return

    # Fallback: GitHub API asset download over HTTPS with a bearer token.
    token = os.environ.get(TOKEN_ENV)
    if not token:
        sys.exit(
            f"Error: need the 'gh' CLI or {TOKEN_ENV} set to pull the generator "
            f"from private repo {repo}."
        )
    api = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    req = urllib.request.Request(
        api, headers={"Authorization": f"Bearer {token}",
                      "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req) as resp:  # noqa: S310 (trusted host)
        release = json.load(resp)
    asset_url = next(
        (a["url"] for a in release.get("assets", []) if a["name"] == asset), None
    )
    if not asset_url:
        sys.exit(f"Error: asset {asset} not found in {repo}@{tag}.")
    print(f"Downloading {asset} ({tag}) from {repo}...")
    dl = urllib.request.Request(
        asset_url, headers={"Authorization": f"Bearer {token}",
                            "Accept": "application/octet-stream"}
    )
    with urllib.request.urlopen(dl) as resp, dest.open("wb") as out:  # noqa: S310
        shutil.copyfileobj(resp, out)


def resolve_jar() -> tuple[Path, dict, str]:
    """Return a verified, cached generator jar (downloading if needed), its pin, and the pin's source."""
    override = os.environ.get(JAR_ENV)
    if override:
        jar = Path(override).expanduser()
        if not jar.is_file():
            sys.exit(f"Error: {JAR_ENV}={override} is not a file.")
        print(
            f"Warning: {JAR_ENV} is set; running {jar} UNPINNED (no checksum verified).",
            file=sys.stderr,
        )
        return jar, {"min_java": _load_kit_pin().get("min_java", 21)}, f"{JAR_ENV}, unpinned"

    pin, source = _load_pin()
    gen = pin["generator"]
    jar = CACHE_DIR / gen["asset"]

    if jar.is_file() and _sha256(jar) == gen["sha256"]:
        return jar, pin, source

    _download(pin, jar)
    actual = _sha256(jar)
    if actual != gen["sha256"]:
        jar.unlink(missing_ok=True)
        sys.exit(
            "Error: checksum mismatch on downloaded generator jar.\n"
            f"       expected {gen['sha256']}\n       got      {actual}\n"
            f"       (pin: {source})"
        )
    return jar, pin, source


def generate(passthrough_args: list[str]) -> int:
    jar, pin, source = resolve_jar()
    _check_java(int(pin.get("min_java", 21)))
    print(f"Running generator: {jar.name} ({source})", flush=True)
    return subprocess.run(["java", "-jar", str(jar), *passthrough_args]).returncode
