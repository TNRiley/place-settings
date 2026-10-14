# 🪑 Place Settings

**Four in five IKEA rugs on sale in Britain in 2022 were named after a Danish town. Of the 136 rugs launched since, thirteen are.**

→ **[Open it](https://tnriley.github.io/place-settings/)**

The famous IKEA naming rulebook (beds after Norwegian places, rugs after Danish ones, sofas after Swedish towns, curtains after girls, desks after boys) tested rule by rule on all 4,110 product names IKEA has sold in Britain since July 2022, read from its own sitemaps and the Internet Archive's copies of them. Sofas, bathrooms and garden furniture still obey. Rugs do not: the Danish towns stopped during 2023, and since 2024 one new rug in 95 has a Danish name. The replacements are ordinary Swedish nouns, many of them railway and road words: JÄRNVÄG, TIDTABELL, VÄXELFEL. Every instrument (two gazetteers, Statistics Sweden's name register, a Swedish lexicon) was calibrated first on a hand-labelled IKEA dictionary from about 2010, which also shows why matching against every Norwegian feature finds a place called almost anything.

## Running it

One self-contained HTML file. No build step, no server, no network access at runtime — open `index.html` in a browser, or serve the directory with any static host.

```bash
python3 -m http.server 8000   # then visit http://localhost:8000
```

## Rebuilding it from scratch

[REBUILD.md](REBUILD.md) is written for an LLM with a shell and nothing else: the data sources and their quirks, the processing decisions, the page's structure and interactions, and a table of expected values to check the result against.

## Source

The full build pipeline is in [`src/`](src/), with a README describing how to regenerate the page from scratch.

## Data

- **[IKEA en-GB product sitemaps (prod-en-GB_1 to 6): 28,699 product URLs whose slugs carry each product's name and English description, read 2026-10-13. Facts about what is on sale; no IKEA text or image is reproduced.](https://www.ikea.com/sitemaps/sitemap.xml)** — Facts; no IKEA content reproduced
- **[Internet Archive Wayback Machine captures of the same sitemaps, one per file per quarter, July 2022 to October 2026 (103 captures)](https://web.archive.org/web/*/https://www.ikea.com/sitemaps/prod-en-GB_*)** — Archived copies of public pages
- **[GeoNames country dumps for Sweden, Norway, Denmark and Finland](https://download.geonames.org/export/dump/)** — CC BY 4.0
- **[Wikidata: villages, hamlets, towns, cities, settlements, farms and parishes in the four countries, by SPARQL](https://query.wikidata.org/)** — CC0
- **[Statistics Sweden (SCB), first names people go by (tilltalsnamn) with at least two bearers, 31 December 2022](https://www.scb.se/hitta-statistik/statistik-efter-amne/befolkning-och-levnadsforhallanden/ovrigt/namnstatistik/)** — Open data, attribution (SCB)
- **[SALDO, Swedish association lexicon, Språkbanken Text, University of Gothenburg](https://spraakbanken.gu.se/en/resources/saldo)** — CC BY 4.0
- **[The IKEA Dictionary by Lars Petrus (about 2010): 1,362 names hand-labelled as word, boy, girl or place. Only each name's label is used, never the definitions.](https://lar5.com/ikea/)** — No licence stated; labels only

Every figure on the page is computed from the data shipped with it. Check the page's own methods panel for how each number is derived and where it should not be pushed.

## Built with

Python, Wayback Machine CDX, Wikidata SPARQL, vanilla JS, SVG, base64 typed-array payload, in-page permutation tests.

## Licence

Code is MIT (see [LICENSE](LICENSE)). Data keeps the licence of its source, listed above.

---

Part of [Quick Projects](https://github.com/TNRiley/quick-projects) — one self-contained thing, built in one session. First published 2026-10-13.
