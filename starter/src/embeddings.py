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
    """Embedder using Google Gemini text-embedding-004 API (768 dimensions)."""

    def __init__(self, api_key: str, model_name: str = "models/text-embedding-004") -> None:
        self.api_key = api_key.strip()
        self.model_name = model_name
        self.dimensions = 768
        # Test connection with a short query
        logger.info("Initializing GeminiEmbedder with model '%s'...", self.model_name)
        _ = self.embed_query("test initialization")
        logger.info("GeminiEmbedder ready (dim=%d).", self.dimensions)

    def _embed_single(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:embedContent?key={self.api_key}"
        payload = {
            "model": self.model_name,
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    return res["embedding"]["values"]
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8")
                if e.code == 429:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(f"Gemini API error ({e.code}): {err_body}") from e
            except Exception as e:
                if attempt == 4:
                    raise
                time.sleep(1)
        raise RuntimeError("Failed to get embedding from Gemini API after 5 retries.")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results = []
        for i, text in enumerate(texts):
            results.append(self._embed_single(text, task_type="RETRIEVAL_DOCUMENT"))
            if (i + 1) % 20 == 0:
                logger.info("Embedded %d/%d documents via Gemini API...", i + 1, len(texts))
            time.sleep(0.05)  # slight rate limit pause
        return results

    def embed_query(self, question: str) -> list[float]:
        return self._embed_single(question, task_type="RETRIEVAL_QUERY")


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
        model = os.getenv("EMBEDDING_MODEL") or "models/text-embedding-004"
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
