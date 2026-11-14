"""Choose a real embedding provider (API or local) and implement this contract."""
from typing import Protocol
from sentence_transformers import SentenceTransformer


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Production embedder using sentence-transformers (local, multilingual)."""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        dim = self.model.get_sentence_embedding_dimension()
        if dim is None:
            raise ValueError(f"Could not determine embedding dimension for model {model_name}")
        self.dimensions = int(dim)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one unit-normalized vector per input text, preserving order."""
        if not texts:
            return []
        vectors = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        vector = self.model.encode(
            question,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector.tolist()
