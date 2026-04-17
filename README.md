# Custom Research RSS Feed

Aggregates the latest research articles from eleven journals into three curated RSS 2.0 feeds, hosted via GitHub Pages.

## Feeds

| Feed | File | Journals |
|---|---|---|
| CNS Feed | `CNSFeed.xml` | Cell, Nature, Science |
| Molecular & Cell Biology Feed | `MolCellFeed.xml` | Molecular Cell, Nature Cell Biology, Genome Biology, Genome Research, Nucleic Acids Research |
| Methodology Feed | `MethodFeed.xml` | Nature Biotechnology, Nature Methods, Briefings in Bioinformatics |

Subscribe using the raw GitHub Pages URLs:

```
https://mahoon2.github.io/custom_rss_feed/CNSFeed.xml
https://mahoon2.github.io/custom_rss_feed/MolCellFeed.xml
https://mahoon2.github.io/custom_rss_feed/MethodFeed.xml
```

## How it works

`src/main.py` fetches each journal's source, parses it into `Article` objects, and serializes three RSS 2.0 files via `rfeed`. Two parsing strategies are used depending on the publisher:

- **HTML scraping** (Genome Biology, Genome Research): CSS selectors target article cards on each journal's "current articles" page.
- **RSS 1.0/RDF feed** (Cell, Molecular Cell, Nature, Nature Cell Biology, Nature Biotechnology, Nature Methods, Science): Official RSS feeds are consumed directly, bypassing JavaScript-rendered pages and Cloudflare challenges. Cell-family in-press feeds filter by `prism:section` to keep only `Article`, `Short article`, and `Resource` (excluding Reviews, Perspectives, Editorials, Corrections, etc.). Nature feeds filter non-research items by title prefix and by requiring two or more `dc:creator` tags (single-author entries are typically News or Perspectives). Science's e-TOC feed filters by `dc:type == "Research Article"`.
- **RSS 2.0 feed** (Nucleic Acids Research, Briefings in Bioinformatics): OUP's per-issue RSS feeds are consumed directly. Because OUP RSS lacks `dc:creator` and `dc:type` fields, non-research items (errata, editorials, letters) are filtered by title prefix.

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
