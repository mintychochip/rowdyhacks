"""Embedding service using sentence-transformers."""

import logging

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Using all-MiniLM-L6-v2 for efficiency (384 dimensions)
# This matches the VECTOR_DIM in vector_store.py
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder:
    """Manages sentence embeddings for the assistant."""

    _instance: "Embedder" | None = None
    _model: SentenceTransformer | None = None
    _model_name: str = DEFAULT_MODEL

    def __new__(cls) -> "Embedder":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model loaded")
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""
        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently."""
        if not texts:
            return []
        model = self._load_model()
        embeddings = model.encode(texts, convert_to_numpy=True, batch_size=32)
        return embeddings.tolist()

    def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        """Embed document chunks with progress logging."""
        if not chunks:
            return []

        logger.info(f"Embedding {len(chunks)} chunks")
        embeddings = self.embed_batch(chunks)
        logger.info(f"Embedded {len(chunks)} chunks successfully")
        return embeddings

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# Global instance
embedder = Embedder()
