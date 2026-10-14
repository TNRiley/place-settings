"""Shape everything the page needs into one JSON payload of base64 typed arrays.

Nothing is precomputed here beyond each instrument's yes/no verdict per name: hit rates,
lifts, permutation tests, cohorts and the calibration tables are all computed in the page
from these arrays.

Two tables:
  ikea  every name seen in Britain from July 2022 to today (archive + live sitemaps)
  dict  every name in Lars Petrus's c.2010 IKEA Dictionary, with his label, measured by the
        same instruments: the page recomputes each instrument's calibration from it

Flag bits (uint32), identical in both tables:
   0-3  GeoNames populated place  SE NO DK FI
   4-7  GeoNames any feature      SE NO DK FI
   8-11 Wikidata settlement       SE NO DK FI
   12   boy's name   13 girl's name   (SCB tilltalsnamn, >= 10 bearers, majority sex)
   14   island in any of the four   15 Swedish water feature   16 exact SALDO word
   17   display spelling reconstructed (no source supplied the real one)
   18   on sale today
   19   sold only as a door mat (never as a rug proper)

Usage:  python build_payload.py   (paths are fixed relative to src/)
"""
import base64
import json
import os
import sys
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gazetteer as G  # noqa: E402
from analyse import NAME_MIN  # noqa: E402

CATS = ["bed", "wardrobe", "hall", "rug", "sofa", "dining", "chair", "desk", "bookcase",
        "curtain", "bed_textile", "cushion", "bathroom", "garden", "lighting", "kitchen",
        "cookware", "decoration", "storage", "table_other", "children", "mattress", "bedside",
        "other"]
COHORTS = ["2022", "2023", "2024", "2025", "2026"]
LAR5 = {"word": 1, "boy": 2, "girl": 3, "other": 8, "unknown": 9}
LAR5_PLACE = {"SE": 4, "NO": 5, "DK": 6, "FI": 7}
CC = G.COUNTRIES


def b64(typecode, values):
    a = array(typecode, values)
    if sys.byteorder != "little":
        a.byteswap()
    return base64.b64encode(a.tobytes()).decode("ascii")


def p(*parts):
    return os.path.join(HERE, *parts)


def load(path):
    with open(p(path), encoding="utf-8") as f:
        return json.load(f)


def spellings(raw_dir, keys):
    """Real spellings for folded keys, from GeoNames (places) where one matches."""
    out = {}
    for cc in CC:
        with open(os.path.join(raw_dir, f"{cc}.txt"), encoding="utf-8") as f:
            for line in f:
                c = line.split("\t")
                k = G.fold(c[1])
                if k in keys and (k not in out or c[6] == "P"):
                    out[k] = c[1]
    return out


def unfold(k):
    # IKEA folds a-umlaut to "ae" and o-umlaut to "oe"; Swedish almost never spells either
    # pair natively, so put them back. a-ring folds to plain "a" and cannot be recovered.
    return k.replace("ae", "ä").replace("oe", "ö")


def main():
    S = G.load(p("raw", "geonames"))
    S.update(G.load_wikidata(p("raw", "wikidata")))
    S["islands"] = S["SE_isl"] | S["NO_isl"] | S["DK_isl"] | S["FI_isl"]
    scb = load("raw/out/scb_names.json")
    saldo = load("raw/out/saldo.json")
    lar5 = load("raw/out/lar5.json")
    tl = load("raw/out/timeline.json")
    live_names = load("raw/out/names.json")

    def flags(k):
        f = 0
        for i, cc in enumerate(CC):
            f |= (k in S[f"{cc}_P"]) << i
            f |= (k in S[f"{cc}_any"]) << (4 + i)
            f |= (k in S[f"{cc}_wd"]) << (8 + i)
        w, m = scb.get(k, (0, 0))
        f |= (m >= NAME_MIN and m > w) << 12
        f |= (w >= NAME_MIN and w > m) << 13
        f |= (k in S["islands"]) << 14
        f |= (k in S["SE_water"]) << 15
        f |= (k in saldo["words"] and any(x != "pm" for x in saldo["words"][k])) << 16
        return f

    def lar5_code(k):
        r = lar5.get(k)
        if not r:
            return 0
        if r["kind"] == "place":
            return LAR5_PLACE.get(r.get("country"), 8)
        return LAR5[r["kind"]]

    quarters = tl["quarters"]
    names = tl["names"]
    keys = sorted(names)
    real = spellings(p("raw", "geonames"), set(keys) | set(lar5))

    def display(k):
        if k in saldo["forms"] and flags(k) >> 16 & 1:
            return saldo["forms"][k].upper(), False
        if k in real:
            return real[k].upper(), False
        if k in lar5:
            return lar5[k]["name"], False
        return unfold(k).upper(), True

    ik_name, ik_cat, ik_coh, ik_q, ik_flag, ik_lar, ik_w, ik_m, ik_theme = [], [], [], [], [], [], [], [], []
    for k in keys:
        v = names[k]
        shown, guessed = display(k)
        f = flags(k) | (guessed << 17) | (v["live"] << 18) | (v["matonly"] << 19)
        cat = v["cat"] if v["cat"] in CATS else "other"
        coh = "2026" if v["cohort"] == "now" else v["cohort"]
        qmask = 0
        for i, q in enumerate(quarters):
            qmask |= (q in tl["seen"][k]) << i
        prim = saldo["primary"].get(k, "") if f >> 16 & 1 else ""
        ik_name.append(shown)
        ik_cat.append(CATS.index(cat))
        ik_coh.append(COHORTS.index(coh))
        ik_q.append(qmask)
        ik_flag.append(f)
        ik_lar.append(lar5_code(k))
        w, m = scb.get(k, (0, 0))
        ik_w.append(w)
        ik_m.append(m)
        ik_theme.append(saldo["forms"].get(prim, prim) if prim else "")

    dk = sorted(lar5)
    payload = {
        "built": "2026-10-13",
        "quarters": quarters,
        "qurls": [tl["urls"][q] for q in quarters],
        "cats": CATS,
        "cohorts": COHORTS,
        "nameMin": NAME_MIN,
        "ikea": {
            "n": len(keys),
            "name": "|".join(ik_name),
            "theme": "|".join(ik_theme),
            "cat": b64("B", ik_cat), "cohort": b64("B", ik_coh), "q": b64("I", ik_q),
            "flag": b64("I", ik_flag), "lar5": b64("B", ik_lar),
            "women": b64("I", ik_w), "men": b64("I", ik_m),
        },
        "dict": {
            "n": len(dk),
            "name": "|".join(lar5[k]["name"] for k in dk),
            "lar5": b64("B", [lar5_code(k) for k in dk]),
            "flag": b64("I", [flags(k) for k in dk]),
            "women": b64("I", [scb.get(k, (0, 0))[0] for k in dk]),
            "men": b64("I", [scb.get(k, (0, 0))[1] for k in dk]),
        },
    }
    assert len(live_names) == sum(names[k]["live"] for k in keys), "live count mismatch"
    with open(p("payload.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"payload.json {os.path.getsize(p('payload.json')) / 1e3:.0f} kB: "
          f"{len(keys)} IKEA names, {len(dk)} dictionary names, {len(quarters)} quarters")


if __name__ == "__main__":
    main()
