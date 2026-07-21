from dataclasses import replace
from pathlib import Path
from typing import Dict, List

from config import FEED_CONFIGS, JOURNAL_CONFIGS
from feed import build_feed
from fetcher import fetch_html
from models import Article, JournalConfig
from parsers import parse_journal


def fetch_and_parse(config: JournalConfig) -> List[Article]:
    """Fetch a primary source, using its configured fallback when necessary."""
    try:
        articles = parse_journal(fetch_html(config.url), config)
    except Exception as error:
        primary_error: Exception | None = error
        articles = []
    else:
        primary_error = None

    if articles:
        return articles
    if not config.fallback_url or not config.fallback_parser_key:
        if primary_error:
            raise RuntimeError(f"Failed to fetch {config.name}") from primary_error
        raise RuntimeError(f"{config.name} returned no valid articles")

    print(f"Warning: {config.name} primary source failed; using capped RSS fallback.")
    fallback_config = replace(
        config,
        url=config.fallback_url,
        parser_key=config.fallback_parser_key,
        fallback_url=None,
        fallback_parser_key=None,
    )
    try:
        fallback_articles = parse_journal(
            fetch_html(fallback_config.url), fallback_config
        )
    except Exception as error:
        raise RuntimeError(f"Failed to fetch {config.name} fallback") from error
    if not fallback_articles:
        raise RuntimeError(f"{config.name} fallback returned no valid articles")
    return fallback_articles


def main() -> None:
    """Generate RSS feed XML files by scraping configured journals."""
    articles_by_journal: Dict[str, List[Article]] = {}
    for config in JOURNAL_CONFIGS:
        print(f"Fetching {config.name}...")
        articles_by_journal.setdefault(config.name, []).extend(fetch_and_parse(config))

    for feed_config in FEED_CONFIGS:
        articles: List[Article] = []
        for journal_name in feed_config.journal_names:
            articles.extend(articles_by_journal.get(journal_name, []))
        feed_content = build_feed(articles, feed_config)
        Path(feed_config.output_file).write_text(feed_content, encoding="utf-8")
        print(f"Wrote {feed_config.output_file} ({len(articles)} articles).")


if __name__ == "__main__":
    main()
