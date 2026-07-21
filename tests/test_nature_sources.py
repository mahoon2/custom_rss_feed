"""Tests for Nature listing extraction and RSS fallback behavior."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import NATURE_ARTICLE_LISTING_CONFIGS
from main import fetch_and_parse
from models import Article, JournalConfig
from parsers import parse_nature, parse_nature_article_listing


class NatureSourceTests(unittest.TestCase):
    """Verify Nature's current-listing source strategy."""

    def setUp(self) -> None:
        """Create a representative direct-listing configuration."""
        self.config = JournalConfig(
            name="Nature Methods",
            url="https://example.test/articles?type=article",
            base_url="https://example.test",
            include_terms=(),
            exclude_terms=(),
            parser_key="nature_html",
            fallback_url="https://example.test/feed.rss",
            fallback_parser_key="nature_rss",
        )
        self.article = Article(
            title="Primary result",
            link="https://example.test/articles/primary",
            summary="Summary",
            published=None,
            source="Nature Methods",
        )

    def test_parse_nature_extracts_listing_card(self) -> None:
        """Extract a complete article record from a Nature listing card."""
        html = """
        <article class="c-card">
          <h3 class="c-card__title"><a href="/articles/example">Example title</a></h3>
          <div data-test="article-description"><p>Example summary.</p></div>
          <time itemprop="datePublished" datetime="2026-07-21">21 July 2026</time>
        </article>
        """

        articles = parse_nature(html, self.config)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Example title")
        self.assertEqual(articles[0].link, "https://example.test/articles/example")
        self.assertEqual(articles[0].summary, "Example summary.")
        self.assertIsNotNone(articles[0].published)

    def test_research_listings_request_article_cards(self) -> None:
        """Keep the direct research sources constrained to Article cards."""
        for config in NATURE_ARTICLE_LISTING_CONFIGS:
            self.assertIn("type=article", config.url)
            self.assertEqual(config.parser_key, "nature_article_html")
            self.assertEqual(config.fallback_parser_key, "nature_rss")

    def test_article_listing_excludes_nonresearch_cards(self) -> None:
        """Keep only cards explicitly labelled Article for research journals."""
        html = """
        <article class="c-card">
          <span class="c-meta__type">Article</span>
          <h3 class="c-card__title"><a href="/articles/article">Article</a></h3>
        </article>
        <article class="c-card">
          <span class="c-meta__type">Editorial</span>
          <h3 class="c-card__title"><a href="/articles/editorial">Editorial</a></h3>
        </article>
        """

        articles = parse_nature_article_listing(html, self.config)

        self.assertEqual([article.title for article in articles], ["Article"])

    @patch("main.parse_journal")
    @patch("main.fetch_html")
    def test_fetch_and_parse_uses_rss_after_empty_primary(
        self, fetch_html: Mock, parse_journal: Mock
    ) -> None:
        """Use the configured RSS fallback after a zero-card primary response."""
        fetch_html.side_effect = ["challenge", "rss"]
        parse_journal.side_effect = [[], [self.article]]

        articles = fetch_and_parse(self.config)

        self.assertEqual(articles, [self.article])
        self.assertEqual(fetch_html.call_count, 2)
        fallback_config = parse_journal.call_args_list[1].args[1]
        self.assertEqual(fallback_config.url, self.config.fallback_url)
        self.assertEqual(fallback_config.parser_key, self.config.fallback_parser_key)

    @patch(
        "main.parse_journal",
        return_value=[Article("Fallback", "link", "", None, "Nature Methods")],
    )
    @patch("main.fetch_html", side_effect=[ConnectionError("blocked"), "rss"])
    def test_fetch_and_parse_uses_rss_after_primary_error(
        self, fetch_html: Mock, parse_journal: Mock
    ) -> None:
        """Use the RSS fallback after an HTTP-client failure."""
        articles = fetch_and_parse(self.config)

        self.assertEqual(articles[0].title, "Fallback")
        self.assertEqual(fetch_html.call_count, 2)
        self.assertEqual(parse_journal.call_count, 1)

    @patch("main.parse_journal", return_value=[])
    @patch("main.fetch_html", side_effect=["challenge", "rss"])
    def test_fetch_and_parse_rejects_empty_fallback(
        self, fetch_html: Mock, parse_journal: Mock
    ) -> None:
        """Raise instead of publishing an empty source when both paths fail."""
        with self.assertRaisesRegex(
            RuntimeError, "fallback returned no valid articles"
        ):
            fetch_and_parse(self.config)

        self.assertEqual(fetch_html.call_count, 2)
        self.assertEqual(parse_journal.call_count, 2)


if __name__ == "__main__":
    unittest.main()
