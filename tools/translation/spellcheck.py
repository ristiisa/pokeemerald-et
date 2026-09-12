#!/usr/bin/env python3
"""spellcheck.py -- Estonian spell-check of the translated `et` fields.

Runs the et_EE Hunspell dictionary over the words of every `et` in a draft
(default et.json) and prints unknown words in context, so typos are
caught before they bake into the ROM. Game tokens ({PLAYER}, {STR_VAR_1}, ...)
and an ALLOW list of proper nouns are ignored.

Usage:  .venv/bin/python spellcheck.py [et.json] [--limit N]
"""
import json
import os
import re
import sys

import phunspell
from termcolor import colored

HERE = os.path.dirname(os.path.abspath(__file__))
pspell = phunspell.Phunspell("et_EE")

ALLOW = {
    "player", "rival", "pokemon", "pokémon", "pokédex", "poké", "pokénav",
    "pk", "mn", "str", "var", "kun",
}
TOKEN = re.compile(r"\{[^}]*\}|\\[nlp]|\$")
STRIP = re.compile(r"[.,!?;:\"“”‘’'()…/&%+\-–—\n]")


def words_of(et):
    et = TOKEN.sub(" ", et)
    et = STRIP.sub(" ", et).lower()
    return [w for w in et.split() if w and not w.isdigit()
            and not any(ord(c) > 0x2e00 for c in w)]


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
    skip = {str(limit)} if limit else set()
    pos = [a for a in sys.argv[1:] if not a.startswith("-") and a not in skip]
    src = pos[0] if pos else os.path.join(HERE, "et.json")
    rows = json.load(open(src, encoding="utf-8"))
    seen, bad_total, shown = set(), 0, 0
    for r in rows:
        et = r.get("et", "")
        if not et:
            continue
        words = [w for w in words_of(et) if w not in ALLOW]
        bad = [w for w in pspell.lookup_list(words) if w not in ALLOW]
        for w in bad:
            if w in seen:
                continue
            seen.add(w)
            bad_total += 1
            if not limit or shown < limit:
                print(colored(f"{r['file']}::{r['label']}", "dark_grey"),
                      colored(w, "yellow"))
                shown += 1
    print(f"\n{bad_total} distinct unknown word(s).", file=sys.stderr)


if __name__ == "__main__":
    main()
