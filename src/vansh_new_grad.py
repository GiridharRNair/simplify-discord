import json
import sys

import requests

from src import common, keywords, new_grad

LISTINGS_URL = (
    "https://raw.githubusercontent.com/vanshb03/New-Grad-2027/"
    "refs/heads/dev/.github/scripts/listings.json"
)


def normalize(listing: dict) -> dict:
    return {**listing, "category": keywords.infer_category(listing.get("title", ""))}


def run() -> bool:
    try:
        raw_listings = common.fetch_json(LISTINGS_URL)
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(
            f"[vansh_new_grad] failed to fetch/parse listings.json: {e}",
            file=sys.stderr,
        )
        return False

    listings = [normalize(listing) for listing in raw_listings]
    print(f"[vansh_new_grad] fetched {len(listings)} listings")

    common.notify_new_vansh_listings(
        name="fulltime",
        listings=listings,
        category_map=new_grad.CATEGORY_MAP,
        uncategorized_env_var=new_grad.UNCATEGORIZED_ENV_VAR,
        show_terms=False,
        footer="vanshb03 · New-Grad-2027",
    )
    return True
