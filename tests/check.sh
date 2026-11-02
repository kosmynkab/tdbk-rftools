#!/bin/sh
# One check for TDBK RFTools: lint, unit tests, offscreen window drivers.
# Runs with RoboFont's bundled Python (3.12), the one the extension runs on.
# Usage: sh tests/check.sh   (from any directory)
set -u

HERE=$(cd "$(dirname "$0")/.." && pwd)
R=/Applications/RoboFont.app/Contents/Resources
PY=/Applications/RoboFont.app/Contents/MacOS/python
LIB="$HERE/TDBKRFTools.roboFontExt/lib"

if [ ! -x "$PY" ]; then
    echo "check: RoboFont not found at /Applications/RoboFont.app" >&2
    exit 1
fi
if ! command -v ruff >/dev/null 2>&1; then
    echo "check: ruff not installed (brew install ruff)" >&2
    exit 1
fi

export PYTHONHOME="$R"
export PYTHONPATH="$R/lib/python3.12:$R/lib/python3.12/lib-dynload:$LIB"
export PYTHONDONTWRITEBYTECODE=1
cd "$HERE" || exit 1

failed=0
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

echo "== lint"
ruff check TDBKRFTools.roboFontExt/lib tests || failed=1

# Models, geometry and the Cleanup session stay free of RoboFont, AppKit and
# UI imports so they run and test in plain Python.
echo "== pure modules"
PKG=TDBKRFTools.roboFontExt/lib/tdbk_rftools
PURE="$PKG/geometry.py $PKG/tools/*_model.py $PKG/tools/*_state.py
      $PKG/cleanup/anchors.py $PKG/cleanup/audit.py $PKG/cleanup/outlines.py
      $PKG/cleanup/session.py $PKG/cleanup/sources.py"
# shellcheck disable=SC2086
if grep -nE '^[[:space:]]*(from|import)[[:space:]]+(mojo|AppKit|Foundation|ezui|vanilla|merz|lib)([.[:space:]]|$)' $PURE; then
    echo "pure modules import RoboFont or UI code (above)"
    failed=1
else
    echo "ok"
fi

echo "== unit tests"
"$PY" -m unittest discover -s tests 2>"$OUT/unit.txt" || { cat "$OUT/unit.txt"; failed=1; }
tail -1 "$OUT/unit.txt"

# The drivers build the real windows offscreen. They print what they see and
# rarely assert, so a crash or a printed traceback counts as a failure: the
# window code catches errors in its redraw and prints them instead of raising.
echo "== offscreen drivers"
for driver in tests/offscreen/*.py; do
    name=$(basename "$driver" .py)
    if "$PY" "$driver" "$LIB" "$OUT/$name.png" >"$OUT/$name.txt" 2>&1 \
        && ! grep -q "Traceback" "$OUT/$name.txt"; then
        echo "ok    $name"
    else
        echo "FAIL  $name"
        tail -15 "$OUT/$name.txt"
        failed=1
    fi
done

[ "$failed" -eq 0 ] && echo "== all checks passed" || echo "== checks FAILED"
exit "$failed"
