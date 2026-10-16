import pytest

from app.gate.identity import (
    extract_code,
    hash_code,
    hash_phone,
    new_invite_code,
    normalize_phone,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("919876543210", "+919876543210"),
        ("+91 98765-43210", "+919876543210"),
        ("+14155550123", "+14155550123"),
    ],
)
def test_normalize_phone(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "+0123456789", "12345"])
def test_normalize_phone_rejects_garbage(raw: str) -> None:
    with pytest.raises(ValueError, match="E.164"):
        normalize_phone(raw)


def test_phone_hash_is_keyed() -> None:
    assert hash_phone("+919876543210", "k1") != hash_phone("+919876543210", "k2")
    assert hash_phone("+919876543210", "k1") == hash_phone("+919876543210", "k1")


def test_codes_are_unique_and_extractable() -> None:
    codes = {new_invite_code() for _ in range(200)}
    assert len(codes) == 200
    code = codes.pop()
    assert extract_code(f"hi! JOIN {code.lower()} thanks") == code
    assert hash_code(code) == hash_code(code.lower())


@pytest.mark.parametrize("text", [None, "", "JOIN CTF-123", "CTF-ABCDEFGHI0"])
def test_extract_code_ignores_non_codes(text: str | None) -> None:
    assert extract_code(text) is None
