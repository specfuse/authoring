#!/usr/bin/env python3
# Copyright 2026 Specfuse Contributors
# Licensed under the Apache License, Version 2.0. See LICENSE.
#
# Vendor-extension vocabulary drift guard.
#
# A Spectral ruleset that validates a vendor extension with
# `additionalProperties: false` is a CLOSED schema over a vocabulary this repo
# does not own — the generator does. When the generator adds a key, a closed
# schema does not merely miss a warning: the first spec that declares the new
# key fails lint outright, so the generator feature cannot be adopted at all.
# Nothing surfaces until someone tries, and then it looks like a spec error.
#
# This has happened three times on the same extension (`x-entity`): `domain`
# shipped across 78 entities and sat broken for months, `concurrency`
# (FEAT-2026-0078) blocked rollout until the ruleset was patched by hand, and
# `delete` (FEAT-2026-0080) was heading for the same wall. Each was caught by a
# human noticing. Patching the ruleset by hand alongside each feature is the
# practice that failed all three times, which is why this check exists.
#
# It compares, per closed guard, the keys the GENERATOR references against the
# keys the ruleset ACCEPTS:
#
#   generator knows a key the ruleset does not  -> FAIL (blocks adoption)
#   ruleset accepts a key the generator does not -> report, never fail
#
# The asymmetry is deliberate: only the first direction can block a spec author.
# The second is still worth reporting — a key the ruleset accepts and codegen
# ignores is metadata documenting intent nothing enforces, which can silently
# stop being true — but it is not a build-stopper, and some of it is kit-only on
# purpose (see `kit_only` in the exceptions file).
#
# Where the vocabulary comes from, per surface:
#
#   `extensions --format json`  the generator's own answer. Authoritative.
#                               Generator FEAT-2026-0098, present from 0.5.8.
#                               Covers the surfaces the parser owns as a closed
#                               vocabulary — `x-entity` today.
#   constant-pool scan          fallback for every other surface, and for jars
#                               older than the subcommand. A heuristic: the
#                               generator reaches some keys through indirect
#                               constants that leave no string literal, so a key
#                               it misses looks ruleset-only when it is not.
#
# The reverse direction is therefore only reported as real drift for surfaces
# the jar publishes. Anywhere else it stays informational, because otherwise a
# heuristic miss reads as a finding and the noise trains a reader to skip it.
#
# `schema` is why this matters: deprecated but still parsed, absent from the
# kit's allow-list, and rejected at ERROR — 17 live schemas could not lint. The
# forward direction would have caught it, and nothing ran the check because
# discovery found no rulesets in the kit repo and exited 0. A guard that passes
# vacuously is worse than no guard, so --require-jar now fails when it finds
# nothing to examine.
#
# Usage:
#   ./scripts/check-extension-vocabulary.py            # lint-time check
#   ./scripts/check-extension-vocabulary.py --require-jar   # CI: no silent skip
#   SPECFUSE_GENERATOR_JAR=/path/to.jar ./scripts/check-extension-vocabulary.py
#
# Exit codes: 0 clean (or skipped), 1 drift found, 2 the check could not run.

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment guidance, not logic
    sys.stderr.write(
        "check-extension-vocabulary.py requires PyYAML, which is not installed.\n"
        "\n"
        "  pip install PyYAML          (or: pipx inject specfuse PyYAML)\n"
        "\n"
        "Without it this guard cannot read the Spectral rulesets, and vendor\n"
        "extension drift goes back to being found by a failing lint.\n"
    )
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parent.parent

# Where the kit delivers its rulesets, plus any project-local ones. A project
# may carry its own ruleset with its own closed guards (a `<token>-*-shape`
# rule); those are exactly as exposed as the kit's, so they are checked too.
RULESET_GLOBS = (
    ".specfuse/authoring/schemas/spectral/*.yaml",
    "api/spectral*.yaml",
    "api/**/spectral*.yaml",
)

# The kit's own copies, for maintainers running this from the kit repo rather
# than from a provisioned project. Resolved relative to the repo root, which is
# three levels above this file (templates/project-init/scripts/). Without this
# the globs above match nothing in the kit repo and the check exits 0 having
# examined nothing — a vacuous pass, which is the failure mode this whole guard
# exists to prevent. See `--require-jar` below, which now refuses to be vacuous.
KIT_ROOT = Path(__file__).resolve().parents[3]
KIT_RULESET_GLOBS = ("schemas/spectral/*.yaml",)

# Keys the generator references that are NOT part of the guarded surface —
# declared here, with a reason, rather than silently tolerated. A new generator
# key must land in the ruleset or in this file; it cannot pass unexamined.
EXCEPTIONS_FILE = ROOT / ".specfuse" / "authoring" / "vocabulary-exceptions.yaml"


def find_jar() -> Path | None:
    """The generator jar the kit resolved most recently.

    `specfuse authoring generate` verifies each jar's SHA-256 against
    generator.lock before caching it under $SPECFUSE_HOME/jars, so a cached jar
    is a jar this project's pinned kit vouched for. SPECFUSE_GENERATOR_JAR
    overrides for CI, where the cache may be primed from a different path.
    """
    override = os.environ.get("SPECFUSE_GENERATOR_JAR")
    if override:
        p = Path(override).expanduser()
        return p if p.is_file() else None
    home = Path(os.environ.get("SPECFUSE_HOME", Path.home() / ".specfuse"))
    jars = sorted((home / "jars").glob("specfuse-generator-*.jar"))
    if not jars:
        return None

    def version_key(p: Path) -> tuple:
        m = re.search(r"-(\d+(?:\.\d+)*)\.jar$", p.name)
        return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)

    return max(jars, key=version_key)


# Constant-pool tag -> bytes to skip after the tag. Entries not listed are
# handled explicitly: 1 (UTF8, length-prefixed) and 5/6 (long/double, which
# occupy two pool slots — a JVM quirk that silently desynchronises any reader
# that forgets it).
_CP_FIXED = {7: 2, 8: 2, 16: 2, 19: 2, 20: 2, 15: 3,
             3: 4, 4: 4, 9: 4, 10: 4, 11: 4, 12: 4, 17: 4, 18: 4}


def class_constants(data: bytes):
    """Every UTF-8 constant in a class file, exactly as stored.

    Parsing the constant pool rather than grepping the raw bytes matters for
    correctness, not tidiness: a UTF-8 entry is preceded by its u2 length, and
    a length byte lands in the printable ASCII range often enough that a
    regex reading past a string's end appends the next entry's length to the
    key — `domain` becomes `domainA`, and the check invents drift that is not
    there. Only the pool is read; everything after it is irrelevant here.
    """
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        return
    count = int.from_bytes(data[8:10], "big")
    i, slot = 10, 1
    while slot < count and i < len(data):
        tag = data[i]
        i += 1
        if tag == 1:
            if i + 2 > len(data):
                return
            length = int.from_bytes(data[i:i + 2], "big")
            i += 2
            yield data[i:i + length]
            i += length
        elif tag in (5, 6):
            i += 8
            slot += 1  # long/double take two slots
        else:
            skip = _CP_FIXED.get(tag)
            if skip is None:
                return  # unknown tag: the pool is not what we think it is
            i += skip
        slot += 1


def published_vocabulary(jar: Path) -> dict[str, set[str]] | None:
    """Ask the jar what it recognises, via `extensions --format json`.

    Authoritative where the constant-pool scan below is a heuristic: the
    subcommand prints the parser's own key set, so a key the generator reads
    through an indirect constant is included and a key that appears only inside
    a diagnostic string is not. Generator FEAT-2026-0098; present from 0.5.8.

    Returns None when the jar predates the subcommand, so the caller falls back
    rather than silently reporting an empty vocabulary — an empty result would
    read as "the generator knows nothing", which passes every comparison.
    """
    try:
        proc = subprocess.run(
            ["java", "-jar", str(jar), "extensions", "--format", "json"],
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(doc, dict) or not doc:
        return None
    out: dict[str, set[str]] = {}
    for surface, entries in doc.items():
        if not isinstance(entries, list):
            return None
        keys = {e["key"] for e in entries
                if isinstance(e, dict) and isinstance(e.get("key"), str)}
        if not keys:
            return None
        out[surface] = keys
    return out or None


def generator_keys(jar: Path, prefixes: set[str]) -> dict[str, set[str]]:
    """Extract `<prefix>.<key>` constants from the jar's class files.

    Reading the generator's own constants rather than a published vocabulary
    document is the point: the generator's behaviour is the authority, and a
    document describing it is one more thing that can drift. Scanning is driven
    by the prefixes the rulesets actually close over, which also keeps the
    bundled openapi-generator's several hundred `x-codegen-*` extensions out of
    the comparison.
    """
    found: dict[str, set[str]] = {p: set() for p in prefixes}
    # Searched within each constant, not anchored to it: the generator names a
    # key inside diagnostic strings ("x-entity.domain must be registered…") as
    # often as it names it alone, and anchoring drops those — the direction that
    # matters, because a key the check fails to see is drift it fails to report.
    # Parsing the pool first is what makes searching safe: a match cannot run
    # off the end of one constant into the next entry's length bytes.
    matchers = {
        p: re.compile(r"(?:^|[^A-Za-z0-9._-])" + re.escape(p) + r"\.([A-Za-z][A-Za-z0-9]*)")
        for p in prefixes
    }
    with zipfile.ZipFile(jar) as z:
        for name in z.namelist():
            if not name.endswith(".class"):
                continue
            data = z.read(name)
            if b"x-" not in data:  # cheap prefilter; most classes have none
                continue
            for raw in class_constants(data):
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                if "x-" not in text:
                    continue
                for prefix, pat in matchers.items():
                    for key in pat.findall(text):
                        found[prefix].add(key)
    return found


def closed_guards(paths: list[Path]) -> list[dict]:
    """Every rule whose `then` closes a schema with `additionalProperties: false`.

    Discovered structurally, not from a hardcoded list of rule names: a repo
    that adds a fifth closed guard next month gets it checked without touching
    this script. The extension surface is read off the rule's `given` — the
    last `x-…` path it selects — so `x-entity`, `x-value-object` and a nested
    surface like `x-ai.entities` are all handled the same way.
    """
    guards: list[dict] = []
    for path in paths:
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            sys.stderr.write(f"⚠️  {path}: unreadable as YAML ({exc}); skipped\n")
            continue
        for name, rule in (doc.get("rules") or {}).items():
            if not isinstance(rule, dict):
                continue
            given = rule.get("given")
            givens = given if isinstance(given, list) else [given]
            thens = rule.get("then") or {}
            for then in thens if isinstance(thens, list) else [thens]:
                if not isinstance(then, dict):
                    continue
                opts = then.get("functionOptions")
                schema = opts.get("schema") if isinstance(opts, dict) else None
                if not isinstance(schema, dict):
                    continue
                if schema.get("additionalProperties") is not False:
                    continue
                props = schema.get("properties")
                if not isinstance(props, dict):
                    continue
                surface = extension_surface(givens)
                if not surface:
                    continue
                guards.append({
                    "ruleset": path,
                    "rule": name,
                    "surface": surface,
                    "keys": set(props),
                    "all_keys": schema_keys(schema),
                })
    return guards


def schema_keys(schema: dict) -> set[str]:
    """Every property name the schema accepts, at any depth.

    Nesting matters here. The generator namespaces a constant by the extension
    it belongs to (`x-value-object.storage`) even when the key is authored
    inside another extension's block — `x-entity.valueObjects.<prop>.storage`
    is where `storage` is actually written. Comparing only a guard's top-level
    properties would report those as missing when the ruleset accepts them
    perfectly well, one level down.
    """
    keys: set[str] = set()
    stack = [schema]
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
            continue
        if not isinstance(node, dict):
            continue
        props = node.get("properties")
        if isinstance(props, dict):
            keys.update(props)
            stack.extend(props.values())
        for branch in ("items", "additionalProperties", "patternProperties",
                       "oneOf", "anyOf", "allOf", "then", "else", "if"):
            child = node.get(branch)
            if isinstance(child, (dict, list)):
                stack.append(child)
    return keys


def extension_surface(givens: list) -> str | None:
    """The dotted extension path a `given` selects: `$…["x-entity"]` -> x-entity."""
    tokens: list[str] = []
    for given in givens:
        if not isinstance(given, str):
            continue
        # Both spellings occur: bracket-quoted (needed for hyphenated names)
        # and bare dotted. Take the deepest x-… path the selector reaches.
        for match in re.finditer(r'(?:\["|\.)(x-[a-z][a-z0-9-]*)(?:"\])?((?:\.[A-Za-z][A-Za-z0-9]*)*)',
                                 given):
            tokens.append(match.group(1) + match.group(2))
    return max(tokens, key=len) if tokens else None


def _exception_section(doc: dict, name: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for surface, entries in (doc.get(name) or {}).items():
        out[surface] = {e["key"]: e.get("reason", "") for e in entries or []
                        if isinstance(e, dict) and "key" in e}
    return out


def load_exceptions() -> dict[str, dict[str, str]]:
    if not EXCEPTIONS_FILE.is_file():
        return {}
    doc = yaml.safe_load(EXCEPTIONS_FILE.read_text(encoding="utf-8")) or {}
    return _exception_section(doc, "out_of_surface")


def load_kit_only() -> dict[str, dict[str, str]]:
    """Keys the rulesets accept on purpose that the generator does not read.

    A separate section from `out_of_surface`, because it is the opposite claim:
    not "the generator knows this under another name" but "nothing in codegen
    reads this, and that is intended". `x-entity.mutability` is the case that
    forced it — the kit's own lint reads it, so removing it would cost a
    working rule, and the generator reporting it dropped is correct about
    codegen and misleading about the key's purpose. Declaring it here keeps it
    out of the drift report while leaving the reason on the record.
    """
    if not EXCEPTIONS_FILE.is_file():
        return {}
    doc = yaml.safe_load(EXCEPTIONS_FILE.read_text(encoding="utf-8")) or {}
    return _exception_section(doc, "kit_only")


def unreferenced_rulesets(paths: list[Path]) -> list[Path]:
    """Ruleset files no script in `scripts/` names.

    A second copy of a hand-maintained ruleset is the same drift problem in a
    different hat: RestoManager carried one that still required only `type` on
    `x-entity`, so the Windows validation path rejected every entity in the
    tree for months while CI ran the other copy and stayed green. One ruleset,
    one runner — a file nothing executes cannot be trusted to be current.
    """
    scripts = list((ROOT / "scripts").glob("*.sh")) + list((ROOT / "scripts").glob("*.py"))
    blob = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in scripts)
    return [p for p in paths if p.name not in blob]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="check-extension-vocabulary.py",
        description="Fail when the generator knows a vendor-extension key the rulesets reject.",
    )
    ap.add_argument("--require-jar", action="store_true",
                    help="Treat a missing generator jar as a failure (use in CI).")
    ap.add_argument("--jar", type=Path, default=None, help="Generator jar to read.")
    ap.add_argument("--ruleset", type=Path, action="append", default=[],
                    metavar="PATH",
                    help="Ruleset to check (repeatable). Overrides discovery.")
    args = ap.parse_args(argv)

    paths: list[Path] = []
    if args.ruleset:
        paths = list(args.ruleset)
    else:
        for pattern in RULESET_GLOBS:
            paths.extend(sorted(ROOT.glob(pattern)))
        # Maintainers run this from the kit repo, where the globs above — which
        # target a provisioned project's layout — match nothing.
        for pattern in KIT_RULESET_GLOBS:
            paths.extend(sorted(KIT_ROOT.glob(pattern)))
    paths = [p for p in dict.fromkeys(paths) if p.is_file()]
    if not paths:
        msg = ("No Spectral rulesets found — nothing was checked.\n"
               "  Pass --ruleset PATH, or run from a provisioned project.\n")
        if args.require_jar:
            sys.stderr.write("❌ " + msg)
            return 2
        print(msg.rstrip())
        return 0

    guards = closed_guards(paths)
    if not guards:
        msg = (f"No closed (`additionalProperties: false`) extension guards in "
               f"{len(paths)} ruleset(s) — nothing was checked.\n")
        if args.require_jar:
            sys.stderr.write("❌ " + msg)
            return 2
        print(msg.rstrip())
        return 0

    jar = args.jar or find_jar()
    if jar is None or not jar.is_file():
        msg = (
            "VERIFICATION SKIPPED — no generator jar is cached, so the rulesets\n"
            "  below were NOT checked against the generator's vocabulary:\n"
            + "".join(f"    {g['rule']} ({g['surface']})\n" for g in guards)
            + "  Run `specfuse authoring generate` once to populate the cache, or\n"
              "  set SPECFUSE_GENERATOR_JAR. CI should pass --require-jar.\n"
        )
        if args.require_jar:
            sys.stderr.write("❌ " + msg)
            return 2
        sys.stderr.write("⚠️  " + msg)
        return 0

    exceptions = load_exceptions()
    kit_only = load_kit_only()
    # Prefer the jar's own answer. The constant-pool scan stays as the fallback
    # for jars older than the subcommand, and its heuristic nature is exactly
    # why the ruleset-only direction is only fatal against a published source:
    # a key the scan fails to see looks ruleset-only when it is not.
    published = published_vocabulary(jar) or {}
    surfaces = {g["surface"] for g in guards}
    scanned = generator_keys(jar, surfaces)
    # Authority is PER SURFACE, not per jar. `extensions` publishes the surfaces
    # the generator's parser owns as a closed vocabulary — `x-entity` today —
    # and says nothing about the rest. Treating an unpublished surface as an
    # empty vocabulary would report every key the ruleset allows as unrecognised
    # (`x-sample.provider`, `x-value-object.immutable`), which is the same
    # "a key the check fails to see is drift it fails to report" error with the
    # sign flipped: noise that trains a reader to ignore the real finding.
    known = {s: published.get(s, scanned.get(s, set())) for s in surfaces}
    authoritative_surfaces = {s for s in surfaces if s in published}

    # Accepted anywhere across the closed guards. A key the generator
    # namespaces under one extension is often authored inside another's block,
    # so a key that no guard accepts is the blocking case; a key some other
    # guard accepts is a note, not a failure.
    accepted_somewhere: set[str] = set()
    for guard in guards:
        accepted_somewhere |= guard["all_keys"]

    failures: list[str] = []
    print("=== Vendor-extension vocabulary check ===")
    print(f"Generator: {jar.name}")
    if published:
        print(f"Vocabulary source: `extensions --format json` for "
              f"{', '.join(sorted(published))}; constant-pool scan elsewhere")
    else:
        print("Vocabulary source: constant-pool scan (heuristic — this jar "
              "predates `extensions`)")
    for guard in sorted(guards, key=lambda g: g["surface"]):
        surface = guard["surface"]
        declared = guard["all_keys"]
        allowed = set(exceptions.get(surface, {}))
        unknown = known.get(surface, set()) - declared - allowed
        elsewhere = sorted(unknown & accepted_somewhere)
        missing = sorted(unknown - accepted_somewhere)
        declared_kit_only = set(kit_only.get(surface, {}))
        extra = sorted(guard["keys"] - known.get(surface, set()) - declared_kit_only)
        accounted = sorted(guard["keys"] & declared_kit_only)
        label = f"{guard['rule']} ({surface}, {guard['ruleset'].name})"
        if elsewhere:
            print(f"   ℹ️  {label}: {', '.join(elsewhere)} accepted under another "
                  f"guard, not this one — expected when the generator namespaces "
                  f"a key by the extension it belongs to rather than where it is "
                  f"authored.")
        if missing:
            failures.append(
                f"❌ {label}\n"
                f"   generator references, ruleset rejects: {', '.join(missing)}\n"
                f"   Any spec declaring one of these fails lint with an\n"
                f"   `additionalProperties` error — the feature cannot be adopted.\n"
                f"   Fix: add the key to the rule's schema (with its value\n"
                f"   constraint), or record it in {EXCEPTIONS_FILE.name} with a\n"
                f"   reason if it belongs to a different surface."
            )
        else:
            print(f"✅ {label}: {len(declared)} key(s), no generator key missing")
        if extra and surface not in authoritative_surfaces:
            print(f"   ℹ️  ruleset-only (informational — this surface is not in "
                  f"`extensions`, so the fallback scan is a heuristic and may "
                  f"simply have missed the key): {', '.join(extra)}")
        elif extra:
            # The other direction of the same drift, and the one nothing used to
            # report usefully. A key the ruleset accepts and the generator does
            # not know is not adoption-blocking, so it is not a failure — but it
            # is not harmless either: authors write it, `ENTITY_SHAPE_UNKNOWN_
            # PROPERTY` reports it dropped, and the metadata documents intent no
            # generated code enforces. Some are legitimately kit-only (a key the
            # kit's own lint reads but codegen does not); those belong in the
            # exceptions file, where the reason is written down.
            print(f"   ⚠️  ruleset accepts, generator does not recognise: "
                  f"{', '.join(extra)}")
            print(f"      The generator drops these silently "
                  f"(ENTITY_SHAPE_UNKNOWN_PROPERTY, WARNING, once per schema+key).")
            print(f"      Either the generator should read them, or the kit "
                  f"should stop advertising them, or — if the kit's own lint "
                  f"depends on one — record it in {EXCEPTIONS_FILE.name}.")
        if accounted:
            print(f"   ℹ️  kit-only by declaration: {', '.join(accounted)} "
                  f"(reasons in {EXCEPTIONS_FILE.name})")

    for orphan in unreferenced_rulesets(paths):
        print(f"   ℹ️  {orphan.relative_to(ROOT)} is not named by any script in "
              f"scripts/ — if it is a second copy of a ruleset, it will drift "
              f"unnoticed (one ruleset, one runner).")

    if failures:
        print()
        for f in failures:
            sys.stderr.write(f + "\n")
        return 1
    print("✅ Every closed extension guard covers the generator's vocabulary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
