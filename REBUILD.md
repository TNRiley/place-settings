# Rebuilding Place Settings

A recipe, not a summary. Assumes a shell, Python 3.13 with `openpyxl`, Node (only for
`node --check`), headless Chrome for the visual check, and no other context. About two hours,
most of it the Internet Archive serving a gigabyte of old sitemaps slowly.

## 1. What is being built

One self-contained HTML page that tests the folk rulebook of IKEA product names, rule by rule,
against every product name IKEA has sold in Britain since July 2022.

The rulebook, as usually repeated (Quartz 2017, reprinted by Mental Floss; Wikipedia gives a
short form): beds, wardrobes and hall furniture are Norwegian places; rugs are Danish places;
sofas, armchairs, chairs and dining tables are Swedish places; desks, chairs and bookcases are
boys' names; fabrics and curtains are girls' names; bathroom things are Swedish lakes and
waters; garden furniture is Scandinavian islands. Other versions put dining tables in Finland.
Note that the Quartz list puts chairs under *both* Swedish places and boys' names.

**The finding:** 79% of the rug names on sale in 2022 (69 of 87) are Danish places; of the 136
rug names launched since January 2023, 13 are (10%). By launch year: 2023 12/41, 2024 0/55,
2025 1/20, 2026 0/20. The replacements are ordinary Swedish nouns, a run of them railway and
road words (JÄRNVÄG, LOKALTÅG, TIDTABELL, VÄXELFEL, VÄGSKYLT). The same retirement shows on
curtains (girls' names 17% to 1%), chairs (boys' names 33% to 2%), wardrobes (Norwegian places
66% to 12%) and lighting (Swedish places 37% to 4%). Sofas (87% to 85%) and garden islands
(48% to 46%) did not move.

## 2. Data

All raw downloads go in `src/raw/` and are not committed. Total about 1.4 GB.

| what | where | notes |
|---|---|---|
| live product sitemaps | `https://www.ikea.com/sitemaps/prod-en-GB_{1..6}.xml` | ~50 MB each, mostly image tags. 28,699 product URLs on 2026-10-13. Listed in `https://www.ikea.com/sitemaps/sitemap.xml`. Not disallowed by robots.txt. Send a browser User-Agent. |
| archived sitemaps | Wayback CDX: `https://web.archive.org/cdx/search/cdx?url=ikea.com/sitemaps/prod-en-GB_*&output=txt&fl=timestamp,original,length&filter=statuscode:200` → `raw/cdx_gb.txt` | 218 captures, July 2022 onward; **nothing earlier exists**. `fetch_wayback.py` takes the first capture of each file number per quarter (103 files, ~1 GB) via `id_` URLs. The archive returns a "Temporarily Offline" HTML page for minutes at a time with status 200: the fetcher checks for `<urlset` and retries. |
| GeoNames | `https://download.geonames.org/export/dump/{SE,NO,DK,FI}.zip` | Unzip to `raw/geonames/XX.txt`. Tab-separated; name col 1, feature class col 6, code col 7. |
| Wikidata | `fetch_wikidata.py` → `raw/wikidata/{CC}_{Q}.csv` | One SPARQL query per country × class (Q532 village, Q5084 hamlet, Q3957 town, Q515 city, Q1549591 big city, Q486972 human settlement, Q131596 farm, Q814648 parish). The `P31/P279*` query times out; a per-country query drops Sweden mid-stream. |
| SCB names | `https://www.scb.se/contentassets/9fe7dbb460994c72b835163dbc491ef9/namn-med-minst-tva-barare-31-december-2022.xlsx` | 13 MB. Use the *Tilltalsnamn* sheets, not *Förnamn*. Header row 5. |
| SALDO | `https://svn.spraakbanken.gu.se/sb-arkiv/pub/lmf/saldo/saldo.xml` | 74 MB LMF XML, the 2017 release. |
| IKEA Dictionary | `https://lar5.com/ikea/index.html` | 249 KB, UTF-8. Each entry is `<DIV><A>NAME</A><span class="bl/b2/by/gl/gr/wr/un">…`. Place entries carry `maps?q=Name@lat,lon`. |
| rulebook text | Wikipedia IKEA article via `action=parse` (revid 1379150695), Mental Floss | for the wording of the claims only |

Dead end, documented: `https://api.dataforsyningen.dk/stednavne2` (Danish place names) answers
HTTP 410 Gone. It has been retired.

## 3. Pipeline (run from `src/`, all with `python -P`)

```
python -P parse_sitemaps.py raw/sitemaps raw/out/articles.json
python -P categorise.py raw/out/articles.json raw/out/names.json
python -P fetch_wayback.py raw/cdx_gb.txt raw/wayback
python -P fetch_wikidata.py raw/wikidata
python    build_names.py raw/scb_names_2022.xlsx raw/out/scb_names.json      # needs openpyxl
python -P build_saldo.py raw/saldo.xml raw/out/saldo.json
python -P parse_lar5.py raw/lar5_ikea.html raw/geonames raw/out/lar5.json
python -P timeline.py raw/wayback raw/sitemaps raw/out/timeline.json
python -P analyse.py raw/out/names.json raw/out/lar5.json raw/out/scb_names.json raw/geonames raw/out/rules.json   # cross-check only
python -P build_payload.py
python -P inject.py        # writes ../index.html, then wrap_for_pages.py and add_catalog_link.py
```

On Windows set `PYTHONIOENCODING=utf-8` for anything that prints.

### Decisions and why

- **Slugs.** `<name tokens>-<english description>-<s?><8-digit article>`. IKEA folds Ä→AE, Ö→OE,
  Å→A. A leading token is a *name* if it heads at least one product of its own; combination
  products (TÄNNFORSEN-VÄSTERSJÖN wash-stand) yield two names. Every list is put through the
  same fold (`gazetteer.fold`, which also maps Æ→AE, Ø→OE, Ü→UE and strips other accents).
- **Unit is the name, not the article.** MAXIMERA alone has 3,164 articles. A name's category
  is the commonest category over the articles where it is the sole name, falling back to the
  ones it heads. Rules in `categorise.RULES`, first hit wins; "outdoor" beats "chair",
  "bedside" beats "bed".
- **Doors.** Door and front names are re-assigned by the frame they are sold with: any
  combination headed by PAX (or the sliding-door frames SKYTTA, AULI) makes it a wardrobe,
  BILLY a bookcase, otherwise a kitchen front. PAX doors are mostly Norwegian places
  (FORSAND, MEHAMN, TYSSEDAL); kitchen fronts mostly Swedish "-viken" bays.
- **Populated places (GeoNames class P), not every feature.** See §5 trap 1.
- **Name register threshold 10 bearers, majority sex**, fixed on the dictionary before any
  furniture was tested (§5 trap 2).
- **SALDO exact match only**, no compound splitting (§5 trap 3).
- **Cohorts.** A name's cohort is the calendar year of the first quarter it appears; anything
  seen at any point in July–December 2022 is "2022". The live sitemaps count as "now"; names
  first seen there are folded into 2026 in the page. Using all of 2022 as the baseline stops a
  shard missing from the July capture making an old name look new in October.
- **A quarter is the union of its captured files.** Shards are random, not alphabetical, and
  most quarters lack one or two. 2022Q3 holds 17,576 distinct URLs against ~30,000 later; the
  page draws quarters under 60% of the fullest one pale and says to read their mix, not counts.
- **Door mats stay in "rugs"** (the folklore lumps them in) but carry flag bit 19 so the page
  can show the result without them.
- **Spelling for display.** Taken from the source that matched (SALDO written form, GeoNames
  name, dictionary entry); otherwise AE→Ä and OE→Ö are put back and the name is flagged as
  reconstructed (bit 17). Å cannot be recovered: GARDSBUTIK should be GÅRDSBUTIK.

## 4. The page

Template `src/template.html`, payload spliced in at `__PAYLOAD__` by `inject.py`. Every
statistic is computed in the page from the arrays: hit rates, background rates, permutation
p values (2,000 shuffles, seeded), cohort gaps, the controls, the calibration tables.

Sections: hero (finding sentence built from the computed rates, a waffle of rug names by
cohort, four number tiles) · the rule table (today's range) · the dumbbell of 2022 vs since,
with the two controls shaded · rugs by quarter, stacked by kind of name · robustness table ·
the rug name wall (toggle cohort, discontinued names struck through) · translations · the
instrument (calibration tables, threshold slider, the Norway paragraph) · name search ·
methods. Inks: Swedish place slate, Norwegian brick, Danish amber, Finnish pine, person plum,
ordinary word grey. No IKEA branding, colours or imagery.

**Withholding.** If either control rule moves more than ten points between cohorts, the
background Danish rate outside rugs exceeds 2% in either cohort, or the false-alarm rate on
ordinary words differs by more than five points, the finding sentence is replaced by a
"Withheld" notice.

## 5. Traps, with the wrong answer and the right one

1. **Norway has a place called everything.** GeoNames holds 366,487 distinct Norwegian names
   against 69,369 Swedish (farms, hills, bogs, skerries). Against *any feature*, 10% of
   Petrus's ordinary Swedish words are "Norwegian places" (MALM, IKEA's best-known bed, is a
   Norwegian village; it is the Swedish word for ore). Against populated places: 2%. Wrong:
   any-feature matching. Right: class P.
2. **The register knows everyone.** With at least two bearers, 5% of dictionary words are
   men's names and 8% women's. At 10 bearers: 2% and 3%, with 95% of boys' and 97% of girls'
   names still caught.
3. **Compound splitting.** Accepting any name that *ends* in a SALDO noun catches 92% of
   dictionary words but also 51% of dictionary places, because Scandinavian place names are
   compounds (BERGSVIKEN = mountain's bay). Wrong: split compounds. Right: exact lemma only
   (87% of words, 2% of places). Cost: measure B is silent on curtains, beds and lighting,
   whose new names are compounds and species names SALDO lacks.
4. **The dictionary is not a time axis.** Petrus wrote down names he could explain, so his
   names are recognisable words and places far more often than IKEA's range. Comparing his
   names with today's suggests a decline that is partly his selection. Wrong: use it as a
   2010 cohort. Right: per-name second opinion and calibration set only.
5. **Archived category pages are a screenful.** `ikea.com/gb/en/cat/rugs-10653/` is in the
   Wayback Machine from 2019, but products load by script; a capture holds the first ~24.
6. **A backgrounded `grep` over the archive** held a handle on the project folder on Windows
   and blocked renaming it. Stop stray shells before moving directories.

## 6. Expected values (check these)

| quantity | value |
|---|---|
| live product URLs / articles / names (2026-10-13) | 28,699 / 28,699 / 2,439 |
| names ever seen, July 2022 to today | 4,110 |
| cohorts | 2022: 2,378 · 2023: 553 · 2024: 473 · 2025: 347 · 2026 (incl. live-only): 359 |
| quarters in the archive | 17, 2022Q3 to 2026Q4 (no 2026Q3 capture), plus "now" |
| dictionary | 1,362 names: 757 word, 320 place (192 SE, 77 NO, 38 DK, 12 FI, 1 France), 80 boy, 63 girl, 130 unknown, 12 other |
| GeoNames P catch rate on dictionary places | SE 72%, NO 88%, DK 89%, FI 67% |
| Wikidata catch rate | SE 20%, NO 69%, DK 95% |
| SCB tilltalsnamn sheets | 55,193 women's names, 47,312 men's |
| SALDO | 115,850 word forms |
| rugs, Danish places, 2022 vs since | 69/87 (79%) vs 13/136 (10%) |
| same, rugs proper (no door-mat-only names) | 55/68 (81%) vs 9/93 (10%) |
| same, still on sale / no longer sold | 19/25 vs 3/53 · 50/62 vs 10/83 |
| same, Wikidata | 67/87 (77%) vs 13/136 (10%) |
| rug words (SALDO), 2022 vs since | 8% vs 40% |
| curtains, girls' names | 13/78 vs 1/75 |
| chairs, boys' names | 26/78 vs 1/48 |
| chairs, Swedish places | 19/78 vs 34/48 |
| wardrobes, Norwegian places | 19/29 vs 1/8 |
| beds, Norwegian places | 21/50 vs 5/26 |
| lighting, Swedish places | 69/188 vs 5/132 |
| bathroom, Swedish waters | 67/90 vs 28/61 |
| sofas, Swedish places (control) | 39/45 vs 28/33 |
| garden, islands (control) | 63/132 vs 37/80 |
| today's range: sofas SE places | 47/55 (85%), background 17.8% |
| today's range: beds NO places | 30%, rival Swedish places 25% |
| recognisable names | MALM bed: NO place by GeoNames, Swedish word by dictionary · HEMNES: Norwegian place · TOFTLUND: Danish place, rug |

## 7. What the page must say about itself

It does not say IKEA changed policy or when; it says new names follow some rules far less
often. The 2022 cohort is a floor, not a launch date. Britain only. "None of these" is not
proof of anything. The categories are inferred from English descriptions, not IKEA's own.
Translations are the page's own. The dictionary states no licence: ship labels, not
definitions. Not affiliated with IKEA.
