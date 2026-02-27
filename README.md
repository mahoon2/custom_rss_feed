# Custom Research RSS Feed

Aggregates the latest research articles from nine journals into three curated RSS 2.0 feeds, hosted via GitHub Pages.

## Feeds

| Feed | File | Journals |
|---|---|---|
| CNS Feed | `CNSFeed.xml` | Cell, Nature, Science |
| Molecular & Cell Biology Feed | `MolCellFeed.xml` | Molecular Cell, Nature Cell Biology, Genome Biology, Genome Research |
| Methodology Feed | `MethodFeed.xml` | Nature Biotechnology, Nature Methods |

Subscribe using the raw GitHub Pages URLs:

```
https://mahoon2.github.io/custom_rss_feed/CNSFeed.xml
https://mahoon2.github.io/custom_rss_feed/MolCellFeed.xml
https://mahoon2.github.io/custom_rss_feed/MethodFeed.xml
```

## How it works

`src/main.py` fetches each journal's source, parses it into `Article` objects, and serializes three RSS 2.0 files via `rfeed`. Two parsing strategies are used depending on the publisher:

- **HTML scraping** (Cell, Science, Molecular Cell, Genome Biology, Genome Research): CSS selectors target article cards on each journal's "new articles" or "current issue" page.
- **RSS 1.0/RDF feed** (Nature, Nature Cell Biology, Nature Biotechnology, Nature Methods): Nature's official RSS feeds are consumed directly. This is necessary because `nature.com` pages return a JavaScript proof-of-work challenge that HTTP-only clients cannot solve. Non-research items (corrections, editorials, daily briefings) are filtered by title prefix.

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
