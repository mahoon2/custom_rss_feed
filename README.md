# Custom Research RSS Feed

Aggregates the latest articles from twenty-three journals into six curated RSS 2.0 feeds, hosted via GitHub Pages.

## Feeds

| Feed | File | Journals |
|---|---|---|
| CNS Feed | `CNSFeed.xml` | Cell, Nature, Science |
| Molecular & Cell Biology Feed | `MolCellFeed.xml` | Molecular Cell, Nature Cell Biology, Nature Structural & Molecular Biology, The EMBO Journal |
| Megajournal Feed | `MegajournalFeed.xml` | Nature Communications (biological and health sciences only), Science Advances |
| Genomics Feed | `GenomicsFeed.xml` | Nature Genetics, Cell Genomics, Genome Biology, Genome Research, Nucleic Acids Research, RNA |
| Methodology Feed | `MethodFeed.xml` | Nature Biotechnology, Nature Methods, Briefings in Bioinformatics, Bioinformatics |
| Reviews Feed | `ReviewsFeed.xml` | Nature Reviews Molecular Cell Biology, Nature Reviews Genetics, Trends in Genetics, Trends in Cell Biology |

Subscribe using the raw GitHub Pages URLs:

```
https://mahoon2.github.io/custom_rss_feed/CNSFeed.xml
https://mahoon2.github.io/custom_rss_feed/MolCellFeed.xml
https://mahoon2.github.io/custom_rss_feed/MegajournalFeed.xml
https://mahoon2.github.io/custom_rss_feed/GenomicsFeed.xml
https://mahoon2.github.io/custom_rss_feed/MethodFeed.xml
https://mahoon2.github.io/custom_rss_feed/ReviewsFeed.xml
```

## How it works

`src/main.py` fetches each journal's source, parses it into `Article` objects, and serializes six RSS 2.0 files via `rfeed`. Two parsing strategies are used depending on the publisher:

- **HTML scraping** (Genome Biology, Genome Research, RNA, The EMBO Journal): CSS selectors target article cards on each journal's "current/all articles" page. Genome Research groups article cards under section headings and keeps the Research, Methods, and Resource sections; RNA keeps every citation because its table-of-contents sections are all research; Genome Biology and The EMBO Journal share a Springer/BMC card layout and filter by article type (`Research` for Genome Biology; Article, Resource, Method, and Report for The EMBO Journal).
- **Nature current listings with RSS fallback** (Nature Cell Biology, Nature Biotechnology, Nature Methods, Nature Genetics, Nature Structural & Molecular Biology, Nature Reviews Molecular Cell Biology, Nature Reviews Genetics): The primary source is each journal's current article listing, which currently exposes twenty cards and avoids the eight-item cap imposed by the corresponding RSS feeds. The research journals request `type=article`; the Nature Reviews journals retain every card in their current listing. If Nature blocks the listing or returns no cards, the generator falls back to the official RSS endpoint and prints a warning. That fallback is intentionally incomplete.
- **RSS 1.0/RDF feed** (Cell, Molecular Cell, Cell Genomics, Trends in Genetics, Trends in Cell Biology, Nature, Science, Science Advances): Official RSS feeds are consumed directly. Cell-family research feeds filter by `prism:section` to keep only `Article`, `Short article`, and `Resource` (excluding Reviews, Perspectives, Editorials, Corrections, etc.). Nature filters non-research items by title prefix, by requiring two or more `dc:creator` tags (single-author entries are typically News or Perspectives), and by DOI prefix: the feed carries no `prism:section` or `dc:type`, and only `s41586` items are research articles, while News, Career, Editorial, and World View content carries `d41586`. Science and Science Advances e-TOC feeds filter by `dc:type == "Research Article"`.
- **Nature per-subject listings** (Nature Communications): Nature Communications is multidisciplinary, and only about 65% of its output is biological or health science; the rest is condensed-matter physics, catalysis, atmospheric science, and machine learning. Neither its RSS feed nor its main article listing carries a subject anywhere, so `nature.com/subjects/<subject>/ncomms` is the only structural way to separate them. Both `biological-sciences` and `health-sciences` are fetched and unioned: Nature files cancer biology, immunology, and infection under health, so filtering on biology alone drops them. These pages predate the `c-card` layout used elsewhere and are parsed separately, keeping only cards explicitly typed `Article`. No source declares an RSS fallback, because the journal's feed carries every subject and falling back to it would readmit exactly the content this filter removes.

  Each subject is fetched to a depth of `NATURE_SUBJECT_PAGES` pages. A rolling listing silently drops whatever scrolls off before the next snapshot, so its depth must exceed the longest gap between runs: at 50 articles per page, one page of biological sciences holds about three days, and the previous 20-item listing lost 44 of the 88 articles published over one ten-day stretch. Two pages carry seven days of biological sciences against a longest observed gap of six.
- **Review feeds**: The Trends feeds (Cell family) keep every `prism:section` except editorial and correction notices. The Nature Reviews listings keep all current cards, including Review Articles, Journal Club, editorial, correspondence, and Tools of the Trade.
- **RSS 2.0 feed** (Nucleic Acids Research, Briefings in Bioinformatics, Bioinformatics): OUP's current-issue RSS feeds are consumed directly. Because OUP RSS lacks `dc:creator` and `dc:type` fields, non-research items (errata, editorials, letters) are filtered by title prefix. OUP's `advanceAccess_` variants are avoided: they return only a handful of items and go stale (Briefings' advance-access feed still serves 2023 content).

### Journal identity check

Parsers stamp the configured journal name onto every article they extract, so the label is an assumption about the fetched page rather than a fact read from it. Each journal therefore declares a `link_pattern` that an article URL must match, using whatever the publisher encodes journal identity in: a Nature DOI prefix, a `cell.com` path segment, or a dedicated host. Articles failing the pattern are dropped.

This matters most on nature.com, where eight journals share one host and one card layout, so a mis-scoped response is otherwise indistinguishable from a correct one. On 2026-08-13 the Nature Reviews endpoints served a site-wide portfolio listing, and twenty Scientific Reports articles were published under the Nature Reviews Molecular Cell Biology label.

When the check empties a journal's results the generator falls back to that journal's own RSS endpoint, reusing the existing fallback path. If both sources fail, the journal is skipped with an error and the remaining journals still publish, so one publisher's outage cannot freeze every feed. A feed that would come out empty is left unchanged rather than overwritten.

Requests are made with `curl_cffi` (TLS fingerprint impersonation) and retried up to five times on transient HTTP errors.

## Setup

Requires Python 3.12+.

```bash
uv sync          # or: pip install -r requirements.txt
```

## Usage

```bash
python src/main.py
```

Writes `CNSFeed.xml`, `MolCellFeed.xml`, `MegajournalFeed.xml`, `MethodFeed.xml`, `GenomicsFeed.xml`, and `ReviewsFeed.xml` to the repository root.

## Deployment

`run_and_push.sh` runs the scraper, commits any changed feed files, and pushes to `main`. Schedule it with cron or any task runner:

```bash
./run_and_push.sh
```

GitHub Pages serves the feed files from the `main` branch at the URLs listed above.
