import yaml
import json
import os
from datetime import date

KEYS_FILE = os.path.expanduser("~/.shrri/keys.yaml")
USAGE_FILE = os.path.expanduser("~/.shrri/usage.json")


class KeyManager:
    def __init__(self):
        self.config = self._load_keys()
        self.usage = self._load_usage()
        self.cooldowns = {}

    def _get_fernet(self):
        from .crypto import load_key
        return load_key()

    def _load_keys(self):
        enc_path = KEYS_FILE + ".enc"
        if os.path.exists(enc_path):
            from .crypto import load_key, decrypt_file
            fernet = load_key()
            data = decrypt_file(KEYS_FILE, fernet)
            return yaml.safe_load(data.decode())
        # Fallback to plain file
        with open(KEYS_FILE, "r") as f:
            return yaml.safe_load(f)

    def _load_usage(self):
        today = str(date.today())
        enc_path = USAGE_FILE + ".enc"

        if os.path.exists(enc_path):
            from .crypto import load_key, decrypt_file
            fernet = load_key()
            raw = decrypt_file(USAGE_FILE, fernet)
            if raw:
                data = json.loads(raw.decode())
                if data.get("date") != today:
                    return {"date": today, "usage": {}}
                return data
            return {"date": today, "usage": {}}

        # Fallback to plain file
        if os.path.exists(USAGE_FILE):
            with open(USAGE_FILE, "r") as f:
                data = json.load(f)
            if data.get("date") != today:
                return {"date": today, "usage": {}}
            return data

        return {"date": today, "usage": {}}

    def _save_usage(self):
        enc_path = USAGE_FILE + ".enc"
        if os.path.exists(enc_path) or not os.path.exists(USAGE_FILE):
            from .crypto import load_key, encrypt_text
            fernet = load_key()
            encrypted = encrypt_text(json.dumps(self.usage, indent=2), fernet)
            with open(enc_path, "wb") as f:
                f.write(encrypted)
        else:
            with open(USAGE_FILE, "w") as f:
                json.dump(self.usage, f, indent=2)

    def get_best_key(self, provider, exclude_ids=None):
        import time
        config = self.config["providers"].get(provider)
        if not config:
            return None, None

        daily_limit = config.get("daily_limit", 999999999)
        keys = config.get("keys", [])
        exclude_ids = exclude_ids or set()
        now = time.time()

        for key_entry in keys:
            key_id = key_entry["id"]
            if key_id in exclude_ids:
                continue
            if self.cooldowns.get(key_id, 0) > now:
                continue
            used = self.usage["usage"].get(key_id, 0)
            if used < daily_limit:
                return key_entry["key"], key_id

        return None, None

    def get_all_keys(self, provider):
        config = self.config["providers"].get(provider, {})
        return config.get("keys", [])

    def mark_cooldown(self, key_id, seconds=60):
        import time
        self.cooldowns[key_id] = time.time() + seconds

    def mark_used(self, key_id):
        if key_id:
            self.usage["usage"][key_id] = self.usage["usage"].get(key_id, 0) + 1
            self._save_usage()

    def get_model(self, provider, task="default"):
        config = self.config["providers"].get(provider, {})
        models = config.get("models", {})
        return models.get(task, models.get("default", ""))

    def get_base_url(self, provider):
        config = self.config["providers"].get(provider, {})
        return config.get("base_url", "")

    def get_status(self):
        today = str(date.today())
        status = {}
        for provider, config in self.config["providers"].items():
            daily_limit = config.get("daily_limit", 999999999)
            keys = config.get("keys", [])
            total_used = sum(self.usage["usage"].get(k["id"], 0) for k in keys)
            total_limit = daily_limit * len(keys)
            status[provider] = {
                "keys": len(keys),
                "used_today": total_used,
                "total_limit": total_limit,
                "available": total_limit - total_used
            }
        return status
