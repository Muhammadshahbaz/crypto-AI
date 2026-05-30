import base64
import hashlib
import os
from typing import Optional

# MVP reversible secret storage.
# For production SaaS, replace with Google Secret Manager/KMS-backed encryption.
def _key() -> bytes:
    raw = os.getenv("APEX_SECRET_KEY", "change-this-secret-key-before-live")
    return hashlib.sha256(raw.encode("utf-8")).digest()

def encrypt_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    data = value.encode("utf-8")
    key = _key()
    mixed = bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
    return base64.urlsafe_b64encode(mixed).decode("utf-8")

def decrypt_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        data = base64.urlsafe_b64decode(value.encode("utf-8"))
        key = _key()
        raw = bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
        return raw.decode("utf-8")
    except Exception:
        return ""

def mask_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    plain = decrypt_secret(value)
    if not plain:
        return ""
    if len(plain) <= 8:
        return "****"
    return plain[:4] + "..." + plain[-4:]
