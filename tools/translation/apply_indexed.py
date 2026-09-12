#!/usr/bin/env python3
"""apply_indexed.py -- build a postedit override file from index->translation.

Usage: apply_indexed.py <en_list.json> <idx_et.json> <out_postedit.json>

<en_list.json>  ordered JSON array of English box strings (from dump).
<idx_et.json>   JSON object {"<i>": "<Estonian>"} keyed by index into en_list.
<out>           written as {english: estonian}, merged into an existing out.

Keying by index (not position) makes a partial/append batch safe, and lets the
translator emit short keys instead of retyping the English. Validates ranges.
"""
import json
import sys

en_list = json.load(open(sys.argv[1], encoding="utf-8"))
idx_et = json.load(open(sys.argv[2], encoding="utf-8"))
out_path = sys.argv[3]

out = {}
try:
    out = json.load(open(out_path, encoding="utf-8"))
except FileNotFoundError:
    pass

added = 0
for k, et in idx_et.items():
    if k.startswith("_"):
        continue
    i = int(k)
    if not (0 <= i < len(en_list)):
        raise SystemExit(f"index {i} out of range 0..{len(en_list)-1}")
    en = en_list[i]
    if et.strip():
        out[en] = et
        added += 1

json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{added} entries -> {out_path} (total {len([k for k in out if not k.startswith('_')])})")
