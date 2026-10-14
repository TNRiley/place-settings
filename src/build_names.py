"""Swedish first names with bearer counts by sex, from Statistics Sweden (SCB).

Source workbook: "Samtliga folkbokforda - fornamn, tilltalsnamn och efternamn med minst
tva barare", 31 December 2022 (namn-med-minst-tva-barare-31-december-2022.xlsx).
We use the *tilltalsnamn* sheets (the name a person actually goes by), not *fornamn*
(every registered given name, including second and third names), because a desk named
after a boy is named after what boys are called.

Output: raw/out/scb_names.json  {folded_name: [women, men]}

Usage:  python build_names.py raw/scb_names_2022.xlsx raw/out/scb_names.json
"""
import json
import os
import sys

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gazetteer import fold  # noqa: E402


def sheet(wb, title):
    out = {}
    for row in wb[title].iter_rows(min_row=6, values_only=True):
        name, n = row[0], row[1]
        if isinstance(name, str) and isinstance(n, int):
            k = fold(name)
            out[k] = out.get(k, 0) + n
    return out


def main(src, dst):
    wb = openpyxl.load_workbook(src, read_only=True)
    w = sheet(wb, "Tilltalsnamn kvinnor")
    m = sheet(wb, "Tilltalsnamn män")
    rows = {k: [w.get(k, 0), m.get(k, 0)] for k in set(w) | set(m)}
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rows, f, ensure_ascii=False, sort_keys=True)
    print(len(w), "women's names,", len(m), "men's names,", len(rows), "folded keys")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
