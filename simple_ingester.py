import hashlib
import sys

import re

import chromadb
from sentence_transformers import SentenceTransformer


def chunk_text(text: str, chunk_words: int = 300, overlap_words: int = 50):
    """Word-based chunks with small overlap; dead-simple and good enough."""
    words = text.split()
    if not words:
        return []
    step = max(1, chunk_words - overlap_words)
    return [" ".join(words[i:i + chunk_words]) for i in range(0, len(words), step)]

def main(path: str = "context.txt", db_path: str = "./vector_db", collection_name: str = "instructions"):

    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(collection_name)
    model = SentenceTransformer("all-MiniLM-L6-v2")

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # Split text into individual rules by numbering (e.g., '1.', '2.', ...)
    parts = re.split(r'(?m)^\s*\d+\.\s*', text)
    # Ignore any empty leading text and strip whitespace
    chunks = [p.strip() for p in parts if p.strip()]
    print(chunks)
    for chunk in chunks:
        emb = model.encode(chunk).tolist()
        cid = hashlib.md5(chunk.encode("utf-8")).hexdigest()
        collection.add(embeddings=[emb], documents=[chunk], ids=[cid])

    print(f"Ingested {len(chunks)} chunks from {path} into collection '{collection_name}' at {db_path}.")

    # tiny search smoke test
    q = "test"
    q_emb = model.encode(q).tolist()
    res = collection.query(
        query_embeddings=[q_emb],
        n_results=3,
        include=["documents", "distances"]  # ✅ valid include keys
    )
    print("IDs:", res.get("ids", []))
    print("Distances:", res.get("distances", []))
    print("Docs preview:", [d[:120] + "…" if len(d) > 120 else d for d in res.get("documents", [[]])[0]])


if __name__ == "__main__":
    # Usage: python simplest_ingest.py [optional_path_to_text_file]
    main(sys.argv[1] if len(sys.argv) > 1 else "context.txt")