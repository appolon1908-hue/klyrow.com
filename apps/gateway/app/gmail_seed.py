"""Minimal, fixed-egress Gmail API adapter for seed-mailbox placement checks."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx


TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


def seed_secret_path(secret_ref: str) -> Path:
    if not secret_ref.startswith("secret://"):
        raise RuntimeError("unsupported seed credential reference")
    name = secret_ref.removeprefix("secret://")
    if not name or name.startswith("/") or ".." in Path(name).parts:
        raise RuntimeError("invalid seed credential reference")
    root = Path(os.getenv("KLYROW_SEED_SECRET_DIR", "/run/klyrow/seed-secrets")).resolve()
    path = (root / name).resolve()
    if path != root and root not in path.parents:
        raise RuntimeError("seed credential reference escapes secret directory")
    return path


def load_oauth_credential(secret_ref: str) -> dict[str, str]:
    try:
        value = json.loads(seed_secret_path(secret_ref).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError("seed OAuth credential is unavailable") from exc
    required = {"client_id", "client_secret", "refresh_token"}
    if not isinstance(value, dict) or not required.issubset(value) or any(not isinstance(value[key], str) or not value[key] for key in required):
        raise RuntimeError("seed OAuth credential is invalid")
    return {key: value[key] for key in required}


def gmail_folder(label_ids: list[str]) -> str:
    labels = set(label_ids)
    for label, folder in (
        ("SPAM", "SPAM"),
        ("TRASH", "TRASH"),
        ("CATEGORY_PROMOTIONS", "PROMOTIONS"),
        ("CATEGORY_UPDATES", "UPDATES"),
        ("CATEGORY_SOCIAL", "SOCIAL"),
        ("CATEGORY_FORUMS", "FORUMS"),
        ("INBOX", "INBOX"),
    ):
        if label in labels:
            return folder
    return "UNKNOWN"


async def check_gmail_placement(secret_ref: str, rfc_message_id: str) -> dict[str, Any]:
    credentials = load_oauth_credential(secret_ref)
    async with httpx.AsyncClient(timeout=15, trust_env=False, follow_redirects=False) as client:
        token_response = await client.post(
            TOKEN_URL,
            data={**credentials, "grant_type": "refresh_token"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_response.raise_for_status()
        access_token = str(token_response.json().get("access_token") or "")
        if not access_token:
            raise RuntimeError("Gmail OAuth response omitted access token")
        headers = {"Authorization": "Bearer " + access_token}
        query_response = await client.get(
            GMAIL_API + "/messages",
            headers=headers,
            params={"q": "rfc822msgid:" + rfc_message_id, "maxResults": "1"},
        )
        query_response.raise_for_status()
        messages = query_response.json().get("messages") or []
        if not messages:
            return {"folder": "NOT_FOUND", "opened": False, "provider_message_id": None}
        provider_message_id = str(messages[0]["id"])
        detail_response = await client.get(
            GMAIL_API + "/messages/" + provider_message_id,
            headers=headers,
            params={"format": "minimal"},
        )
        detail_response.raise_for_status()
        labels = detail_response.json().get("labelIds") or []
    return {"folder": gmail_folder(labels), "opened": "UNREAD" not in labels, "provider_message_id": provider_message_id}
