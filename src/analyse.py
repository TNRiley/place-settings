"""Test each rule of the folk IKEA naming system against today's range.

For every testable rule ("beds are named after Norwegian places") we report, per name:

  hit      share of the rule's category whose name is in the claimed source
  base     share of every *other* name in the range that is in the same source
  lift     hit / base: the rule has to beat the background, not just score high
  p        one-sided permutation p: shuffle category labels across all names 10,000 times
  rival    the best-scoring *other* source for the same category, so that a category that
           is as Swedish as it is Norwegian cannot pass as "Norwegian"
  B        Lars Petrus's c.2010 human labels for the same names, where he covered them.
           Never averaged with the gazetteer; shown beside it.

Measure A sources (all fixed before looking at the rule table):
  <CC>_P      GeoNames populated places (class P). Chosen over "any feature" because on
              Petrus's labels it catches 72-89% of real places while calling only 1-4% of
              ordinary Swedish words a place; "any feature" calls 10% of them Norwegian.
  boy / girl  SCB tilltalsnamn, 31 Dec 2022, at least 10 bearers and more of that sex.
              At 10 bearers: 95% of Petrus's boys' names, 97% of girls', 2-3% of words.
  islands     GeoNames ISL* features in any of the four countries
  SE_water    GeoNames class H (lakes, bays, streams, sounds) in Sweden

Usage:  python analyse.py raw/out/names.json raw/out/lar5.json raw/out/scb_names.json raw/geonames raw/out/rules.json
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gazetteer as G  # noqa: E402

NAME_MIN = 10

# (id, claim as the folklore states it, categories, claimed source, untestable note)
RULES = [
    ("beds",      "Beds are named after Norwegian places",              ["bed"],                 "NO_P"),
    ("wardrobes", "Wardrobes are named after Norwegian places",         ["wardrobe"],            "NO_P"),
    ("hall",      "Hall furniture is named after Norwegian places",     ["hall"],                "NO_P"),
    ("rugs",      "Rugs are named after Danish places",                 ["rug"],                 "DK_P"),
    ("sofas",     "Sofas and armchairs are named after Swedish places", ["sofa"],                "SE_P"),
    ("dining",    "Dining tables are named after Swedish places",       ["dining"],              "SE_P"),
    ("dining_fi", "Dining tables are named after Finnish places",       ["dining"],              "FI_P"),
    ("chairs_pl", "Chairs are named after Swedish places",              ["chair"],               "SE_P"),
    ("chairs_bn", "Chairs are named after boys",                        ["chair"],               "boy"),
    ("desks",     "Desks and office chairs are named after boys",       ["desk"],                "boy"),
    ("bookcases", "Bookcases are named after boys (or occupations)",    ["bookcase"],            "boy"),
    ("curtains",  "Fabrics and curtains are named after girls",         ["curtain"],             "girl"),
    ("bathroom",  "Bathroom things are named after Swedish lakes and waters", ["bathroom"],      "SE_water"),
    ("garden",    "Garden furniture is named after Scandinavian islands", ["garden"],            "islands"),
    ("lighting",  "Lighting is named after Swedish places (among much else)", ["lighting"],      "SE_P"),
]
SOURCES = ["SE_P", "NO_P", "DK_P", "FI_P", "boy", "girl", "islands", "SE_water"]
# what Petrus's label has to say for measure B to count a name as a hit for each source
B_MATCH = {"SE_P": ("place", "SE"), "NO_P": ("place", "NO"), "DK_P": ("place", "DK"),
           "FI_P": ("place", "FI"), "boy": ("boy", None), "girl": ("girl", None),
           "islands": None, "SE_water": None}


def main(names_p, lar5_p, scb_p, geo_dir, out):
    names = json.load(open(names_p, encoding="utf-8"))
    lar5 = json.load(open(lar5_p, encoding="utf-8"))
    scb = json.load(open(scb_p, encoding="utf-8"))
    S = G.load(geo_dir)
    S["islands"] = S["SE_isl"] | S["NO_isl"] | S["DK_isl"] | S["FI_isl"]

    def boy(k):
        w, m = scb.get(k, (0, 0))
        return m >= NAME_MIN and m > w

    def girl(k):
        w, m = scb.get(k, (0, 0))
        return w >= NAME_MIN and w > m

    keys = sorted(names)
    hits = {s: [(boy(k) if s == "boy" else girl(k) if s == "girl" else k in S[s]) for k in keys]
            for s in SOURCES}
    cat = [names[k]["cat"] for k in keys]
    rng = random.Random(20261013)

    rows = []
    for rid, claim, cats, src in RULES:
        inside = [i for i, c in enumerate(cat) if c in cats]
        outside = [i for i, c in enumerate(cat) if c not in cats]
        h = sum(hits[src][i] for i in inside)
        hit = h / len(inside)
        base = sum(hits[src][i] for i in outside) / len(outside)
        # permutation: how often does a random set of the same size score this high?
        allhits = hits[src]
        ge = 0
        for _ in range(10000):
            if sum(allhits[i] for i in rng.sample(range(len(keys)), len(inside))) >= h:
                ge += 1
        rival = max((s for s in SOURCES if s != src),
                    key=lambda s: sum(hits[s][i] for i in inside))
        rival_rate = sum(hits[rival][i] for i in inside) / len(inside)
        # measure B
        bm = B_MATCH[src]
        covered = [keys[i] for i in inside if keys[i] in lar5]
        if bm:
            kind, cc = bm
            bh = sum(1 for k in covered
                     if lar5[k]["kind"] == kind and (cc is None or lar5[k].get("country") == cc))
        else:
            bh = None
        rows.append({
            "id": rid, "claim": claim, "cats": cats, "source": src, "n": len(inside),
            "hits": h, "hit": round(hit, 4), "base": round(base, 4),
            "lift": round(hit / base, 2) if base else None,
            "p": (ge + 1) / 10001, "rival": rival, "rival_rate": round(rival_rate, 4),
            "B_n": len(covered), "B_hits": bh,
            "names_hit": [keys[i] for i in inside if hits[src][i]],
            "names_miss": [keys[i] for i in inside if not hits[src][i]],
        })
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"{'rule':10s} {'n':>4s} {'hit':>6s} {'base':>6s} {'lift':>6s} {'p':>7s}  rival          B")
    for r in rows:
        b = f"{r['B_hits']}/{r['B_n']}" if r["B_hits"] is not None else f"-/{r['B_n']}"
        print(f"{r['id']:10s} {r['n']:4d} {r['hit']*100:5.0f}% {r['base']*100:5.1f}% {r['lift'] or 0:6.1f} "
              f"{r['p']:7.4f}  {r['rival']:8s} {r['rival_rate']*100:3.0f}%  {b}")


if __name__ == "__main__":
    main(*sys.argv[1:6])
