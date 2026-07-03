"""
Secrets Manager — SHRRI Phase 13
Stores secrets encrypted at rest. Never logs values.
"""
import os, json, base64, hashlib
from pathlib import Path

SECRETS_PATH = Path.home() / ".shrri" / "secrets.enc"
_SALT = b"shrri_secrets_v1"


def _derive_key(passphrase: str) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode(), _SALT, 100_000)


def _xor_encrypt(data: bytes, key: bytes) -> bytes:
    key_cycle = (key * (len(data) // len(key) + 1))[:len(data)]
    return bytes(a ^ b for a, b in zip(data, key_cycle))


class SecretsManager:
    def __init__(self, passphrase: str = "shrri_default"):
        self._key = _derive_key(passphrase)
        self._secrets = self._load()

    def _load(self) -> dict:
        if not SECRETS_PATH.exists():
            return {}
        try:
            raw = base64.b64decode(SECRETS_PATH.read_bytes())
            decrypted = _xor_encrypt(raw, self._key)
            return json.loads(decrypted.decode())
        except Exception:
            return {}

    def _save(self):
        data = json.dumps(self._secrets).encode()
        encrypted = _xor_encrypt(data, self._key)
        SECRETS_PATH.write_bytes(base64.b64encode(encrypted))

    def set(self, name: str, value: str):
        self._secrets[name] = value
        self._save()

    def get(self, name: str, default: str = "") -> str:
        # Also check env vars first
        env_val = os.environ.get(name.upper())
        if env_val:
            return env_val
        return self._secrets.get(name, default)

    def delete(self, name: str):
        self._secrets.pop(name, None)
        self._save()

    def list_keys(self) -> list:
        return list(self._secrets.keys())
