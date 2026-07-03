"""
Memory Optimizer — SHRRI Phase 11
Deduplicates, merges, and promotes high-value memories across all layers.
"""
from engine.memory import Memory
from engine.episodic_memory import EpisodicMemory
from engine.memory_manager import MemoryManager


def deduplicate_facts() -> str:
    m = Memory()
    facts = m.get_all_facts()
    duplicates = []
    keys = list(facts.keys())
    for i, k1 in enumerate(keys):
        for k2 in keys[i+1:]:
            # Same value different key
            if facts[k1].strip().lower() == facts[k2].strip().lower():
                duplicates.append((k1, k2))

    removed = 0
    for k1, k2 in duplicates:
        # Keep shorter key
        to_remove = k2 if len(k1) <= len(k2) else k1
        m.delete_fact(to_remove)
        removed += 1

    return f"✅ Deduplication: removed {removed} duplicate facts"


def promote_episodes_to_facts() -> str:
    """High-importance episodes (importance >= 8) become long-term facts."""
    em = EpisodicMemory()
    m = Memory()
    rows = em.conn.execute(
        "SELECT summary, outcome, importance FROM episodes WHERE importance >= 8"
    ).fetchall()
    promoted = 0
    for summary, outcome, importance in rows:
        key = f"episode_{summary[:30].lower().replace(' ', '_')}"
        value = f"{summary} → {outcome}"
        if not m.get_fact(key):
            m.save_fact(key, value)
            promoted += 1
    return f"✅ Promoted {promoted} high-importance episodes to long-term facts"


def run_full_optimization() -> str:
    results = []
    results.append(deduplicate_facts())
    results.append(promote_episodes_to_facts())
    mm = MemoryManager()
    results.append(mm.forget_old(days=90, min_importance=4))
    results.append(mm.compress_episodes())
    return "\n".join(results)
