#!/usr/bin/env python3
"""writeback.py -- render et.json translations back into the sources.

The inverse of extract.py. For every translated label/string it re-wraps the
Estonian to the proportional box width (208px; Estonian hyphenation via
syllabify/pyphen) and splices it in, leaving surrounding code untouched.

ASM `.string` blocks:
  A label's text is one stream of `.string` fragments ending in `$`. We re-wrap
  each box and emit one `.string "<line><break>"` per on-screen line -- the
  first break in a box is `\\n`, the rest `\\l`, boxes joined by `\\p`, the whole
  terminated by `$`. Only rewritten when safe: the block is a clean run of
  `.string` lines, its box count matches the translation, and every box has a
  non-empty `et`. Anything else is left English and reported, so reruns are safe.

C `_("...")` strings:
  The string literal is replaced in place. Multi-box (`\\p`) strings re-wrap like
  ASM; single strings are emitted on one logical line. Fixed-array byte caps
  (from extract.py) are honoured -- a translation that would overflow its buffer
  is skipped and reported.

Usage:
  .venv/bin/python writeback.py                 # rewrite every safe block
  .venv/bin/python writeback.py --dry-run       # report only
  .venv/bin/python writeback.py --from et.json  # use a reviewed file
  .venv/bin/python writeback.py data/text       # limit to path substrings
"""
import json
import os
import re
import sys
from collections import defaultdict

from textwidth import pixels, LINE_WIDTH, _CHARS, _SYMBOLS
import syllabify

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

def et_of(entry):
    """The Estonian for a box -- baked directly into et.json (`et` field)."""
    return entry.get("et", "")


# Exact source-string replacements for hand-laid-out strings the flow-wrapper
# must not touch (battle menu etc.). Applied verbatim as "<en>" -> "<et>".
_lpath = os.path.join(HERE, "literals.json")
LITERALS = {k: v for k, v in (json.load(open(_lpath, encoding="utf-8")).items()
            if os.path.exists(_lpath) else []) if not k.startswith("_")}


def apply_literals(files, report):
    changed = 0
    for f in files:
        path = os.path.join(ROOT, f)
        if not os.path.exists(path):
            continue
        txt = open(path, encoding="utf-8", errors="ignore").read()
        orig = txt
        for en, et in LITERALS.items():
            txt = txt.replace(f'"{en}"', f'"{et}"')
        if txt != orig:
            if "--dry-run" not in sys.argv:
                open(path, "w", encoding="utf-8", errors="ignore").write(txt)
            changed += 1
    return changed

STRING = re.compile(r'"((?:[^"\\]|\\.)*)"')
LABEL = re.compile(r"^(\w[\w]*)::?\s*$")
C_STR = re.compile(r'_\(\s*((?:"(?:[^"\\]|\\.)*"\s*)+)\)', re.S)
C_FRAG = re.compile(r'"((?:[^"\\]|\\.)*)"')
TOKEN = re.compile(r"\{[^}]*\}")
# absolute-positioning control codes: text after these sits at a fixed column, so
# the string is hand-laid-out and must NOT be re-wrapped. (Timing/sound/colour
# codes like {PAUSE 15}, {PLAY_SE ...}, {PALETTE 5} are fine to reflow.)
EXOTIC = re.compile(r"\{(CLEAR_TO|SKIP_TO|CLEAR|FILL_WINDOW|SHIFT_RIGHT|"
                    r"SHIFT_DOWN|MIN_LETTER_SPACING)\b")


def split_words(text):
    """Split on whitespace OUTSIDE {...}, so {PAUSE 15} stays one atomic word."""
    words, buf, depth = [], "", 0
    for ch in text:
        if ch == "{":
            depth += 1; buf += ch
        elif ch == "}":
            depth = max(0, depth - 1); buf += ch
        elif ch == " " and depth == 0:
            if buf:
                words.append(buf); buf = ""
        else:
            buf += ch
    if buf:
        words.append(buf)
    return words


def tokens(s):
    return sorted(TOKEN.findall(s))


def safe_translation(en_boxes, et_boxes, src_stream):
    """True if it's safe to splice these et boxes in place of the English."""
    if EXOTIC.search(src_stream):
        return False                       # layout string -> leave English
    for en, et in zip(en_boxes, et_boxes):
        if et.count("{") != et.count("}"):
            return False                   # NMT broke a brace
        if tokens(en) != tokens(et):
            return False                   # token added/dropped/corrupted
    return True


# --------------------------------------------------------------- wrapping ----
_SIMPLE = {"–": "-", "—": "-", "‒": "-", "―": "-", "„": "“", "‚": "‘",
           " ": " ", " ": " ", " ": " ", "*": "", "`": "’",
           "…": "…"}
_TOKEN_SPLIT = re.compile(r"(\{[^}]*\}|\\[nlp]|\$)")
_dropped = set()


def _sanitize_text(seg):
    """Map NMT punctuation to charmap-representable glyphs; drop the rest.
    Straight double-quotes become curly “ ” in open/close alternation."""
    seg = re.sub(r"\.{3,}", "…", seg)          # NMT "..." -> game ellipsis
    out, open_q = [], True
    for ch in seg:
        if ch in _SIMPLE:
            out.append(_SIMPLE[ch])
        elif ch == '"':
            out.append("“" if open_q else "”")
            open_q = not open_q
        elif ch in _CHARS:
            out.append(ch)
        else:
            _dropped.add(ch)            # unrepresentable: drop (reported)
    return "".join(out)


def norm(s):
    """Sanitize text while leaving {tokens}/break-codes/$ untouched."""
    parts = _TOKEN_SPLIT.split(s)
    for i in range(0, len(parts), 2):          # even indices are plain text
        parts[i] = _sanitize_text(parts[i])
    return "".join(parts)


def wrap_box(text, width=LINE_WIDTH):
    """Wrap one paragraph (words + inline {TOKEN}s) into <=width-px rows.

    Lines are filled greedily. When a word overflows the current line we ask
    syllabify.wrap for a clean break that fills the remaining room; it returns
    one only if a break leaves >=MIN_PREFIX letters before it (never a
    one-letter split). If there's no clean break for the room left, the whole
    word wraps to the next line instead of being split uglily.
    """
    rows, cur = [], ""
    for word in split_words(norm(text)):
        cand = (cur + " " + word).strip()
        if pixels(cand) <= width:
            cur = cand
            continue
        room = width - (pixels(cur) + pixels(" ")) if cur else width
        piece = syllabify.wrap(word, room)
        if piece:
            rows.append((cur + " " + piece[0]).strip())
            word = piece[1]
        elif cur:
            rows.append(cur)
        cur = ""
        while pixels(word) > width:
            p = syllabify.wrap(word, width)
            if not p:
                break
            rows.append(p[0])
            word = p[1]
        cur = word
    if cur:
        rows.append(cur)
    return rows or [""]


def break_after(bi, li, nboxes, nrows):
    """The in-string break code after on-screen line li of box bi."""
    if bi == nboxes - 1 and li == nrows - 1:
        return None                        # last line overall (caller adds $/none)
    if li == nrows - 1:
        return "\\p"                        # box boundary
    return "\\n" if li == 0 else "\\l"


def emit_string_lines(boxes, indent="\t"):
    """boxes: list of Estonian paragraphs. Return `.string` source lines."""
    wrapped = [wrap_box(b) for b in boxes]
    out = []
    for bi, rows in enumerate(wrapped):
        for li, row in enumerate(rows):
            sep = break_after(bi, li, len(wrapped), len(rows))
            out.append(f'{indent}.string "{row}{sep if sep else "$"}"')
    return out


def render_inline(boxes):
    """Render boxes as one in-string body (break codes embedded, no EOS)
    for a C `_("...")` literal."""
    wrapped = [wrap_box(b) for b in boxes]
    parts = []
    for bi, rows in enumerate(wrapped):
        for li, row in enumerate(rows):
            parts.append(row)
            sep = break_after(bi, li, len(wrapped), len(rows))
            if sep:
                parts.append(sep)
    return "".join(parts)


# ----------------------------------------------------------- byte length ----
def nbytes(s):
    """Encoded byte length of a source string (excludes $, counts tokens)."""
    n, i = 0, 0
    toks = re.split(r"(\{[^}]*\}|\\[nlp]|\$)", s)
    for t in toks:
        if not t:
            continue
        if t in ("\\n", "\\l", "\\p"):
            n += 1
        elif t == "$":
            continue
        elif t.startswith("{") and t.endswith("}"):
            bs = _SYMBOLS.get(t[1:-1]) or _CHARS.get(t[1:-1])
            n += len(bs) if bs else 2
        else:
            for ch in t:
                bs = _CHARS.get(ch)
                n += len(bs) if bs else 1
    return n


# --------------------------------------------------------------- ASM pass ----
def process_asm(path, by_label, report):
    lines = open(path, encoding="utf-8", errors="ignore").readlines()
    out, i, changed = [], 0, 0
    rel = os.path.relpath(path, ROOT)
    while i < len(lines):
        m = LABEL.match(lines[i].rstrip("\n"))
        lbl = m.group(1) if m else None
        if lbl not in by_label:
            out.append(lines[i]); i += 1; continue
        # gather contiguous .string block from i+1 until a fragment ends with $
        j, frags, ok = i + 1, [], False
        while j < len(lines):
            s = lines[j].strip()
            if s.startswith(".string"):
                q = STRING.findall(s)
                if not q:
                    break
                frags.append(q[0])
                if q[0].rstrip().endswith("$"):
                    ok = True
                    j += 1
                    break
                j += 1
            elif not s or s.startswith("@") or s.startswith(";"):
                break   # blank/comment inside the pool -> not a clean block
            else:
                break
        if not ok or not frags:
            report["no_block"].append(f"{rel}::{lbl}"); out.append(lines[i]); i += 1
            continue
        stream = "".join(frags).rstrip()
        if stream.endswith("$"):
            stream = stream[:-1]
        n_src = stream.count("\\p") + 1
        entries = sorted(by_label[lbl], key=lambda r: r["box"])
        # require box-for-box alignment, and every NON-EMPTY source box translated
        # (empty boxes -- e.g. a trailing \p before $ -- stay empty, preserving
        # the structure).
        if len(entries) != n_src or any(
                e["en"].strip() and not et_of(e).strip() for e in entries):
            report["box_mismatch"].append(f"{rel}::{lbl} (et {len(entries)} vs src {n_src})")
            out.extend(lines[i:j]); i = j; continue
        boxes = [et_of(e) for e in entries]
        if not safe_translation([e["en"] for e in entries], boxes, stream):
            report["exotic"].append(f"{rel}::{lbl}")
            out.extend(lines[i:j]); i = j; continue
        out.append(lines[i])
        out.extend(l + "\n" for l in emit_string_lines(boxes))
        changed += 1
        i = j
    if changed and "--dry-run" not in sys.argv:
        open(path, "w", encoding="utf-8", errors="ignore").writelines(out)
    return changed


# ----------------------------------------------------------------- C pass ----
def process_c(path, rows, report):
    text = open(path, encoding="utf-8", errors="ignore").read()
    rel = os.path.relpath(path, ROOT)
    # group by the original raw literal (order-independent; identical English
    # strings share one translation). Dedup by box index: the same raw may occur
    # as many separate literals (e.g. 7 species with categoryName "DRAGON") --
    # they are ONE string's boxes, not many, so keep one entry per box index.
    by_raw = {}
    for r in rows:
        d = by_raw.setdefault(r.get("raw"), {})
        d.setdefault(r["box"], r)
    changed = [0]

    def repl(m):
        raw = "".join(C_FRAG.findall(m.group(1)))    # join adjacent literals
        d = by_raw.get(raw)
        if not d:
            return m.group(0)
        entries = [d[k] for k in sorted(d)]
        if any(e["en"].strip() and not et_of(e).strip() for e in entries):
            return m.group(0)
        boxes = [et_of(e) for e in entries]
        if not safe_translation([e["en"] for e in entries], boxes, raw):
            report["exotic"].append(f"{rel}::{entries[0].get('label')}")
            return m.group(0)
        new = render_inline(boxes)
        cap = entries[0].get("maxlen")
        if cap is not None and nbytes(new) + 1 > cap:     # +1 for EOS
            report["cap_overflow"].append(f"{rel}::{entries[0]['label']}")
            return m.group(0)
        changed[0] += 1
        return f'_("{new}")'

    # only replace literals that belong to an extracted occ (skip NAME tables)
    new_text = C_STR.sub(repl, text)
    if changed[0] and "--dry-run" not in sys.argv:
        open(path, "w", encoding="utf-8", errors="ignore").write(new_text)
    return changed[0]


def main():
    src = None
    for flag in ("--from",):
        if flag in sys.argv:
            src = sys.argv[sys.argv.index(flag) + 1]
    src = src or os.path.join(HERE, "et.json")
    only = [a for a in sys.argv[1:] if not a.startswith("-")
            and not a.endswith(".json")]
    rows = json.load(open(src, encoding="utf-8"))

    asm_by_file = defaultdict(lambda: defaultdict(list))
    c_by_file = defaultdict(list)
    for r in rows:
        if r.get("kind") == "c":
            c_by_file[r["file"]].append(r)
        else:
            asm_by_file[r["file"]][r["label"]].append(r)

    with_c = "--with-c" in sys.argv        # C files need per-file care; opt in
    report = defaultdict(list)
    changed = 0
    files = list(asm_by_file) + (list(c_by_file) if with_c else [])
    for f in sorted(set(files)):
        if only and not any(o in f for o in only):
            continue
        path = os.path.join(ROOT, f)
        if not os.path.exists(path):
            report["no_file"].append(f); continue
        if f in c_by_file and with_c:
            changed += process_c(path, c_by_file[f], report)
        else:
            changed += process_asm(path, asm_by_file[f], report)

    lit = apply_literals(sorted(set(f for f in files
                                    if not only or any(o in f for o in only))),
                         report) if LITERALS else 0

    print(f"rewritten: {changed}  (literal layout strings: {lit})")
    if _dropped:
        print(f"  dropped unrepresentable chars: {sorted(_dropped)}")
    for reason in ("no_file", "no_block", "box_mismatch", "exotic", "cap_overflow"):
        n = len(report[reason])
        if n:
            print(f"  skipped [{reason}]: {n}")
            for k in report[reason][:6]:
                print(f"      {k}")
            if n > 6:
                print(f"      ... +{n-6} more")


if __name__ == "__main__":
    main()
