import json
import os
import sys

import requests

from src import common

INTERNSHIP_LISTING_SCHEMA: dict[str, type] = {
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
    "terms": list,
}

LISTINGS_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/"
    "refs/heads/dev/.github/scripts/listings.json"
)

SUMMER_CATEGORY_ENV_MAP = common.build_category_env_map("", "_INTERNSHIPS_WEBHOOK_URL")
SUMMER_UNCATEGORIZED_ENV_VAR = "UNCATEGORIZED_INTERNSHIPS_WEBHOOK_URL"

OFFSEASON_CATEGORY_ENV_MAP = common.build_category_env_map(
    "OFFSEASON_", "_INTERNSHIPS_WEBHOOK_URL"
)
OFFSEASON_UNCATEGORIZED_ENV_VAR = "OFFSEASON_UNCATEGORIZED_INTERNSHIPS_WEBHOOK_URL"


def is_summer(listing: dict) -> bool:
    for term in listing.get("terms", []):
        if term.get("season") == "summer":
            return True
    return False


def _process_season(
    *,
    season: str,
    listings: list[dict],
    category_env_map: dict[str, str],
    uncategorized_env_var: str,
    footer: str,
) -> bool:
    log_label = f"[{season}]"

    active_listings = [
        listing
        for listing in listings
        if listing.get("is_visible") and listing.get("active")
    ]
    active_ids = {listing["id"] for listing in active_listings}

    seen_ids, is_first_run = common.load_seen_ids(season)

    if is_first_run:
        print(
            f"{log_label} no state file found — bootstrapping with "
            f"{len(active_ids)} existing active listings. Nothing "
            "will be posted this run."
        )
        common.save_seen_ids(season, active_ids)
        return False

    new_listings = [
        listing for listing in active_listings if listing["id"] not in seen_ids
    ]
    print(f"{log_label} {len(new_listings)} new listing(s).")
    if not new_listings:
        return False

    posted_ids = set()
    for listing in new_listings:
        category = (listing.get("category") or "").strip().lower()
        env_var = category_env_map.get(category, uncategorized_env_var)

        webhook_url = os.environ.get(env_var)
        if not webhook_url:
            print(
                f"{log_label}   {env_var} is not set, skipping listing {listing['id']}",
                file=sys.stderr,
            )
            continue

        embed = common.build_embed(listing, show_terms=True, footer=footer)
        if common.post_embed(webhook_url, embed):
            posted_ids.add(listing["id"])
        else:
            print(
                f"{log_label}   will retry listing {listing['id']} next run",
                file=sys.stderr,
            )

    if not posted_ids:
        print(f"{log_label} no listings were successfully posted", file=sys.stderr)
        return False

    common.save_seen_ids(season, seen_ids | posted_ids)
    return True


def run() -> bool:
    try:
        raw_listings = common.fetch_json(LISTINGS_URL)
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(
            f"[internships] failed to fetch/parse listings.json: {e}", file=sys.stderr
        )
        return False

    try:
        listings = common.validate_listings(
            raw_listings, schema=INTERNSHIP_LISTING_SCHEMA, label="internships"
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        return False

    print(f"[internships] fetched {len(raw_listings)} listings, {len(listings)} valid")

    summer_listings = [listing for listing in listings if is_summer(listing)]
    offseason_listings = [listing for listing in listings if not is_summer(listing)]

    summer_result = _process_season(
        season="summer",
        listings=summer_listings,
        category_env_map=SUMMER_CATEGORY_ENV_MAP,
        uncategorized_env_var=SUMMER_UNCATEGORIZED_ENV_VAR,
        footer="Simplify · Internships",
    )
    offseason_result = _process_season(
        season="offseason",
        listings=offseason_listings,
        category_env_map=OFFSEASON_CATEGORY_ENV_MAP,
        uncategorized_env_var=OFFSEASON_UNCATEGORIZED_ENV_VAR,
        footer="Simplify · Off-Season Internships",
    )

    if summer_result is False or offseason_result is False:
        return False
    return True
