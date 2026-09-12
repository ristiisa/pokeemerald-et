#!/usr/bin/env python3
"""translate.py -- draft Estonian for the extraction worksheet via TartuNLP.

Fills the empty `et` of each {file,label,box,kind,en,et} row:
  1. exact matches from the pokered translation memory (human-reviewed) win,
  2. everything else is machine-drafted by the TartuNLP NMT API
     (https://api.tartunlp.ai/translation/v2).

Unique English strings are translated once and fanned back out to every row, so
shared phrases stay consistent and the API is called as little as possible.

Game tokens are protected: every `{...}` and POKéMON/POKé is masked to an opaque
tag before the call and restored after, so the model can neither translate nor
break them (a broken `{STR_VAR_1}` would fail the build). Rows whose token
multiset still changed are flagged "check". The glossary (glossary.json) further
forces element-type roots, fixes word-sense misses, and keeps all-caps
names/places English.

Every row gets `et_src`: "memory", "mt", or "" (untouched). Output goes to a
SEPARATE file and the run is resumable -- rerun to continue; rows already
drafted/reviewed are kept. Set TARTUNLP_API_KEY for higher rate limits.

Usage:
  .venv/bin/python translate.py [et_untranslated.json] [--out et_draft.json]
      [--memory pocketred_et_memory.json] [--glossary glossary.json]
      [--limit N] [--batch 25] [--redo-mt]
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.tartunlp.ai/translation/v2"
TOKEN = re.compile(r"\{[^}]*\}")
PROTECT_WORDS = ("POKéMON", "POKéMONS", "POKé", "POKéDEX", "POKéNAV",
                 "POKéBLOCK", "POKéCENTER")


def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def default_path(fname):
    return os.path.join(HERE, fname)


# ---- glossary: mask game terms before NMT, restore after (see glossary.json) ----
class Glossary:
    def __init__(self, path):
        g = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
        self.types = g.get("types", {})
        self.terms = g.get("terms", {})
        self.caps = g.get("caps", {})
        self.keep_caps = g.get("keep_caps", False)

    def mask(self, en):
        restore, ctr = {}, [0]
        s = en

        def tag(val):
            t = f"★{ctr[0]}★"          # ★N★ : NMT leaves it untouched
            restore[t] = val
            ctr[0] += 1
            return t

        # 1. game tokens and proper product nouns -> always protected verbatim
        s = TOKEN.sub(lambda m: tag(m.group(0)), s)
        for w in sorted(PROTECT_WORDS, key=len, reverse=True):
            s = s.replace(w, tag(w))

        # 2. element types: "<word> type/-type" or "<word> #MON" equivalents
        def typerep(m):
            w, lw = m.group(1), m.group(1).lower()
            if lw in self.types:
                v = self.types[lw]
                return tag(v.capitalize() if w[0].isupper() else v) + m.group(2)
            return m.group(0)
        s = re.sub(r"\b([A-Za-z]+)(-type| type| TYPE)", typerep, s)

        # 3. explicit term overrides
        for term, val in sorted(self.terms.items(), key=lambda x: -len(x[0])):
            s = re.sub(rf"\b{re.escape(term)}\b", lambda m, v=val: tag(v), s)

        # 4. caps overrides, then keep remaining all-caps runs English
        for cap, val in sorted(self.caps.items(), key=lambda x: -len(x[0])):
            if cap in s:
                s = s.replace(cap, tag(val))
        if self.keep_caps:
            s = re.sub(r"(?<![<>\w★])[A-Z][A-Z0-9]{1,}(?:[ '\-][A-Z0-9]+)*",
                       lambda m: tag(m.group(0)), s)
        return s, restore

    @staticmethod
    def restore(et, rmap):
        # A mask tag is ★<id>★. NMT mangles the ★ delimiters -- injects spaces
        # (★ 0★), and for ADJACENT tags (★0★★1★) collapses the ★★ junction and
        # orphans a digit (} 1★). The id is the digit, so recover by number.
        def by_id(m):
            return rmap.get(f"★{m.group(1)}★", "")
        # 1. clean / internal-space tags
        et = re.sub(r"★\s*(\d+)\s*★", by_id, et)
        # 2. orphaned delimiters left by a collapsed junction
        et = re.sub(r"(\d+)\s*★", by_id, et)       # closing orphan:  1★
        et = re.sub(r"★\s*(\d+)", by_id, et)       # opening orphan:  ★1
        et = et.replace("★", "")                   # any lone ★ remaining
        return et


def tokens(s):
    """Multiset of protected game tokens, to detect NMT breakage."""
    return tuple(sorted(TOKEN.findall(s)))


def translate_batch(texts, retries=5):
    body = json.dumps({"text": texts, "src": "en", "tgt": "et"}).encode()
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("TARTUNLP_API_KEY")
    if key:
        headers["x-api-key"] = key
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.load(resp)["result"]
            return result if isinstance(result, list) else [result]
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            wait = 2 ** attempt
            print(f"  API error {getattr(e,'code','')} ({e}); retry in {wait}s",
                  file=sys.stderr)
            time.sleep(wait)
    raise SystemExit("TartuNLP API unreachable after retries")


VALUE_FLAGS = ("--out", "--memory", "--glossary", "--limit", "--batch")


def positionals():
    args, out, skip = sys.argv[1:], [], False
    for i, a in enumerate(args):
        if skip:
            skip = False
            continue
        if a in VALUE_FLAGS:
            skip = True
        elif a.startswith("-"):
            continue
        else:
            out.append(a)
    return out


def main():
    pos = positionals()
    infile = pos[0] if pos else default_path("et_untranslated.json")
    outfile = opt("--out", default_path("et_draft.json"))
    memfile = opt("--memory", default_path("pocketred_et_memory.json"))
    limit = int(opt("--limit", "0"))
    batch = int(opt("--batch", "25"))

    rows = json.load(open(infile, encoding="utf-8"))
    prior = {}
    if os.path.exists(outfile):
        for r in json.load(open(outfile, encoding="utf-8")):
            # a residual mask tag means restore failed: re-queue (drop the et)
            if r.get("et") and "★" not in r["et"]:
                prior[(r["file"], r["label"], r["box"])] = r
    memory = json.load(open(memfile, encoding="utf-8")) if os.path.exists(memfile) else {}
    gloss = Glossary(opt("--glossary", default_path("glossary.json")))
    redo_mt = "--redo-mt" in sys.argv

    for r in rows:
        r.setdefault("et", "")
        r.setdefault("et_src", "")
        p = prior.get((r["file"], r["label"], r["box"]))
        # only reuse a prior translation if its source English still matches --
        # guards against a draft contaminated by extracting already-translated
        # source (those rows get re-translated from the clean English).
        if p and p.get("en") == r["en"]:
            r["et"], r["et_src"] = p["et"], p.get("et_src", "")
            if p.get("flag"):
                r["flag"] = p["flag"]
        if redo_mt and r.get("et_src") == "mt":
            r["mt_raw"] = r["et"]
            r["et"], r["et_src"] = "", ""

    todo = {}
    for r in rows:
        if not r["et"] and r["en"]:
            todo.setdefault(r["en"], [])
    uniques = list(todo)
    if limit:
        uniques = uniques[:limit]

    resolved = {}
    mt_queue = []
    for en in uniques:
        if en in memory:
            resolved[en] = (memory[en], "memory")
        else:
            mt_queue.append(en)

    print(f"{len(rows)} rows | {len(todo)} unique to fill | "
          f"{len(resolved)} from memory | {len(mt_queue)} to NMT")

    def write_back():
        for r in rows:
            if not r["et"] and r["en"] in resolved:
                et, src = resolved[r["en"]]
                r["et"], r["et_src"] = et, src
                if tokens(r["en"]) != tokens(et):
                    r["flag"] = "check"
                elif r.get("flag") == "check":
                    del r["flag"]
        json.dump(rows, open(outfile, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    for i in range(0, len(mt_queue), batch):
        chunk = mt_queue[i:i + batch]
        masked = [gloss.mask(en) for en in chunk]
        out = translate_batch([m[0] for m in masked])
        for en, (_, rmap), et in zip(chunk, masked, out):
            resolved[en] = (gloss.restore(et, rmap), "mt")
        write_back()
        done = min(i + batch, len(mt_queue))
        print(f"  NMT {done}/{len(mt_queue)}", end="\r", file=sys.stderr)
        time.sleep(0.15)
    write_back()

    flagged = sum(1 for r in rows if r.get("flag") == "check")
    filled = sum(1 for r in rows if r["et"])
    print(f"\n{filled}/{len(rows)} rows drafted "
          f"({flagged} flagged for token review) -> {outfile}")


if __name__ == "__main__":
    main()
