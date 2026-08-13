from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple


@dataclass(frozen=True)
class Article:
    """A single journal article scraped from a publisher's website."""

    title: str
    link: str
    summary: str
    published: Optional[datetime]
    source: str


@dataclass(frozen=True)
class FeedConfig:
    """Static configuration for one output RSS feed."""

    title: str
    description: str
    output_file: str
    link: str
    journal_names: Tuple[str, ...]


@dataclass(frozen=True)
class JournalConfig:
    """Static configuration for fetching and filtering one journal."""

    name: str
    url: str
    base_url: str
    include_terms: Tuple[str, ...]
    exclude_terms: Tuple[str, ...]
    parser_key: Optional[str] = None
    fallback_url: Optional[str] = None
    fallback_parser_key: Optional[str] = None
    link_pattern: Optional[str] = None
    """Regex an article link must match to be attributed to this journal.

    Publishers encode journal identity in the article URL (a Nature DOI prefix,
    a cell.com path segment, a dedicated host), so the link is the one field
    that can falsify the journal label a parser would otherwise assume. None
    disables the check.
    """
