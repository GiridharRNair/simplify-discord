# Discord For Simplify Jobs

[![Join us on Discord](https://img.shields.io/badge/Discord-Join%20the%20server-5865F2?logo=discord&logoColor=white)](https://discord.gg/RRpXJZjxhM)

A cron job that watches the Simplify Jobs [internship](https://github.com/SimplifyJobs/Summer2027-Internships) and [new-grad](https://github.com/SimplifyJobs/New-Grad-Positions) listings, and posts new ones to Discord — sorted into channels by category (Software, Product, Data Science/AI/ML, Quant, Hardware).

## How it works

Every 15 minutes, [cron-job.org](https://cron-job.org) hits a small API endpoint hosted on Vercel. That endpoint triggers this repo's GitHub Actions workflow, which runs the script. This project initially used a GitHub Actions cron schedule, but that was removed because GitHub Actions cron jobs are not guaranteed to run on time.


The script does the following:

1. Fetches the latest listings from Simplify's internship and new-grad repos.
2. Compares them against seen job listings stored in the `data` directory.
3. Posts each new listing as a Discord embed to the webhook for its category.
4. Saves the updated list of seen jobs to the `data` directory and commits it back to the repo.





