"""
One-time script to generate tools/flake8_helpers/s025_exceptions.py.

Scans src/sentry/ for all .filter(...).first() patterns (excluding .order_by() chains)
and writes the exception list so existing code is not flagged by S025.

Exceptions are keyed by (path, fingerprint) where the fingerprint is derived from
the .filter(...) expression, making the list robust to line movement.

Usage: python -m tools.flake8_helpers.generate_s025_exceptions
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.flake8_plugin import _is_filter_first_chain, _s025_fingerprint  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "src" / "sentry"
EXCEPTIONS_FILE = Path(__file__).resolve().parent / "s025_exceptions.py"


def find_filter_first_locations() -> list[tuple[str, str]]:
    locations: list[tuple[str, str]] = []
    for root, _dirs, files in os.walk(SRC_DIR):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            relpath = os.path.relpath(fpath, REPO_ROOT)
            try:
                with open(fpath) as f:
                    tree = ast.parse(f.read(), filename=fpath)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and _is_filter_first_chain(node):
                    locations.append((relpath, _s025_fingerprint(node)))
    return sorted(set(locations))


def write_exceptions_file(locations: list[tuple[str, str]]) -> None:
    content = '''"""
Existing .filter().first() occurrences exempt from S025.

New code should use .get_or_none() instead. This list was auto-generated
and should not be manually edited. To regenerate:

    python -m tools.flake8_helpers.generate_s025_exceptions

Entries are (path, fingerprint) pairs; the fingerprint is derived from the
.filter(...) expression so the list is robust to line movement. Editing the
filter on an exempt statement changes its fingerprint, so it must be reviewed
and re-added (or the statement fixed) before S025 stops flagging it.

DO NOT ADD NEW ENTRIES TO THIS LIST.
"""

S025_EXCEPTIONS: frozenset[tuple[str, str]] = frozenset({
'''
    for path, fingerprint in locations:
        content += f'    ("{path}", "{fingerprint}"),\n'
    content += "})\n"
    with open(EXCEPTIONS_FILE, "w") as f:
        f.write(content)
    print(f"Wrote {len(locations)} exceptions to {EXCEPTIONS_FILE}")


def main() -> None:
    print("Scanning for .filter().first() patterns in src/sentry/...")
    locations = find_filter_first_locations()
    write_exceptions_file(locations)


if __name__ == "__main__":
    main()
