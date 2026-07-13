import os
import time

import requests

import insforge_store

CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")

TOKEN_URL = "https://www.strava.com/oauth/token"
API_BASE = "https://www.strava.com/api/v3"

# Refresh this many seconds before actual expiry to avoid using a stale token mid-request.
EXPIRY_BUFFER_SECONDS = 60


def save_tokens(data):
    return insforge_store.save_tokens(data)


def load_tokens():
    return insforge_store.load_tokens()


def exchange_code_for_token(code):
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        },
    )
    resp.raise_for_status()
    tokens = resp.json()
    save_tokens(tokens)
    return tokens


def refresh_access_token():
    tokens = load_tokens()
    if not tokens or "refresh_token" not in tokens:
        raise RuntimeError("No refresh token available. Complete /login first.")

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        },
    )
    resp.raise_for_status()
    new_tokens = resp.json()
    save_tokens(new_tokens)
    return new_tokens


def get_valid_access_token():
    tokens = load_tokens()
    if not tokens:
        raise RuntimeError("Not authenticated. Visit /login first.")

    if tokens.get("expires_at", 0) - EXPIRY_BUFFER_SECONDS <= time.time():
        tokens = refresh_access_token()

    return tokens["access_token"]


def api_get(path, params=None):
    token = get_valid_access_token()
    resp = requests.get(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
    )
    resp.raise_for_status()
    return resp.json()


def api_put(path, data=None):
    token = get_valid_access_token()
    resp = requests.put(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
    )
    resp.raise_for_status()
    return resp.json()


def append_activity_description(activity_id, addition):
    current = api_get(f"/activities/{activity_id}").get("description") or ""
    new_description = f"{current.rstrip()}\n\n{addition}" if current.strip() else addition
    return api_put(f"/activities/{activity_id}", data={"description": new_description})
