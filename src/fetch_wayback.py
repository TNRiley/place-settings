"""Fetch archived copies of IKEA's en-GB product sitemaps from the Wayback Machine.

The live sitemaps only say what is on sale today. The Internet Archive has captured the
same files (https://www.ikea.com/sitemaps/prod-en-GB_<n>.xml) since July 2022. Captures
are patchy: in a given month some file numbers are missing, and the number of files
changes as IKEA re-shards. So we take the first capture of every file number in every
calendar quarter and later treat a quarter as the *union* of its files.

Reads the CDX listing written by:
  curl "https://web.archive.org/cdx/search/cdx?url=ikea.com/sitemaps/prod-en-GB_*&output=txt&fl=timestamp,original,length&filter=statuscode:200" > raw/cdx_gb.txt

Usage:  python fetch_wayback.py raw/cdx_gb.txt raw/wayback
The archive goes "Temporarily Offline" for minutes at a time; failures are retried and the
script is safe to re-run (it skips files already on disk).
"""
import os
import re
import sys
import time
import urllib.request

UA = "place-settings research fetch (one request every few seconds)"


def quarter(ts):
    return f"{ts[:4]}Q{(int(ts[4:6]) - 1) // 3 + 1}"


def main(cdx, outdir):
    os.makedirs(outdir, exist_ok=True)
    picks = {}
    with open(cdx, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2 or not parts[0].startswith("20"):
                continue
            ts, url = parts[0], parts[1]
            n = re.search(r"_(\d+)\.xml$", url).group(1)
            key = (quarter(ts), int(n))
            if key not in picks or ts < picks[key][0]:
                picks[key] = (ts, url)
    print(len(picks), "captures to fetch")
    for (q, n), (ts, url) in sorted(picks.items()):
        dest = os.path.join(outdir, f"{q}_{n:02d}_{ts}.xml")
        if os.path.exists(dest) and os.path.getsize(dest) > 10000:
            continue
        src = f"https://web.archive.org/web/{ts}id_/{url}"
        for attempt in range(6):
            try:
                req = urllib.request.Request(src, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=180) as r:
                    body = r.read()
                if b"<urlset" not in body[:2000]:
                    raise ValueError("not a sitemap (archive offline page?)")
                with open(dest, "wb") as f:
                    f.write(body)
                print("ok", dest, len(body), flush=True)
                break
            except Exception as e:  # noqa: BLE001 - log and back off, whatever it was
                print("retry", q, n, attempt, e, flush=True)
                time.sleep(20 * (attempt + 1))
        time.sleep(3)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
