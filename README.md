# simplify-discord

Posts newly listed internships from [SimplifyJobs/Summer2027-Internships](https://github.com/SimplifyJobs/Summer2027-Internships)
to category-specific Discord webhooks, on an hourly GitHub Actions cron.

## How it works

- `main.py` fetches [`listings.json`](https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/refs/heads/dev/.github/scripts/listings.json)
  directly (not the README), diffs it against `data/seen_ids.json`, and posts
  any listing that is both new and currently `active`/`is_visible` to the
  matching webhook as a Discord embed.
- Each listing's `category` is mapped to one of the five webhooks below
  (`CATEGORY_MAP` in `main.py` handles a couple of known spelling variants
  the upstream repo has used, e.g. "Software" vs "Software Engineering").
- `data/seen_ids.json` is committed back to the repo by the workflow after
  every run, so state survives across ephemeral GitHub Actions runners.
- **First run is a silent bootstrap**: it records every currently
  active listing as "seen" but posts nothing, so you don't get ~1,800
  messages blasted into your channels on day one.

## Setup

1. Push this repo to GitHub.
2. In **Settings → Secrets and variables → Actions**, add these 6 repository
   secrets (values from your `.env`):
   - `SOFTWARE_INTERNSHIPS_WEBHOOK_URL`
   - `PRODUCT_MANAGEMENT_INTERNSHIPS_WEBHOOK_URL`
   - `DATA_SCIENCE_ML_AI_INTERNSHIPS_WEBHOOK_URL`
   - `QUANTITATIVE_FINANCE_INTERNSHIPS_WEBHOOK_URL`
   - `HARDWARE_INTERNSHIPS_WEBHOOK_URL`
   - `UNCATEGORIZED_INTERNSHIPS_WEBHOOK_URL` — catch-all for any listing
     whose `category` doesn't match one of the five above (upstream has
     occasionally used other spellings/values; these get a "Category"
     field showing the raw string so it's clear why it landed here)
3. That's it — `.github/workflows/check-internships.yml` runs hourly
   (`workflow_dispatch` is also enabled, so you can trigger a run manually
   from the Actions tab to test).

`.env` stays local-only for testing (`python main.py` with `python-dotenv`
installed) and is gitignored — it is never read in CI.

## Local testing

```bash
pip install -r requirements.txt
python main.py
```

Delete `data/seen_ids.json` to re-trigger a bootstrap run (no Discord
messages), or manually remove an id from it to force a re-notification of
that one listing.

## Adjusting the interval

Edit the `cron` expression in `.github/workflows/check-internships.yml`
(currently `0 * * * *`, top of every hour, UTC). GitHub Actions schedules
are best-effort and can lag during high load — don't rely on exact timing.
