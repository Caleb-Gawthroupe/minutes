import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def chunk_document(
    text: str,
    metadata: dict,
    chunk_size: int = 500,
    overlap: int = 50
) -> List[Dict]:
    """
    Splits a long document into overlapping chunks for vector ingestion.
    Each chunk retains the parent metadata (source, date, type).
    """
    if not text or not text.strip():
        return []

    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_text = " ".join(words[start:end])

        chunk_meta = {
            **metadata,
            "chunk_index": len(chunks),
            "char_start": sum(len(w) + 1 for w in words[:start]),
        }

        chunks.append({
            "text": chunk_text,
            "metadata": chunk_meta
        })

        if end >= len(words):
            break
        start += chunk_size - overlap

    logger.info(f"Chunked document '{metadata.get('source', 'unknown')}' into {len(chunks)} chunks.")
    return chunks
