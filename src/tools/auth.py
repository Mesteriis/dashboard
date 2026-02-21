from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from time import time


@dataclass(frozen=True)
class AuthFailure(Exception):
    status_code: int
    detail: str


def ensure_admin_token(token: str | None, *, admin_token: str) -> None:
    if not admin_token:
        raise AuthFailure(
            status_code=503,
            detail=(
                "Admin token is not configured. "
                "Set DASHBOARD_ADMIN_TOKEN to enable protected actions."
            ),
        )
    if token is None or not hmac.compare_digest(token, admin_token):
        raise AuthFailure(status_code=401, detail="Invalid admin token")


@dataclass(frozen=True)
class ProxyAccessSigner:
    secret: str
    ttl_sec: int

    def build_token(self, item_id: str) -> str | None:
        if not self.secret:
            return None
        expires_at = int(time()) + self.ttl_sec
        payload = f"{item_id}:{expires_at}"
        signature = hmac.new(
            self.secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{expires_at}.{signature}"

    def is_valid(self, token: str | None, *, item_id: str) -> bool:
        if not self.secret or not token:
            return False

        expires_raw, separator, signature = token.partition(".")
        if not separator:
            return False

        try:
            expires_at = int(expires_raw)
        except ValueError:
            return False

        if expires_at < int(time()):
            return False

        payload = f"{item_id}:{expires_at}"
        expected_signature = hmac.new(
            self.secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
