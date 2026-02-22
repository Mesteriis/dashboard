from __future__ import annotations

from faker import Faker

from tools.auth import ProxyAccessSigner


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
