"""Read IKEA's en-GB product sitemaps into one row per article.

Each product URL looks like
    https://www.ikea.com/gb/en/p/hemnes-bed-frame-white-stain-luroey-s49012345/
i.e. <name tokens>-<english type, colour, material>-<s?><8 digit article number>.
The sitemaps fold Swedish letters: a-ring -> a, a-umlaut -> ae, o-umlaut -> oe.

Name tokens are split off the front greedily: a leading token counts as a name if it
appears as the *first* token of some product (every name heads at least one product of
its own). Combination products ("tannforsen-vastersjon-wash-stnd-...") therefore yield
two names. The English remainder is kept whole for categorisation in categorise.py.

Usage:  python parse_sitemaps.py raw/sitemaps raw/out/articles.json
"""
import glob
import json
import os
import re
import sys

LOC = re.compile(r"<loc>https://www\.ikea\.com/gb/en/p/([^<]+?)/?</loc>")
TAIL = re.compile(r"^(.*)-(s?)(\d{8})$")


def slugs_in(path):
    with open(path, encoding="utf-8") as f:
        return LOC.findall(f.read())


def split(slugs, heads=None):
    """Parse slugs into article rows. `heads` (the set of known name tokens) defaults to
    the first tokens of these same slugs; pass a wider set when parsing a partial snapshot."""
    rows = {}
    for slug in slugs:
        m = TAIL.match(slug)
        if m:
            body, combo, art = m.groups()
            rows[art] = (body.split("-"), combo == "s")
    if heads is None:
        heads = {toks[0] for toks, _ in rows.values()}
    out = []
    for art, (toks, combo) in sorted(rows.items()):
        names, i = [], 0
        # a name never starts with a digit; stop at the first non-head token
        while i < len(toks) - 1 and toks[i] in heads and not toks[i][0].isdigit():
            names.append(toks[i])
            i += 1
        if names:
            out.append({"art": art, "names": names, "rest": " ".join(toks[i:]), "combo": combo})
    return out, heads


def main(src, out):
    slugs = []
    for path in sorted(glob.glob(os.path.join(src, "prod-en-GB_*.xml"))):
        slugs += slugs_in(path)
    rows, heads = split(slugs)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rows, f, ensure_ascii=False)
    print(f"{len(slugs)} urls, {len(rows)} articles, {len(heads)} head names")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
