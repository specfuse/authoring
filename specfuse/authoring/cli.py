"""specfuse-authoring command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    # `generate` passes every following token verbatim to the jar, including
    # leading-dash flags (argparse REMAINDER mishandles a leading '-'), so
    # intercept it before argparse touches the tail.
    if raw and raw[0] == "generate":
        from . import generator
        return generator.generate(raw[1:])

    parser = argparse.ArgumentParser(
        prog="specfuse-authoring",
        description="Bootstrap Specfuse projects and run the spec->code generator.",
    )
    parser.add_argument("--version", action="version", version=f"specfuse-authoring {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Bootstrap a new Specfuse project.")
    p_init.add_argument("target", type=Path, help="Target directory for the new project.")
    p_init.add_argument("--name", help="Project name (kebab-case). Prompted if omitted.")
    p_init.add_argument("--token", help="Project token (lowercase alnum). Prompted if omitted.")
    p_init.add_argument("--domain", help="Initial domain (kebab-case). Prompted if omitted.")
    p_init.add_argument("-y", "--yes", action="store_true", help="Don't prompt to overwrite a non-empty dir.")

    p_upgrade = sub.add_parser(
        "upgrade",
        help="Update kit-owned files (handbooks, samples, schemas, scripts) in an existing project.",
    )
    p_upgrade.add_argument("target", type=Path, help="Existing project directory.")
    p_upgrade.add_argument(
        "-n", "--dry-run", action="store_true",
        help="Report what would change without writing anything.",
    )

    # `refresh` predates the versioned overlay and synced only handbooks and
    # samples, blindly. Kept as an alias so existing muscle memory and docs
    # keep working; it now runs the overlay.
    p_refresh = sub.add_parser("refresh", help="Deprecated alias for `upgrade`.")
    p_refresh.add_argument("target", type=Path, help="Existing project directory.")
    p_refresh.add_argument("-n", "--dry-run", action="store_true", help=argparse.SUPPRESS)

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
    if ns.command in ("upgrade", "refresh"):
        if ns.command == "refresh":
            print(
                "specfuse-authoring: `refresh` is deprecated — use `upgrade`.",
                file=sys.stderr,
            )
        from . import bootstrap
        return bootstrap.upgrade(ns.target, dry_run=ns.dry_run)
    if ns.command == "generate":
        from . import generator
        return generator.generate(ns.args)
    return 1


def _run() -> int:
    """Entry point wrapper that survives a closed stdout.

    Piping into a reader that exits early — `… | head`, `… | grep -q` — closes
    the pipe under us. Python then fails to flush stdout at shutdown and exits
    120 with a BrokenPipeError traceback, which looks like a crash in the CLI
    rather than the normal end of a pipeline. Redirect the dangling stdout to
    devnull and report the conventional SIGPIPE status instead.
    """
    import os

    try:
        rc = main()
        sys.stdout.flush()
        return rc
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 128 + 13  # conventional SIGPIPE exit status


if __name__ == "__main__":
    raise SystemExit(_run())
