import chromadb
from sentence_transformers import SentenceTransformer
import hashlib


class SimpleIngester:
    def __init__(self, db_path="./vector_db"):
        """Initialize with ChromaDB and embedding model."""
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection("instructions")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def store_text(self, text, title="", metadata=None):
        """Store text directly in vector database."""
        # Generate simple ID
        text_id = hashlib.md5(text.encode()).hexdigest()

        # Generate embedding
        embedding = self.embedding_model.encode(text).tolist()

        # Prepare metadata, ensuring a title is always stored
        meta = {"title": title}
        if metadata:
            meta.update(metadata)

        # Store in database including metadata so we can retrieve context later
        self.collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[meta],
            ids=[text_id]
        )
        return True
    
    def search(self, query, limit=5):
        """Search stored text."""
        query_embedding = self.embedding_model.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
        return results