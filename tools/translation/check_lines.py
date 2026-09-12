#!/usr/bin/env python3
"""check_lines.py -- flag .string lines wider than the dialogue box.

Measures each on-screen line of every `.string` (stripped of its \\n/\\l/\\p/$
break code) in proportional pixels (see textwidth.py) and reports any over
LINE_WIDTH. Run after writeback to catch lines that won't fit the box.

Usage:  .venv/bin/python check_lines.py [data/text data/maps ...]
"""
import os
import re
import sys

from textwidth import LINE_WIDTH, pixels

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT = ["data/text", "data/maps", "data/scripts"]
STRING = re.compile(r'^\s*\.string\s+"((?:[^"\\]|\\.)*)"')
BREAK = re.compile(r"\\n$|\\l$|\\p$|\$$")
# absolute-positioned layout strings ({CLEAR_TO 10}, {SKIP_TO 5}, ...) don't
# flow, so pixel width is meaningless for them -- skip (matches writeback's skip).
EXOTIC = re.compile(r"\{[A-Z_0-9]+\s")


def check_file(path):
    hits = 0
    for i, line in enumerate(open(path, encoding="utf-8", errors="ignore"), 1):
        m = STRING.match(line)
        if not m:
            continue
        if EXOTIC.search(m.group(1)):
            continue
        text = BREAK.sub("", m.group(1))
        w = pixels(text)
        if w > LINE_WIDTH:
            print(f"{os.path.relpath(path, ROOT)}:{i}: {w}px (>{LINE_WIDTH})  {text!r}")
            hits += 1
    return hits


def walk(root):
    p = os.path.join(ROOT, root)
    if os.path.isfile(p):
        return check_file(p)
    hits = 0
    for dp, _, names in os.walk(p):
        for n in names:
            if n.endswith(".inc"):
                hits += check_file(os.path.join(dp, n))
    return hits


def main():
    dirs = [a for a in sys.argv[1:] if not a.startswith("-")] or DEFAULT
    total = sum(walk(d) for d in dirs if os.path.exists(os.path.join(ROOT, d)))
    print(f"\n{total} line(s) over {LINE_WIDTH}px.", file=sys.stderr)
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
