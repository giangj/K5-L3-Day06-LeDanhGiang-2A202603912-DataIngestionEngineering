"""Evaluate retrieved evidence and preserve per-query traces."""
import re
import unicodedata
from typing import Any


def _normalize_for_match(text: str) -> str:
    """Normalize text for substring/evidence matching."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and gold evidence quote in hits; produce full trace."""
    gold_source = question.get("gold_source_id", "")
    gold_page = question.get("gold_page", 0)
    evidence_quote = question.get("evidence_quote", "")
    norm_evidence = _normalize_for_match(evidence_quote)

    hit_at_1 = False
    evidence_hit_at_3 = False

    # Check top-1
    if hits:
        top1 = hits[0]
        if top1.get("document_id") == gold_source and top1.get("page") == gold_page:
            hit_at_1 = True

    # Check top-3 for evidence
    top3 = hits[:3]
    for h in top3:
        doc_match = (h.get("document_id") == gold_source)
        page_match = (h.get("page") == gold_page)
        
        # Check text match
        chunk_text = _normalize_for_match(h.get("text", ""))
        evidence_found = False
        if norm_evidence and norm_evidence in chunk_text:
            evidence_found = True
        elif norm_evidence:
            # Fallback: check if major words (>= 4 chars) of quote are in chunk
            words = [w for w in norm_evidence.split() if len(w) >= 4]
            if words and sum(1 for w in words if w in chunk_text) / len(words) >= 0.75:
                evidence_found = True

        if (doc_match and page_match) or evidence_found:
            evidence_hit_at_3 = True
            break

    return {
        "id": question.get("id"),
        "split": question.get("split"),
        "type": question.get("type", "standard"),
        "question": question.get("question"),
        "expected_answer": question.get("expected_answer"),
        "gold_source_id": gold_source,
        "gold_page": gold_page,
        "evidence_quote": evidence_quote,
        "filter": question.get("filter"),
        "hit_at_1": hit_at_1,
        "evidence_hit_at_3": evidence_hit_at_3,
        "hits": hits,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by dev and test splits in fraction format."""
    summary: dict[str, Any] = {}

    for split in ["dev", "test", "total"]:
        if split == "total":
            split_traces = traces
        else:
            split_traces = [t for t in traces if t.get("split") == split]

        total = len(split_traces)
        if total == 0:
            summary[split] = {
                "total": 0,
                "hit_at_1": "0/0",
                "hit_at_1_pct": 0.0,
                "evidence_hit_at_3": "0/0",
                "evidence_hit_at_3_pct": 0.0,
            }
            continue

        hit_1 = sum(1 for t in split_traces if t.get("hit_at_1"))
        hit_3 = sum(1 for t in split_traces if t.get("evidence_hit_at_3"))

        summary[split] = {
            "total": total,
            "hit_at_1": f"{hit_1}/{total}",
            "hit_at_1_pct": round((hit_1 / total) * 100, 2),
            "evidence_hit_at_3": f"{hit_3}/{total}",
            "evidence_hit_at_3_pct": round((hit_3 / total) * 100, 2),
        }

    return summary
