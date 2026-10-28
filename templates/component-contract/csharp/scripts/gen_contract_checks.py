#!/usr/bin/env python3
"""Project-specific checks for gen-contract.yml (`builtins:`).

Seeded from the Specfuse authoring kit and owned by this repo. The shared
engine (`specfuse.loop.gen_contract`) runs the generic checks; a rule with
`check: builtin` and `name: <function>` resolves here. Every function has the
signature

    fn(root, rule, scope, filesets, files) -> list[Finding]

and may use `Finding`, `Scope` and `read` from the engine. Keep each check
small and deterministic: the same tree must always produce the same findings.
"""

from __future__ import annotations

import re
from pathlib import Path

from specfuse.loop.gen_contract import Finding, Scope, read


def generated_base_adopted(root, rule, _scope, filesets, files):
    """Every generated `*Base.g.cs` matched by `base_glob` is derived from by
    some file matched by `consumer_glob`.

    The generator emits the extension point (an abstract base plus an
    interface); the concrete class is the consumer's. A base nobody derives
    from is a declared handler, job or gated service that does not exist at
    runtime, and the build cannot see it. The rule needs two globs:

        base_glob:     "*/gen-src/**/*HandlerBase.g.cs"
        consumer_glob: "*/src/**/*.cs"

    A base is adopted when a consumer file names it in a base list, as
    `: XBase` or `, XBase`, with or without a primary-constructor argument
    list after it.
    """
    bases = Scope({"include": [rule["base_glob"]]}, filesets, files).paths
    consumers = Scope({"include": [rule["consumer_glob"]]}, filesets, files).paths
    texts = [read(root, p) for p in consumers]
    out: list[Finding] = []
    for base in bases:
        name = Path(base).name.removesuffix(".g.cs")
        derived = re.compile(rf"[:,]\s*{re.escape(name)}\b")
        if not any(derived.search(t) for t in texts):
            out.append(Finding(rule["id"], rule["severity"], base, 0,
                               f"no type under {rule['consumer_glob']} derives from {name}; "
                               f"the extension point the generator emitted is unused"))
    return out


_HANDLER_INTERFACE = re.compile(r"\binterface\s+(I\w+Handler)\b")
_CLASS_DECL = re.compile(
    r"^\s*(?:(?:public|internal|private|protected|sealed|abstract|partial|static)\s+)*"
    r"class\s+(?P<name>\w+)\s*(?:<[^>]*>)?\s*(?:\([^)]*\))?\s*:\s*(?P<bases>[^{\n]+)",
    re.M)


def generated_handler_interface_implemented_directly(root, rule, scope, filesets, files):
    """A class in scope lists a generated `I*Handler` interface in its base
    list and no `*HandlerBase` beside it.

    The generator declares the interface and an abstract `{X}HandlerBase`
    that implements it; the concrete class derives from the base. A class
    that names the interface directly compiles, is found by the generated
    assembly scan and runs with none of the base's scaffolding. Interfaces
    are collected from the generated files matched by `interface_glob`, so a
    hand-written `IFooHandler` is never flagged; `scope` decides which
    hand-written files are judged (production code, not test doubles).
    """
    gen = Scope({"include": [rule["interface_glob"]]}, filesets, files).paths
    interfaces: set[str] = set()
    for p in gen:
        interfaces.update(_HANDLER_INTERFACE.findall(read(root, p)))
    out: list[Finding] = []
    if not interfaces:
        return out
    for p in scope.paths:
        text = read(root, p)
        for m in _CLASS_DECL.finditer(text):
            bases = [b.strip().split("(")[0].strip() for b in m.group("bases").split(",")]
            hit = [b for b in bases if b in interfaces]
            if hit and not any(b.endswith("HandlerBase") for b in bases):
                out.append(Finding(rule["id"], rule["severity"], p,
                                   text.count("\n", 0, m.start()) + 1,
                                   f"{m.group('name')} implements {hit[0]} directly; derive from "
                                   f"{hit[0][1:]}Base instead so the generated scaffolding applies"))
    return out


BUILTINS = {
    "generated_base_adopted": generated_base_adopted,
    "generated_handler_interface_implemented_directly": generated_handler_interface_implemented_directly,
}
