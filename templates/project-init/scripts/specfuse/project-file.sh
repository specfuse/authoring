#!/bin/bash
# Project-file reader, sourced by generate.sh and generate-scenario-docs.sh so
# the project file (<name>-project.json) has one reader. Not run directly.
#
# The functions read the project file named by $CONFIG. They need python3
# rather than jq: no extra dependency, and no CRLF output on Windows.

# find_project_file <root> — the first <name>-project.json in <root>, or nothing.
find_project_file() {
    local candidate
    for candidate in "$1"/*-project.json; do
        if [ -f "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
}

# groups_tsv — one line per group: name<TAB>language<TAB>destination<TAB>basePackage.
groups_tsv() {
    python3 - "$CONFIG" <<'PY'
import json, sys
for g in json.load(open(sys.argv[1], encoding="utf-8")).get("groups", []):
    print("\t".join(str(g.get(k) or "") for k in ("name", "language", "destination", "basePackage")))
PY
}

# config_value <key> — a top-level value of the project file, or nothing.
config_value() {
    python3 - "$CONFIG" "$1" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8")).get(sys.argv[2]) or "")
PY
}

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

# Language aliases, matched case-insensitively against each group's `language`.
canon_lang() {
    case "$(lower "$1")" in
        c#|cs|csharp|dotnet) echo "c#" ;;
        py|python)           echo "python" ;;
        dart|flutter)        echo "dart" ;;
        ts|typescript)       echo "typescript" ;;
        md|markdown|docs)    echo "markdown" ;;
        *)                   lower "$1" ;;
    esac
}
