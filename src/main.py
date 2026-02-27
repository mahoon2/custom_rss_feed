from pathlib import Path
from typing import Dict, List

from config import FEED_CONFIGS, JOURNAL_CONFIGS
from feed import build_feed
from fetcher import fetch_html
from models import Article
from parsers import parse_journal


def main() -> None:
    """Generate RSS feed XML files by scraping configured journals."""
    articles_by_journal: Dict[str, List[Article]] = {}
    for config in JOURNAL_CONFIGS:
        print(f"Fetching {config.name}...")
        html = fetch_html(config.url)
        articles_by_journal[config.name] = parse_journal(html, config)

    for feed_config in FEED_CONFIGS:
        articles: List[Article] = []
        for journal_name in feed_config.journal_names:
            articles.extend(articles_by_journal.get(journal_name, []))
        feed_content = build_feed(articles, feed_config)
        Path(feed_config.output_file).write_text(feed_content, encoding="utf-8")
        print(f"Wrote {feed_config.output_file} ({len(articles)} articles).")


if __name__ == "__main__":
    main()
