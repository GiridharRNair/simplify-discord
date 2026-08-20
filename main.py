#!/usr/bin/env python3
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is a local-dev convenience only; not required in CI

LISTINGS_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/"
    "refs/heads/dev/.github/scripts/listings.json"
)

STATE_PATH = Path(__file__).parent / "data" / "seen_ids.json"

CATEGORY_MAP = {
    "software": "SOFTWARE_INTERNSHIPS_WEBHOOK_URL",
    "software engineering": "SOFTWARE_INTERNSHIPS_WEBHOOK_URL",
    "product": "PRODUCT_MANAGEMENT_INTERNSHIPS_WEBHOOK_URL",
    "product management": "PRODUCT_MANAGEMENT_INTERNSHIPS_WEBHOOK_URL",
    "ai/ml/data": "DATA_SCIENCE_ML_AI_INTERNSHIPS_WEBHOOK_URL",
    "data science, ai & machine learning": "DATA_SCIENCE_ML_AI_INTERNSHIPS_WEBHOOK_URL",
    "quant": "QUANTITATIVE_FINANCE_INTERNSHIPS_WEBHOOK_URL",
    "quantitative finance": "QUANTITATIVE_FINANCE_INTERNSHIPS_WEBHOOK_URL",
    "hardware": "HARDWARE_INTERNSHIPS_WEBHOOK_URL",
    "hardware engineering": "HARDWARE_INTERNSHIPS_WEBHOOK_URL",
}

UNCATEGORIZED_ENV_VAR = "UNCATEGORIZED_INTERNSHIPS_WEBHOOK_URL"

CATEGORY_COLOR = {
    "SOFTWARE_INTERNSHIPS_WEBHOOK_URL": 0x5865F2,
    "PRODUCT_MANAGEMENT_INTERNSHIPS_WEBHOOK_URL": 0x57F287,
    "DATA_SCIENCE_ML_AI_INTERNSHIPS_WEBHOOK_URL": 0xEB459E,
    "QUANTITATIVE_FINANCE_INTERNSHIPS_WEBHOOK_URL": 0xFEE75C,
    "HARDWARE_INTERNSHIPS_WEBHOOK_URL": 0xED4245,
    UNCATEGORIZED_ENV_VAR: 0x99AAB5,
}

DISCORD_EMBEDS_PER_MESSAGE = 10  # Discord's hard cap per webhook execute call


def fetch_listings() -> list[dict]:
    resp = requests.get(LISTINGS_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def load_seen_ids() -> tuple[set[str], bool]:
    if not STATE_PATH.exists():
        return set(), True
    with STATE_PATH.open() as f:
        data = json.load(f)
    return set(data.get("seen_ids", [])), False


def save_seen_ids(seen_ids: set[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w") as f:
        json.dump(
            {
                "seen_ids": sorted(seen_ids),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            },
            f,
            indent=2,
        )
        f.write("\n")


def category_env_var(listing: dict) -> str:
    category = (listing.get("category") or "").strip().lower()
    return CATEGORY_MAP.get(category, UNCATEGORIZED_ENV_VAR)


def build_embed(listing: dict) -> dict:
    company = listing.get("company_name", "Unknown Company").strip()
    title = listing.get("title", "Untitled Role").strip()
    locations = ", ".join(listing.get("locations", [])) or "Not specified"
    terms = ", ".join(listing.get("terms", [])) or "Not specified"
    sponsorship = listing.get("sponsorship") or "Not specified"
    url = listing.get("url") or listing.get("company_url")
    date_posted = listing.get("date_posted")

    env_var = category_env_var(listing)
    color = CATEGORY_COLOR.get(env_var, 0x2B2D31)

    fields = [
        {"name": "Location(s)", "value": locations[:1024], "inline": True},
        {"name": "Term(s)", "value": terms[:1024], "inline": True},
        {"name": "Sponsorship", "value": str(sponsorship)[:1024], "inline": True},
    ]
    if env_var == UNCATEGORIZED_ENV_VAR:
        fields.append(
            {
                "name": "Category",
                "value": listing.get("category") or "(none)",
                "inline": True,
            }
        )

    embed = {
        "title": f"{company} — {title}"[:256],
        "url": url,
        "color": color,
        "fields": fields,
        "footer": {"text": "Simplify · Summer2027-Internships"},
    }
    if date_posted:
        embed["timestamp"] = datetime.fromtimestamp(
            date_posted, tz=timezone.utc
        ).isoformat()
    return embed


def post_embeds(webhook_url: str, embeds: list[dict]) -> None:
    for i in range(0, len(embeds), DISCORD_EMBEDS_PER_MESSAGE):
        chunk = embeds[i : i + DISCORD_EMBEDS_PER_MESSAGE]
        payload = {"embeds": chunk}
        resp = requests.post(webhook_url, json=payload, timeout=15)

        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 2)
            print(f"  rate limited, retrying after {retry_after}s", file=sys.stderr)
            time.sleep(float(retry_after))
            resp = requests.post(webhook_url, json=payload, timeout=15)

        if not resp.ok:
            print(
                f"  failed to post {len(chunk)} embed(s): "
                f"{resp.status_code} {resp.text[:300]}",
                file=sys.stderr,
            )
        else:
            print(f"  posted {len(chunk)} embed(s)")

        time.sleep(1) 


def main() -> int:
    print(f"[{datetime.now(timezone.utc).isoformat()}] Checking for new internships…")

    try:
        listings = fetch_listings()
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Failed to fetch/parse listings.json: {e}", file=sys.stderr)
        return 1

    seen_ids, is_first_run = load_seen_ids()

    active_visible_ids = {
        listing["id"]
        for listing in listings
        if listing.get("id") and listing.get("is_visible") and listing.get("active")
    }

    if is_first_run:
        print(
            f"No state file found — bootstrapping with {len(active_visible_ids)} "
            "existing active listings. Nothing will be posted this run."
        )
        save_seen_ids(active_visible_ids)
        return 0

    new_listings = [
        listing
        for listing in listings
        if listing.get("id")
        and listing["id"] in active_visible_ids
        and listing["id"] not in seen_ids
    ]

    print(f"Fetched {len(listings)} listings, {len(new_listings)} new.")

    by_webhook: dict[str, list[dict]] = {}
    uncategorized: set[str] = set()

    for listing in new_listings:
        env_var = category_env_var(listing)
        if env_var == UNCATEGORIZED_ENV_VAR:
            uncategorized.add(listing.get("category") or "(none)")

        webhook_url = os.environ.get(env_var)
        if not webhook_url:
            print(f"  {env_var} is not set, skipping listing {listing['id']}", file=sys.stderr)
            continue

        by_webhook.setdefault(webhook_url, []).append(listing)

    if uncategorized:
        print(f"Routed unmapped categories to uncategorized: {sorted(uncategorized)}")

    for webhook_url, listings_for_webhook in by_webhook.items():
        embeds = [build_embed(listing) for listing in listings_for_webhook]
        print(f"Posting {len(embeds)} new listing(s) to webhook…")
        post_embeds(webhook_url, embeds)

    save_seen_ids(seen_ids | active_visible_ids)

    return 0


if __name__ == "__main__":
    sys.exit(main())
