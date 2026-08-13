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
    """Generate RSS feed XML files by scraping configured journals.

    A journal whose primary and fallback sources both fail is skipped rather
    than aborting the run, so one publisher's outage cannot freeze every feed.
    A feed that would come out empty is left untouched instead: an empty file
    would overwrite the last good copy with nothing.
    """
    articles_by_journal: Dict[str, List[Article]] = {}
    failed: List[str] = []
    for config in JOURNAL_CONFIGS:
        print(f"Fetching {config.name}...")
        try:
            articles = fetch_and_parse(config)
        except RuntimeError as error:
            print(f"ERROR: skipping {config.name}: {error}")
            failed.append(config.name)
            continue
        articles_by_journal.setdefault(config.name, []).extend(articles)

    for feed_config in FEED_CONFIGS:
        articles = []
        for journal_name in feed_config.journal_names:
            articles.extend(articles_by_journal.get(journal_name, []))
        if not articles:
            print(
                f"ERROR: {feed_config.output_file} would be empty; leaving it unchanged."
            )
            continue
        feed_content = build_feed(articles, feed_config)
        Path(feed_config.output_file).write_text(feed_content, encoding="utf-8")
        missing = [n for n in feed_config.journal_names if n in failed]
        note = f"; missing {', '.join(missing)}" if missing else ""
        print(f"Wrote {feed_config.output_file} ({len(articles)} articles{note}).")

    if failed:
        print(
            f"\nWARNING: {len(failed)} journal(s) skipped this run: {', '.join(failed)}"
        )


if __name__ == "__main__":
    main()
