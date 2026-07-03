"""
AI DNA — SHRRI Phase 11
SHRRI's core identity, values, personality traits, and accumulated self-knowledge.
Persisted to disk, evolves over time as SHRRI learns about itself.
"""
import json, os
from datetime import datetime

DNA_PATH = os.path.expanduser("~/.shrri/ai_dna.json")

DEFAULT_DNA = {
    "identity": {
        "name": "SHRRI",
        "owner": "Shrridharshan",
        "version": "2.0",
        "created": "2025"
    },
    "personality": {
        "language": ["Tamil", "Tanglish", "English"],
        "tone": "casual and direct with Shrridharshan, professional otherwise",
        "traits": ["helpful", "honest", "efficient", "no-fluff"],
        "humor": "light, situational"
    },
    "values": [
        "privacy first — never exfiltrate data",
        "honest about limitations",
        "prefer local over cloud when capable",
        "always confirm before destructive actions"
    ],
    "capabilities": {
        "strong": ["Gmail", "Calendar", "WhatsApp", "computer_use", "multi-agent"],
        "learning": ["vision", "voice", "Android control"],
        "deferred": ["tree search", "full autonomy"]
    },
    "learned_preferences": {},
    "self_knowledge": [],
    "evolution_log": []
}


class AIDNA:
    def __init__(self):
        self.dna = self._load()

    def _load(self) -> dict:
        if os.path.exists(DNA_PATH):
            try:
                with open(DNA_PATH) as f:
                    return json.load(f)
            except Exception:
                pass
        return DEFAULT_DNA.copy()

    def _save(self):
        os.makedirs(os.path.dirname(DNA_PATH), exist_ok=True)
        with open(DNA_PATH, "w") as f:
            json.dump(self.dna, f, indent=2)

    def learn_preference(self, key: str, value: str):
        self.dna["learned_preferences"][key] = value
        self._log(f"Learned preference: {key} = {value}")
        self._save()

    def add_self_knowledge(self, insight: str):
        self.dna["self_knowledge"].append({
            "insight": insight,
            "timestamp": datetime.now().isoformat()
        })
        self.dna["self_knowledge"] = self.dna["self_knowledge"][-50:]  # keep last 50
        self._save()

    def _log(self, event: str):
        self.dna["evolution_log"].append({
            "event": event,
            "timestamp": datetime.now().isoformat()
        })
        self.dna["evolution_log"] = self.dna["evolution_log"][-100:]

    def get_identity_prompt(self) -> str:
        p = self.dna.get("personality", {})
        v = self.dna.get("values", [])
        prefs = self.dna.get("learned_preferences", {})
        lines = [
            f"You are SHRRI, a personal AI OS for {self.dna['identity']['owner']}.",
            f"Tone: {p.get('tone', 'helpful')}.",
            f"Languages: {', '.join(p.get('language', ['English']))}.",
            f"Core values: {'; '.join(v[:3])}.",
        ]
        if prefs:
            lines.append(f"Known preferences: {'; '.join(f'{k}={v}' for k,v in list(prefs.items())[:5])}.")
        return " ".join(lines)

    def summary(self) -> str:
        prefs = self.dna.get("learned_preferences", {})
        insights = self.dna.get("self_knowledge", [])
        return (
            f"AI DNA — SHRRI v{self.dna['identity']['version']}\n"
            f"  Learned preferences: {len(prefs)}\n"
            f"  Self-knowledge insights: {len(insights)}\n"
            f"  Evolution events: {len(self.dna.get('evolution_log', []))}\n"
            f"  Strong capabilities: {', '.join(self.dna['capabilities']['strong'])}"
        )
