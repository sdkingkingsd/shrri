#!/usr/bin/env python3
"""
SHRRI Semantic Search
Hybrid FTS5 keyword + vector embedding search using ChromaDB + sentence-transformers
"""
import sys, os, sqlite3
sys.path.insert(0, '/home/shrridharshan/shrri')

CHROMA_PATH = os.path.expanduser("~/.shrri/chroma")
CONV_DB = "/home/shrridharshan/.shrri/conversations.db"

def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")  # tiny, fast, good quality

def get_chroma_collection():
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection("shrri_memory")

def index_conversations(days=30):
    """Index last N days of conversations into ChromaDB"""
    conn = sqlite3.connect(CONV_DB)
    rows = conn.execute("""
        SELECT id, role, message, timestamp
        FROM conversations
        WHERE role='user'
        AND date(timestamp) >= date('now', ?)
        ORDER BY timestamp DESC
    """, (f"-{days} days",)).fetchall()
    conn.close()

    if not rows:
        print("[semantic] No conversations to index")
        return

    embedder = get_embedder()
    collection = get_chroma_collection()

    # Get already indexed IDs
    existing = set()
    try:
        existing_data = collection.get()
        existing = set(existing_data["ids"])
    except Exception:
        pass

    docs, ids, metas = [], [], []
    for row in rows:
        doc_id = f"conv_{row[0]}"
        if doc_id in existing:
            continue
        text = row[2][:500]
        docs.append(text)
        ids.append(doc_id)
        metas.append({"role": row[1], "timestamp": row[3], "conv_id": row[0]})

    if not docs:
        print("[semantic] All conversations already indexed")
        return

    # Batch embed and store
    batch_size = 50
    for i in range(0, len(docs), batch_size):
        batch_docs = docs[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        batch_metas = metas[i:i+batch_size]
        embeddings = embedder.encode(batch_docs).tolist()
        collection.add(documents=batch_docs, ids=batch_ids,
                      metadatas=batch_metas, embeddings=embeddings)
        print(f"[semantic] Indexed {min(i+batch_size, len(docs))}/{len(docs)}")

    print(f"[semantic] Done — {len(docs)} new messages indexed")

def semantic_search(query, n=5):
    """Search using vector similarity"""
    try:
        embedder = get_embedder()
        collection = get_chroma_collection()
        query_embedding = embedder.encode([query]).tolist()
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n,
            include=["documents", "metadatas", "distances"]
        )
        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            hits.append({
                "text": doc,
                "timestamp": meta.get("timestamp", "")[:10],
                "score": round(1 - dist, 3)
            })
        return hits
    except Exception as e:
        print(f"[semantic] search error: {e}")
        return []

def hybrid_search(query, n=5):
    """Combine FTS5 keyword + semantic vector search"""
    results = {}

    # 1. FTS5 keyword search
    try:
        conn = sqlite3.connect(CONV_DB)
        fts_rows = conn.execute("""
            SELECT message, timestamp FROM conversations
            WHERE rowid IN (
                SELECT rowid FROM conversations_fts
                WHERE conversations_fts MATCH ?
            )
            ORDER BY timestamp DESC LIMIT ?
        """, (query, n)).fetchall()
        conn.close()
        for row in fts_rows:
            key = row[0][:80]
            results[key] = {"text": row[0][:200], "timestamp": row[1][:10], "source": "keyword"}
    except Exception as e:
        print(f"[semantic] FTS error: {e}")

    # 2. Semantic vector search
    semantic_hits = semantic_search(query, n)
    for hit in semantic_hits:
        key = hit["text"][:80]
        if key not in results:
            results[key] = {"text": hit["text"][:200], "timestamp": hit["timestamp"], "source": "semantic"}
        else:
            results[key]["source"] = "both"

    return list(results.values())[:n]

if __name__ == "__main__":
    print("[semantic] Indexing conversations...")
    index_conversations(days=30)
    print("[semantic] Testing search: 'biryani food'")
    hits = hybrid_search("biryani food")
    for h in hits:
        print(f"  [{h['source']}] [{h['timestamp']}]: {h['text'][:100]}")
