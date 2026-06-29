#!/usr/bin/env python3
"""
SHRRI Dream Cycle — Background Memory Consolidation
Inspired by OpenClaw's dreaming system
Phase 1: Light Sleep — ingest, dedupe daily notes
Phase 2: REM Sleep — extract themes, score candidates  
Phase 3: Deep Sleep — promote high-score items to SOUL.md facts
"""
import sys, os, sqlite3, json, re
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/home/shrridharshan/shrri')

MEMORY_DIR = Path.home() / ".shrri" / "memory"
DREAMS_FILE = Path.home() / ".shrri" / "DREAMS.md"
DREAMS_DIR = Path.home() / ".shrri" / "memory" / ".dreams"
CONV_DB = "/home/shrridharshan/.shrri/conversations.db"

DREAMS_DIR.mkdir(parents=True, exist_ok=True)

# Promotion thresholds (like OpenClaw)
MIN_SCORE = 0.6       # lowered from 0.8 for SHRRI's smaller dataset
MIN_RECALL = 2        # lowered from 3
MIN_QUERIES = 2       # lowered from 3

def jaccard_similarity(a, b):
    """Deduplicate using Jaccard similarity"""
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b:
        return 0
    return len(set_a & set_b) / len(set_a | set_b)

def phase_light(days=7):
    """Light Sleep: Ingest daily notes, dedupe, stage candidates"""
    print("[dream] Phase 1: Light Sleep")
    candidates = []
    seen = []

    for i in range(days):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        note_file = MEMORY_DIR / f"{day}.md"
        if not note_file.exists():
            continue
        
        with open(note_file) as f:
            content = f.read()

        # Skip already consolidated
        if "<!-- consolidated -->" in content:
            continue

        # Extract user messages from notes
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                # Extract content from bullet points
                if line.startswith("- ") and len(line) > 10:
                    snippet = line[2:].strip()
                    if len(snippet) < 10:
                        continue
                    # Dedupe using Jaccard
                    is_dup = any(jaccard_similarity(snippet, s["text"]) > 0.9 for s in seen)
                    if not is_dup:
                        candidates.append({
                            "text": snippet,
                            "date": day,
                            "recall_count": 0,
                            "query_count": 0,
                            "score": 0.0
                        })
                        seen.append({"text": snippet})

    # Save staged candidates
    stage_file = DREAMS_DIR / "staged.json"
    with open(stage_file, "w") as f:
        json.dump(candidates, f, indent=2)

    print(f"[dream] Light Sleep: staged {len(candidates)} candidates")
    return candidates

def phase_rem(candidates):
    """REM Sleep: Extract themes, boost recall counts"""
    print("[dream] Phase 2: REM Sleep")
    
    # Check recall counts from semantic search history
    conn = sqlite3.connect(CONV_DB)
    
    for candidate in candidates:
        text = candidate["text"]
        keywords = [w for w in text.lower().split() if len(w) > 3]
        
        if not keywords:
            continue

        # Count how many times similar topics were searched/recalled
        for kw in keywords[:3]:
            try:
                count = conn.execute("""
                    SELECT COUNT(*) FROM conversations
                    WHERE message LIKE ? AND role='user'
                """, (f"%{kw}%",)).fetchone()[0]
                candidate["recall_count"] = max(candidate["recall_count"], count)
            except Exception:
                pass

        # Count unique query variations
        try:
            unique = conn.execute("""
                SELECT COUNT(DISTINCT message) FROM conversations
                WHERE message LIKE ? AND role='user'
            """, (f"%{keywords[0]}%",)).fetchone()[0]
            candidate["query_count"] = unique
        except Exception:
            pass

    conn.close()

    # Save REM results
    rem_file = DREAMS_DIR / "rem.json"
    with open(rem_file, "w") as f:
        json.dump(candidates, f, indent=2)

    print(f"[dream] REM Sleep: scored {len(candidates)} candidates")
    return candidates

def score_candidate(c):
    """Score using 6 weighted signals like OpenClaw"""
    recall = min(c.get("recall_count", 0) / 10, 1.0)
    frequency = min(c.get("recall_count", 0) / 5, 1.0)
    diversity = min(c.get("query_count", 0) / 5, 1.0)
    
    # Recency score
    try:
        days_ago = (datetime.now() - datetime.strptime(c["date"], "%Y-%m-%d")).days
        recency = max(0, 1 - days_ago / 30)
    except Exception:
        recency = 0.5
    
    # Consolidation — longer text = more information
    consolidation = min(len(c["text"]) / 200, 1.0)
    
    # Conceptual richness — unique words ratio
    words = c["text"].split()
    conceptual = len(set(words)) / max(len(words), 1)

    # Weighted sum (same weights as OpenClaw)
    score = (
        0.30 * recall +
        0.24 * frequency +
        0.15 * diversity +
        0.15 * recency +
        0.10 * consolidation +
        0.06 * conceptual
    )
    return round(score, 3)

def phase_deep(candidates):
    """Deep Sleep: Score, threshold, promote to facts DB"""
    print("[dream] Phase 3: Deep Sleep")
    
    from engine.memory import Memory
    m = Memory()
    
    promoted = []
    rejected = []

    for c in candidates:
        c["score"] = score_candidate(c)
        
        # Apply all three threshold gates
        if (c["score"] >= MIN_SCORE and 
            c["recall_count"] >= MIN_RECALL and
            c["query_count"] >= MIN_QUERIES):
            promoted.append(c)
        else:
            rejected.append(c)

    # Promote to facts DB
    for c in promoted:
        # Extract as a fact using simple pattern matching
        text = c["text"]
        key = "dream_" + text[:40].lower().replace(" ", "_").replace("'", "")[:35]
        ok, reason = m._scan_injection(key, text)
        if ok:
            m.save_fact(key, text)
            print(f"[dream] Promoted: {text[:60]} (score={c['score']})")

    m._save_encrypted()

    # Write DREAMS.md diary
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(DREAMS_FILE, "a") as f:
        f.write(f"\n\n## Dream Cycle — {now}\n\n")
        f.write(f"### Summary\n")
        f.write(f"- Candidates: {len(candidates)}\n")
        f.write(f"- Promoted: {len(promoted)}\n")
        f.write(f"- Rejected: {len(rejected)}\n\n")
        if promoted:
            f.write("### Promoted Memories\n")
            for c in promoted:
                f.write(f"- [{c['date']}] {c['text'][:100]} (score={c['score']})\n")

    print(f"[dream] Deep Sleep: {len(promoted)} promoted, {len(rejected)} rejected")
    return promoted

def mark_consolidated(days=7):
    """Mark processed daily notes as consolidated"""
    for i in range(days):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        note_file = MEMORY_DIR / f"{day}.md"
        if note_file.exists():
            with open(note_file, "a") as f:
                f.write("\n<!-- consolidated -->\n")

def run_dream_cycle():
    print(f"[dream] Starting dream cycle at {datetime.now()}")
    candidates = phase_light(days=7)
    if not candidates:
        print("[dream] No candidates to process")
        return
    candidates = phase_rem(candidates)
    promoted = phase_deep(candidates)
    mark_consolidated(days=7)
    print(f"[dream] Dream cycle complete. {len(promoted)} memories promoted.")

if __name__ == "__main__":
    run_dream_cycle()
