import os

import requests

API_URL = os.environ.get("INSFORGE_API_URL", "").rstrip("/")
API_KEY = os.environ.get("INSFORGE_API_KEY")

TABLE = "strava_tokens"
SERVICE = "strava"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def save_tokens(data):
    payload = {
        "service": SERVICE,
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": data["expires_at"],
        "expires_in": data.get("expires_in"),
        "token_type": data.get("token_type"),
        "scope": data.get("scope"),
        "athlete": data.get("athlete"),
    }
    resp = requests.post(
        f"{API_URL}/api/database/records/{TABLE}",
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=representation"},
        json=[payload],
    )
    resp.raise_for_status()
    return resp.json()[0]


def load_tokens():
    resp = requests.get(
        f"{API_URL}/api/database/records/{TABLE}",
        headers=HEADERS,
        params={"service": f"eq.{SERVICE}", "limit": 1},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None
