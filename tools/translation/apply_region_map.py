#!/usr/bin/env python3
"""apply_region_map.py -- write map-banner translations from et.json into
src/data/region_map/region_map_sections.json (the TRACKED source; the build
regenerates the gitignored region_map_entries.h from it). Run before building.
Rows come from extract.py's region_map_entries.h target (en = English banner).
"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ET = os.path.join(ROOT, "tools", "translation", "et.json")
JS = os.path.join(ROOT, "src", "data", "region_map", "region_map_sections.json")
tr = {e["en"]: e["et"] for e in json.load(open(ET, encoding="utf-8"))
      if e.get("file", "").endswith("region_map_entries.h") and e.get("et") and e["et"] != e["en"]}
data = json.load(open(JS, encoding="utf-8"))
n = 0
def walk(o):
    global n
    if isinstance(o, dict):
        if "name" in o and o["name"] in tr:
            o["name"] = tr[o["name"]]; n += 1
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(data)
json.dump(data, open(JS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
open(JS, "a", encoding="utf-8").write("\n")
print(f"region_map_sections.json: {n} names translated")
