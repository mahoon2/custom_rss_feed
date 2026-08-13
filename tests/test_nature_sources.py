"""Tests for Nature listing extraction and RSS fallback behavior."""

import collections
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import (
    JOURNAL_CONFIGS,
    NATURE_ARTICLE_LISTING_CONFIGS,
    NATURE_SUBJECT_JOURNALS,
    NATURE_SUBJECT_LISTING_CONFIGS,
    NATURE_SUBJECT_PAGES,
    NATURE_SUBJECTS,
)
from main import fetch_and_parse
from models import Article, JournalConfig
from parsers import (
    parse_nature,
    parse_nature_article_listing,
    parse_nature_subject_listing,
)

SUBJECT_CARD = """
<article>
  <div class="cleared" itemscope itemtype="http://schema.org/ScholarlyArticle">
    <p><span data-test="article.type">{type}</span>
       <time datetime="2026-08-13" itemprop="datePublished">13 August 2026</time></p>
    <h3 itemprop="name headline">
      <a href="/articles/{doi}" itemprop="url">{title}</a>
    </h3>
    <div itemprop="description"><p>{summary}</p></div>
  </div>
</article>
"""


class NatureSubjectListingTests(unittest.TestCase):
    """Verify the per-subject listing used to keep Nature Communications on topic."""

    def setUp(self) -> None:
        """Use the production biological-sciences configuration."""
        self.config = NATURE_SUBJECT_LISTING_CONFIGS[0]

    def test_extracts_a_complete_article_record(self) -> None:
        """Read title, link, summary, and date from a subject-listing card."""
        html = SUBJECT_CARD.format(
            type="Article",
            doi="s41467-026-76678-y",
            title="Hypothalamic prolactin receptor neurons",
            summary="Authors find PRLR neurons regulate metabolism.",
        )

        articles = parse_nature_subject_listing(html, self.config)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Hypothalamic prolactin receptor neurons")
        self.assertEqual(
            articles[0].link, "https://www.nature.com/articles/s41467-026-76678-y"
        )
        self.assertEqual(
            articles[0].summary, "Authors find PRLR neurons regulate metabolism."
        )
        self.assertIsNotNone(articles[0].published)
        self.assertEqual(articles[0].source, "Nature Communications")

    def test_keeps_only_cards_typed_article(self) -> None:
        """Drop the Comment and Review Article entries these listings mix in.

        Both were present on the live pages: a Comment on biological sciences
        and a Review Article on health sciences.
        """
        html = "".join(
            SUBJECT_CARD.format(
                type=t, doi=f"s41467-026-0000{i}-x", title=t, summary=""
            )
            for i, t in enumerate(("Article", "Comment", "Review Article"))
        )

        articles = parse_nature_subject_listing(html, self.config)

        self.assertEqual([article.title for article in articles], ["Article"])


def _subject_and_page(url: str) -> tuple:
    """Split a subject-listing URL into its subject and page number."""
    subject = url.split("/subjects/")[1].split("/")[0]
    return subject, int(url.rsplit("page=", 1)[1])


class NatureSubjectScopeTests(unittest.TestCase):
    """Verify the multidisciplinary journals are drawn from subject listings.

    Nature and Nature Communications both publish roughly half their output
    outside this project's scope, and neither exposes a subject in any feed.
    """

    def test_covers_every_configured_journal(self) -> None:
        """Restrict each multidisciplinary journal, not only the first."""
        names = {config.name for config in NATURE_SUBJECT_LISTING_CONFIGS}
        self.assertEqual(names, {name for name, _, _ in NATURE_SUBJECT_JOURNALS})

    def test_uses_biological_and_health_sciences(self) -> None:
        """Cover both subjects, since Nature files biomedicine under health."""
        for name, _, _ in NATURE_SUBJECT_JOURNALS:
            subjects = {
                _subject_and_page(config.url)[0]
                for config in NATURE_SUBJECT_LISTING_CONFIGS
                if config.name == name
            }
            with self.subTest(journal=name):
                self.assertEqual(subjects, set(NATURE_SUBJECTS))

    def test_paginates_every_subject_to_the_same_depth(self) -> None:
        """Fetch each subject to NATURE_SUBJECT_PAGES, with no page skipped.

        A rolling listing loses whatever scrolls off between snapshots, so its
        depth has to exceed the longest gap between runs.
        """
        pages = collections.defaultdict(set)
        for config in NATURE_SUBJECT_LISTING_CONFIGS:
            subject, page = _subject_and_page(config.url)
            pages[(config.name, subject)].add(page)

        expected = set(range(1, NATURE_SUBJECT_PAGES + 1))
        self.assertEqual(
            len(pages), len(NATURE_SUBJECT_JOURNALS) * len(NATURE_SUBJECTS)
        )
        for key, seen in pages.items():
            with self.subTest(source=key):
                self.assertEqual(seen, expected)

    def test_every_source_is_distinct(self) -> None:
        """Guard against a duplicated URL quietly halving the window."""
        urls = [config.url for config in NATURE_SUBJECT_LISTING_CONFIGS]
        self.assertEqual(len(urls), len(set(urls)))

    def test_each_journal_keeps_its_own_identity_pattern(self) -> None:
        """Keep the DOI prefixes distinct so one journal cannot absorb another."""
        for name, _, doi in NATURE_SUBJECT_JOURNALS:
            for config in NATURE_SUBJECT_LISTING_CONFIGS:
                if config.name == name:
                    with self.subTest(journal=name, url=config.url):
                        self.assertIn(doi, config.link_pattern)

    def test_declares_no_fallback(self) -> None:
        """Keep the unfiltered RSS feed out of a subject-filtered source.

        Falling back to a journal's own RSS feed would readmit the physics and
        chemistry the subject listings exist to exclude.
        """
        for config in NATURE_SUBJECT_LISTING_CONFIGS:
            with self.subTest(url=config.url):
                self.assertIsNone(config.fallback_url)

    def test_no_unfiltered_source_remains(self) -> None:
        """Ensure the unfiltered sources were replaced, not merely added to.

        Nature previously came from nature.rss and Nature Communications from
        the all-subject listing; either surviving would readmit everything.
        """
        for name, _, _ in NATURE_SUBJECT_JOURNALS:
            configs = [c for c in JOURNAL_CONFIGS if c.name == name]
            with self.subTest(journal=name):
                self.assertEqual(
                    len(configs), len(NATURE_SUBJECTS) * NATURE_SUBJECT_PAGES
                )
                for config in configs:
                    self.assertIn("/subjects/", config.url)


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
