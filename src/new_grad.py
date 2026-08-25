import json
import os
import sys

import requests

from src import common

FULLTIME_LISTING_SCHEMA: dict[str, type] = {
    "id": str,
    "company_name": str,
    "title": str,
    "active": bool,
    "is_visible": bool,
    "url": str,
    "company_url": str,
    "locations": list,
    "category": str,
    "sponsorship": str,
    "date_posted": int,
}

LISTINGS_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/"
    "refs/heads/dev/.github/scripts/listings.json"
)

CATEGORY_ENV_MAP = common.build_category_env_map("FULLTIME_", "_WEBHOOK_URL")
UNCATEGORIZED_ENV_VAR = "FULLTIME_UNCATEGORIZED_WEBHOOK_URL"


def run() -> bool:
    try:
        raw_listings = common.fetch_json(LISTINGS_URL)
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"[new_grad] failed to fetch/parse listings.json: {e}", file=sys.stderr)
        return False

    try:
        listings = common.validate_listings(
            raw_listings, schema=FULLTIME_LISTING_SCHEMA, label="new_grad"
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        return False

    print(f"[new_grad] fetched {len(raw_listings)} listings, {len(listings)} valid")

    active_listings = [
        listing
        for listing in listings
        if listing.get("is_visible") and listing.get("active")
    ]
    active_ids = {listing["id"] for listing in active_listings}

    seen_ids, is_first_run = common.load_seen_ids("fulltime")

    if is_first_run:
        print(
            f"[new_grad] no state file found — bootstrapping with "
            f"{len(active_ids)} existing active listings. Nothing "
            "will be posted this run."
        )
        common.save_seen_ids("fulltime", active_ids)
        return True

    new_listings = [
        listing for listing in active_listings if listing["id"] not in seen_ids
    ]
    print(f"[new_grad] {len(new_listings)} new listing(s).")
    if not new_listings:
        return True

    posted_ids = set()
    for listing in new_listings:
        category = (listing.get("category") or "").strip().lower()
        env_var = CATEGORY_ENV_MAP.get(category, UNCATEGORIZED_ENV_VAR)

        webhook_url = os.environ.get(env_var)
        if not webhook_url:
            print(
                f"[new_grad]   {env_var} is not set, skipping listing {listing['id']}",
                file=sys.stderr,
            )
            continue

        embed = common.build_embed(
            listing, show_terms=False, footer="Simplify · New Grad"
        )
        print(
            f"[new_grad]   posting {listing.get('company_name')} — "
            f"{listing.get('title')}…"
        )
        if common.post_embed(webhook_url, embed):
            posted_ids.add(listing["id"])
        else:
            print(
                f"[new_grad]   will retry listing {listing['id']} next run",
                file=sys.stderr,
            )

    if not posted_ids and new_listings:
        print("[new_grad] no listings were successfully posted", file=sys.stderr)
        return False

    common.save_seen_ids("fulltime", seen_ids | posted_ids)
    return True
