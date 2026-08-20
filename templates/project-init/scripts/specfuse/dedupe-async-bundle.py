#!/usr/bin/env python3
"""
Post-process a redocly-bundled AsyncAPI file to deduplicate inlined channel
content inside operation blocks.

Each `emit-*` / `on-*` / `run-*` operation file declares its channel via a
file-path $ref. Redocly's bundler inlines the entire channel content (with
its full `messages` map) into each operation. With ~150 operations and a
shared `application-events.yaml` channel carrying ~130 message refs, the
bundle balloons to ~74MB and exceeds Specfuse's 50MB YAML parse limit.

This script walks the bundled YAML, identifies each operation's channel by
its `address` field, and replaces the inlined channel block with an
in-document $ref pointing at the corresponding entry under top-level
`channels:` (which Redocly already deduplicates).

Usage:
    python3 scripts/specfuse/dedupe-async-bundle.py output/asyncapi-bundled.yaml

In-place edit. No backup is made — the bundled file is regenerable from
source via `./scripts/specfuse/bundle-async-spec.sh`.
"""
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    # Say what is missing and how to fix it. The caller reports only "post-bundle
    # dedup failed", so an unhandled ImportError here reaches the user as an
    # opaque bundling failure with no indication that a dependency is absent.
    sys.stderr.write(
        "dedupe-async-bundle.py requires PyYAML, which is not installed.\n"
        "\n"
        "  pip install PyYAML          (or: pipx inject specfuse PyYAML)\n"
        "\n"
        "It is used to slim the bundled AsyncAPI document after redocly expands\n"
        "it; without it the bundle stays large enough to hit the generator's\n"
        "YAML parse limit.\n"
    )
    raise SystemExit(2)

# Parsing the ~124MB raw bundle is the slowest step in the whole bundling
# pipeline, and PyYAML's pure-Python loader spends most of it. When PyYAML is
# built against libyaml (the common case), CSafeLoader/CSafeDumper are the same
# safe subset implemented in C and cut this step by roughly an order of
# magnitude. Fall back to the pure-Python pair when libyaml is absent so the
# script still runs anywhere.
try:
    from yaml import CSafeLoader as SafeLoader, CSafeDumper as SafeDumper
except ImportError:  # pragma: no cover - depends on how PyYAML was built
    from yaml import SafeLoader, SafeDumper


def slim_channel(chan: dict) -> dict:
    """Return a copy of the channel object with the bloated `messages` map
    stripped. Keeps the metadata Specfuse needs (address, x-domain,
    x-channel-type, description) while dropping the per-channel inlined
    message bodies that drove the bundle size to 70+ MB."""
    keep_keys = ("address", "description", "x-domain", "x-channel-type")
    return {k: chan[k] for k in keep_keys if k in chan}


def dedupe_operations(doc: dict) -> int:
    """Replace each operation's inlined channel with a slim metadata-only
    inline (no messages map). Specfuse needs the channel metadata to derive
    worker config but doesn't need the full messages list duplicated per
    operation. Returns the number of operations modified.

    NOTE: in-document `$ref: '#/channels/<id>'` refs would be cleaner but
    Specfuse's resolver doesn't follow them in operation.channel position
    today — once it does, swap this slim-inline approach for a true ref.
    """
    channels = doc.get("channels", {})
    operations = doc.get("operations", {})
    modified = 0
    skipped_no_address = 0

    for op_id, op in operations.items():
        chan = op.get("channel")
        if not isinstance(chan, dict):
            continue
        # Already slim (no messages key)? skip.
        if "messages" not in chan:
            continue
        addr = chan.get("address")
        if not addr:
            skipped_no_address += 1
            continue
        op["channel"] = slim_channel(chan)
        modified += 1

    if skipped_no_address:
        print(
            f"warning: {skipped_no_address} operations had a channel block "
            f"with no address — skipped",
            file=sys.stderr,
        )
    return modified


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"error: {path} not found", file=sys.stderr)
        return 2

    loader_kind = "libyaml" if SafeLoader is not yaml.SafeLoader else "pure-python"
    print(
        f"loading {path} ({path.stat().st_size / 1024 / 1024:.1f} MB, "
        f"{loader_kind} parser)…"
    )
    with path.open(encoding="utf-8") as f:
        doc = yaml.load(f, Loader=SafeLoader)

    modified = dedupe_operations(doc)
    print(f"deduplicated {modified} operation channel inlines")

    print(f"writing {path}…")
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(
            doc,
            f,
            Dumper=SafeDumper,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=120,
        )

    new_size = path.stat().st_size / 1024 / 1024
    print(f"done. new size: {new_size:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
