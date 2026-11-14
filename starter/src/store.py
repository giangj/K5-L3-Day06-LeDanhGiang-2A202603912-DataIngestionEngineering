"""Store and search vectors using PostgreSQL + pgvector."""
import json
import logging
from typing import Any
from urllib.parse import urlparse
from .models import Chunk

logger = logging.getLogger(__name__)


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        """Initialize store connection parameters and validate embedding dimensions."""
        if dimensions <= 0:
            raise ValueError(f"dimensions must be positive, got {dimensions}")
        self.database_url = database_url
        self.dimensions = dimensions
        self.parsed_url = urlparse(database_url)

    def _get_connection(self):
        """Create a connection using psycopg if possible, or fall back to pure-python pg8000."""
        try:
            import psycopg
            return psycopg.connect(self.database_url, connect_timeout=10)
        except Exception:
            import pg8000.dbapi
            return pg8000.dbapi.connect(
                user=self.parsed_url.username or "day6",
                password=self.parsed_url.password or "day6_local_only",
                host=self.parsed_url.hostname or "127.0.0.1",
                port=self.parsed_url.port or 55433,
                database=self.parsed_url.path.lstrip("/") or "day6_lab",
                timeout=10,
            )

    def create_schema(self) -> None:
        """Create extension and document_chunks table with vector column and metadata index."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    strategy TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    metadata JSONB NOT NULL,
                    embedding vector({self.dimensions}) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (strategy, chunk_id)
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_doc_chunks_lookup 
                ON document_chunks (strategy, document_id);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_doc_chunks_metadata 
                ON document_chunks USING gin (metadata);
            """)
            conn.commit()
            logger.info("Schema verified: table document_chunks with vector(%d)", self.dimensions)
        finally:
            conn.close()

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Validate lengths/dimensions, delete obsolete chunks for document, and upsert stably.

        Prevents duplicate chunks when re-ingesting documents.
        """
        if len(chunks) != len(vectors):
            raise ValueError(f"Length mismatch: {len(chunks)} chunks vs {len(vectors)} vectors")

        if not chunks:
            return

        conn = self._get_connection()
        try:
            cur = conn.cursor()

            # Group incoming chunk IDs by document_id to clean obsolete chunks
            doc_chunk_map: dict[str, list[str]] = {}
            for chunk in chunks:
                doc_chunk_map.setdefault(chunk.document_id, []).append(chunk.chunk_id)

            for doc_id, chunk_ids in doc_chunk_map.items():
                # Delete old chunks for this (strategy, doc_id) that are not in incoming set
                placeholders = ",".join(["%s"] * len(chunk_ids))
                delete_sql = f"""
                    DELETE FROM document_chunks 
                    WHERE strategy = %s AND document_id = %s AND chunk_id NOT IN ({placeholders})
                """
                cur.execute(delete_sql, [strategy, doc_id, *chunk_ids])

            # Upsert incoming chunks with ON CONFLICT DO UPDATE
            upsert_sql = """
                INSERT INTO document_chunks 
                    (strategy, chunk_id, document_id, source, page, text, metadata, embedding, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (strategy, chunk_id) DO UPDATE SET
                    document_id = EXCLUDED.document_id,
                    source = EXCLUDED.source,
                    page = EXCLUDED.page,
                    text = EXCLUDED.text,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding,
                    created_at = CURRENT_TIMESTAMP;
            """

            for chunk, vec in zip(chunks, vectors):
                if len(vec) != self.dimensions:
                    raise ValueError(f"Vector dim {len(vec)} does not match store dim {self.dimensions}")
                vec_str = f"[{','.join(f'{x:.8f}' for x in vec)}]"
                meta_json = json.dumps(chunk.metadata, ensure_ascii=False)
                params = [
                    strategy,
                    chunk.chunk_id,
                    chunk.document_id,
                    chunk.source,
                    chunk.page,
                    chunk.text,
                    meta_json,
                    vec_str,
                ]
                cur.execute(upsert_sql, params)

            conn.commit()
            logger.info("Upserted %d chunks for strategy '%s'", len(chunks), strategy)
        finally:
            conn.close()

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Filter metadata in SQL, rank by cosine distance (<=>), and return top-k matches."""
        if len(query_vector) != self.dimensions:
            raise ValueError(f"Query vector dim {len(query_vector)} != {self.dimensions}")

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            vec_str = f"[{','.join(f'{x:.8f}' for x in query_vector)}]"

            sql = """
                SELECT chunk_id, document_id, source, page, text, metadata, (embedding <=> %s) AS distance
                FROM document_chunks
                WHERE strategy = %s
            """
            params: list[Any] = [vec_str, strategy]

            if filters:
                sql += " AND metadata @> %s::jsonb"
                params.append(json.dumps(filters, ensure_ascii=False))

            sql += " ORDER BY embedding <=> %s ASC LIMIT %s"
            params.extend([vec_str, top_k])

            cur.execute(sql, params)
            rows = cur.fetchall()

            results: list[dict[str, Any]] = []
            for r in rows:
                meta = r[5]
                if isinstance(meta, str):
                    meta = json.loads(meta)
                results.append({
                    "chunk_id": r[0],
                    "document_id": r[1],
                    "source": r[2],
                    "page": r[3],
                    "text": r[4],
                    "metadata": meta,
                    "score": float(r[6]),  # Cosine distance: 0 is identical, lower is better
                    "strategy": strategy,
                })
            return results
        finally:
            conn.close()
