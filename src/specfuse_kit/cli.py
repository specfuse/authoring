"""specfuse-kit command-line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__


def main(argv: list[str] | None = None) -> int:
    import sys

    raw = list(sys.argv[1:] if argv is None else argv)
    # `generate` passes every following token verbatim to the jar, including
    # leading-dash flags (argparse REMAINDER mishandles a leading '-'), so
    # intercept it before argparse touches the tail.
    if raw and raw[0] == "generate":
        from . import generator
        return generator.generate(raw[1:])

    parser = argparse.ArgumentParser(
        prog="specfuse-kit",
        description="Bootstrap Specfuse projects and run the spec->code generator.",
    )
    parser.add_argument("--version", action="version", version=f"specfuse-kit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Bootstrap a new Specfuse project.")
    p_init.add_argument("target", type=Path, help="Target directory for the new project.")
    p_init.add_argument("--name", help="Project name (kebab-case). Prompted if omitted.")
    p_init.add_argument("--token", help="Project token (lowercase alnum). Prompted if omitted.")
    p_init.add_argument("--domain", help="Initial domain (kebab-case). Prompted if omitted.")
    p_init.add_argument("-y", "--yes", action="store_true", help="Don't prompt to overwrite a non-empty dir.")

    p_refresh = sub.add_parser("refresh", help="Re-copy kit claude-assets into an existing project.")
    p_refresh.add_argument("target", type=Path, help="Existing project directory.")

    p_gen = sub.add_parser(
        "generate",
        help="Run the pinned generator (downloads/verifies the jar on demand).",
    )
    p_gen.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed through to the generator jar.")

    ns = parser.parse_args(argv)

    if ns.command == "init":
        from . import bootstrap
        return bootstrap.init(
            ns.target, name=ns.name, token=ns.token, domain=ns.domain, assume_yes=ns.yes
        )
    if ns.command == "refresh":
        from . import bootstrap
        return bootstrap.refresh(ns.target)
    if ns.command == "generate":
        from . import generator
        return generator.generate(ns.args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
