import json
import os
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import requests

STATE_DIR = Path(__file__).resolve().parent.parent / "data" / "seen_ids"

DISCORD_EMBEDS_PER_MESSAGE = 10  # Discord's hard cap per webhook execute call

CATEGORY_ENV_LABEL: dict[str, str] = {
    "software": "SOFTWARE",
    "product": "PRODUCT_MANAGEMENT",
    "ai/ml/data": "DATA_SCIENCE_ML_AI",
    "quant": "QUANTITATIVE_FINANCE",
    "hardware": "HARDWARE",
}

CATEGORY_COLOR: dict[str, int] = {
    "software": 0x5865F2,
    "product": 0x57F287,
    "ai/ml/data": 0xEB459E,
    "quant": 0xFEE75C,
    "hardware": 0xED4245,
}
UNCATEGORIZED_COLOR = 0x99AAB5


def build_category_env_map(prefix: str, suffix: str) -> dict[str, str]:
    category_env_map = {}
    for category, env_label in CATEGORY_ENV_LABEL.items():
        env_var = f"{prefix}{env_label}{suffix}"
        category_env_map[category] = env_var
    return category_env_map


def fetch_json(url: str) -> list[dict]:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def load_seen_ids(name: str) -> tuple[set[str], bool]:
    path = STATE_DIR / f"{name}.json"
    if not path.exists():
        return set(), True
    with path.open() as f:
        data = json.load(f)
    return set(data.get("seen_ids", [])), False


def save_seen_ids(name: str, seen_ids: set[str]) -> None:
    path = STATE_DIR / f"{name}.json"
    if path.exists():
        with path.open() as f:
            existing = set(json.load(f).get("seen_ids", []))
        if existing == seen_ids:
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(
            {
                "seen_ids": sorted(seen_ids),
                "last_updated": datetime.now(UTC).isoformat(),
            },
            f,
            indent=2,
        )
        f.write("\n")


def build_embed(
    listing: dict,
    *,
    category_map: dict[str, str],
    uncategorized_env_var: str,
    show_terms: bool,
    footer: str,
) -> dict:
    company = listing.get("company_name", "Unknown Company").strip()
    title = listing.get("title", "Untitled Role").strip()
    locations = ", ".join(listing.get("locations", [])) or "Not specified"
    sponsorship = listing.get("sponsorship") or "Not specified"
    url = listing.get("url") or listing.get("company_url")
    date_posted = listing.get("date_posted")

    category = (listing.get("category") or "").strip().lower()
    env_var = category_map.get(category, uncategorized_env_var)
    is_uncategorized = env_var == uncategorized_env_var
    color = CATEGORY_COLOR.get(category, UNCATEGORIZED_COLOR)

    fields = [{"name": "Location(s)", "value": locations[:1024], "inline": True}]
    if show_terms:
        terms = ", ".join(listing.get("terms", [])) or "Not specified"
        fields.append({"name": "Term(s)", "value": terms[:1024], "inline": True})
    fields.append(
        {"name": "Sponsorship", "value": str(sponsorship)[:1024], "inline": True}
    )
    if is_uncategorized:
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
        "footer": {"text": footer},
    }
    if date_posted:
        embed["timestamp"] = datetime.fromtimestamp(date_posted, tz=UTC).isoformat()
    return embed


def post_embeds(webhook_url: str, embeds: list[dict]) -> None:
    for i in range(0, len(embeds), DISCORD_EMBEDS_PER_MESSAGE):
        chunk = embeds[i : i + DISCORD_EMBEDS_PER_MESSAGE]
        payload = {"embeds": chunk}
        resp = requests.post(webhook_url, json=payload, timeout=15)

        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 2)
            print(f"    rate limited, retrying after {retry_after}s", file=sys.stderr)
            time.sleep(float(retry_after))
            resp = requests.post(webhook_url, json=payload, timeout=15)

        if not resp.ok:
            print(
                f"    failed to post {len(chunk)} embed(s): "
                f"{resp.status_code} {resp.text[:300]}",
                file=sys.stderr,
            )
        else:
            print(f"    posted {len(chunk)} embed(s)")

        time.sleep(1)  # stay comfortably under Discord's per-webhook rate limit


def notify_new_listings(
    *,
    bucket: str,
    listings: list[dict],
    category_map: dict[str, str],
    uncategorized_env_var: str,
    show_terms: bool,
    footer: str,
    term_filter: Callable[[dict], bool] | None = None,
) -> None:
    log_label = f"[{bucket}]"

    seen_ids, is_first_run = load_seen_ids(bucket)

    active_visible_ids = {
        listing["id"]
        for listing in listings
        if listing.get("id")
        and listing.get("is_visible")
        and listing.get("active")
        and (term_filter is None or term_filter(listing))
    }

    if is_first_run:
        print(
            f"{log_label} no state file found — bootstrapping with "
            f"{len(active_visible_ids)} existing active listings. Nothing "
            "will be posted this run."
        )
        save_seen_ids(bucket, active_visible_ids)
        return

    new_listings = [
        listing
        for listing in listings
        if listing.get("id")
        and listing["id"] in active_visible_ids
        and listing["id"] not in seen_ids
    ]

    print(f"{log_label} {len(new_listings)} new listing(s).")

    by_webhook: dict[str, list[dict]] = {}
    uncategorized: set[str] = set()

    for listing in new_listings:
        category = (listing.get("category") or "").strip().lower()
        env_var = category_map.get(category, uncategorized_env_var)
        if env_var == uncategorized_env_var:
            uncategorized.add(listing.get("category") or "(none)")

        webhook_url = os.environ.get(env_var)
        if not webhook_url:
            print(
                f"{log_label}   {env_var} is not set, skipping listing "
                f"{listing['id']}",
                file=sys.stderr,
            )
            continue

        by_webhook.setdefault(webhook_url, []).append(listing)

    if uncategorized:
        print(
            f"{log_label} routed unmapped categories to uncategorized: "
            f"{sorted(uncategorized)}"
        )

    for webhook_url, listings_for_webhook in by_webhook.items():
        embeds = [
            build_embed(
                listing,
                category_map=category_map,
                uncategorized_env_var=uncategorized_env_var,
                show_terms=show_terms,
                footer=footer,
            )
            for listing in listings_for_webhook
        ]
        print(f"{log_label}   posting {len(embeds)} new listing(s)…")
        post_embeds(webhook_url, embeds)

    save_seen_ids(bucket, seen_ids | active_visible_ids)
