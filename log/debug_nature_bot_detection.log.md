# Nature.com Bot Detection Debugging Log

## Problem

`MethodFeed.xml` contained no entries. All Nature-hosted journals
(`Nature`, `Nature Cell Biology`, `Nature Biotechnology`, `Nature Methods`)
extracted 0 articles per run.

## Root Cause

Nature.com began returning a JavaScript proof-of-work challenge page instead
of actual HTML content. The response is a 3099-byte page with:

- `<title>Client Challenge</title>`
- Bot-detection assets under `/_fs-ch-1T1wmsGaOgGaSxcX/` (Fingerprint-style)
- A requirement to execute JavaScript to prove the client is a real browser

`curl_cffi` impersonates the TLS/HTTP fingerprint of a real browser but cannot
execute JavaScript. All tested profiles produced the same challenge page:
`chrome131`, `chrome133a`, `chrome136`, `safari260`, `safari184`, `firefox135`.

## Diagnostic Commands

### 1. Fetch HTML pages and inspect

```bash
source .venv/bin/activate && cd src && python3 - <<'EOF'
from fetcher import fetch_html

for journal, url in [
    ("nbt", "https://www.nature.com/nbt/research-articles"),
    ("nmeth", "https://www.nature.com/nmeth/research-articles"),
]:
    html = fetch_html(url)
    with open(f"../log/debug_{journal}.html", "w") as f:
        f.write(html)
    print(f"{journal}: {len(html)} bytes, challenge={'Client Challenge' in html}")
EOF
```

All returned 3099 bytes with `challenge=True`.

### 2. Test all curl_cffi impersonation profiles

```bash
python3 -c "from curl_cffi import BrowserType; print([b.value for b in BrowserType])"
```

Tried: `chrome131`, `chrome133a`, `chrome136`, `safari260`, `safari184`,
`firefox135`, `safari17_0`, `safari18_0` — all returned the challenge page.

### 3. Test official RSS feeds

```bash
python3 - <<'EOF'
from curl_cffi import requests
# Test https://www.nature.com/nbt.rss, https://www.nature.com/nmeth.rss, etc.
EOF
```

RSS feeds returned full content (15–126 KB), no challenge.

## Fix Applied

Switched all four Nature journals from scraping the `research-articles` HTML
page to consuming the official RSS 1.0 (RDF) feeds:

| Journal               | Old URL (broken)                                 | New URL                           |
|-----------------------|--------------------------------------------------|-----------------------------------|
| Nature                | `https://www.nature.com/nature/research-articles`| `https://www.nature.com/nature.rss` |
| Nature Cell Biology   | `https://www.nature.com/ncb/research-articles`   | `https://www.nature.com/ncb.rss`  |
| Nature Biotechnology  | `https://www.nature.com/nbt/research-articles`   | `https://www.nature.com/nbt.rss`  |
| Nature Methods        | `https://www.nature.com/nmeth/research-articles` | `https://www.nature.com/nmeth.rss`|

Added `parse_nature_rss` in `src/parsers.py` to handle the RSS 1.0/RDF format
(namespaces `rss:`, `dc:`, `content:`). Also filters out "Author Correction:"
and "Publisher Correction:" items, which appear in the RSS but are not
research articles.

## Result

```
Fetching Nature Biotechnology...   Extracted 8 entries.
Fetching Nature Methods...         Extracted 7 entries.
Wrote MethodFeed.xml (15 articles).
```
