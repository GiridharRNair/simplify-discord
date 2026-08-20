# Discord For Simplify Jobs

[![Join us on Discord](https://img.shields.io/badge/Discord-Join%20the%20server-5865F2?logo=discord&logoColor=white)](https://discord.gg/RRpXJZjxhM)

A cron job that watches the [Simplify Jobs](https://github.com/SimplifyJobs) internship and new-grad listings, and posts new ones to Discord — sorted into channels by category (Software, Product, Data Science/AI/ML, Quant, Hardware).

## How it works

Every hour, a GitHub Actions workflow runs the script. It:

1. Fetches the latest listings from Simplify's public repos ([Summer Internships](https://github.com/SimplifyJobs/Summer2027-Internships) and [New Grad Positions](https://github.com/SimplifyJobs/New-Grad-Positions)).
2. Compares them against `data/seen_ids/` — a record of listings already posted.
3. Splits the new ones into three feeds: **summer internships**, **off-season internships**, and **new grad**.
4. Posts each new listing as a Discord embed to the webhook for its category.
5. Saves the updated list of seen IDs and commits it back to the repo, so nothing gets posted twice.

On the very first run for a given feed, nothing is posted — it just records what's currently live so future runs only announce what's actually new.


