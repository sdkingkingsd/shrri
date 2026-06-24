import os
import hashlib
import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader

KNOWLEDGE_DIR = os.path.expanduser("~/shrri/knowledge")
CHROMA_DIR = os.path.expanduser("~/.shrri/chroma")

SUPPORTED_EXTENSIONS = {".txt", ".md", ".py", ".pdf"}

CHUNK_SIZE = 800   # characters per chunk
CHUNK_OVERLAP = 100


class RAG:
    def __init__(self):
        os.makedirs(CHROMA_DIR, exist_ok=True)
        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(path=CHROMA_DIR)
        # Default embedding function (downloads a small local model on first use)
        self.embedder = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="shrri_knowledge",
            embedding_function=self.embedder
        )

    def _read_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".pdf":
                reader = PdfReader(path)
                return "\n".join((page.extract_text() or "") for page in reader.pages)
            else:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
        except Exception as e:
            print(f"[SHRRI] Could not read {path}: {e}")
            return ""

    def _chunk_text(self, text):
        chunks = []
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunks.append(text[start:end])
            start = end - CHUNK_OVERLAP
        return [c.strip() for c in chunks if c.strip()]

    def _file_hash(self, path):
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def index_all(self):
        """Scan KNOWLEDGE_DIR recursively, index new/changed files only."""
        indexed_count = 0
        skipped_count = 0

        for root, _, files in os.walk(KNOWLEDGE_DIR):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, KNOWLEDGE_DIR)
                file_hash = self._file_hash(fpath)
                doc_id_prefix = rel_path.replace("/", "_")

                # Check if this exact file version is already indexed
                existing = self.collection.get(
                    where={"source": rel_path},
                    limit=1
                )
                already_indexed = (
                    existing["metadatas"]
                    and existing["metadatas"][0].get("file_hash") == file_hash
                )
                if already_indexed:
                    skipped_count += 1
                    continue

                # Remove old chunks for this file (in case it changed)
                self.collection.delete(where={"source": rel_path})

                text = self._read_file(fpath)
                if not text.strip():
                    continue

                chunks = self._chunk_text(text)
                ids = [f"{doc_id_prefix}_{i}" for i in range(len(chunks))]
                metadatas = [
                    {"source": rel_path, "file_hash": file_hash, "chunk": i}
                    for i in range(len(chunks))
                ]

                if chunks:
                    self.collection.add(documents=chunks, ids=ids, metadatas=metadatas)
                    indexed_count += 1
                    print(f"[SHRRI] Indexed: {rel_path} ({len(chunks)} chunks)")

        print(f"[SHRRI] Indexing complete — {indexed_count} files indexed, {skipped_count} unchanged/skipped.")
        return indexed_count, skipped_count

    def query(self, text, n_results=3):
        """Return top matching chunks for a query string."""
        try:
            count = self.collection.count()
            if count == 0:
                return []
            results = self.collection.query(
                query_texts=[text],
                n_results=min(n_results, count)
            )
            matches = []
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            for doc, meta in zip(docs, metas):
                matches.append({"text": doc, "source": meta.get("source", "unknown")})
            return matches
        except Exception as e:
            print(f"[SHRRI] RAG query failed: {e}")
            return []
