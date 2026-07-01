#!/usr/bin/env python3
"""
No-Mock Scanner — CI quality gate enforcing Law #1 (NO MOCK IMPLEMENTATIONS).

Heuristic first line of defense: flags fakery markers on the normal path
(non-test source). Complements — does not replace — Copilot/human review.

Honest by design: `raise NotImplementedError` and explicit `BLOCKED` markers are
NOT flagged — declaring "not built yet" is allowed; *faking success* is not.

Usage:  no_mock_scan.py <file.py> [<file.py> ...]
Exit 1 if any fakery markers are found.
"""
import re
import sys

# Markers that indicate a faked/canned capability on the normal path.
PATTERNS = [
    r'#.*\b(mock|stub|fake|dummy|placeholder)\b',
    r'#.*simplified\s+mock',
    r'#.*\bcoming soon\b',
    r'return\s+True\s*#.*\b(stub|dummy|fake|placeholder|for now)\b',
    r'pass\s*#.*\b(stub|todo:?\s*implement|placeholder)\b',
]
# Never flag these — they are honest declarations of "not built", not fakery.
ALLOW = [r'NotImplementedError', r'\bBLOCKED\b']

_rx = [re.compile(p, re.IGNORECASE) for p in PATTERNS]
_allow = [re.compile(p) for p in ALLOW]
_SKIP_DIRS = {"tests", "test", "vendor", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}


def _skip(path):
    parts = path.replace("\\", "/").split("/")
    base = parts[-1]
    if any(d in _SKIP_DIRS for d in parts):
        return True
    return base.startswith("test_") or base.endswith("_test.py")


def scan(path):
    out = []
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except Exception:
        return out
    for i, line in enumerate(lines, 1):
        if any(a.search(line) for a in _allow):
            continue
        if any(r.search(line) for r in _rx):
            out.append((path, i, line.strip()))
    return out


def main(argv):
    files = [f for f in argv if f.endswith(".py") and not _skip(f)]
    findings = [f for path in files for f in scan(path)]
    if findings:
        print("❌ NO-MOCK GATE FAILED — fakery markers on the normal path:\n")
        for path, ln, text in findings:
            print(f"  {path}:{ln}:  {text}")
        print("\nLaw #1: no canned/fake capability. If it can't be built yet, "
              "`raise NotImplementedError` or mark BLOCKED — never fake a success.")
        return 1
    print(f"✅ No-mock gate passed ({len(files)} file(s) scanned).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
