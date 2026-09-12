#!/usr/bin/env python3
"""extract.py -- pull pokeemerald English text into a translation worksheet.

Produces tools/translation/et.json: a flat list of
{file, label, box, kind, en, et:""} rows, the inverse of writeback.py.

Two text homes in pokeemerald:
  * ASM  -- `.string "..."` blocks in data/{text,maps,scripts}/**.inc. A label's
    consecutive `.string` fragments concatenate into one stream ending in `$`.
    `\\p` splits it into boxes (message windows); `\\n`/`\\l` are soft line breaks
    within a box and are re-flowed into one paragraph per box (kind "asm").
  * C    -- `_("...")` string literals in selected src/ and include/ files
    (prose: system strings, battle messages, Pokédex entries, ...). Fixed-size
    arrays (`[13]`, `[POKEMON_NAME_LENGTH+1]`) carry a byte cap so writeback can
    keep names within their buffer; NAME tables that stay English are excluded
    entirely (see C_SKIP). kind "c".

Box text keeps game tokens verbatim (`{PLAYER}`, `{STR_VAR_1}`, `{PKMN}`, ...)
and de-hyphenates wrapped lines back into whole sentences for translation.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "tools", "translation", "et.json")

ASM_DIRS = ("data/text", "data/maps", "data/scripts")
# Top-level ASM files not under ASM_DIRS (e.g. event_scripts.s).
ASM_FILES = ("data/event_scripts.s",)
STRING = re.compile(r'"((?:[^"\\]|\\.)*)"')
LABEL = re.compile(r"^(\w[\w]*)::?\s*$")
BREAK = re.compile(r"\\p|\\n|\\l")

# --- C translation targets: prose only. NAME/symbol tables stay English. ---
C_FILES = [
    "src/strings.c",
    "src/battle_message.c",
    "src/data/text/match_call_messages.h",
    "src/data/text/abilities.h",
    "src/data/text/move_descriptions.h",
    "src/data/text/item_descriptions.h",
    "src/data/text/gift_ribbon_descriptions.h",
    "src/data/text/ribbon_descriptions.h",
    "src/data/pokemon/pokedex_entries.h",
    "src/data/pokemon/pokedex_text.h",
    "src/data/union_room.h",
    "src/data/credits.h",
    "src/berry.c",
    "src/berry_blender.c",
    "src/berry_fix_program.c",
    "src/data/trade.h",
    "src/data/decoration/description.h",
    "src/mystery_event_msg.c",
    "src/data/text/move_names.h",
    "src/battle_main.c",
]
# one _() holding one or more adjacent C string literals (they concatenate).
C_LITERALS = re.compile(r'_\(\s*((?:"(?:[^"\\]|\\.)*"\s*)+)\)', re.S)
# C declarations we never translate: proper-noun name tables / symbol arrays.
# Matched on the literal's own line (individual decls like ExpandedPlaceholder),
# AND as whole 2D-array byte ranges (name tables whose rows are [IDX]=_("..")
# and so don't mention the array name) -- see _skip_ranges.
C_SKIP = re.compile(r"gSpeciesNames|gAbilityNames|gNatureNames|"
                    r"TrainerClassNames|ExpandedPlaceholder")
C_SKIP_ARRAY = re.compile(
    r"u8\s+\w*(?:SpeciesNames|AbilityNames|NatureNames|"
    r"TrainerClassNames)\w*\s*\[[^=]*=\s*\{")


def _match_brace(text, i):
    """Given i just after an opening '{', return index just after its match,
    skipping over "..." string literals (which may contain { } in tokens)."""
    depth, n = 1, len(text)
    while i < n and depth > 0:
        c = text[i]
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return i


def _skip_ranges(text):
    out = []
    for m in C_SKIP_ARRAY.finditer(text):
        out.append((m.start(), _match_brace(text, m.end())))
    return out


def de_hyphen(box):
    """Join a box's soft-wrapped lines into one paragraph."""
    out = ""
    for part in re.split(r"\\n|\\l", box):
        part = part.strip()
        if not part:
            continue
        if not out:
            out = part
        elif out.endswith("-"):
            out = out[:-1] + part
        else:
            out += " " + part
    return re.sub(r"\s+", " ", out).strip()


def boxes_of(stream):
    """Split a full text stream (sans trailing $) into de-hyphenated boxes."""
    stream = stream.rstrip()
    if stream.endswith("$"):
        stream = stream[:-1]
    return [de_hyphen(b) for b in stream.split("\\p")]


# ------------------------------------------------------------------ ASM ----
def extract_asm(rel, rows):
    path = os.path.join(ROOT, rel)
    label, frags = None, []

    def flush():
        if not (label and frags):
            return
        stream = "".join(frags)
        bx = boxes_of(stream)
        if not any(b.strip() for b in bx):      # not a real text block
            return
        for i, en in enumerate(bx):              # keep empty boxes so box count
            rows.append({"file": rel, "label": label, "box": i,   # matches source
                         "kind": "asm", "en": en, "et": ""})

    for raw in open(path, encoding="utf-8", errors="ignore"):
        s = raw.strip()
        m = LABEL.match(s)
        if m:
            flush()
            label, frags = m.group(1), []
            continue
        if s.startswith(".string"):
            q = STRING.findall(s)
            if not q:
                continue
            frags.append(q[0])
            if q[0].rstrip().endswith("$"):
                flush()
                frags = []          # keep label; next .string would be a 2nd str
    flush()


# -------------------------------------------------------------------- C ----
# const u8 Name[] = _("..");   or   [INDEX] = _("..");   with optional array cap
C_DECL = re.compile(
    r'(?:const\s+u8\s+(?P<name>\w+)\s*\[\s*\]\s*\[\s*(?P<cap>[^\]]+)\s*\]'  # 2D arr
    r'|const\s+u8\s+(?P<name1>\w+)\s*\[\s*(?P<cap1>[^\]]*)\s*\]'            # 1D arr
    r'|\[(?P<index>[^\]]+)\])?'
    r'\s*=?\s*_\(\s*"(?P<str>(?:[^"\\]|\\.)*)"\s*\)')
NAME_CAP = {"POKEMON_NAME_LENGTH": 10, "MOVE_NAME_LENGTH": 12,
            "ITEM_NAME_LENGTH": 14}
# fixed-size struct fields holding a _() string (byte cap incl. EOS).
FIELD_CAP = {"categoryName": 12}


def _cap(expr):
    if expr is None:
        return None
    expr = expr.strip()
    if not expr:
        return None
    for k, v in NAME_CAP.items():
        expr = expr.replace(k, str(v))
    try:
        return int(eval(expr, {"__builtins__": {}}, {}))  # e.g. "10 + 1"
    except Exception:
        return None


# a fixed-size (possibly 2D) u8 array opening a { ... } initializer; the element
# byte cap is the LAST [N]. Rows inside ([INDEX] = _("..")) inherit that cap.
ARRAY_DECL = re.compile(r'u8\s+\w+\s*(?:\[[^\]]*\])?\[\s*([^\]\s]+)\s*\]\s*=\s*\{')


def _array_caps(text):
    """List of (start, end, cap) byte ranges for fixed-size array initializers."""
    out = []
    for m in ARRAY_DECL.finditer(text):
        cap = _cap(m.group(1))
        if cap is None:
            continue
        out.append((m.end(), _match_brace(text, m.end()), cap))
    return out


def extract_c(rel, rows):
    path = os.path.join(ROOT, rel)
    text = open(path, encoding="utf-8", errors="ignore").read()
    caps = _array_caps(text)
    skips = _skip_ranges(text)
    seen = 0
    for m in C_LITERALS.finditer(text):
        en_raw = "".join(STRING.findall(m.group(1)))   # join adjacent literals
        # find the enclosing line to pick up a label/index and array cap
        ls = text.rfind("\n", 0, m.start()) + 1
        le = text.find("\n", m.end())
        line = text[ls:le if le != -1 else len(text)]
        if C_SKIP.search(line) or any(a0 <= m.start() <= a1 for a0, a1 in skips):
            continue
        label, maxlen = None, None
        p = m.start()
        for a0, a1, cap in caps:                 # inside a fixed-size array?
            if a0 <= p <= a1:
                maxlen = cap
        lm = re.search(r"\[\s*([A-Za-z0-9_]+)\s*\]\s*=\s*_\(", line)
        if lm:
            label = lm.group(1)
        nm = re.search(r"\bu8\s+(\w+)\s*\[", line)
        if nm:
            label = nm.group(1)
        fm = re.search(r"\.([A-Za-z0-9_]+)\s*=\s*_\(", line)   # struct field
        if fm:
            label = label or fm.group(1)
            maxlen = FIELD_CAP.get(fm.group(1), maxlen)
        if not en_raw.strip("\\$ "):
            continue
        boxes = boxes_of(en_raw)
        if not any(b.strip() for b in boxes):
            continue
        for i, en in enumerate(boxes):           # keep empty boxes (box alignment)
            row = {"file": rel, "label": label or f"@{seen}",
                   "box": i, "kind": "c", "en": en, "et": "",
                   "occ": seen, "raw": en_raw}
            if maxlen is not None:
                row["maxlen"] = maxlen
            rows.append(row)
        seen += 1


def main():
    which = [a for a in sys.argv[1:] if not a.startswith("-")]
    rows = []
    if not which or "asm" in which:
        for d in ASM_DIRS:
            base = os.path.join(ROOT, d)
            for dp, _, names in os.walk(base):
                for n in sorted(names):
                    if n.endswith(".inc"):
                        extract_asm(os.path.relpath(os.path.join(dp, n), ROOT), rows)
        for rel in ASM_FILES:
            if os.path.exists(os.path.join(ROOT, rel)):
                extract_asm(rel, rows)
    if not which or "c" in which:
        for rel in C_FILES:
            if os.path.exists(os.path.join(ROOT, rel)):
                extract_c(rel, rows)

    # Merge into et.json, PRESERVING existing translations (keyed by file/label/box).
    # New boxes come in with et="" for hand-translation; nothing is overwritten.
    prev = {}
    if os.path.exists(OUT):
        for e in json.load(open(OUT, encoding="utf-8")):
            prev[(e["file"], e["label"], e["box"])] = e
    kept = 0
    for r in rows:
        p = prev.get((r["file"], r["label"], r["box"]))
        if p is not None and (p.get("et") or ""):
            r["et"] = p["et"]
            r["et_src"] = p.get("et_src", "human")
            kept += 1
        else:
            r["et_src"] = ""
    json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    asm = sum(1 for r in rows if r["kind"] == "asm")
    c = sum(1 for r in rows if r["kind"] == "c")
    print(f"{len(rows)} boxes ({asm} asm, {c} c) -> {os.path.relpath(OUT, ROOT)}; "
          f"kept {kept} existing translations, {len(rows)-kept} untranslated")


if __name__ == "__main__":
    main()
