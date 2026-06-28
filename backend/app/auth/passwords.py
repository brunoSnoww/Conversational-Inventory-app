from __future__ import annotations

import base64
import re
import secrets
from hashlib import pbkdf2_hmac

_DJANGO_PBKDF2_RE = re.compile(r"^pbkdf2_sha256\$(\d+)\$([^$]+)\$(.+)$")
_DEFAULT_ITERATIONS = 600_000


def _encode_digest(digest: bytes) -> str:
    return base64.b64encode(digest).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(12)
    digest = pbkdf2_hmac("sha256", password.encode(), salt.encode(), _DEFAULT_ITERATIONS)
    return f"pbkdf2_sha256${_DEFAULT_ITERATIONS}${salt}${_encode_digest(digest)}"


def verify_password(password: str, stored: str) -> bool:
    match = _DJANGO_PBKDF2_RE.match(stored)
    if not match:
        return False
    iterations = int(match.group(1))
    salt = match.group(2)
    expected = match.group(3)
    digest = pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    encoded = _encode_digest(digest)
    if secrets.compare_digest(encoded, expected):
        return True
    # Legacy FastAPI hashes used hex instead of Django's base64.
    return secrets.compare_digest(digest.hex(), expected)
