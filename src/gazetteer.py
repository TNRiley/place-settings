"""Nordic place-name sets from the GeoNames country dumps, folded the way IKEA slugs are.

IKEA's URLs spell a-ring as "a", a-umlaut as "ae" and o-umlaut as "oe". Every gazetteer
name is put through the same fold (plus the Danish/Norwegian ae and o-slash, which IKEA
never needs but the gazetteers do), so a match is a match in one shared spelling.

Two families of set per country, deliberately kept apart:
  <CC>_P    populated places only (GeoNames feature class P: cities, towns, villages, farms)
  <CC>_any  every feature: terrain, water, farms, roads, everything
The gap between them is the instrument: Norway's dump carries ~600,000 features, most
of them terrain and water, against ~97,000 for Sweden.

Only each feature's main `name` column is used. Alternate names are not: Finnish places
carry Swedish exonyms there, and including them would let a Swedish word count as Finnish.
"""
import os
import unicodedata

FOLD = {"å": "a", "ä": "ae", "æ": "ae", "ö": "oe", "ø": "oe", "ü": "ue"}
COUNTRIES = ("SE", "NO", "DK", "FI")


def fold(s):
    s = s.lower()
    out = []
    for ch in s:
        if ch in FOLD:
            out.append(FOLD[ch])
            continue
        # strip any other accent (é -> e), drop anything that is not a letter
        base = unicodedata.normalize("NFKD", ch)[0]
        if base.isalpha() and base.isascii():
            out.append(base)
    return "".join(out)


def load(raw_dir):
    """Return {set_name: set(folded names)} and {set_name: {folded: feature_code}}."""
    sets = {}
    for cc in COUNTRIES:
        path = os.path.join(raw_dir, f"{cc}.txt")
        P, ANY, ISL, WATER = set(), set(), set(), set()
        with open(path, encoding="utf-8") as f:
            for line in f:
                c = line.rstrip("\n").split("\t")
                name, fclass, fcode = c[1], c[6], c[7]
                k = fold(name)
                if len(k) < 2:
                    continue
                ANY.add(k)
                if fclass == "P":
                    P.add(k)
                if fcode.startswith("ISL"):
                    ISL.add(k)
                if fclass == "H":
                    WATER.add(k)
        sets[f"{cc}_P"] = P
        sets[f"{cc}_any"] = ANY
        sets[f"{cc}_isl"] = ISL
        sets[f"{cc}_water"] = WATER
    return sets


def load_wikidata(wd_dir):
    """Second, independent place list: {<CC>_wd: set(folded labels)} from fetch_wikidata.py.

    Labels are reduced to the bare place name: anything after a comma or inside brackets is
    dropped ("Hemnes (Nordland)"), as is a trailing parish word ("Toftlund Sogn")."""
    import csv
    import glob
    sets = {}
    for cc in COUNTRIES:
        names = set()
        for path in glob.glob(os.path.join(wd_dir, f"{cc}_*.csv")):
            with open(path, encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    lab = row["label"].split(",")[0].split("(")[0].strip()
                    for suffix in (" sogn", " Sogn", " socken", " församling", " kommune", " kommun"):
                        if lab.endswith(suffix):
                            lab = lab[: -len(suffix)]
                    k = fold(lab)
                    if len(k) >= 2 and " " not in lab:
                        names.add(k)
        sets[f"{cc}_wd"] = names
    return sets
