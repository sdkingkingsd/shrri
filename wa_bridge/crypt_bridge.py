"""
Encrypt/decrypt wa_bridge sensitive files using SHRRI's existing Fernet key.

Usage:
  python3 crypt_bridge.py encrypt-json <file>   # encrypt a JSON file in place
  python3 crypt_bridge.py decrypt-json <file>   # decrypt to stdout
  python3 crypt_bridge.py lock-auth             # zip + encrypt auth/ folder
  python3 crypt_bridge.py unlock-auth           # decrypt + unzip auth/ folder
"""
import sys, os, json, zipfile, shutil

BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_DIR   = os.path.join(BRIDGE_DIR, "auth")
AUTH_ZIP   = os.path.join(BRIDGE_DIR, "auth.zip")
AUTH_ENC   = os.path.join(BRIDGE_DIR, "auth.zip.enc")

sys.path.insert(0, os.path.expanduser("~/shrri"))
from engine.crypto import load_key, encrypt_file, decrypt_file

def get_fernet():
    return load_key()

def encrypt_json(path):
    if not os.path.exists(path):
        return
    fernet = get_fernet()
    with open(path, "rb") as f:
        data = f.read()
    enc = fernet.encrypt(data)
    with open(path + ".enc", "wb") as f:
        f.write(enc)
    os.remove(path)

def decrypt_json(path):
    enc_path = path + ".enc"
    if not os.path.exists(enc_path):
        # Already plain — just print it
        if os.path.exists(path):
            with open(path) as f:
                print(f.read(), end="")
        return
    fernet = get_fernet()
    with open(enc_path, "rb") as f:
        enc = f.read()
    data = fernet.decrypt(enc)
    # Restore plain file, remove enc
    with open(path, "wb") as f:
        f.write(data)
    os.remove(enc_path)
    print(data.decode(), end="")

def lock_auth():
    """Zip auth/ then encrypt the zip, remove plain auth/."""
    if not os.path.exists(AUTH_DIR):
        return
    # Create zip
    with zipfile.ZipFile(AUTH_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(AUTH_DIR):
            for fname in files:
                fpath = os.path.join(root, fname)
                zf.write(fpath, os.path.relpath(fpath, BRIDGE_DIR))
    # Encrypt zip
    fernet = get_fernet()
    with open(AUTH_ZIP, "rb") as f:
        data = f.read()
    with open(AUTH_ENC, "wb") as f:
        f.write(fernet.encrypt(data))
    os.remove(AUTH_ZIP)
    shutil.rmtree(AUTH_DIR)
    print("[crypt_bridge] auth/ locked.")

def unlock_auth():
    """Decrypt auth.zip.enc and unzip to auth/."""
    if not os.path.exists(AUTH_ENC):
        print("[crypt_bridge] No encrypted auth found — skipping unlock.")
        return
    fernet = get_fernet()
    with open(AUTH_ENC, "rb") as f:
        enc = f.read()
    data = fernet.decrypt(enc)
    with open(AUTH_ZIP, "wb") as f:
        f.write(data)
    with zipfile.ZipFile(AUTH_ZIP, "r") as zf:
        zf.extractall(BRIDGE_DIR)
    os.remove(AUTH_ZIP)
    os.remove(AUTH_ENC)
    print("[crypt_bridge] auth/ unlocked.")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "encrypt-json":
        encrypt_json(sys.argv[2])
    elif cmd == "decrypt-json":
        decrypt_json(sys.argv[2])
    elif cmd == "lock-auth":
        lock_auth()
    elif cmd == "unlock-auth":
        unlock_auth()
    else:
        print(__doc__)
