from src import common

KEYWORDS: dict[str, tuple[str, ...]] = {
    "hardware": (
        "hardware",
        "embedded",
        "firmware",
        "electrical engineer",
        "fpga",
        "asic",
        "mechanical engineer",
        "robotics",
    ),
    "data_science": (
        "data scientist",
        "data science",
        "machine learning",
        "ml engineer",
        "ai engineer",
        "artificial intelligence",
        "deep learning",
        "nlp",
        "computer vision",
        "data engineer",
        "data analyst",
    ),
    "quant": (
        "quant",
        "quantitative",
        "trading",
        "trader",
    ),
    "product": (
        "product manager",
        "product management",
        "technical program manager",
        "associate product manager",
    ),
    "software": (
        "software",
        "swe",
        "backend",
        "back end",
        "frontend",
        "front end",
        "full stack",
        "full-stack",
        "web developer",
        "ios",
        "android",
        "mobile",
        "devops",
        "site reliability",
        "cloud engineer",
        "platform engineer",
        "infrastructure engineer",
        "systems engineer",
    ),
}


# Software's keyword list is by far the broadest and would false-positive
# on titles that are really a more specific category
PRIORITY = ["hardware", "data_science", "quant", "product", "software"]


def infer_category(title: str) -> str | None:
    lowered = title.lower()
    for slug in PRIORITY:
        if any(keyword in lowered for keyword in KEYWORDS[slug]):
            return common.CATEGORY_ALIASES[slug][0]
    return None
