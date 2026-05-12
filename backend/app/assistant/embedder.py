"""Embedding service using sentence-transformers."""

from __future__ import annotations

import logging

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Using all-MiniLM-L6-v2 for efficiency (384 dimensions)
# This matches the VECTOR_DIM in vector_store.py
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder:
    """Singleton sentence-embedding manager for the assistant.

    Uses the ``all-MiniLM-L6-v2`` model (384-dimension vectors) and
    provides single-text, batch, and chunked embedding interfaces.
    """

    _instance: Embedder | None = None
    _model: SentenceTransformer | None = None
    _model_name: str = DEFAULT_MODEL

    def __new__(cls) -> Embedder:
        """Create or return the singleton embedder instance.

        Behavior:
        1. Instantiate the singleton on first call.
        2. Return the existing instance on subsequent calls.

        Raises: None
        Side Effects: Sets ``cls._instance`` on first call.
        Dependencies: None
        Consumers: Global ``embedder`` instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self) -> SentenceTransformer:
        """Lazy-load the underlying ``SentenceTransformer`` model.

        Behavior:
        1. Check if the model is already cached.
        2. If not, download/load the model and cache it.
        3. Return the cached model.

        Raises: None
        Side Effects: Sets ``self._model`` on first call.
        Dependencies: sentence_transformers.SentenceTransformer.
        Consumers: Embedder.embed_text, Embedder.embed_batch.
        """
        if self._model is None:
            logger.info(f"Loading embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model loaded")
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string into a dense vector.

        Behavior:
        1. Load the embedding model.
        2. Encode the text into a numpy array.
        3. Convert to a Python list and return.

        Raises: None
        Side Effects: None (read-only from caller perspective).
        Dependencies: Embedder._load_model.
        Consumers: Assistant search, indexing, and similarity pipelines.
        """
        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single batched call.

        Behavior:
        1. Return an empty list if no texts are provided.
        2. Load the embedding model.
        3. Encode all texts in a single batched call.
        4. Convert the numpy result to a nested Python list and return.

        Raises: None
        Side Effects: None (read-only from caller perspective).
        Dependencies: Embedder._load_model.
        Consumers: Embedder.embed_chunks, bulk indexing pipelines.
        """
        if not texts:
            return []
        model = self._load_model()
        embeddings = model.encode(texts, convert_to_numpy=True, batch_size=32)
        return embeddings.tolist()

    def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        """Embed document chunks with progress logging.

        Behavior:
        1. Return an empty list if no chunks are provided.
        2. Log the number of chunks being embedded.
        3. Delegate to embed_batch for the actual encoding.
        4. Log completion and return the embeddings.

        Raises: None
        Side Effects: Writes log lines.
        Dependencies: Embedder.embed_batch.
        Consumers: Document indexing pipeline.
        """
        if not chunks:
            return []

        logger.info(f"Embedding {len(chunks)} chunks")
        embeddings = self.embed_batch(chunks)
        logger.info(f"Embedded {len(chunks)} chunks successfully")
        return embeddings

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two dense vectors.

        Behavior:
        1. Convert both vectors to numpy arrays.
        2. Compute the dot product and divide by the product of L2 norms.
        3. Return the scalar cosine similarity.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: numpy.dot, numpy.linalg.norm.
        Consumers: Similarity scoring in assistant pipelines.
        """
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# Global instance
embedder = Embedder()
