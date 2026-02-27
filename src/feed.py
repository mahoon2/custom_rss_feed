from datetime import datetime, timezone
from typing import Iterable, List, Optional

from rfeed import Feed, Guid, Item

from models import Article, FeedConfig


def ensure_timezone(value: Optional[datetime]) -> datetime:
    """Normalize datetimes to UTC so they can be compared safely."""
    fallback = datetime(1970, 1, 1, tzinfo=timezone.utc)
    if not value:
        return fallback
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def build_feed(articles: Iterable[Article], feed_config: FeedConfig) -> str:
    """Serialize the list of Article objects into RSS 2.0 XML."""
    unique_links = set()
    sorted_articles = sorted(
        articles,
        key=lambda entry: ensure_timezone(entry.published),
        reverse=True,
    )
    items: List[Item] = []
    for article in sorted_articles:
        if article.link in unique_links:
            continue
        unique_links.add(article.link)
        items.append(
            Item(
                title=f"{article.source}: {article.title}",
                link=article.link,
                description=article.summary,
                guid=Guid(article.link, isPermaLink=True),
                pubDate=article.published,
            )
        )
    feed = Feed(
        title=feed_config.title,
        link=feed_config.link,
        description=feed_config.description,
        language="en-US",
        items=items,
    )
    return feed.rss()
