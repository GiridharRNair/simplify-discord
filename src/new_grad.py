import json
import sys

import requests

from src import common

LISTINGS_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/"
    "refs/heads/dev/.github/scripts/listings.json"
)

CATEGORY_ENV_MAP = common.build_category_env_map("FULLTIME_", "_WEBHOOK_URL")
UNCATEGORIZED_ENV_VAR = "FULLTIME_UNCATEGORIZED_WEBHOOK_URL"


def run() -> bool:
    try:
        listings = common.fetch_json(LISTINGS_URL)
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"[new_grad] failed to fetch/parse listings.json: {e}", file=sys.stderr)
        return False

    print(f"[new_grad] fetched {len(listings)} listings")

    common.notify_new_listings(
        bucket="fulltime",
        listings=listings,
        category_map=CATEGORY_ENV_MAP,
        uncategorized_env_var=UNCATEGORIZED_ENV_VAR,
        show_terms=False,
        footer="Simplify · New Grad",
    )
    return True
