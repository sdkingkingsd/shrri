import os
import base64
import hashlib
from cryptography.fernet import Fernet
from getpass import getpass

KEY_FILE = os.path.expanduser("~/.shrri/.shrri_key")

_cached_fernet = None


def _derive_key(password: str) -> bytes:
    """Derive a Fernet key from a password using SHA256."""
    digest = hashlib.sha256(password.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def setup_encryption(password: str = None):
    """
    First-time setup — create encryption key from password.
    Saves derived key to ~/.shrri/.shrri_key
    """
    if not password:
        password = getpass("Set SHRRI master password: ")
        confirm = getpass("Confirm password: ")
        if password != confirm:
            print("Passwords don't match!")
            return False

    key = _derive_key(password)
    os.makedirs(os.path.expanduser("~/.shrri"), exist_ok=True)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    os.chmod(KEY_FILE, 0o600)  # Only owner can read
    print("✅ Encryption key saved.")
    return True


_cached_fernet = None

def load_key(password: str = None) -> Fernet:
    """Load encryption key. Caches in memory. Checks env var before prompting."""
    global _cached_fernet
    if _cached_fernet is not None:
        return _cached_fernet

    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            key = f.read()
        _cached_fernet = Fernet(key)
        return _cached_fernet

    # Key file missing — check env var first (for services), then prompt
    if not password:
        password = os.environ.get("SHRRI_MASTER_PASSWORD")
    if not password:
        password = getpass("SHRRI master password: ")
    key = _derive_key(password)
    _cached_fernet = Fernet(key)
    return _cached_fernet


def encrypt_file(filepath: str, fernet: Fernet = None):
    """Encrypt a file in place."""
    if not os.path.exists(filepath):
        return

    if fernet is None:
        fernet = load_key()

    with open(filepath, "rb") as f:
        data = f.read()

    encrypted = fernet.encrypt(data)

    with open(filepath + ".enc", "wb") as f:
        f.write(encrypted)

    os.remove(filepath)
    pass  # silent encrypt


def decrypt_file(filepath: str, fernet: Fernet = None) -> bytes:
    """Decrypt a .enc file and return contents."""
    enc_path = filepath + ".enc"

    if not os.path.exists(enc_path):
        # Try plain file
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                return f.read()
        return b""

    if fernet is None:
        fernet = load_key()

    with open(enc_path, "rb") as f:
        encrypted = f.read()

    return fernet.decrypt(encrypted)


def encrypt_text(text: str, fernet: Fernet = None) -> bytes:
    """Encrypt a string and return encrypted bytes."""
    if fernet is None:
        fernet = load_key()
    return fernet.encrypt(text.encode())


def decrypt_text(encrypted: bytes, fernet: Fernet = None) -> str:
    """Decrypt encrypted bytes and return string."""
    if fernet is None:
        fernet = load_key()
    return fernet.decrypt(encrypted).decode()


def encrypt_all_shrri_files():
    """Encrypt all sensitive SHRRI files."""
    fernet = load_key()

    files_to_encrypt = [
        os.path.expanduser("~/.shrri/keys.yaml"),
        os.path.expanduser("~/.shrri/usage.json"),
        os.path.expanduser("~/.shrri/memory.json"),
        os.path.expanduser("~/.shrri/experiences.json"),
        os.path.expanduser("~/.shrri/facts.json"),
    ]

    print("\n🔐 Encrypting SHRRI files...")
    for f in files_to_encrypt:
        if os.path.exists(f):
            encrypt_file(f, fernet)
        else:
            print(f"  ⏭ Skipped (not found): {f}")

    print("\n✅ All files encrypted.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_encryption()
        encrypt_all_shrri_files()
    elif len(sys.argv) > 1 and sys.argv[1] == "encrypt":
        encrypt_all_shrri_files()
    else:
        print("Usage:")
        print("  python3 crypto.py setup    — first time setup + encrypt all files")
        print("  python3 crypto.py encrypt  — encrypt all files with existing key")
