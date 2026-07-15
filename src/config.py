from typing import Dict, Tuple

from models import FeedConfig, JournalConfig

TRUST_HEADERS: Dict[str, str] = {
    "Referer": "https://www.google.com/",
    "Accept-Language": "en-US,en;q=0.9",
}

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
    JournalConfig(
        name="Nature Cell Biology",
        url="https://www.nature.com/ncb.rss",
        base_url="https://www.nature.com",
        include_terms=("research article", "research"),
        exclude_terms=("news & views",),
    ),
    JournalConfig(
        name="Nature Communications",
        url="https://www.nature.com/ncomms.rss",
        base_url="https://www.nature.com",
        include_terms=(),
        exclude_terms=(),
    ),
    JournalConfig(
        name="Nature Biotechnology",
        url="https://www.nature.com/nbt.rss",
        base_url="https://www.nature.com",
        include_terms=("research article", "research"),
        exclude_terms=("news & views",),
    ),
    JournalConfig(
        name="Nature Methods",
        url="https://www.nature.com/nmeth.rss",
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
        url="https://academic.oup.com/rss/site_5139/advanceAccess_3001.xml",
        base_url="https://academic.oup.com",
        include_terms=(),
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
        description="Aggregated research articles from Nature Cell Biology, Nature Communications, Genome Biology, Genome Research, Molecular Cell, and Nucleic Acids Research.",
        output_file="MolCellFeed.xml",
        link=f"{BASE_GITHUB_URL}/MolCellFeed.xml",
        journal_names=(
            "Nature Cell Biology",
            "Nature Communications",
            "Genome Biology",
            "Genome Research",
            "Molecular Cell",
            "Nucleic Acids Research",
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
)
