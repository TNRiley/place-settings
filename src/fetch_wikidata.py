"""A second, independently curated place list: Wikidata settlements in SE, NO, DK and FI.

GeoNames is the primary gazetteer. This one exists only to check it: Wikidata items are
added and typed by a different community, from different national sources, so a result
that holds on both is not an artefact of either.

The obvious query (instance of any subclass of "human settlement") times out on the public
endpoint, and even one query per country drops Sweden mid-stream, so it runs one query per
country and class, and the classes are named outright. They were chosen from the most common
instance-of values of Danish items with coordinates: village, hamlet, town, city, human
settlement, farm, and parish (Scandinavian parishes carry the name of their village).
Danish parish labels end in " Sogn" / " sogn", which is stripped.

Danmarks Adressers Web API (api.dataforsyningen.dk/stednavne2), the obvious *Danish*
source, answered every request with HTTP 410 Gone on 2026-10-13. It has been retired.

Usage:  python fetch_wikidata.py raw/wikidata
"""
import os
import sys
import time
import urllib.parse
import urllib.request

COUNTRIES = {"SE": "Q34", "NO": "Q20", "DK": "Q35", "FI": "Q33"}
CLASSES = "wd:Q532 wd:Q5084 wd:Q3957 wd:Q515 wd:Q1549591 wd:Q486972 wd:Q131596 wd:Q814648"
LANGS = '"sv","nb","nn","da","fi","en"'
UA = "place-settings-research/0.1 (one-off place-name list)"


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    for cc, q in COUNTRIES.items():
        for cls in CLASSES.split():
            dest = os.path.join(outdir, f"{cc}_{cls[3:]}.csv")
            if os.path.exists(dest):
                continue
            query = (f"SELECT DISTINCT ?label WHERE {{ "
                     f"?item wdt:P17 wd:{q}; wdt:P31 {cls}; rdfs:label ?label. "
                     f"FILTER(LANG(?label) IN ({LANGS})) }}")
            url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": query})
            req = urllib.request.Request(url, headers={"Accept": "text/csv", "User-Agent": UA})
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(req, timeout=300) as r:
                        body = r.read()
                    break
                except Exception as e:  # noqa: BLE001 - the endpoint drops long responses
                    print("retry", cc, cls, e)
                    time.sleep(30)
            else:
                sys.exit(f"gave up on {cc} {cls}")
            with open(dest, "wb") as f:
                f.write(body)
            print(cc, cls, body.count(b"\n") - 1, "labels", flush=True)
            time.sleep(3)


if __name__ == "__main__":
    main(sys.argv[1])
