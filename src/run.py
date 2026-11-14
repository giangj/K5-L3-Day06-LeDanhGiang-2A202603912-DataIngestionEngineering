"""Pipeline entry point; orchestrates ingestion, chunking, embedding, storage, and evaluation."""
import csv
import json
import logging
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf
from .models import Chunk, DocumentPage
from .store import PgVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_paths() -> tuple[Path, Path, Path, Path]:
    """Return starter_dir, data_dir, results_dir, artifacts_dir."""
    src_dir = Path(__file__).resolve().parent
    starter_dir = src_dir.parent
    data_dir = starter_dir / "data"
    results_dir = starter_dir / "results"
    repo_root = starter_dir.parent
    artifacts_dir = repo_root / "artifacts"
    results_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return starter_dir, data_dir, results_dir, artifacts_dir


def load_corpus(data_dir: Path) -> list[DocumentPage]:
    """Load corpus PDFs and validate minimum content page count."""
    manifest_path = data_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest file at {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    all_pages: list[DocumentPage] = []

    for entry in manifest:
        source_id = entry["source_id"]
        source_path = data_dir / Path(entry["source_path"]).name
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        meta = entry.get("metadata_fields", {})
        pages = load_pdf(source_path, document_id=source_id, source=entry["source_path"], metadata=meta)
        all_pages.extend(pages)

    # Validate at least 30 content pages (> 50 chars)
    content_pages = [p for p in all_pages if len(p.text.strip()) > 50]
    logger.info("Total physical pages: %d | Content pages: %d", len(all_pages), len(content_pages))
    if len(content_pages) < 30:
        raise ValueError(f"Corpus does not satisfy requirement: {len(content_pages)} content pages < 30")

    return all_pages


def update_experiment_log(artifacts_dir: Path, rows: list[dict]):
    """Update artifacts/experiment_log.csv with the 3 strategy results."""
    csv_path = artifacts_dir / "experiment_log.csv"
    headers = [
        "strategy",
        "model",
        "chunk_params",
        "num_chunks",
        "upsert_time_s",
        "hit_at_1_dev",
        "evidence_hit3_dev",
        "hit_at_1_test",
        "evidence_hit3_test",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in headers})
    logger.info("Updated experiment log at %s", csv_path)


def main() -> None:
    starter_dir, data_dir, results_dir, artifacts_dir = get_paths()
    load_dotenv(starter_dir / ".env")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL missing in .env")

    model_name = os.getenv("EMBEDDING_MODEL") or "paraphrase-multilingual-MiniLM-L12-v2"
    logger.info("Initializing Embedder with model '%s'...", model_name)
    embedder = MyEmbedder(model_name=model_name)
    logger.info("Embedder initialized. Dimensions: %d", embedder.dimensions)

    logger.info("Initializing Vector Store...")
    store = PgVectorStore(database_url=database_url, dimensions=embedder.dimensions)
    store.create_schema()

    # 1. Load Corpus
    logger.info("Loading corpus from %s...", data_dir)
    pages = load_corpus(data_dir)

    # 2. Load Benchmark Questions
    benchmark_path = data_dir / "benchmark_questions.json"
    if not benchmark_path.exists():
        sys.exit(f"Benchmark file not found at {benchmark_path}")
    questions = json.loads(benchmark_path.read_text(encoding="utf-8"))
    logger.info("Loaded %d benchmark questions.", len(questions))

    # Pre-embed questions for efficiency and consistency
    logger.info("Embedding %d query questions...", len(questions))
    query_vectors = [embedder.embed_query(q["question"]) for q in questions]

    experiment_rows = []

    # -------------------------------------------------------------
    # STRATEGY A: Fixed-size (500 chars, 50 overlap)
    # -------------------------------------------------------------
    logger.info("=== Running Strategy A (Fixed-size: 500/50) ===")
    start_time = time.time()
    chunks_A: list[Chunk] = []
    for p in pages:
        chunks_A.extend(fixed_size(p, size=500, overlap=50))
    logger.info("Strategy A generated %d chunks. Embedding...", len(chunks_A))
    vectors_A = embedder.embed_documents([c.text for c in chunks_A])
    store.upsert("strategy_a", chunks_A, vectors_A)
    time_A = round(time.time() - start_time, 2)
    logger.info("Strategy A stored in %.2fs", time_A)

    traces_A = []
    for q, q_vec in zip(questions, query_vectors):
        hits = store.search("strategy_a", q_vec, top_k=3, filters=None)
        trace = evaluate_query(q, hits)
        traces_A.append(trace)
    summary_A = summarize(traces_A)

    experiment_rows.append({
        "strategy": "A (fixed-size)",
        "model": model_name,
        "chunk_params": "size=500,overlap=50",
        "num_chunks": len(chunks_A),
        "upsert_time_s": time_A,
        "hit_at_1_dev": summary_A["dev"]["hit_at_1"],
        "evidence_hit3_dev": summary_A["dev"]["evidence_hit_at_3"],
        "hit_at_1_test": summary_A["test"]["hit_at_1"],
        "evidence_hit3_test": summary_A["test"]["evidence_hit_at_3"],
    })

    # -------------------------------------------------------------
    # STRATEGY B: By Paragraph (max 500 chars, no metadata filter)
    # -------------------------------------------------------------
    logger.info("=== Running Strategy B (By Paragraph: max 500) ===")
    start_time = time.time()
    chunks_B: list[Chunk] = []
    for p in pages:
        chunks_B.extend(by_paragraph(p, max_size=500))
    logger.info("Strategy B generated %d chunks. Embedding...", len(chunks_B))
    vectors_B = embedder.embed_documents([c.text for c in chunks_B])
    store.upsert("strategy_b", chunks_B, vectors_B)
    time_B = round(time.time() - start_time, 2)
    logger.info("Strategy B stored in %.2fs", time_B)

    traces_B = []
    for q, q_vec in zip(questions, query_vectors):
        hits = store.search("strategy_b", q_vec, top_k=3, filters=None)
        trace = evaluate_query(q, hits)
        traces_B.append(trace)
    summary_B = summarize(traces_B)

    experiment_rows.append({
        "strategy": "B (by-paragraph)",
        "model": model_name,
        "chunk_params": "max_size=500",
        "num_chunks": len(chunks_B),
        "upsert_time_s": time_B,
        "hit_at_1_dev": summary_B["dev"]["hit_at_1"],
        "evidence_hit3_dev": summary_B["dev"]["evidence_hit_at_3"],
        "hit_at_1_test": summary_B["test"]["hit_at_1"],
        "evidence_hit3_test": summary_B["test"]["evidence_hit_at_3"],
    })

    # -------------------------------------------------------------
    # STRATEGY C: By Paragraph + Metadata Filter
    # -------------------------------------------------------------
    logger.info("=== Running Strategy C (By Paragraph + Metadata Filter) ===")
    start_time = time.time()
    # Strategy C uses the exact same chunks and vectors as B (controlled variable)
    store.upsert("strategy_c", chunks_B, vectors_B)
    time_C = round(time.time() - start_time, 2)
    logger.info("Strategy C stored in %.2fs", time_C)

    traces_C = []
    for q, q_vec in zip(questions, query_vectors):
        # Apply filter if provided in question
        filters = q.get("filter")
        hits = store.search("strategy_c", q_vec, top_k=3, filters=filters)
        trace = evaluate_query(q, hits)
        traces_C.append(trace)
    summary_C = summarize(traces_C)

    experiment_rows.append({
        "strategy": "C (paragraph + filter)",
        "model": model_name,
        "chunk_params": "max_size=500,filter=on",
        "num_chunks": len(chunks_B),
        "upsert_time_s": time_C,
        "hit_at_1_dev": summary_C["dev"]["hit_at_1"],
        "evidence_hit3_dev": summary_C["dev"]["evidence_hit_at_3"],
        "hit_at_1_test": summary_C["test"]["hit_at_1"],
        "evidence_hit3_test": summary_C["test"]["evidence_hit_at_3"],
    })

    # -------------------------------------------------------------
    # Save Results & Summaries
    # -------------------------------------------------------------
    (results_dir / "traces_strategy_a.json").write_text(
        json.dumps(traces_A, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (results_dir / "traces_strategy_b.json").write_text(
        json.dumps(traces_B, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (results_dir / "traces_strategy_c.json").write_text(
        json.dumps(traces_C, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    metrics_summary = {
        "strategy_a": summary_A,
        "strategy_b": summary_B,
        "strategy_c": summary_C,
        "parameters": {
            "model": model_name,
            "dimensions": embedder.dimensions,
            "total_questions": len(questions),
            "dev_questions": len([q for q in questions if q.get("split") == "dev"]),
            "test_questions": len([q for q in questions if q.get("split") == "test"]),
            "chunks_a": len(chunks_A),
            "chunks_b": len(chunks_B),
            "chunks_c": len(chunks_B),
        },
    }
    (results_dir / "metrics_summary.json").write_text(
        json.dumps(metrics_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    update_experiment_log(artifacts_dir, experiment_rows)

    # Print summary table
    print("\n" + "=" * 80)
    print("BENCHMARK RETRIEVAL METRICS SUMMARY")
    print("=" * 80)
    print(f"{'Strategy':<24} | {'Hit@1 (dev)':<12} | {'Hit@3 (dev)':<12} | {'Hit@1 (test)':<12} | {'Hit@3 (test)':<12}")
    print("-" * 80)
    for row in experiment_rows:
        print(f"{row['strategy']:<24} | {row['hit_at_1_dev']:<12} | {row['evidence_hit3_dev']:<12} | {row['hit_at_1_test']:<12} | {row['evidence_hit3_test']:<12}")
    print("=" * 80)
    print(f"Results saved to: {results_dir}")


if __name__ == "__main__":
    main()
