"""Phone numbers and invite codes: normalisation, hashing and extraction."""

import hashlib
import hmac
import re
import secrets

E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")
# No 0/O/1/I to avoid misreads when typed by hand.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LEN = 10
CODE_PATTERN = re.compile(rf"\bCTF-([{CODE_ALPHABET}]{{{CODE_LEN}}})\b", re.IGNORECASE)


def normalize_phone(raw: str) -> str:
    """Return E.164. WhatsApp sends wa_id as bare digits with country code ("919876543210")."""
    digits = re.sub(r"[\s\-()]", "", raw)
    if not digits.startswith("+"):
        digits = "+" + digits
    if not E164.match(digits):
        raise ValueError(f"not an E.164 phone number: {raw!r}")
    return digits


def hash_phone(phone_e164: str, key: str) -> str:
    return hmac.new(key.encode(), phone_e164.encode(), hashlib.sha256).hexdigest()


def new_invite_code() -> str:
    return "CTF-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LEN))


def hash_code(code: str) -> str:
    """Codes are ~50 bits of randomness, single-use and attempt-limited, so SHA-256 suffices."""
    return hashlib.sha256(code.upper().encode()).hexdigest()


def extract_code(text: str | None) -> str | None:
    if not text:
        return None
    m = CODE_PATTERN.search(text)
    return f"CTF-{m.group(1).upper()}" if m else None
