"""Compact lookup of Swedish words from SALDO (Sprakbanken, University of Gothenburg).

SALDO is a lexicon of modern Swedish: every lemma with its part of speech, and every sense
linked to a "primary descriptor", a more general sense it is a kind of (bergnejlika ->
nejlika -> blomma). That gives the second, independent measure of what an IKEA name is:
not "is it a place or a person" (gazetteers, name registry) but "is it an ordinary Swedish
word", and if so, what kind of thing it names.

Output: raw/out/saldo.json
  words:   {folded lemma: [parts of speech]}       (pm = proper name, kept but flagged)
  primary: {folded lemma: folded primary lemma}    first sense only, nouns only
  forms:   {folded lemma: written form}            the real spelling, for display

Usage:  python build_saldo.py raw/saldo.xml raw/out/saldo.json
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gazetteer import fold  # noqa: E402

SENSE_ID = re.compile(r"^(.*)\.\.(\d+)$")


def main(src, dst):
    words, primary, spelling = {}, {}, {}
    for _, el in ET.iterparse(src, events=("end",)):
        if el.tag != "LexicalEntry":
            continue
        forms = el.findall("./Lemma/FormRepresentation")
        lemmas = []
        for fr in forms:
            feats = {f.get("att"): f.get("val") for f in fr.findall("feat")}
            wf, pos = feats.get("writtenForm"), feats.get("partOfSpeech")
            if not wf or " " in wf or not pos:
                continue
            k = fold(wf)
            if len(k) < 2:
                continue
            words.setdefault(k, set()).add(pos)
            if pos != "pm":
                spelling.setdefault(k, wf)
            lemmas.append((k, pos))
        sense = el.find("./Sense")
        if sense is not None and lemmas:
            m = SENSE_ID.match(sense.get("id") or "")
            for rel in sense.findall("SenseRelation"):
                lab = rel.find("feat")
                if lab is not None and lab.get("val") == "primary" and m and m.group(2) == "1":
                    tm = SENSE_ID.match(rel.get("targets") or "")
                    if tm:
                        for k, pos in lemmas:
                            if pos == "nn":
                                primary.setdefault(k, fold(tm.group(1)))
        el.clear()
    out = {"words": {k: sorted(v) for k, v in words.items()}, "primary": primary, "forms": spelling}
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, sort_keys=True)
    print(len(words), "word forms,", len(primary), "noun primaries")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
