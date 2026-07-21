# Custom Research RSS Feed

Aggregates the latest articles from twenty-two journals into five curated RSS 2.0 feeds, hosted via GitHub Pages.

## Feeds

| Feed | File | Journals |
|---|---|---|
| CNS Feed | `CNSFeed.xml` | Cell, Nature, Science, Science Advances |
| Molecular & Cell Biology Feed | `MolCellFeed.xml` | Molecular Cell, Nature Cell Biology, Nature Communications, Nature Structural & Molecular Biology, RNA |
| Genomics Feed | `GenomicsFeed.xml` | Nature Genetics, Cell Genomics, Genome Biology, Genome Research, Nucleic Acids Research |
| Methodology Feed | `MethodFeed.xml` | Nature Biotechnology, Nature Methods, Briefings in Bioinformatics, Bioinformatics |
| Reviews Feed | `ReviewsFeed.xml` | Nature Reviews Molecular Cell Biology, Nature Reviews Genetics, Trends in Genetics, Trends in Cell Biology |

Subscribe using the raw GitHub Pages URLs:

```
https://mahoon2.github.io/custom_rss_feed/CNSFeed.xml
https://mahoon2.github.io/custom_rss_feed/MolCellFeed.xml
https://mahoon2.github.io/custom_rss_feed/GenomicsFeed.xml
https://mahoon2.github.io/custom_rss_feed/MethodFeed.xml
https://mahoon2.github.io/custom_rss_feed/ReviewsFeed.xml
```

## How it works

`src/main.py` fetches each journal's source, parses it into `Article` objects, and serializes three RSS 2.0 files via `rfeed`. Two parsing strategies are used depending on the publisher:

- **HTML scraping** (Genome Biology, Genome Research, RNA): CSS selectors target article cards on each journal's "current articles" page. Genome Research keeps only the `Research` table-of-contents section; RNA keeps every citation because its table-of-contents sections are all research.
- **RSS 1.0/RDF feed** (Cell, Molecular Cell, Cell Genomics, Trends in Genetics, Trends in Cell Biology, Nature, Nature Cell Biology, Nature Communications, Nature Biotechnology, Nature Methods, Nature Genetics, Nature Structural & Molecular Biology, Nature Reviews Molecular Cell Biology, Nature Reviews Genetics, Science, Science Advances): Official RSS feeds are consumed directly, bypassing JavaScript-rendered pages and Cloudflare challenges. Cell-family research feeds filter by `prism:section` to keep only `Article`, `Short article`, and `Resource` (excluding Reviews, Perspectives, Editorials, Corrections, etc.). Nature research feeds filter non-research items by title prefix and by requiring two or more `dc:creator` tags (single-author entries are typically News or Perspectives). Science and Science Advances e-TOC feeds filter by `dc:type == "Research Article"`.
- **Review feeds**: The Reviews feed uses relaxed filters so review-type content survives. The Trends feeds (Cell family) keep every `prism:section` except editorial and correction notices, and the Nature Reviews feeds admit single-author reviews (requiring only one `dc:creator`).
- **RSS 2.0 feed** (Nucleic Acids Research, Briefings in Bioinformatics, Bioinformatics): OUP's per-issue and advance-access RSS feeds are consumed directly. Because OUP RSS lacks `dc:creator` and `dc:type` fields, non-research items (errata, editorials, letters) are filtered by title prefix.

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

Writes `CNSFeed.xml`, `MolCellFeed.xml`, and `MethodFeed.xml` to the repository root.

## Deployment

`run_and_push.sh` runs the scraper, commits any changed feed files, and pushes to `main`. Schedule it with cron or any task runner:

```bash
./run_and_push.sh
```

GitHub Pages serves the feed files from the `main` branch at the URLs listed above.
