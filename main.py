from dataclasses import dataclass
from datetime import datetime, timezone
from os import getenv
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from curl_cffi import requests
from rfeed import Feed, Guid, Item
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

DEFAULT_FEED_LINK = "https://github.com/qbio/mahoon2"

TRUST_HEADERS = {
    "Referer": "https://www.google.com/",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_feed_link() -> str:
    """Return the configured channel link for the RSS feed."""
    return getenv("FEED_LINK", DEFAULT_FEED_LINK)


@dataclass(frozen=True)
class Article:
    title: str
    link: str
    summary: str
    published: Optional[datetime]
    source: str


@dataclass(frozen=True)
class JournalConfig:
    name: str
    url: str
    base_url: str
    include_terms: Tuple[str, ...]
    exclude_terms: Tuple[str, ...]


JOURNAL_CONFIGS: Tuple[JournalConfig, ...] = (
    JournalConfig(
        name="Cell",
        url="https://www.cell.com/cell/newarticles",
        base_url="https://www.cell.com",
        include_terms=("research article", "article"),
        exclude_terms=(
            "news",
            "editorial",
            "briefing",
            "ahead of print",
            "perspective",
            "pre-proof",
        ),
    ),
    JournalConfig(
        name="Nature",
        url="https://www.nature.com/nature/research-articles",
        base_url="https://www.nature.com",
        include_terms=("research article", "research"),
        exclude_terms=("news & views",),
    ),
    JournalConfig(
        name="Science",
        url="https://www.science.org/journal/science/research",
        base_url="https://www.science.org",
        include_terms=("research article", "research"),
        exclude_terms=("perspective", "books", "policy forum", "letter", "news"),
    ),
)


def is_transient_error(exception: Exception) -> bool:
    """Determine whether an exception should trigger a retry."""
    if isinstance(exception, requests.exceptions.HTTPError):
        response = exception.response
        if response and response.status_code in {403, 503}:
            return True
    return False


@retry(
    retry=retry_if_exception(is_transient_error),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(5),
)
def fetch_html(url: str) -> str:
    """Retrieve the HTML body for a provided URL."""
    response = requests.get(
        url,
        timeout=30,
        allow_redirects=True,
        impersonate="safari15_5",
        headers=TRUST_HEADERS,
    )
    response.raise_for_status()
    return response.text


def parse_date(value: Optional[str]) -> Optional[datetime]:
    """Convert assorted date representations into timezone-aware datetime objects."""
    if not value:
        return None
    cleaned = value.strip()
    if ":" in cleaned and not cleaned.startswith("20"):
        parts = cleaned.split(":", 1)
        cleaned = parts[1].strip() if len(parts) > 1 else parts[0].strip()
    iso_candidate = cleaned.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_candidate)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        formats = ("%B %d, %Y", "%d %b %Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S")
        for fmt in formats:
            try:
                return datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def text_or_empty(tag: Optional[Tag]) -> str:
    """Return the stripped text of a tag or an empty string."""
    return tag.get_text(" ", strip=True) if tag else ""


def parse_nature(html: str, config: JournalConfig) -> List[Article]:
    """Extract article data from the Nature research page."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article.c-card")
    articles: List[Article] = []
    for card in cards:
        title_tag = card.select_one("h3.c-card__title a")
        if not title_tag:
            continue
        summary_tag = card.select_one('div[data-test="article-description"] p')
        time_tag = card.select_one('time[itemprop="datePublished"]')
        published = (
            parse_date(time_tag.get("datetime"))
            if time_tag and time_tag.get("datetime")
            else parse_date(text_or_empty(time_tag))
        )
        articles.append(
            Article(
                title=text_or_empty(title_tag),
                link=urljoin(config.base_url, title_tag.get("href", "")),
                summary=text_or_empty(summary_tag),
                published=published,
                source=config.name,
            )
        )
    return articles


def parse_science(html: str, config: JournalConfig) -> List[Article]:
    """Extract article data from the Science research page."""
    soup = BeautifulSoup(html, "html.parser")
    containers = soup.select("div.card-content, article.card-do")
    articles: List[Article] = []

    def choose_title(container: Tag) -> Optional[Tag]:
        """Return the most likely title link."""
        return container.select_one("h3.article-title a") or container.select_one(
            "div.card__title a"
        )

    for container in containers:
        title_element = choose_title(container)
        if not title_element:
            continue
        summary_source = container.select_one("ul.card-contribs")
        time_element = container.select_one("span.card-meta__item time")
        published = (
            parse_date(time_element.get("datetime"))
            if time_element and time_element.get("datetime")
            else parse_date(text_or_empty(time_element))
        )
        articles.append(
            Article(
                title=text_or_empty(title_element),
                link=urljoin(config.base_url, title_element.get("href", "")),
                summary=text_or_empty(summary_source),
                published=published,
                source=config.name,
            )
        )
    return articles


def parse_cell(html: str, config: JournalConfig) -> List[Article]:
    """Extract article data from the Cell new articles page."""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.toc__item")
    articles: List[Article] = []
    for item in items:
        title_tag = item.select_one("h3.toc__item__title a")
        if not title_tag:
            continue
        summary_tag = item.select_one("div.toc__item__brief")
        date_tag = item.select_one("div.toc__item__date")
        published = parse_date(text_or_empty(date_tag))
        articles.append(
            Article(
                title=text_or_empty(title_tag),
                link=urljoin(config.base_url, title_tag.get("href", "")),
                summary=text_or_empty(summary_tag),
                published=published,
                source=config.name,
            )
        )
    return articles


PARSER_MAP = {
    "Cell": parse_cell,
    "Nature": parse_nature,
    "Science": parse_science,
}


def parse_journal(html: str, config: JournalConfig) -> List[Article]:
    """Parse the journal page using the CSS-based parser for that journal."""
    parser = PARSER_MAP.get(config.name)
    if not parser:
        return []
    candidates = parser(html, config)
    print(f"Extracted {len(candidates)} JSON-LD entries.")
    filtered = [article for article in candidates if article.title and article.link]
    print(f"Filtered down to {len(filtered)} valid articles.")
    return filtered


def ensure_timezone(value: Optional[datetime]) -> datetime:
    """Normalize datetimes to UTC so they can be compared safely."""
    fallback = datetime(1970, 1, 1, tzinfo=timezone.utc)
    if not value:
        return fallback
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def build_feed(articles: Iterable[Article], channel_link: str) -> str:
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
        title="Custom Biological Research Feed",
        link=channel_link,
        description="Aggregated research articles from Cell, Nature, and Science.",
        language="en-US",
        lastBuildDate=datetime.now(timezone.utc),
        items=items,
    )
    return feed.rss()


def main() -> None:
    """Generate feed.xml by scraping configured journals."""
    articles: List[Article] = []
    for config in JOURNAL_CONFIGS:
        print(f"Fetching {config.name}...")
        html = fetch_html(config.url)
        articles.extend(parse_journal(html, config))
    feed_content = build_feed(articles, get_feed_link())
    Path("feed.xml").write_text(feed_content, encoding="utf-8")


if __name__ == "__main__":
    main()
