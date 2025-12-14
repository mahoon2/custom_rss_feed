# Custom Research RSS Feed

This repository scrapes the latest research articles from **Cell**, **Nature**, and **Science** and generates a curated RSS feed that only contains published research articles.

## Features
- Functional Python pipeline that parses JSON-LD metadata to find article title, link, abstract, and publication date.
- Journal-specific include/exclude filters to drop news, editorials, perspectives, letters, and other non-research content.
- RSS serialization via `rfeed` produces a `feed.xml` ready for hosting through GitHub Pages (or any static file host).
- GitHub Actions workflow keeps the feed refreshed once per day by running the scraper and pushing `feed.xml` to the `gh-pages` branch.

## Setup
1. Activate the provided virtual environment or create your own with Python 3.9+.
2. Use `uv sync` or `pip install -r requirements.txt` to install dependencies.
3. Run `python main.py` to produce/refresh `feed.xml`.

## Deployment
Enable GitHub Pages on the `gh-pages` branch after the workflow commits `feed.xml`. The published raw feed URL can then be used in any RSS reader.
