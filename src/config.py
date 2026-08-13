from typing import Dict, Tuple

from models import FeedConfig, JournalConfig

TRUST_HEADERS: Dict[str, str] = {
    "Referer": "https://www.google.com/",
    "Accept-Language": "en-US,en;q=0.9",
}

# (display name, nature.com journal code, DOI prefix identifying the journal).
# The DOI prefix is what distinguishes one nature.com journal from another: all
# eight listing scrapers share a host and card markup, so a mis-scoped response
# is otherwise indistinguishable from a correct one.
NATURE_ARTICLE_JOURNALS: Tuple[Tuple[str, str, str], ...] = (
    ("Nature Cell Biology", "ncb", "s41556"),
    ("Nature Biotechnology", "nbt", "s41587"),
    ("Nature Methods", "nmeth", "s41592"),
    ("Nature Genetics", "ng", "s41588"),
    ("Nature Structural & Molecular Biology", "nsmb", "s41594"),
)

NATURE_ARTICLE_LISTING_CONFIGS: Tuple[JournalConfig, ...] = tuple(
    JournalConfig(
        name=name,
        url=f"https://www.nature.com/{code}/articles?searchType=journalSearch&sort=PubDate&type=article",
        base_url="https://www.nature.com",
        include_terms=(),
        exclude_terms=(),
        parser_key="nature_article_html",
        fallback_url=f"https://www.nature.com/{code}.rss",
        fallback_parser_key="nature_rss",
        link_pattern=rf"nature\.com/articles/{doi}-",
    )
    for name, code, doi in NATURE_ARTICLE_JOURNALS
)

# Nature and Nature Communications are multidisciplinary, and roughly half of
# what they publish is outside this project's scope: condensed-matter physics,
# astronomy, catalysis, atmospheric science, and machine learning. About 65% of
# Nature Communications and 48% of Nature is biological or health science.
#
# Their subject listings are the only structural way to separate the two, since
# neither journal's RSS feed nor its main listing carries a subject anywhere.
# Health sciences is needed alongside biological sciences because Nature files
# cancer biology, immunology, and infection under the former; filtering on
# biological sciences alone drops them.
#
# All sources share a journal name, so main() unions them and build_feed
# deduplicates the overlap by link. None declares a fallback: the journal's
# RSS feed is unfiltered, so falling back to it would silently readmit exactly
# the content this filter exists to remove.
#
# A rolling listing silently drops whatever scrolls off before the next
# snapshot, so its depth has to exceed the longest gap between runs, which is
# six days: the 20-item listing previously used for Nature Communications lost
# 44 of the 88 articles published over one ten-day stretch. A page holds 50
# cards, which is about three days of Nature Communications biology and eight
# days of Nature's, so two pages leave both with headroom. Consecutive pages do
# not overlap, and page one is equivalent to the unparameterized URL.
NATURE_SUBJECT_PAGES: int = 2

NATURE_SUBJECTS: Tuple[str, ...] = ("biological-sciences", "health-sciences")

# (display name, nature.com journal code, DOI prefix identifying the journal).
NATURE_SUBJECT_JOURNALS: Tuple[Tuple[str, str, str], ...] = (
    ("Nature Communications", "ncomms", "s41467"),
    ("Nature", "nature", "s41586"),
)

NATURE_SUBJECT_LISTING_CONFIGS: Tuple[JournalConfig, ...] = tuple(
    JournalConfig(
        name=name,
        url=f"https://www.nature.com/subjects/{subject}/{code}?page={page}",
        base_url="https://www.nature.com",
        include_terms=(),
        exclude_terms=(),
        parser_key="nature_subject_html",
        link_pattern=rf"nature\.com/articles/{doi}-",
    )
    for name, code, doi in NATURE_SUBJECT_JOURNALS
    for subject in NATURE_SUBJECTS
    for page in range(1, NATURE_SUBJECT_PAGES + 1)
)

NATURE_REVIEW_LISTING_CONFIGS: Tuple[JournalConfig, ...] = (
    JournalConfig(
        name="Nature Reviews Molecular Cell Biology",
        url="https://www.nature.com/nrm/articles",
        base_url="https://www.nature.com",
        include_terms=(),
        exclude_terms=(),
        parser_key="nature_html",
        fallback_url="https://www.nature.com/nrm.rss",
        fallback_parser_key="nature_review_rss",
        link_pattern=r"nature\.com/articles/s41580-",
    ),
    JournalConfig(
        name="Nature Reviews Genetics",
        url="https://www.nature.com/nrg/articles",
        base_url="https://www.nature.com",
        include_terms=(),
        exclude_terms=(),
        parser_key="nature_html",
        fallback_url="https://www.nature.com/nrg.rss",
        fallback_parser_key="nature_review_rss",
        link_pattern=r"nature\.com/articles/s41576-",
    ),
)

JOURNAL_CONFIGS: Tuple[JournalConfig, ...] = (
    JournalConfig(
        name="Cell",
        url="https://www.cell.com/cell/inpress.rss",
        base_url="https://www.cell.com",
        include_terms=(),
        exclude_terms=(),
        link_pattern=r"cell\.com/cell/",
    ),
    JournalConfig(
        name="Science",
        url="https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science",
        base_url="https://www.science.org",
        include_terms=(),
        exclude_terms=(),
        link_pattern=r"science\.org/doi/(abs/)?10\.1126/science\.",
    ),
    JournalConfig(
        name="Molecular Cell",
        url="https://www.cell.com/molecular-cell/inpress.rss",
        base_url="https://www.cell.com",
        include_terms=(),
        exclude_terms=(),
        link_pattern=r"cell\.com/molecular-cell/",
    ),
    *NATURE_ARTICLE_LISTING_CONFIGS,
    *NATURE_SUBJECT_LISTING_CONFIGS,
    JournalConfig(
        name="Genome Biology",
        url="https://genomebiology.biomedcentral.com/articles",
        base_url="https://genomebiology.biomedcentral.com",
        include_terms=("research",),
        exclude_terms=(),
        link_pattern=r"genomebiology\.biomedcentral\.com",
    ),
    JournalConfig(
        name="Genome Research",
        url="https://genome.cshlp.org/content/current",
        base_url="https://genome.cshlp.org",
        include_terms=("research",),
        exclude_terms=(),
        link_pattern=r"genome\.cshlp\.org",
    ),
    JournalConfig(
        name="Nucleic Acids Research",
        url="https://academic.oup.com/rss/site_5127/3091.xml",
        base_url="https://academic.oup.com",
        include_terms=(),
        exclude_terms=(),
        link_pattern=r"academic\.oup\.com/nar",
    ),
    JournalConfig(
        name="Briefings in Bioinformatics",
        url="https://academic.oup.com/rss/site_5143/3005.xml",
        base_url="https://academic.oup.com",
        include_terms=(),
        exclude_terms=(),
        link_pattern=r"academic\.oup\.com/bib",
    ),
    JournalConfig(
        name="Bioinformatics",
        url="https://academic.oup.com/rss/site_5139/3001.xml",
        base_url="https://academic.oup.com",
        include_terms=(),
        exclude_terms=(),
        link_pattern=r"academic\.oup\.com/bioinformatics",
    ),
    JournalConfig(
        name="Cell Genomics",
        url="https://www.cell.com/cell-genomics/inpress.rss",
        base_url="https://www.cell.com",
        include_terms=(),
        exclude_terms=(),
        link_pattern=r"cell\.com/cell-genomics",
    ),
    JournalConfig(
        name="The EMBO Journal",
        url="https://link.springer.com/journal/44318/articles",
        base_url="https://link.springer.com",
        include_terms=(),
        exclude_terms=(),
        link_pattern=r"/s44318-",
    ),
    JournalConfig(
        name="Science Advances",
        url="https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=sciadv",
        base_url="https://www.science.org",
        include_terms=(),
        exclude_terms=(),
        link_pattern=r"science\.org/doi/(abs/)?10\.1126/sciadv",
    ),
    JournalConfig(
        name="RNA",
        url="https://rnajournal.cshlp.org/content/current",
        base_url="https://rnajournal.cshlp.org",
        include_terms=(),
        exclude_terms=(),
        link_pattern=r"rnajournal\.cshlp\.org",
    ),
    *NATURE_REVIEW_LISTING_CONFIGS,
    JournalConfig(
        name="Trends in Genetics",
        url="https://www.cell.com/trends/genetics/inpress.rss",
        base_url="https://www.cell.com",
        include_terms=(),
        exclude_terms=(),
        link_pattern=r"cell\.com/trends/genetics",
    ),
    JournalConfig(
        name="Trends in Cell Biology",
        url="https://www.cell.com/trends/cell-biology/inpress.rss",
        base_url="https://www.cell.com",
        include_terms=(),
        exclude_terms=(),
        link_pattern=r"cell\.com/trends/cell-biology",
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
        description="Aggregated research articles from Nature Cell Biology, Molecular Cell, Nature Structural & Molecular Biology, and The EMBO Journal.",
        output_file="MolCellFeed.xml",
        link=f"{BASE_GITHUB_URL}/MolCellFeed.xml",
        journal_names=(
            "Nature Cell Biology",
            "Molecular Cell",
            "Nature Structural & Molecular Biology",
            "The EMBO Journal",
        ),
    ),
    # Nature Communications and Science Advances publish 30-60 times what a
    # selective journal does, so grouping them with one buries the other: they
    # were 92% of the Molecular & Cell Biology feed's weekly flow against ~16
    # articles per week for its four other journals combined. They are split off
    # rather than capped, since a smaller window would drop articles between
    # snapshots instead of merely reordering them.
    FeedConfig(
        title="Megajournal Feed",
        description="Aggregated research articles from the multidisciplinary megajournals: Nature Communications, restricted to biological and health sciences, and Science Advances, which is not filtered by subject because no accessible source exposes one.",
        output_file="MegajournalFeed.xml",
        link=f"{BASE_GITHUB_URL}/MegajournalFeed.xml",
        journal_names=(
            "Nature Communications",
            "Science Advances",
        ),
    ),
    FeedConfig(
        title="Methodology Feed",
        description="Aggregated research articles from Nature Biotechnology, Nature Methods, Briefings in Bioinformatics, and Bioinformatics.",
        output_file="MethodFeed.xml",
        link=f"{BASE_GITHUB_URL}/MethodFeed.xml",
        journal_names=(
            "Nature Biotechnology",
            "Nature Methods",
            "Briefings in Bioinformatics",
            "Bioinformatics",
        ),
    ),
    FeedConfig(
        title="Genomics Feed",
        description="Aggregated research articles from Nature Genetics, Cell Genomics, Genome Biology, Genome Research, Nucleic Acids Research, and RNA.",
        output_file="GenomicsFeed.xml",
        link=f"{BASE_GITHUB_URL}/GenomicsFeed.xml",
        journal_names=(
            "Nature Genetics",
            "Cell Genomics",
            "Genome Biology",
            "Genome Research",
            "Nucleic Acids Research",
            "RNA",
        ),
    ),
    FeedConfig(
        title="Reviews Feed",
        description="Aggregated reviews from Nature Reviews Molecular Cell Biology, Nature Reviews Genetics, Trends in Genetics, and Trends in Cell Biology.",
        output_file="ReviewsFeed.xml",
        link=f"{BASE_GITHUB_URL}/ReviewsFeed.xml",
        journal_names=(
            "Nature Reviews Molecular Cell Biology",
            "Nature Reviews Genetics",
            "Trends in Genetics",
            "Trends in Cell Biology",
        ),
    ),
)
