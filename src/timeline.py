"""When each IKEA name was first and last on sale in Britain, 2022 to today.

Inputs: the archived sitemaps from fetch_wayback.py (raw/wayback/<YYYYQn>_<file>_<ts>.xml)
and today's live sitemaps (raw/sitemaps). Each quarter is the union of every file captured
in it, because no quarter has every shard.

A name's *cohort* is when it first appears:
  2022      on sale in the first year the archive covers (July to December 2022). This is a
            floor, not a launch date: these names could be decades old.
  2023 ...  first seen in that calendar year, and absent from all of 2022.
  now       first seen in today's live sitemaps.
Taking the whole of 2022 as the baseline, rather than its first quarter, stops a shard that
happened to be missing in July from making an old name look new in October.

Every article ever seen (deduplicated by article number, latest wins) is categorised with
the same rules as today's range, so a name that has since been discontinued still gets one.

Usage:  python timeline.py raw/wayback raw/sitemaps raw/out/timeline.json
"""
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from categorise import assign  # noqa: E402
from parse_sitemaps import slugs_in, split  # noqa: E402

LIVE = "now"


def main(wb_dir, live_dir, out):
    by_q = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(wb_dir, "*.xml"))):
        by_q[os.path.basename(p).split("_")[0]] += slugs_in(p)
    for p in sorted(glob.glob(os.path.join(live_dir, "prod-en-GB_*.xml"))):
        by_q[LIVE] += slugs_in(p)
    quarters = sorted(q for q in by_q if q != LIVE) + [LIVE]

    # name tokens are recognised against every snapshot at once
    _, heads = split([s for q in quarters for s in by_q[q]])
    seen = collections.defaultdict(list)
    latest = {}
    for q in quarters:
        rows, _ = split(by_q[q], heads)
        names = {n for r in rows for n in r["names"][:1]}
        for n in names:
            seen[n].append(q)
        for r in rows:
            latest[r["art"]] = r
        print(f"{q}: {len(by_q[q]):6d} urls, {len(names):5d} names")

    cats = assign(list(latest.values()))
    # names sold only as door mats: kept in "rugs" (the folklore lumps them together), but
    # flagged so the page can show the rug result without them
    kinds = collections.defaultdict(set)
    for r in latest.values():
        kinds[r["names"][0]].add("mat" if "door mat" in r["rest"] else "other")
    timeline = {}
    for n, qs in seen.items():
        first = qs[0]
        cohort = "2022" if first.startswith("2022") else (LIVE if first == LIVE else first[:4])
        timeline[n] = {"cohort": cohort, "first": first, "last": qs[-1], "nq": len(qs),
                       "live": qs[-1] == LIVE, "cat": cats[n]["cat"],
                       "matonly": kinds[n] == {"mat"}}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"quarters": quarters, "names": timeline, "seen": dict(seen),
                   "urls": {q: len(set(by_q[q])) for q in quarters}}, f,
                  ensure_ascii=False, sort_keys=True)
    print(collections.Counter(v["cohort"] for v in timeline.values()))
    print(len(timeline), "names ever seen;", sum(v["live"] for v in timeline.values()), "on sale now")


if __name__ == "__main__":
    main(*sys.argv[1:4])
