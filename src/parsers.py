import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Dict, List, Optional
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup, Tag

from models import Article, JournalConfig

_HTML_TAG = re.compile(r"<[^>]+>")
_NATURE_RSS_PREFIX = re.compile(r"^<p>.*?</p>", re.DOTALL)


def parse_date(value: Optional[str]) -> Optional[datetime]:
    """Convert assorted date representations into timezone-aware datetime objects."""
    if not value:
        return None
    cleaned = value.strip()

    try:
        parsed = parsedate_to_datetime(cleaned)
        if parsed:
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        pass

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


_CELL_RESEARCH_SECTIONS = frozenset({"Article", "Short article", "Resource"})


def parse_cell_rss(xml: str, config: JournalConfig) -> List[Article]:
    """Extract research articles from Cell's RSS 1.0 (RDF) in-press feed.

    Filters on prism:section to keep only primary research (Article, Short
    article, Resource), excluding Reviews, Perspectives, Editorials, Previews,
    Commentaries, SnapShots, Spotlights, Voices, Stories, and Corrections that
    share the same feed.
    """
    ns = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rss": "http://purl.org/rss/1.0/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "prism": "http://prismstandard.org/namespaces/1.2/basic/",
    }
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    articles: List[Article] = []
    for item in root.findall("rss:item", ns):
        section = (item.findtext("prism:section", namespaces=ns) or "").strip()
        if section not in _CELL_RESEARCH_SECTIONS:
            continue

        title_raw = (
            item.findtext("dc:title", namespaces=ns)
            or item.findtext("rss:title", namespaces=ns)
            or ""
        ).strip()
        title = _HTML_TAG.sub(" ", title_raw).strip()
        link = (item.findtext("rss:link", namespaces=ns) or "").strip()
        summary_raw = item.findtext("rss:description", namespaces=ns) or ""
        summary = _HTML_TAG.sub(" ", summary_raw).strip()
        date_str = (
            item.findtext("dc:date", namespaces=ns)
            or item.findtext("prism:publicationDate", namespaces=ns)
            or ""
        )
        articles.append(
            Article(
                title=title,
                link=link,
                summary=summary,
                published=parse_date(date_str),
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


def parse_nature_rss(html: str, config: JournalConfig) -> List[Article]:
    """Extract article data from Nature's official RSS 1.0 (RDF) feed.

    Nature.com research-article pages now return a JavaScript challenge page
    that cannot be solved by HTTP-only clients. The official RSS feeds remain
    accessible and contain the same article metadata.
    """
    ns = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rss": "http://purl.org/rss/1.0/",
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    try:
        root = ET.fromstring(html)
    except ET.ParseError:
        return []

    _SKIP_PREFIXES = (
        "Author Correction:",
        "Publisher Correction:",
        "Editorial Expression of Concern:",
        "Editorial:",
        "Daily briefing:",
        "Reply to:",
    )

    articles: List[Article] = []
    for item in root.findall("rss:item", ns):
        title_raw = (
            item.findtext("dc:title", namespaces=ns)
            or item.findtext("rss:title", namespaces=ns)
            or ""
        ).strip()
        title = _HTML_TAG.sub(" ", title_raw).strip()
        if any(title.startswith(prefix) for prefix in _SKIP_PREFIXES):
            continue

        creators = item.findall("dc:creator", ns)
        if len(creators) < 2:
            continue

        link = item.findtext("rss:link", namespaces=ns) or ""

        content = item.findtext("content:encoded", namespaces=ns) or ""
        summary_html = _NATURE_RSS_PREFIX.sub("", content).strip()
        summary = _HTML_TAG.sub(" ", summary_html).strip()

        date_str = item.findtext("dc:date", namespaces=ns) or ""
        articles.append(
            Article(
                title=title,
                link=link,
                summary=summary,
                published=parse_date(date_str),
                source=config.name,
            )
        )
    return articles


def parse_science_rss(xml: str, config: JournalConfig) -> List[Article]:
    """Extract Research Articles from Science's official RSS 1.0 (RDF) e-TOC feed.

    Filters on dc:type == 'Research Article' to exclude Perspectives, News,
    Letters, and other non-research content that share the same feed.
    """
    ns = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rss": "http://purl.org/rss/1.0/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    articles: List[Article] = []
    for item in root.findall("rss:item", ns):
        dc_type = (item.findtext("dc:type", namespaces=ns) or "").strip()
        if dc_type != "Research Article":
            continue

        title_raw = (
            item.findtext("dc:title", namespaces=ns)
            or item.findtext("rss:title", namespaces=ns)
            or ""
        ).strip()
        title = _HTML_TAG.sub(" ", title_raw).strip()
        link = item.findtext("rss:link", namespaces=ns) or ""
        date_str = item.findtext("dc:date", namespaces=ns) or ""
        articles.append(
            Article(
                title=title,
                link=link,
                summary="",
                published=parse_date(date_str),
                source=config.name,
            )
        )
    return articles


_OUP_SKIP_PREFIXES = (
    "Correction to",
    "Corrigendum",
    "Editorial",
    "Erratum",
    "Letter to the editor",
    "Retraction",
    "Retraction of",
)


def parse_oup_rss(xml: str, config: JournalConfig) -> List[Article]:
    """Extract articles from OUP's RSS 2.0 feed (used by NAR, Briefings in Bioinformatics).

    OUP RSS lacks dc:creator and dc:type, so non-research items are filtered by
    title prefix instead of by metadata.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    articles: List[Article] = []
    for item in root.findall("./channel/item"):
        title_raw = (item.findtext("title") or "").strip()
        title = _HTML_TAG.sub(" ", title_raw).strip()
        lowered = title.lower()
        if any(lowered.startswith(p.lower()) for p in _OUP_SKIP_PREFIXES):
            continue

        link = (item.findtext("link") or "").strip()
        summary_html = (item.findtext("description") or "").strip()
        summary = _HTML_TAG.sub(" ", summary_html).strip()
        date_str = item.findtext("pubDate") or ""

        articles.append(
            Article(
                title=title,
                link=link,
                summary=summary,
                published=parse_date(date_str),
                source=config.name,
            )
        )
    return articles


PARSER_MAP: Dict[str, Callable[[str, JournalConfig], List[Article]]] = {
    "Cell": parse_cell_rss,
    "Nature": parse_nature_rss,
    "Science": parse_science_rss,
    "Molecular Cell": parse_cell_rss,
    "Nature Cell Biology": parse_nature_rss,
    "Nature Biotechnology": parse_nature_rss,
    "Nature Methods": parse_nature_rss,
    "Genome Biology": parse_genome_biology,
    "Genome Research": parse_genome_research,
    "Nucleic Acids Research": parse_oup_rss,
    "Briefings in Bioinformatics": parse_oup_rss,
}


def parse_journal(html: str, config: JournalConfig) -> List[Article]:
    """Parse the journal page using the CSS-based parser for that journal."""
    parser = PARSER_MAP.get(config.name)
    if not parser:
        return []
    candidates = parser(html, config)
    print(f"Extracted {len(candidates)} entries.")
    filtered = [article for article in candidates if article.title and article.link]
    print(f"Filtered down to {len(filtered)} valid articles.")
    return filtered
