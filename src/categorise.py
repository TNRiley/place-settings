"""Assign each IKEA name the product category it is sold as, from the English slug text.

Categories are the ones the folk rulebook talks about (Quartz 2017, repeated by Mental
Floss and others), plus a handful of large catch-alls so every name lands somewhere.
Rules are tried in order and the first hit wins, so "outdoor" beats "chair" and
"bedside table" beats "bed".

A name's category is the most common category over the articles where it is the *sole*
name; if it has none (it only ever appears inside combinations), the articles where it is
the *first* name. Names whose articles split across categories keep their majority and
record the share it won (`purity`), so the page can show how mixed a name is.

Usage:  python categorise.py raw/out/articles.json raw/out/names.json
"""
import collections
import json
import re
import sys

# (category, regex on the English remainder). Order matters.
RULES = [
    ("garden",      r"\boutdoor\b|\bgarden\b|\bparasol\b|\bsun lounger\b|\bdeck chair\b|\bgazebo\b"),
    ("children",    r"\bchildren s\b|\bchild s\b|\bsoft toy\b|\btoy\b|\bcot\b|\bbaby\b|\bhigh chair\b|\bjunior\b"),
    ("bathroom",    r"\bwash ?st(?:a)?nd\b|\bwash basin\b|\binset sink\b|\bcountertop wash\b|\bmirror cabinet\b|"
                    r"\bbath mat\b|\bbath towel\b|\bhand towel\b|\btowel\b|\bshower\b|\btoilet\b|\bbathroom\b|\bmixer tap\b"),
    ("bed_textile", r"\bduvet\b|\bpillowcase\b|\bfitted sheet\b|\bflat sheet\b|\bbedspread\b|\bpillow\b|\bmattress protector\b"),
    ("mattress",    r"\bmattress\b"),
    ("bedside",     r"\bbedside\b"),
    ("bed",         r"\bbed frame\b|\bdivan bed\b|\bupholstered bed\b|\bday ?bed\b|\bbunk bed\b|\bloft bed\b|"
                    r"\bstorage bed\b|\bsofa[- ]bed\b|\bbed\b"),
    ("wardrobe",    r"\bwardrobe\b|\bclothes rail\b"),
    ("hall",        r"\bshoe (?:cabinet|rack|storage|bench)\b|\bhat and coat\b|\bcoat (?:rack|stand|hanger)\b|\bhallway\b"),
    ("rug",         r"\brug\b|\bdoor ?mat\b"),
    ("curtain",     r"\bcurtain\b|\bcurtains\b|\bblind\b|\bblinds\b|\bfabric\b"),
    ("cushion",     r"\bcushion\b|\bthrow\b"),
    ("sofa",        r"\bsofa\b|\bseat section\b|\b\d seat\b|\bchaise longue\b|\barmchair\b|\bfootstool\b|\bpouffe\b|\brecliner\b"),
    ("desk",        r"\bdesk\b|\boffice chair\b|\bswivel chair\b|\bgaming chair\b|\bconference table\b|\bdrawer unit on castors\b"),
    ("chair",       r"\bchair\b|\bstool\b|\bbench\b"),
    ("dining",      r"\bdining\b|\bextendable table\b|\btable and \d|\btable \d chairs\b|\bbar table\b|^table\b"),
    ("table_other", r"\bcoffee table\b|\bside table\b|\bnest of tables\b|\btable\b"),
    ("bookcase",    r"\bbookcase\b|\bshelving unit\b|\bshelf unit\b|\bwall shelf\b|\bshelf\b"),
    ("lighting",    r"\blamp\b|\bpendant\b|\bled\b|\blight\b|\blighting\b|\bbulb\b|\bspotlight\b|\bchandelier\b"),
    ("fronts",      r"^door\b(?! stop| window)|^glass door\b|^sliding door\b|^cover panel\b|^drawer front\b|^front\b|^pair of\b"),
    ("kitchen",     r"\bbase cab|\bwall cab|\bhigh cab|\bhi cab|\bbase cb\b|\bwall cb\b|\bhc w\b|\bbc w\b|\bworktop\b|"
                    r"\bdrawer front\b|\bkitchen\b|\bsink\b|\bextractor\b|\bhob\b|\boven\b|\bfridge\b|\bfreezer\b|\bdishwasher\b"),
    ("cookware",    r"\bpan\b|\bpot\b(?! plant)|\bknife\b|\butensil\b|\bbowl\b|\bplate\b|\bmug\b|\bglass\b|\bcutlery\b|"
                    r"\bserving\b|\bchopping\b|\bcontainer\b|\bjar\b|\bbaking\b|\bnapkin\b|\btray\b"),
    ("decoration",  r"\bframe\b|\bpicture\b|\bmirror\b|\bclock\b|\bvase\b|\bcandle\b|\btealight\b|\bplant\b|\bpot\b|"
                    r"\bartificial\b|\bornament\b|\bdecoration\b|\bart card\b|\bposter\b"),
    ("storage",     r"\bbox\b|\bbasket\b|\bstorage\b|\bcabinet\b|\bchest of\b|\btrolley\b|\bpegboard\b|\bbin\b|\bdrawer\b|\bsideboard\b|\btv bench\b|\binsert\b"),
]
RULES = [(c, re.compile(p)) for c, p in RULES]


def category(rest):
    for c, rx in RULES:
        if rx.search(rest):
            return c
    return "other"


def assign(arts):
    """{name: {cat, n, purity, basis, cats}} for a list of parsed articles."""
    sole = collections.defaultdict(collections.Counter)
    first = collections.defaultdict(collections.Counter)
    for a in arts:
        c = category(a["rest"])
        if len(a["names"]) == 1:
            sole[a["names"][0]][c] += 1
        first[a["names"][0]][c] += 1
    # which frame a door or front is sold on: the first name of the combinations it sits in
    frames = collections.defaultdict(collections.Counter)
    for a in arts:
        for n in a["names"][1:]:
            frames[n][a["names"][0]] += 1
    names = {}
    for n in set(first) | set(sole):
        cnt = sole[n] if sole[n] else first[n]
        top, k = cnt.most_common(1)[0]
        if top == "fronts":
            # A door is part of the furniture it hangs on. PAX (and its sliding-door frames
            # SKYTTA and AULI) is the wardrobe system; BILLY is the bookcase; everything else
            # with no frame of its own is a kitchen front (METOD/ENHET are not in the slugs).
            fr = frames[n]
            top = ("wardrobe" if fr["pax"] or fr["skytta"] or fr["auli"] or n in ("skytta", "auli")
                   else "bookcase" if fr["billy"] else "kitchen")
        names[n] = {"cat": top, "n": sum(cnt.values()), "purity": round(k / sum(cnt.values()), 3),
                    "basis": "sole" if sole[n] else "first", "cats": dict(cnt)}
    return names


def main(src, out):
    with open(src, encoding="utf-8") as f:
        names = assign(json.load(f))
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(names, f, ensure_ascii=False, sort_keys=True)
    tally = collections.Counter(v["cat"] for v in names.values())
    for c, k in tally.most_common():
        print(f"{c:12s} {k}")
    print(len(names), "names")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
