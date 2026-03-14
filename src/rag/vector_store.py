import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class CivicVectorStore:
    """
    ChromaDB-backed vector store for civic documents.
    Accumulates knowledge over time — every scraped document gets stored
    so the AI can reference historical context and find contradictions.
    """

    def __init__(self, persist_dir: str = "data/chroma_db", collection_name: str = "civic_docs"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        os.makedirs(persist_dir, exist_ok=True)
        self._collection = None

    def _get_collection(self):
        """Lazy-load the ChromaDB collection."""
        if self._collection is None:
            try:
                import chromadb
                from chromadb.config import Settings

                client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=Settings(anonymized_telemetry=False)
                )
                self._collection = client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Connected to ChromaDB collection '{self.collection_name}' "
                            f"({self._collection.count()} existing documents).")
            except ImportError:
                logger.error("chromadb not installed. Run: pip install chromadb")
                raise
        return self._collection

    def ingest(self, chunks: List[Dict]) -> int:
        """
        Ingest a list of document chunks into the vector store.
        Each chunk: {"text": str, "metadata": dict}
        Returns the number of new chunks added.
        """
        if not chunks:
            return 0

        collection = self._get_collection()

        # Build unique IDs to prevent duplicates
        documents = []
        metadatas = []
        ids = []

        for chunk in chunks:
            text = chunk["text"]
            meta = chunk.get("metadata", {})

            # Create a deterministic ID from source + chunk index
            source = meta.get("source", "unknown")
            idx = meta.get("chunk_index", 0)
            doc_id = f"{source}__chunk_{idx}"

            # Skip if already exists
            existing = collection.get(ids=[doc_id])
            if existing and existing.get("ids"):
                continue

            documents.append(text)
            # ChromaDB metadata must be str/int/float/bool only
            clean_meta = {k: str(v) for k, v in meta.items()}
            metadatas.append(clean_meta)
            ids.append(doc_id)

        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            logger.info(f"Ingested {len(documents)} new chunks into vector store.")

        return len(documents)

    def search(self, query: str, k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Semantic search for the most relevant document chunks.
        Returns list of {"text": str, "metadata": dict, "distance": float}.
        """
        collection = self._get_collection()

        if collection.count() == 0:
            logger.warning("Vector store is empty. No historical context available.")
            return []

        kwargs = {"query_texts": [query], "n_results": min(k, collection.count())}
        if filter_metadata:
            kwargs["where"] = filter_metadata

        results = collection.query(**kwargs)

        output = []
        for i, doc_text in enumerate(results["documents"][0]):
            output.append({
                "text": doc_text,
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "distance": results["distances"][0][i] if results.get("distances") else 0.0
            })

        logger.info(f"Retrieved {len(output)} relevant chunks for query: '{query[:60]}...'")
        return output

    def get_stats(self) -> dict:
        """Returns basic stats about the vector store."""
        collection = self._get_collection()
        return {
            "total_chunks": collection.count(),
            "collection_name": self.collection_name,
            "persist_dir": self.persist_dir
        }
