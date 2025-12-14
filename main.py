import json
from dataclasses import dataclass
from datetime import datetime, timezone
from os import getenv
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup
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
        timeout=15,
        allow_redirects=True,
        impersonate="safari15_5",
        headers=TRUST_HEADERS,
    )
    response.raise_for_status()
    return response.text


def extract_json_ld(html: str) -> List[dict]:
    """Collect JSON-LD objects embedded in the page."""
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.select("script[type='application/ld+json']")
    collected: List[dict] = []
    for script in scripts:
        if not script.string:
            continue
        try:
            payload = json.loads(script.string.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            graph = payload.get("@graph")
            if isinstance(graph, list):
                collected.extend(graph)
            main_entity = payload.get("mainEntity")
            if isinstance(main_entity, list):
                collected.extend(main_entity)
            elif isinstance(main_entity, dict):
                collected.append(main_entity)
            collected.append(payload)
        elif isinstance(payload, list):
            collected.extend(payload)
    return collected


def normalize_field(value: Any) -> str:
    """Serialize nested structures into a single string."""
    if isinstance(value, dict):
        return " ".join(normalize_field(subvalue) for subvalue in value.values())
    if isinstance(value, list):
        return " ".join(normalize_field(entry) for entry in value)
    if value is None:
        return ""
    return str(value)


def entry_text(entry: dict) -> str:
    """Build a lowercase token stream for filtering heuristics."""
    fields = (
        "@type",
        "articleSection",
        "articleType",
        "headline",
        "name",
        "genre",
        "keywords",
    )
    text_parts = (normalize_field(entry.get(field)) for field in fields)
    return " ".join(filter(None, text_parts)).lower()


def matches_keywords(text: str, include: Tuple[str, ...], exclude: Tuple[str, ...]) -> bool:
    """Decide whether the candidate text passes the include/exclude lists."""
    has_allowed = not include or any(term in text for term in include)
    has_banned = any(term in text for term in exclude)
    return has_allowed and not has_banned


def best_link(entry: dict, base_url: str) -> Optional[str]:
    """Extract the most reliable URL from the JSON-LD entry."""
    candidates = ("url", "mainEntityOfPage", "sameAs", "identifier")
    for key in candidates:
        candidate = entry.get(key)
        if isinstance(candidate, dict):
            candidate = candidate.get("@id")
        if isinstance(candidate, list):
            candidate = candidate[0]
        if not candidate:
            continue
        url = str(candidate).strip()
        if url:
            return urljoin(base_url, url)
    return None


def parse_date(value: Optional[str]) -> Optional[datetime]:
    """Convert ISO-formatted strings into datetime objects."""
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(normalized, fmt)
            except ValueError:
                continue
    return None


def to_article(entry: dict, config: JournalConfig) -> Optional[Article]:
    """Transform a JSON-LD entry into an Article when it meets filters."""
    text = entry_text(entry)
    if not matches_keywords(text, config.include_terms, config.exclude_terms):
        return None
    title = normalize_field(entry.get("headline") or entry.get("name") or "")
    title = title.strip()
    if not title:
        return None
    link = best_link(entry, config.base_url)
    if not link:
        return None
    summary = normalize_field(entry.get("description") or entry.get("abstract") or "")
    published = parse_date(entry.get("datePublished"))
    return Article(
        title=title,
        link=link,
        summary=summary.strip(),
        published=published,
        source=config.name,
    )


def parse_journal(html: str, config: JournalConfig) -> List[Article]:
    """Parse the JSON-LD footprint for a specific journal feed."""
    entries = extract_json_ld(html)
    return [article for article in (to_article(entry, config) for entry in entries) if article]


def build_feed(articles: Iterable[Article], channel_link: str) -> str:
    """Serialize the list of Article objects into RSS 2.0 XML."""
    unique_links = set()
    sorted_articles = sorted(
        articles,
        key=lambda entry: entry.published or datetime(1970, 1, 1, tzinfo=timezone.utc),
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
                guid=Guid(article.link, permalink=True),
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
    articles = [
        article
        for config in JOURNAL_CONFIGS
        for article in parse_journal(fetch_html(config.url), config)
    ]
    feed_content = build_feed(articles, get_feed_link())
    Path("feed.xml").write_text(feed_content, encoding="utf-8")


if __name__ == "__main__":
    main()
