"""Tests for the journal-identity check that gates scraped articles.

Regression cover for the 2026-08-13 incident, in which nature.com served a
site-wide portfolio listing for the Nature Reviews Molecular Cell Biology and
Nature Reviews Genetics endpoints. Both journals were attributed twenty
Scientific Reports articles; the link dedup in build_feed then discarded the
Nature Reviews Genetics copies, removing the journal from the feed entirely.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import JOURNAL_CONFIGS
from main import fetch_and_parse
from models import Article, JournalConfig
from parsers import matches_journal, parse_journal

# Links taken verbatim from the contaminated feed committed as 7456d53.
CONTAMINATED_LINKS = (
    "https://www.nature.com/articles/s41598-026-62801-y",
    "https://www.nature.com/articles/s41599-026-08691-x",
    "https://www.nature.com/articles/s41467-026-76669-z",
)
NRM_LINK = "https://www.nature.com/articles/s41580-026-01005-8"


def _config(name: str) -> JournalConfig:
    """Return the production configuration for a journal by name."""
    return next(config for config in JOURNAL_CONFIGS if config.name == name)


def _article(link: str, source: str) -> Article:
    """Build a minimal article record carrying the given link and label."""
    return Article(title="t", link=link, summary="", published=None, source=source)


class MatchesJournalTests(unittest.TestCase):
    """Verify link-based falsification of a parser's journal attribution."""

    def test_accepts_link_from_the_configured_journal(self) -> None:
        """Accept an article whose DOI prefix belongs to the journal."""
        config = _config("Nature Reviews Molecular Cell Biology")
        self.assertTrue(matches_journal(_article(NRM_LINK, config.name), config))

    def test_rejects_links_from_other_nature_journals(self) -> None:
        """Reject the foreign articles served during the 2026-08-13 incident."""
        config = _config("Nature Reviews Molecular Cell Biology")
        for link in CONTAMINATED_LINKS:
            with self.subTest(link=link):
                self.assertFalse(matches_journal(_article(link, config.name), config))

    def test_reviews_journals_do_not_accept_each_other(self) -> None:
        """Keep the two Nature Reviews journals mutually exclusive.

        Both endpoints returned identical content in the incident, so a shared
        or overlapping pattern would have admitted it under both labels.
        """
        nrm = _config("Nature Reviews Molecular Cell Biology")
        nrg = _config("Nature Reviews Genetics")
        self.assertTrue(matches_journal(_article(NRM_LINK, nrm.name), nrm))
        self.assertFalse(matches_journal(_article(NRM_LINK, nrg.name), nrg))

    def test_unpatterned_journal_is_not_checked(self) -> None:
        """Accept every link when the journal configures no pattern."""
        config = JournalConfig(
            name="Unpatterned",
            url="https://example.test",
            base_url="https://example.test",
            include_terms=(),
            exclude_terms=(),
        )
        self.assertTrue(matches_journal(_article("anything", "Unpatterned"), config))

    def test_every_configured_journal_declares_a_pattern(self) -> None:
        """Require an identity pattern for each configured journal."""
        for config in JOURNAL_CONFIGS:
            with self.subTest(journal=config.name):
                self.assertTrue(config.link_pattern)


class ParseJournalIdentityTests(unittest.TestCase):
    """Verify that parse_journal drops articles failing the identity check."""

    def setUp(self) -> None:
        """Use the production Nature Reviews Molecular Cell Biology config."""
        self.config = _config("Nature Reviews Molecular Cell Biology")

    def _parse_with(self, links: tuple) -> list:
        """Run parse_journal over a stubbed parser returning the given links."""
        parsed = [_article(link, self.config.name) for link in links]
        with patch.dict(
            "parsers.PARSER_MAP", {self.config.parser_key: lambda html, cfg: parsed}
        ):
            return parse_journal("<html/>", self.config)

    def test_returns_empty_when_every_article_is_foreign(self) -> None:
        """Return nothing when the whole response belongs to other journals.

        An empty result is the signal fetch_and_parse already uses to retry the
        journal-scoped fallback, so the guard needs no separate wiring.
        """
        self.assertEqual(self._parse_with(CONTAMINATED_LINKS), [])

    def test_keeps_articles_from_the_configured_journal(self) -> None:
        """Preserve articles that satisfy the journal's identity pattern."""
        kept = self._parse_with((NRM_LINK,))
        self.assertEqual([article.link for article in kept], [NRM_LINK])

    def test_drops_only_the_foreign_articles_in_a_mixed_response(self) -> None:
        """Keep the journal's own articles when a response is partly foreign."""
        kept = self._parse_with((NRM_LINK,) + CONTAMINATED_LINKS)
        self.assertEqual([article.link for article in kept], [NRM_LINK])


class FallbackOnIdentityFailureTests(unittest.TestCase):
    """Verify the identity check hands off to the configured fallback."""

    @patch("main.fetch_html", side_effect=["portfolio listing", "journal rss"])
    def test_contaminated_primary_falls_back_to_journal_rss(
        self, fetch_html: Mock
    ) -> None:
        """Retry the journal-scoped RSS feed after a contaminated listing."""
        config = _config("Nature Reviews Molecular Cell Biology")
        responses = {
            "portfolio listing": [
                _article(link, config.name) for link in CONTAMINATED_LINKS
            ],
            "journal rss": [_article(NRM_LINK, config.name)],
        }
        with patch.dict(
            "parsers.PARSER_MAP",
            {
                config.parser_key: lambda html, cfg: responses[html],
                config.fallback_parser_key: lambda html, cfg: responses[html],
            },
        ):
            articles = fetch_and_parse(config)

        self.assertEqual([article.link for article in articles], [NRM_LINK])
        self.assertEqual(fetch_html.call_count, 2)

    @patch("main.fetch_html", side_effect=["portfolio listing", "portfolio listing"])
    def test_raises_when_fallback_is_contaminated_too(self, fetch_html: Mock) -> None:
        """Raise rather than publish foreign articles under a journal's name.

        main() converts this into a skipped journal so one publisher's outage
        cannot freeze every feed.
        """
        config = _config("Nature Reviews Genetics")
        foreign = [_article(link, config.name) for link in CONTAMINATED_LINKS]
        with patch.dict(
            "parsers.PARSER_MAP",
            {
                config.parser_key: lambda html, cfg: foreign,
                config.fallback_parser_key: lambda html, cfg: foreign,
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "no valid articles"):
                fetch_and_parse(config)


if __name__ == "__main__":
    unittest.main()
