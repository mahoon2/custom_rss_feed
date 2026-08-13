import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Dict, List, Optional, Tuple
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


def attr_or_empty(tag: Tag, name: str) -> str:
    """Return a string attribute value or an empty string."""
    value = tag.get(name, "")
    return value if isinstance(value, str) else ""


def parse_nature(html: str, config: JournalConfig) -> List[Article]:
    """Extract every card from a Nature journal listing page."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article.c-card")
    return _parse_nature_cards(cards, config)


def parse_nature_article_listing(html: str, config: JournalConfig) -> List[Article]:
    """Extract only cards explicitly labelled as Nature research Articles."""
    soup = BeautifulSoup(html, "html.parser")
    cards = [
        card
        for card in soup.select("article.c-card")
        if text_or_empty(card.select_one("span.c-meta__type")) == "Article"
    ]
    return _parse_nature_cards(cards, config)


def parse_nature_subject_listing(html: str, config: JournalConfig) -> List[Article]:
    """Extract research Articles from a nature.com per-subject journal listing.

    Multidisciplinary journals publish far outside this project's scope: about
    65% of Nature Communications and 48% of Nature is biological or health
    science, the rest being condensed-matter physics, astronomy, catalysis,
    atmospheric science, and machine learning. Nature's own subject taxonomy is
    the only structural way to separate them, and it lives on
    ``/subjects/<subject>/<journal>`` rather than in any feed or on the main
    listing, whose cards carry no subject at all.

    These pages predate the ``c-card`` layout used elsewhere, so the markup is
    matched separately. Cards are kept only when explicitly typed ``Article``,
    which drops the Comment and Review Article entries these listings mix in.
    """
    soup = BeautifulSoup(html, "html.parser")
    articles: List[Article] = []
    for card in soup.find_all("article"):
        type_tag = card.select_one('span[data-test="article.type"]')
        if not type_tag or type_tag.get_text(strip=True) != "Article":
            continue
        title_tag = card.select_one('h3 a[href^="/articles/"]')
        if not title_tag:
            continue
        time_tag = card.select_one('time[itemprop="datePublished"]')
        summary_tag = card.select_one('div[itemprop="description"] p')
        articles.append(
            Article(
                title=text_or_empty(title_tag),
                link=urljoin(config.base_url, attr_or_empty(title_tag, "href")),
                summary=text_or_empty(summary_tag),
                published=parse_date(attr_or_empty(time_tag, "datetime"))
                if time_tag
                else None,
                source=config.name,
            )
        )
    return articles


def _parse_nature_cards(cards: List[Tag], config: JournalConfig) -> List[Article]:
    """Convert selected Nature listing cards into article records."""
    articles: List[Article] = []
    for card in cards:
        title_tag = card.select_one("h3.c-card__title a")
        if not title_tag:
            continue
        summary_tag = card.select_one('div[data-test="article-description"] p')
        time_tag = card.select_one('time[itemprop="datePublished"]')
        datetime_value = attr_or_empty(time_tag, "datetime") if time_tag else ""
        published = (
            parse_date(datetime_value)
            if datetime_value
            else parse_date(text_or_empty(time_tag))
        )
        articles.append(
            Article(
                title=text_or_empty(title_tag),
                link=urljoin(config.base_url, attr_or_empty(title_tag, "href")),
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
        datetime_value = attr_or_empty(time_tag, "datetime") if time_tag else ""
        published = (
            parse_date(datetime_value)
            if datetime_value
            else parse_date(text_or_empty(time_tag))
        )
        articles.append(
            Article(
                title=text_or_empty(title_tag),
                link=urljoin(config.base_url, attr_or_empty(title_tag, "href")),
                summary=text_or_empty(summary_tag),
                published=published,
                source=config.name,
            )
        )
    return articles


_CELL_RESEARCH_SECTIONS = frozenset({"Article", "Short article", "Resource"})
_CELL_REVIEW_SKIP_SECTIONS = frozenset(
    {"Editorial", "Correction", "Erratum", "Retraction", "Preview"}
)


def _parse_cell_rss(
    xml: str, config: JournalConfig, keep_section: Callable[[str], bool]
) -> List[Article]:
    """Extract items from a Cell-family RSS 1.0 (RDF) feed.

    keep_section decides which prism:section values to include, letting the same
    parser serve research feeds (an allow-list) and review feeds (a skip-list).
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
        if not keep_section(section):
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


def parse_cell_rss(xml: str, config: JournalConfig) -> List[Article]:
    """Extract research articles from a Cell-family in-press RSS feed.

    Keeps only primary research (Article, Short article, Resource), excluding
    Reviews, Perspectives, Editorials, Previews, Commentaries, and Corrections
    that share the same feed.
    """
    return _parse_cell_rss(
        xml, config, lambda section: section in _CELL_RESEARCH_SECTIONS
    )


def parse_cell_review_rss(xml: str, config: JournalConfig) -> List[Article]:
    """Extract review content from a Cell-family feed (e.g. Trends journals).

    Keeps every section (Review, Feature Review, Opinion, Forum, Spotlight,
    Science & Society, ...) except editorial and correction notices.
    """
    return _parse_cell_rss(
        xml, config, lambda section: section not in _CELL_REVIEW_SKIP_SECTIONS
    )


def _parse_springer_listing(
    html: str, config: JournalConfig, keep_type: Callable[[str], bool]
) -> List[Article]:
    """Extract article cards from a Springer/BMC 'all articles' listing page.

    keep_type decides which c-meta__type values to include, letting the same
    scraper serve Genome Biology (BMC) and The EMBO Journal (link.springer.com).
    """
    soup = BeautifulSoup(html, "html.parser")
    listing = soup.find(attrs={"data-test": "article-listing"})
    if not listing:
        return []
    date_pattern = re.compile(r"^\d{1,2} \w+ \d{4}$")
    articles: List[Article] = []
    for card in listing.find_all("article", class_="app-card-open"):
        type_tag = card.find("span", class_="c-meta__type")
        if not type_tag or not keep_type(type_tag.get_text(strip=True)):
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
                link=urljoin(config.base_url, attr_or_empty(link_tag, "href")),
                summary="",
                published=parse_date(date_str),
                source=config.name,
            )
        )
    return articles


_EMBO_RESEARCH_TYPES = frozenset(
    {"Article", "Resource", "Method", "Report", "Short Report"}
)


def parse_genome_biology(html: str, config: JournalConfig) -> List[Article]:
    """Extract research article data from the Genome Biology articles page."""
    return _parse_springer_listing(html, config, lambda t: t.lower() == "research")


def parse_embo(html: str, config: JournalConfig) -> List[Article]:
    """Extract research articles from The EMBO Journal articles page (Springer).

    Keeps primary research types (Article, Resource, Method, Report), excluding
    Author Corrections, Comments, Reviews, Perspectives, and Obituaries.
    """
    return _parse_springer_listing(html, config, lambda t: t in _EMBO_RESEARCH_TYPES)


def _cshl_toc_date(item: Tag) -> str:
    """Extract the publication date string from a CSHL/HighWire TOC citation."""
    ahead_tag = item.select_one("span.cit-ahead-of-print-date")
    if ahead_tag:
        return " ".join(
            t.strip()
            for t in ahead_tag.strings
            if t.strip() and t.strip() not in ("Published in Advance", ",")
        )
    print_tag = item.select_one("span.cit-print-date")
    return text_or_empty(print_tag)


_GENOME_RESEARCH_SECTIONS = frozenset(
    {"Research", "Methods", "Resource", "Report", "Article"}
)


def parse_genome_research(html: str, config: JournalConfig) -> List[Article]:
    """Extract research article data from the Genome Research current issue page.

    The redesigned issue page groups article cards under <h3> section headings
    (Perspective, Research, Methods, Resource, Corrigenda); each card's nearest
    preceding heading is its section, and only primary research sections are
    kept.
    """
    soup = BeautifulSoup(html, "html.parser")
    articles: List[Article] = []
    for card in soup.select("article.article-section"):
        heading = card.find_previous("h3")
        section = heading.get_text(" ", strip=True) if heading else ""
        if section not in _GENOME_RESEARCH_SECTIONS:
            continue
        link_tag = card.select_one("h5.title a.title") or card.select_one("a.title")
        if not link_tag:
            continue
        date_tag = card.select_one("span.card-citation-value")
        articles.append(
            Article(
                title=link_tag.get_text(" ", strip=True),
                link=urljoin(config.base_url, attr_or_empty(link_tag, "href")),
                summary="",
                published=parse_date(text_or_empty(date_tag)),
                source=config.name,
            )
        )
    return articles


def parse_rna(html: str, config: JournalConfig) -> List[Article]:
    """Extract research articles from the RNA journal current issue page.

    RNA is on the same CSHL/HighWire platform as Genome Research, but its TOC
    sections are all research (Communications, RNA and Gene Expression, ...), so
    every citation is kept, and the article link is the full-text anchor rather
    than an abstract anchor.
    """
    soup = BeautifulSoup(html, "html.parser")
    articles: List[Article] = []
    for item in soup.select("li.toc-cit"):
        title_tag = item.select_one("h4.cit-title-group")
        if not title_tag:
            continue
        link_tag = item.select_one("div.cit-extra a[rel='full-text']")
        if not link_tag:
            continue
        articles.append(
            Article(
                title=title_tag.get_text(" ", strip=True),
                link=urljoin(config.base_url, attr_or_empty(link_tag, "href")),
                summary="",
                published=parse_date(_cshl_toc_date(item)),
                source=config.name,
            )
        )
    return articles


_NATURE_SKIP_PREFIXES = (
    "Author Correction:",
    "Publisher Correction:",
    "Editorial Expression of Concern:",
    "Editorial:",
    "Daily briefing:",
    "Reply to:",
)


def _parse_nature_rss(
    html: str, config: JournalConfig, min_creators: int
) -> List[Article]:
    """Extract article data from Nature's official RSS 1.0 (RDF) feed.

    Nature.com research-article pages now return a JavaScript challenge page
    that cannot be solved by HTTP-only clients. The official RSS feeds remain
    accessible and contain the same article metadata. min_creators is the
    minimum dc:creator count required to keep an item: research feeds use two
    (single-author entries are typically News & Views), while review feeds use
    one to admit single-author reviews.
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

    articles: List[Article] = []
    for item in root.findall("rss:item", ns):
        title_raw = (
            item.findtext("dc:title", namespaces=ns)
            or item.findtext("rss:title", namespaces=ns)
            or ""
        ).strip()
        title = _HTML_TAG.sub(" ", title_raw).strip()
        if any(title.startswith(prefix) for prefix in _NATURE_SKIP_PREFIXES):
            continue

        creators = item.findall("dc:creator", ns)
        if len(creators) < min_creators:
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


def parse_nature_rss(html: str, config: JournalConfig) -> List[Article]:
    """Extract research articles from a Nature-family RSS feed.

    Requires two or more dc:creator tags, since single-author entries are
    typically News & Views or other non-research content.
    """
    return _parse_nature_rss(html, config, min_creators=2)


def parse_nature_review_rss(html: str, config: JournalConfig) -> List[Article]:
    """Extract content from a Nature Reviews RSS feed.

    Keeps single-author reviews (min_creators=1) while still dropping the
    correction and editorial notices handled by the shared skip-prefix filter.
    """
    return _parse_nature_rss(html, config, min_creators=1)


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


def _parse_rss2(
    xml: str, config: JournalConfig, skip_prefixes: Tuple[str, ...]
) -> List[Article]:
    """Extract articles from a plain RSS 2.0 feed.

    Used for feeds that carry no dc:creator or dc:type metadata, so non-research
    items can only be filtered by title prefix. Prefix matching is case-insensitive.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    lowered_prefixes = tuple(prefix.lower() for prefix in skip_prefixes)
    articles: List[Article] = []
    for item in root.findall("./channel/item"):
        title_raw = (item.findtext("title") or "").strip()
        title = _HTML_TAG.sub(" ", title_raw).strip()
        if title.lower().startswith(lowered_prefixes):
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


def parse_oup_rss(xml: str, config: JournalConfig) -> List[Article]:
    """Extract articles from OUP's RSS 2.0 feed (used by NAR, Briefings, Bioinformatics).

    OUP RSS lacks dc:creator and dc:type, so non-research items are filtered by
    title prefix instead of by metadata.
    """
    return _parse_rss2(xml, config, _OUP_SKIP_PREFIXES)


PARSER_MAP: Dict[str, Callable[[str, JournalConfig], List[Article]]] = {
    "nature_html": parse_nature,
    "nature_article_html": parse_nature_article_listing,
    "nature_subject_html": parse_nature_subject_listing,
    "nature_rss": parse_nature_rss,
    "nature_review_rss": parse_nature_review_rss,
    "Cell": parse_cell_rss,
    "Science": parse_science_rss,
    "Molecular Cell": parse_cell_rss,
    "Nature Cell Biology": parse_nature_rss,
    "Nature Biotechnology": parse_nature_rss,
    "Nature Methods": parse_nature_rss,
    "Genome Biology": parse_genome_biology,
    "Genome Research": parse_genome_research,
    "Nucleic Acids Research": parse_oup_rss,
    "Briefings in Bioinformatics": parse_oup_rss,
    "Bioinformatics": parse_oup_rss,
    "Nature Genetics": parse_nature_rss,
    "Nature Structural & Molecular Biology": parse_nature_rss,
    "Cell Genomics": parse_cell_rss,
    "Science Advances": parse_science_rss,
    "RNA": parse_rna,
    "Nature Reviews Molecular Cell Biology": parse_nature_review_rss,
    "Nature Reviews Genetics": parse_nature_review_rss,
    "Trends in Genetics": parse_cell_review_rss,
    "Trends in Cell Biology": parse_cell_review_rss,
    "The EMBO Journal": parse_embo,
}


def matches_journal(article: Article, config: JournalConfig) -> bool:
    """Whether an article link is consistent with the journal it is attributed to.

    Parsers stamp source=config.name onto every card they find, so the label is
    an assumption about the fetched page rather than a fact read from it. The
    link is the one field that can falsify that assumption: publishers encode
    journal identity in the URL (a Nature DOI prefix, a cell.com path segment,
    a dedicated host). Journals with no configured pattern are not checked.
    """
    if not config.link_pattern:
        return True
    return re.search(config.link_pattern, article.link) is not None


def report_identity_check(config: JournalConfig, total: int, rejected: int) -> None:
    """Report the outcome of the journal-identity check for one fetch.

    Rejection is bimodal in practice: 22 of 23 journals reject nothing on a
    healthy run, while Nature rejects its d41586 news items on every run. A
    per-run warning for the routine case would train the reader to skim past
    the line that matters, so only a total rejection is raised to ERROR. That
    is also the only outcome that changes behaviour, since it leaves the caller
    with nothing and triggers the fallback or skips the journal.
    """
    if not rejected:
        return
    if rejected == total:
        print(
            f"ERROR: all {total} {config.name} entries failed the identity check "
            f"(expected links matching {config.link_pattern!r})."
        )
    else:
        print(f"Rejected {rejected}/{total} entries not identifying as {config.name}.")


def parse_journal(html: str, config: JournalConfig) -> List[Article]:
    """Parse the journal page using the CSS-based parser for that journal.

    Articles whose link contradicts the journal's identity pattern are dropped.
    When every article is dropped the caller sees an empty list, which is the
    signal fetch_and_parse already uses to retry the journal-scoped fallback.
    """
    parser = PARSER_MAP.get(config.parser_key or config.name)
    if not parser:
        return []
    candidates = parser(html, config)
    print(f"Extracted {len(candidates)} entries.")
    filtered = [article for article in candidates if article.title and article.link]
    print(f"Filtered down to {len(filtered)} valid articles.")
    verified = [article for article in filtered if matches_journal(article, config)]
    report_identity_check(config, len(filtered), len(filtered) - len(verified))
    return verified
