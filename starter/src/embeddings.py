"""Embedding provider adapter supporting Gemini API, OpenAI API, and Local Models."""
import json
import logging
import os
import time
import urllib.request
import urllib.error
from typing import Protocol

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class GeminiEmbedder:
    """Embedder using Google Gemini embedding API (768 dimensions) with disk cache and rate limit handling."""

    def __init__(self, api_key: str, model_name: str = "models/gemini-embedding-001") -> None:
        import hashlib
        import sqlite3
        from pathlib import Path

        self.api_key = api_key.strip()
        self.model_name = model_name if model_name.startswith("models/") else f"models/{model_name}"
        self.dimensions = 768

        # Setup persistent SQLite cache
        cache_dir = Path(__file__).resolve().parent.parent / "data"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_db = cache_dir / "gemini_embeddings_cache.sqlite"
        self._init_cache()

        logger.info("Initializing GeminiEmbedder with model '%s'...", self.model_name)
        _ = self.embed_query("test initialization")
        logger.info("GeminiEmbedder ready (dim=%d, cache=%s).", self.dimensions, self.cache_db.name)

    def _init_cache(self) -> None:
        import sqlite3
        with sqlite3.connect(str(self.cache_db)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    text_hash TEXT PRIMARY KEY,
                    vector_json TEXT NOT NULL
                )
            """)

    def _get_from_cache(self, text: str) -> list[float] | None:
        import hashlib
        import sqlite3
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        with sqlite3.connect(str(self.cache_db)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT vector_json FROM cache WHERE text_hash = ?", (h,))
            row = cur.fetchone()
            if row:
                return json.loads(row[0])
        return None

    def _save_to_cache(self, texts: list[str], vectors: list[list[float]]) -> None:
        import hashlib
        import sqlite3
        rows = [
            (hashlib.sha256(t.encode("utf-8")).hexdigest(), json.dumps(v))
            for t, v in zip(texts, vectors)
        ]
        with sqlite3.connect(str(self.cache_db)) as conn:
            conn.executemany("INSERT OR REPLACE INTO cache (text_hash, vector_json) VALUES (?, ?)", rows)

    def _embed_batch(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        if not texts:
            return []
        url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:batchEmbedContents?key={self.api_key}"
        requests = [
            {
                "model": self.model_name,
                "content": {"parts": [{"text": t}]},
                "taskType": task_type,
                "outputDimensionality": self.dimensions,
            }
            for t in texts
        ]
        payload = {"requests": requests}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        max_attempts = 8
        for attempt in range(max_attempts):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    vectors = [item["values"] for item in res["embeddings"]]
                    self._save_to_cache(texts, vectors)
                    return vectors
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8")
                if e.code == 429:
                    wait_s = 15 * (attempt + 1)
                    logger.warning("Gemini 429 Rate Limit. Sleeping %ds before retry %d/%d...", wait_s, attempt + 1, max_attempts)
                    time.sleep(wait_s)
                    continue
                raise RuntimeError(f"Gemini API error ({e.code}): {err_body}") from e
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                wait_s = 5 * (attempt + 1)
                logger.warning("Network error (%s). Retrying in %ds...", e, wait_s)
                time.sleep(wait_s)
        raise RuntimeError(f"Failed to batch embed from Gemini API after {max_attempts} retries.")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float] | None] = [self._get_from_cache(t) for t in texts]
        missing_indices = [i for i, v in enumerate(results) if v is None]

        if missing_indices:
            logger.info("Found %d/%d cached embeddings. Fetching %d from API...", len(texts) - len(missing_indices), len(texts), len(missing_indices))
            batch_size = 30
            for start in range(0, len(missing_indices), batch_size):
                chunk_idxs = missing_indices[start : start + batch_size]
                chunk_texts = [texts[idx] for idx in chunk_idxs]
                chunk_vectors = self._embed_batch(chunk_texts, task_type="RETRIEVAL_DOCUMENT")
                for idx, vec in zip(chunk_idxs, chunk_vectors):
                    results[idx] = vec
                logger.info("Embedded %d/%d new texts...", min(start + batch_size, len(missing_indices)), len(missing_indices))
                time.sleep(1.0)  # Safe breathing room between batches
        else:
            logger.info("All %d embeddings loaded from local cache.", len(texts))

        return [v for v in results if v is not None]

    def embed_query(self, question: str) -> list[float]:
        cached = self._get_from_cache(question)
        if cached is not None:
            return cached
        vectors = self._embed_batch([question], task_type="RETRIEVAL_QUERY")
        return vectors[0]


class OpenAIEmbedder:
    """Embedder using OpenAI / OpenRouter text-embedding-3-small (1536 dimensions)."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model_name: str = "text-embedding-3-small") -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.dimensions = 1536 if "large" not in model_name else 3072
        logger.info("Initializing OpenAIEmbedder with model '%s'...", self.model_name)
        _ = self.embed_query("test initialization")
        logger.info("OpenAIEmbedder ready (dim=%d).", self.dimensions)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        url = f"{self.base_url}/embeddings"
        payload = {"model": self.model_name, "input": texts}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return [item["embedding"] for item in sorted(res["data"], key=lambda x: x["index"])]

    def embed_query(self, question: str) -> list[float]:
        res = self.embed_documents([question])
        return res[0]


def get_embedder() -> Embedder:
    """Factory creating appropriate embedder based on available API keys or local fallback."""
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()

    if gemini_key:
        model = os.getenv("EMBEDDING_MODEL") or "models/gemini-embedding-001"
        return GeminiEmbedder(api_key=gemini_key, model_name=model)
    elif openai_key:
        model = os.getenv("EMBEDDING_MODEL") or "text-embedding-3-small"
        return OpenAIEmbedder(api_key=openai_key, model_name=model)
    elif openrouter_key:
        model = os.getenv("EMBEDDING_MODEL") or "openai/text-embedding-3-small"
        return OpenAIEmbedder(
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            model_name=model,
        )
    else:
        # Fall back to local SentenceTransformer
        from sentence_transformers import SentenceTransformer

        class LocalEmbedder:
            def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
                self.model_name = model_name
                self.model = SentenceTransformer(model_name)
                self.dimensions = int(self.model.get_sentence_embedding_dimension())

            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                return self.model.encode(texts, normalize_embeddings=True).tolist()

            def embed_query(self, question: str) -> list[float]:
                return self.model.encode(question, normalize_embeddings=True).tolist()

        model = os.getenv("EMBEDDING_MODEL") or "paraphrase-multilingual-MiniLM-L12-v2"
        return LocalEmbedder(model_name=model)


class MyEmbedder:
    """Wrapper delegating to configured embedding provider."""

    def __init__(self, model_name: str | None = None) -> None:
        self.provider = get_embedder()
        self.model_name = self.provider.model_name
        self.dimensions = self.provider.dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.provider.embed_documents(texts)

    def embed_query(self, question: str) -> list[float]:
        return self.provider.embed_query(question)
