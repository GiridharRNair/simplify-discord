import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

STATE_DIR = Path(__file__).resolve().parent.parent / "data" / "seen_ids"

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


def validate_listings(
    listings: list[dict], *, schema: dict[str, type], label: str
) -> list[dict]:
    valid_listing = []
    dropped = 0
    for listing in listings:
        if all(
            field in listing and isinstance(listing[field], type_)
            for field, type_ in schema.items()
        ):
            valid_listing.append(listing)
        else:
            dropped += 1

    if dropped:
        print(
            f"[{label}] dropped {dropped}/{len(listings)} listing(s) failing schema",
            file=sys.stderr,
        )

    if listings and not valid_listing:
        raise ValueError(
            f"[{label}] 0/{len(listings)} listings matched the expected schema "
            "— upstream shape likely changed"
        )

    if valid_listing and not any(
        listing.get("active") and listing.get("is_visible") for listing in valid_listing
    ):
        raise ValueError(
            f"[{label}] {len(valid_listing)} listing(s) parsed but "
            "none have the active/visible flags set — upstream shape likely changed"
        )

    return valid_listing


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


def build_embed(listing: dict, *, show_terms: bool, footer: str) -> dict:
    company = listing.get("company_name", "Unknown Company").strip()
    title = listing.get("title", "Untitled Role").strip()
    locations = ", ".join(listing.get("locations", [])) or "Not specified"
    sponsorship = listing.get("sponsorship") or "Not specified"
    url = listing.get("url") or listing.get("company_url")
    date_posted = listing.get("date_posted")

    category = (listing.get("category") or "").strip().lower()
    color = CATEGORY_COLOR.get(category, UNCATEGORIZED_COLOR)
    is_uncategorized = category not in CATEGORY_COLOR

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


def post_embed(webhook_url: str, embed: dict) -> bool:
    payload = {"embeds": [embed]}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)

        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 2)
            print(f"    rate limited, retrying after {retry_after}s", file=sys.stderr)
            time.sleep(float(retry_after))
            resp = requests.post(webhook_url, json=payload, timeout=15)
    except requests.RequestException as e:
        print(f"    failed to post embed: {e}", file=sys.stderr)
        return False

    time.sleep(1)  # stay comfortably under Discord's per-webhook rate limit

    if not resp.ok:
        print(
            f"    failed to post embed: {resp.status_code} {resp.text[:300]}",
            file=sys.stderr,
        )
        return False

    return True
