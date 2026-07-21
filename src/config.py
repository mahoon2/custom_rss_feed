from typing import Dict, Tuple

from models import FeedConfig, JournalConfig

TRUST_HEADERS: Dict[str, str] = {
    "Referer": "https://www.google.com/",
    "Accept-Language": "en-US,en;q=0.9",
}

NATURE_ARTICLE_JOURNALS: Tuple[Tuple[str, str], ...] = (
    ("Nature Cell Biology", "ncb"),
    ("Nature Communications", "ncomms"),
    ("Nature Biotechnology", "nbt"),
    ("Nature Methods", "nmeth"),
    ("Nature Genetics", "ng"),
    ("Nature Structural & Molecular Biology", "nsmb"),
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
    )
    for name, code in NATURE_ARTICLE_JOURNALS
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
    ),
)

JOURNAL_CONFIGS: Tuple[JournalConfig, ...] = (
    JournalConfig(
        name="Cell",
        url="https://www.cell.com/cell/inpress.rss",
        base_url="https://www.cell.com",
        include_terms=(),
        exclude_terms=(),
    ),
    JournalConfig(
        name="Nature",
        url="https://www.nature.com/nature.rss",
        base_url="https://www.nature.com",
        include_terms=("research article", "research"),
        exclude_terms=("news & views",),
    ),
    JournalConfig(
        name="Science",
        url="https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science",
        base_url="https://www.science.org",
        include_terms=(),
        exclude_terms=(),
    ),
    JournalConfig(
        name="Molecular Cell",
        url="https://www.cell.com/molecular-cell/inpress.rss",
        base_url="https://www.cell.com",
        include_terms=(),
        exclude_terms=(),
    ),
    *NATURE_ARTICLE_LISTING_CONFIGS,
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
    JournalConfig(
        name="Nucleic Acids Research",
        url="https://academic.oup.com/rss/site_5127/3091.xml",
        base_url="https://academic.oup.com",
        include_terms=(),
        exclude_terms=(),
    ),
    JournalConfig(
        name="Briefings in Bioinformatics",
        url="https://academic.oup.com/rss/site_5143/3005.xml",
        base_url="https://academic.oup.com",
        include_terms=(),
        exclude_terms=(),
    ),
    JournalConfig(
        name="Bioinformatics",
        url="https://academic.oup.com/rss/site_5139/3001.xml",
        base_url="https://academic.oup.com",
        include_terms=(),
        exclude_terms=(),
    ),
    JournalConfig(
        name="Cell Genomics",
        url="https://www.cell.com/cell-genomics/inpress.rss",
        base_url="https://www.cell.com",
        include_terms=(),
        exclude_terms=(),
    ),
    JournalConfig(
        name="The EMBO Journal",
        url="https://link.springer.com/journal/44318/articles",
        base_url="https://link.springer.com",
        include_terms=(),
        exclude_terms=(),
    ),
    JournalConfig(
        name="Science Advances",
        url="https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=sciadv",
        base_url="https://www.science.org",
        include_terms=(),
        exclude_terms=(),
    ),
    JournalConfig(
        name="RNA",
        url="https://rnajournal.cshlp.org/content/current",
        base_url="https://rnajournal.cshlp.org",
        include_terms=(),
        exclude_terms=(),
    ),
    *NATURE_REVIEW_LISTING_CONFIGS,
    JournalConfig(
        name="Trends in Genetics",
        url="https://www.cell.com/trends/genetics/inpress.rss",
        base_url="https://www.cell.com",
        include_terms=(),
        exclude_terms=(),
    ),
    JournalConfig(
        name="Trends in Cell Biology",
        url="https://www.cell.com/trends/cell-biology/inpress.rss",
        base_url="https://www.cell.com",
        include_terms=(),
        exclude_terms=(),
    ),
)

BASE_GITHUB_URL: str = "https://mahoon2.github.io/custom_rss_feed"

FEED_CONFIGS: Tuple[FeedConfig, ...] = (
    FeedConfig(
        title="CNS Feed",
        description="Aggregated research articles from Cell, Nature, Science, and Science Advances.",
        output_file="CNSFeed.xml",
        link=f"{BASE_GITHUB_URL}/CNSFeed.xml",
        journal_names=("Cell", "Nature", "Science", "Science Advances"),
    ),
    FeedConfig(
        title="Molecular & Cell Biology Feed",
        description="Aggregated research articles from Nature Cell Biology, Nature Communications, Molecular Cell, Nature Structural & Molecular Biology, The EMBO Journal, and RNA.",
        output_file="MolCellFeed.xml",
        link=f"{BASE_GITHUB_URL}/MolCellFeed.xml",
        journal_names=(
            "Nature Cell Biology",
            "Nature Communications",
            "Molecular Cell",
            "Nature Structural & Molecular Biology",
            "The EMBO Journal",
            "RNA",
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
        description="Aggregated research articles from Nature Genetics, Cell Genomics, Genome Biology, Genome Research, and Nucleic Acids Research.",
        output_file="GenomicsFeed.xml",
        link=f"{BASE_GITHUB_URL}/GenomicsFeed.xml",
        journal_names=(
            "Nature Genetics",
            "Cell Genomics",
            "Genome Biology",
            "Genome Research",
            "Nucleic Acids Research",
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
