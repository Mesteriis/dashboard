from __future__ import annotations

import pytest
from faker import Faker

from tools.auth import AuthFailure, ProxyAccessSigner, ensure_admin_token


def test_ensure_admin_token_requires_configured_secret(fake: Faker) -> None:
    with pytest.raises(AuthFailure) as exc_info:
        ensure_admin_token(token=fake.pystr(min_chars=4, max_chars=12), admin_token="")

    assert exc_info.value.status_code == 503


@pytest.mark.parametrize(
    ("token", "admin_token", "expected_status"),
    [
        ("invalid", "secret", 401),
        (None, "secret", 401),
    ],
)
def test_ensure_admin_token_rejects_invalid_token(
    token: str | None,
    admin_token: str,
    expected_status: int,
) -> None:
    with pytest.raises(AuthFailure) as exc_info:
        ensure_admin_token(token=token, admin_token=admin_token)

    assert exc_info.value.status_code == expected_status


def test_ensure_admin_token_accepts_valid_token(fake: Faker) -> None:
    admin_token = fake.pystr(min_chars=8, max_chars=16)
    ensure_admin_token(token=admin_token, admin_token=admin_token)


def test_proxy_access_signer_returns_none_without_secret() -> None:
    signer = ProxyAccessSigner(secret="", ttl_sec=60)
    assert signer.build_token("item") is None
    assert signer.is_valid("1.signature", item_id="item") is False


def test_proxy_access_signer_validates_signed_token(fake: Faker) -> None:
    item_id = fake.slug()
    signer = ProxyAccessSigner(secret="proxy-secret", ttl_sec=60)

    token = signer.build_token(item_id)

    assert token is not None
    assert signer.is_valid(token, item_id=item_id)
    assert not signer.is_valid(token, item_id=f"{item_id}-other")
    assert not signer.is_valid("broken-token", item_id=item_id)


def test_proxy_access_signer_rejects_expired_tokens() -> None:
    signer = ProxyAccessSigner(secret="proxy-secret", ttl_sec=-1)
    token = signer.build_token("item-1")

    assert token is not None
    assert not signer.is_valid(token, item_id="item-1")
