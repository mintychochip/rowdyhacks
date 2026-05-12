"""Tests for assistant embedder service."""

from unittest.mock import MagicMock, patch

import numpy as np

from app.assistant.embedder import DEFAULT_MODEL, Embedder


class TestEmbedderSingleton:
    def test_singleton_instance(self):
        e1 = Embedder()
        e2 = Embedder()
        assert e1 is e2

    def test_reset_instance(self):
        # Ensure fresh singleton state for other tests
        Embedder._instance = None
        Embedder._model = None


class TestEmbedText:
    @patch("app.assistant.embedder.SentenceTransformer")
    def test_embed_single_text(self, mock_cls):
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_cls.return_value = mock_model

        Embedder._instance = None
        Embedder._model = None

        e = Embedder()
        result = e.embed_text("hello world")

        assert result == [0.1, 0.2, 0.3]
        mock_model.encode.assert_called_once_with("hello world", convert_to_numpy=True)

        # Cleanup
        Embedder._instance = None
        Embedder._model = None


class TestEmbedBatch:
    @patch("app.assistant.embedder.SentenceTransformer")
    def test_embed_batch(self, mock_cls):
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_cls.return_value = mock_model

        Embedder._instance = None
        Embedder._model = None

        e = Embedder()
        result = e.embed_batch(["hello", "world"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2]
        mock_model.encode.assert_called_once_with(["hello", "world"], convert_to_numpy=True, batch_size=32)

        Embedder._instance = None
        Embedder._model = None

    @patch("app.assistant.embedder.SentenceTransformer")
    def test_empty_batch_returns_empty_list(self, mock_cls):
        Embedder._instance = None
        Embedder._model = None
        e = Embedder()
        assert e.embed_batch([]) == []
        Embedder._instance = None
        Embedder._model = None


class TestEmbedChunks:
    @patch("app.assistant.embedder.SentenceTransformer")
    def test_embed_chunks_logs(self, mock_cls):
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1], [0.2]])
        mock_cls.return_value = mock_model

        Embedder._instance = None
        Embedder._model = None

        e = Embedder()
        result = e.embed_chunks(["chunk a", "chunk b"])

        assert len(result) == 2
        Embedder._instance = None
        Embedder._model = None

    def test_empty_chunks_returns_empty(self):
        Embedder._instance = None
        Embedder._model = None
        e = Embedder()
        assert e.embed_chunks([]) == []
        Embedder._instance = None
        Embedder._model = None


class TestCosineSimilarity:
    def test_identical_vectors(self):
        Embedder._instance = None
        Embedder._model = None
        e = Embedder()
        vec = [1.0, 0.0, 0.0]
        score = e.cosine_similarity(vec, vec)
        assert round(score, 5) == 1.0

    def test_orthogonal_vectors(self):
        Embedder._instance = None
        Embedder._model = None
        e = Embedder()
        score = e.cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert round(score, 5) == 0.0

    def test_opposite_vectors(self):
        Embedder._instance = None
        Embedder._model = None
        e = Embedder()
        score = e.cosine_similarity([1.0, 0.0], [-1.0, 0.0])
        assert round(score, 5) == -1.0


class TestDefaultModel:
    def test_default_model_constant(self):
        assert "MiniLM" in DEFAULT_MODEL
