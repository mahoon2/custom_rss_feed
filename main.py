import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from curl_cffi import requests
from rfeed import Feed, Guid, Item
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

TRUST_HEADERS = {
    "Referer": "https://www.google.com/",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass(frozen=True)
class Article:
    title: str
    link: str
    summary: str
    published: Optional[datetime]
    source: str


@dataclass(frozen=True)
class FeedConfig:
    title: str
    description: str
    output_file: str
    link: str
    journal_names: Tuple[str, ...]


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
    JournalConfig(
        name="Molecular Cell",
        url="https://www.cell.com/molecular-cell/newarticles",
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
        name="Nature Cell Biology",
        url="https://www.nature.com/ncb/research-articles",
        base_url="https://www.nature.com",
        include_terms=("research article", "research"),
        exclude_terms=("news & views",),
    ),
    JournalConfig(
        name="Nature Biotechnology",
        url="https://www.nature.com/nbt/research-articles",
        base_url="https://www.nature.com",
        include_terms=("research article", "research"),
        exclude_terms=("news & views",),
    ),
    JournalConfig(
        name="Nature Methods",
        url="https://www.nature.com/nmeth/research-articles",
        base_url="https://www.nature.com",
        include_terms=("research article", "research"),
        exclude_terms=("news & views",),
    ),
    JournalConfig(
        name="Genome Biology",
        url="https://genomebiology.biomedcentral.com/articles",
        base_url="https://genomebiology.biomedcentral.com",
        include_terms=("research",),
        exclude_terms=(),
    ),
    JournalConfig(
        name="Genome Research",
        url="https://genome.cshlp.org/content/current",
        base_url="https://genome.cshlp.org",
        include_terms=("research",),
        exclude_terms=(),
    ),
)

BASE_GITHUB_URL: str = "https://mahoon2.github.io/custom_rss_feed"

FEED_CONFIGS: Tuple[FeedConfig, ...] = (
    FeedConfig(
        title="CNS Feed",
        description="Aggregated research articles from Cell, Nature, and Science.",
        output_file="CNSFeed.xml",
        link=f"{BASE_GITHUB_URL}/CNSFeed.xml",
        journal_names=("Cell", "Nature", "Science"),
    ),
    FeedConfig(
        title="Molecular & Cell Biology Feed",
        description="Aggregated research articles from Nature Cell Biology, Genome Biology, Genome Research, and Molecular Cell.",
        output_file="MolCellFeed.xml",
        link=f"{BASE_GITHUB_URL}/MolCellFeed.xml",
        journal_names=(
            "Nature Cell Biology",
            "Genome Biology",
            "Genome Research",
            "Molecular Cell",
        ),
    ),
    FeedConfig(
        title="Methodology Feed",
        description="Aggregated research articles from Nature Biotechnology and Nature Methods.",
        output_file="MethodFeed.xml",
        link=f"{BASE_GITHUB_URL}/MethodFeed.xml",
        journal_names=("Nature Biotechnology", "Nature Methods"),
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
        formats = (
            "%B %d, %Y",
            "%d %b %Y",
            "%d %B %Y",
            "%B %Y",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
        )
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
    """Extract Science research article data using explicit Research labels."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.card")
    articles: List[Article] = []
    valid_labels = ("research article", "research resource", "short article")

    for card in cards:
        label_tag = card.select_one("span.overline")
        if not label_tag:
            continue
        label_text = text_or_empty(label_tag).lower()
        if not any(term in label_text for term in valid_labels):
            continue

        title_tag = card.select_one("h2.article-title a")
        if not title_tag:
            continue
        summary_tag = card.select_one("ul.card-contribs")
        time_tag = card.select_one("div.card-meta time")
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


def parse_genome_biology(html: str, config: JournalConfig) -> List[Article]:
    """Extract research article data from the Genome Biology articles page."""
    soup = BeautifulSoup(html, "html.parser")
    listing = soup.find(attrs={"data-test": "article-listing"})
    if not listing:
        return []
    date_pattern = re.compile(r"^\d{1,2} \w+ \d{4}$")
    articles: List[Article] = []
    for card in listing.find_all("article", class_="app-card-open"):
        type_tag = card.find("span", class_="c-meta__type")
        if not type_tag or type_tag.get_text(strip=True).lower() != "research":
            continue
        heading = card.find("h2", class_="app-card-open__heading")
        if not heading:
            continue
        link_tag = heading.find("a")
        if not link_tag:
            continue
        date_str: Optional[str] = None
        for item in card.find_all("span", class_="c-meta__item"):
            text = item.get_text(strip=True)
            if date_pattern.match(text):
                date_str = text
                break
        articles.append(
            Article(
                title=text_or_empty(link_tag),
                link=urljoin(config.base_url, link_tag.get("href", "")),
                summary="",
                published=parse_date(date_str),
                source=config.name,
            )
        )
    return articles


def parse_genome_research(html: str, config: JournalConfig) -> List[Article]:
    """Extract research article data from the Genome Research current issue page."""
    soup = BeautifulSoup(html, "html.parser")
    articles: List[Article] = []
    for section in soup.select("div.toc-level.pub-section-Research"):
        for item in section.select("li.toc-cit"):
            title_tag = item.select_one("h4.cit-title-group")
            if not title_tag:
                continue
            link_tag = item.select_one("div.cit-extra a[rel='abstract']")
            if not link_tag:
                continue
            ahead_tag = item.select_one("span.cit-ahead-of-print-date")
            if ahead_tag:
                date_str = " ".join(
                    t.strip()
                    for t in ahead_tag.strings
                    if t.strip() and t.strip() not in ("Published in Advance", ",")
                )
            else:
                print_tag = item.select_one("span.cit-print-date")
                date_str = text_or_empty(print_tag)
            articles.append(
                Article(
                    title=title_tag.get_text(" ", strip=True),
                    link=urljoin(config.base_url, link_tag.get("href", "")),
                    summary="",
                    published=parse_date(date_str),
                    source=config.name,
                )
            )
    return articles


PARSER_MAP = {
    "Cell": parse_cell,
    "Nature": parse_nature,
    "Science": parse_science,
    "Molecular Cell": parse_cell,
    "Nature Cell Biology": parse_nature,
    "Nature Biotechnology": parse_nature,
    "Nature Methods": parse_nature,
    "Genome Biology": parse_genome_biology,
    "Genome Research": parse_genome_research,
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


def main() -> None:
    """Generate RSS feed XML files by scraping configured journals."""
    articles_by_journal: dict[str, List[Article]] = {}
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
