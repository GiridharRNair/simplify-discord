import os

import requests
from fastapi import FastAPI, Header, HTTPException

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

app = FastAPI()

REPO = "GiridharRNair/simplify-discord"
WORKFLOW = "check-internships.yml"
SIMPLIFY_DISCORD_REPO_WORKFLOW_DISPATCH = os.environ.get(
    "SIMPLIFY_DISCORD_REPO_WORKFLOW_DISPATCH"
)
if not SIMPLIFY_DISCORD_REPO_WORKFLOW_DISPATCH:
    raise RuntimeError(
        "SIMPLIFY_DISCORD_REPO_WORKFLOW_DISPATCH environment variable is not set"
    )
CRON_SECRET = os.environ.get("CRON_SECRET")
if not CRON_SECRET:
    raise RuntimeError("CRON_SECRET environment variable is not set")


@app.post("/api/trigger")
def trigger(authorization: str = Header(None)):
    if authorization != f"Bearer {CRON_SECRET}":
        raise HTTPException(status_code=401)

    response = requests.post(
        f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches",
        headers={
            "Authorization": f"Bearer {SIMPLIFY_DISCORD_REPO_WORKFLOW_DISPATCH}",
            "Accept": "application/vnd.github+json",
        },
        json={"ref": "main"},
        timeout=10,
    )

    if response.status_code != 204:
        raise HTTPException(status_code=502, detail=response.text)

    return {"status": "triggered"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
