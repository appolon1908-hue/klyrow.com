"""Fail-closed Postal transport selection without storing API keys in the database.

One Klyrow deployment can serve domains that live on different Postal servers.
The registry contains only routing metadata and secret *file references*.  It is
safe to mount the registry read-only in both the gateway and mail worker.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


@dataclass(frozen=True)
class PostalTransport:
    name: str
    api_url: str
    api_host: str | None
    api_key_file: Path
    webhook_public_key_file: Path | None = None
    tenant_id: str | None = None

    def public_status(self) -> dict[str, Any]:
        try:
            credential_configured = self.api_key_file.is_file() and self.api_key_file.stat().st_size > 0
        except OSError:
            credential_configured = False
        try:
            signing_key_configured = bool(self.webhook_public_key_file and self.webhook_public_key_file.is_file() and self.webhook_public_key_file.stat().st_size > 0)
        except OSError:
            signing_key_configured = False
        return {
            "name": self.name,
            "tls": self.api_url.startswith("https://"),
            "credential_configured": credential_configured,
            "signing_key_configured": signing_key_configured,
            "tenant_mapped": bool(self.tenant_id),
        }


def _validate_transport(name: str, value: dict[str, Any]) -> PostalTransport:
    api_url = str(value.get("api_url") or "").rstrip("/")
    parsed = urlsplit(api_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError(f"invalid Postal API URL for transport {name}")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError(f"Postal transport {name} contains forbidden URL credentials")
    # Plain HTTP is accepted only for a single-label container hostname or an
    # explicitly approved private network. Public Postal APIs must use HTTPS.
    if parsed.scheme == "http" and "." in parsed.hostname and os.getenv(
        "KLYROW_POSTAL_ALLOW_PRIVATE_HTTP", "false"
    ).lower() != "true":
        raise RuntimeError(f"Postal transport {name} must use HTTPS")
    key_file = Path(str(value.get("api_key_file") or ""))
    if not key_file.is_absolute():
        raise RuntimeError(f"Postal credential path for transport {name} must be absolute")
    api_host = str(value.get("api_host") or "").strip() or None
    if api_host and any(character in api_host for character in "/:@?#"):
        raise RuntimeError(f"invalid Postal Host header for transport {name}")
    public_key_value = str(value.get("webhook_public_key_file") or "").strip()
    public_key_file = Path(public_key_value) if public_key_value else None
    if public_key_file is not None and not public_key_file.is_absolute():
        raise RuntimeError(f"Postal signing-key path for transport {name} must be absolute")
    tenant_id = str(value.get("tenant_id") or "").strip() or None
    return PostalTransport(
        name=name,
        api_url=api_url,
        api_host=api_host,
        api_key_file=key_file,
        webhook_public_key_file=public_key_file,
        tenant_id=tenant_id,
    )


def _environment_default() -> PostalTransport:
    return _validate_transport(
        "default",
        {
            "api_url": os.getenv("KLYROW_POSTAL_API_URL", ""),
            "api_host": os.getenv("KLYROW_POSTAL_API_HOST_HEADER", ""),
            "api_key_file": os.getenv("KLYROW_POSTAL_API_KEY_FILE", ""),
            "webhook_public_key_file": os.getenv("KLYROW_POSTAL_WEBHOOK_PUBLIC_KEY", ""),
            "tenant_id": os.getenv("KLYROW_POSTAL_TENANT_ID", ""),
        },
    )


def load_transport_registry() -> tuple[PostalTransport, dict[str, PostalTransport]]:
    registry_path = os.getenv("KLYROW_POSTAL_TRANSPORTS_FILE", "").strip()
    if not registry_path:
        return _environment_default(), {}
    path = Path(registry_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError("Postal transport registry is unavailable or invalid") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise RuntimeError("unsupported Postal transport registry version")
    default_value = payload.get("default")
    domains_value = payload.get("domains", {})
    if not isinstance(default_value, dict) or not isinstance(domains_value, dict):
        raise RuntimeError("invalid Postal transport registry structure")
    default = _validate_transport("default", default_value)
    domains: dict[str, PostalTransport] = {}
    for raw_domain, value in domains_value.items():
        domain = str(raw_domain).strip().lower().rstrip(".")
        if not domain or "@" in domain or not isinstance(value, dict):
            raise RuntimeError("invalid domain in Postal transport registry")
        domains[domain] = _validate_transport(domain, value)
    return default, domains


def resolve_postal_transport(sender_or_domain: str) -> PostalTransport:
    value = sender_or_domain.strip().lower().rstrip(".")
    domain = value.rsplit("@", 1)[-1]
    default, domains = load_transport_registry()
    return domains.get(domain, default)


def authorized_postal_transports() -> list[PostalTransport]:
    try:
        default, domains = load_transport_registry()
    except RuntimeError:
        if os.getenv("KLYROW_POSTAL_TRANSPORTS_FILE", "").strip():
            raise
        public_key = os.getenv("KLYROW_POSTAL_WEBHOOK_PUBLIC_KEY", "").strip()
        if not public_key:
            raise
        default = PostalTransport(name="default", api_url="https://unconfigured.invalid",
            api_host=None, api_key_file=Path("/nonexistent"),
            webhook_public_key_file=Path(public_key),
            tenant_id=os.getenv("KLYROW_POSTAL_TENANT_ID", "").strip() or None)
        domains = {}
    result: list[PostalTransport] = []
    seen: set[tuple[str, str]] = set()
    for transport in [default, *domains.values()]:
        identity = (transport.name, str(transport.webhook_public_key_file or ""))
        if identity not in seen:
            seen.add(identity)
            result.append(transport)
    return result


def postal_api_key(transport: PostalTransport) -> str:
    try:
        key = transport.api_key_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError("Postal credential is unavailable") from exc
    if not key:
        raise RuntimeError("Postal credential is unavailable")
    return key


def postal_headers(transport: PostalTransport, idempotency_key: str) -> dict[str, str]:
    headers = {
        "X-Server-API-Key": postal_api_key(transport),
        "Idempotency-Key": idempotency_key,
    }
    if transport.api_host:
        headers["Host"] = transport.api_host
    return headers


def transport_status(sender_or_domain: str) -> dict[str, Any]:
    try:
        transport = resolve_postal_transport(sender_or_domain)
        status = transport.public_status()
        status["ready"] = bool(status["credential_configured"])
        status["webhook_ready"] = bool(status["signing_key_configured"] and (status["tenant_mapped"] or transport.name == "default"))
        return status
    except RuntimeError as exc:
        return {
            "name": None,
            "tls": False,
            "credential_configured": False,
            "signing_key_configured": False,
            "tenant_mapped": False,
            "ready": False,
            "webhook_ready": False,
            "error": str(exc),
        }
