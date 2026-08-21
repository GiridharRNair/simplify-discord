import json
import sys

import requests

from src import common, internships, keywords

LISTINGS_URL = (
    "https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/"
    "refs/heads/dev/.github/scripts/listings.json"
)


def normalize(listing: dict) -> dict:
    season = listing.get("season") or ""
    return {
        **listing,
        "category": keywords.infer_category(listing.get("title", "")),
        "terms": [season] if season else [],
    }


def is_summer(listing: dict) -> bool:
    return "summer" in (listing.get("season") or "").lower()


def run() -> bool:
    try:
        raw_listings = common.fetch_json(LISTINGS_URL)
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(
            f"[vansh_internships] failed to fetch/parse listings.json: {e}",
            file=sys.stderr,
        )
        return False

    listings = [normalize(listing) for listing in raw_listings]
    print(f"[vansh_internships] fetched {len(listings)} listings")

    common.notify_new_vansh_listings(
        name="summer",
        listings=listings,
        category_map=internships.SUMMER_CATEGORY_MAP,
        uncategorized_env_var=internships.SUMMER_UNCATEGORIZED_ENV_VAR,
        term_filter=is_summer,
        show_terms=True,
        footer="vanshb03 · Internships",
    )
    common.notify_new_vansh_listings(
        name="offseason",
        listings=listings,
        category_map=internships.OFFSEASON_CATEGORY_MAP,
        uncategorized_env_var=internships.OFFSEASON_UNCATEGORIZED_ENV_VAR,
        term_filter=lambda listing: not is_summer(listing),
        show_terms=True,
        footer="vanshb03 · Off-Season Internships",
    )
    return True
