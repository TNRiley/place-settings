"""Turn Lars Petrus's IKEA Dictionary (lar5.com/ikea, c. 2010) into one label per name.

Each entry is a <DIV> holding the name, then one or more senses, each introduced by a
<span> whose class says what kind of sense it is:
    bl  proper Swedish word          b2  "improper" (made-up or bent) Swedish word
    by  boy's name                   gl  girl's name
    gr  geographical name            wr  something else (myth, foreign word...)
    un  not yet worked out
A place sense usually carries a Google Maps link with coordinates. We assign the place a
country by its nearest GeoNames feature in Sweden, Norway, Denmark or Finland, rather than
by parsing the prose, which says things like "uninhabited place in Smaland".

Only the label is kept, never Petrus's definitions. The dictionary states no licence, so the
page ships the class and country code per name and links to the site for the meanings.

Usage:  python parse_lar5.py raw/lar5_ikea.html raw/geonames raw/out/lar5.json
"""
import html
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gazetteer import COUNTRIES, fold  # noqa: E402

DIV = re.compile(r"<DIV><A [^>]*>([^<]+)</A>(.*?)</DIV>", re.S)
SENSE = re.compile(r'<span class="(\w+)">')
COORD = re.compile(r"maps\?q=[^@\"]*@(-?[\d.]+),(-?[\d.]+)")
CLASS = {"bl": "word", "b2": "word", "by": "boy", "gl": "girl", "gr": "place", "wr": "other", "un": "unknown"}


def grid_points(raw_dir):
    """Every GeoNames feature in the four countries, bucketed on a 0.5 degree grid."""
    grid = {}
    for cc in COUNTRIES:
        with open(os.path.join(raw_dir, f"{cc}.txt"), encoding="utf-8") as f:
            for line in f:
                c = line.split("\t")
                lat, lon = float(c[4]), float(c[5])
                grid.setdefault((round(lat * 2), round(lon * 2)), []).append((lat, lon, cc))
    return grid


def nearest_country(grid, lat, lon):
    best = (1e9, None)
    gy, gx = round(lat * 2), round(lon * 2)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for plat, plon, cc in grid.get((gy + dy, gx + dx), ()):
                d = (plat - lat) ** 2 + ((plon - lon) * math.cos(math.radians(lat))) ** 2
                if d < best[0]:
                    best = (d, cc)
    # nothing within ~50 km means the place is outside the four countries
    return best[1] if best[0] < 0.5 ** 2 else "XX"


def main(src, raw_dir, out):
    with open(src, encoding="utf-8") as f:
        page = f.read()
    grid = grid_points(raw_dir)
    rows = {}
    for name, body in DIV.findall(page):
        name = html.unescape(name).strip()
        senses = SENSE.findall(body)
        if not senses or not name.isupper():
            continue
        kinds = [CLASS.get(s, "unknown") for s in senses]
        rec = {"name": name, "kind": kinds[0], "kinds": sorted(set(kinds))}
        m = COORD.search(body)
        if "place" in kinds:
            rec["country"] = nearest_country(grid, float(m.group(1)), float(m.group(2))) if m else "?"
        rows[fold(name)] = rec
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rows, f, ensure_ascii=False, sort_keys=True)
    from collections import Counter
    print(len(rows), "names;", Counter(r["kind"] for r in rows.values()))
    print("place countries:", Counter(r.get("country") for r in rows.values() if "place" in r["kinds"]))


if __name__ == "__main__":
    main(*sys.argv[1:4])
