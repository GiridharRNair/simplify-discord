import json
import sys

import requests

from src import common

LISTINGS_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/"
    "refs/heads/dev/.github/scripts/listings.json"
)

SUMMER_CATEGORY_MAP = common.build_category_map("", "_INTERNSHIPS_WEBHOOK_URL")
SUMMER_UNCATEGORIZED_ENV_VAR = "UNCATEGORIZED_INTERNSHIPS_WEBHOOK_URL"

OFFSEASON_CATEGORY_MAP = common.build_category_map(
    "OFFSEASON_", "_INTERNSHIPS_WEBHOOK_URL"
)
OFFSEASON_UNCATEGORIZED_ENV_VAR = "OFFSEASON_UNCATEGORIZED_INTERNSHIPS_WEBHOOK_URL"


def is_summer(listing: dict) -> bool:
    return any("summer" in t.lower() for t in listing.get("terms", []))


def run() -> bool:
    try:
        listings = common.fetch_json(LISTINGS_URL)
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(
            f"[internships] failed to fetch/parse listings.json: {e}", file=sys.stderr
        )
        return False

    print(f"[internships] fetched {len(listings)} listings")

    common.notify_new_listings(
        bucket="summer",
        listings=listings,
        category_map=SUMMER_CATEGORY_MAP,
        uncategorized_env_var=SUMMER_UNCATEGORIZED_ENV_VAR,
        term_filter=is_summer,
        show_terms=True,
        footer="Simplify · Internships",
    )
    common.notify_new_listings(
        bucket="offseason",
        listings=listings,
        category_map=OFFSEASON_CATEGORY_MAP,
        uncategorized_env_var=OFFSEASON_UNCATEGORIZED_ENV_VAR,
        term_filter=lambda listing: not is_summer(listing),
        show_terms=True,
        footer="Simplify · Off-Season Internships",
    )
    return True
