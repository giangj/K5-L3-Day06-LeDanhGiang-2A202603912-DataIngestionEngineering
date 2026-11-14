"""Implement fixed-size and structure-aware chunking."""
import re
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split page text into overlapping fixed-size character windows, retaining metadata."""
    text = page.text.strip()
    if not text:
        return []

    if len(text) <= size:
        chunk_id = f"{page.document_id}_p{page.page}_c0"
        return [
            Chunk(
                chunk_id=chunk_id,
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=text,
                metadata={**page.metadata, "chunk_id": chunk_id, "chunk_index": 0},
            )
        ]

    chunks: list[Chunk] = []
    step = max(1, size - overlap)
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + size, len(text))
        sub_text = text[start:end].strip()
        if sub_text:
            chunk_id = f"{page.document_id}_p{page.page}_c{idx}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=sub_text,
                    metadata={
                        **page.metadata,
                        "chunk_id": chunk_id,
                        "chunk_index": idx,
                        "start_char": start,
                        "end_char": end,
                    },
                )
            )
            idx += 1
        if end >= len(text):
            break
        start += step

    return chunks


def _split_oversized_paragraph(para: str, max_size: int) -> list[str]:
    """Split a paragraph that exceeds max_size into smaller sentence-aware pieces."""
    # Split by sentence ending punctuation while preserving sentences
    sentence_delimiters = re.split(r"(?<=[.!?;\n])\s+", para)
    pieces: list[str] = []
    current = ""

    for s in sentence_delimiters:
        s = s.strip()
        if not s:
            continue
        if len(s) > max_size:
            # If even a single sentence is huge, slice it hard
            if current:
                pieces.append(current.strip())
                current = ""
            for i in range(0, len(s), max_size - 40):
                piece = s[i:i + max_size].strip()
                if piece:
                    pieces.append(piece)
        elif len(current) + len(s) + 1 <= max_size:
            current = f"{current} {s}" if current else s
        else:
            if current:
                pieces.append(current.strip())
            current = s

    if current:
        pieces.append(current.strip())
    return pieces


def by_paragraph(page: DocumentPage, max_size: int = 500) -> list[Chunk]:
    """Group paragraphs, split oversized paragraphs, and retain page metadata."""
    text = page.text.strip()
    if not text:
        return []

    # First split by double newlines or single newlines that look like separate items
    raw_paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not raw_paras:
        raw_paras = [text]

    # Normalize paragraph list (split any that are already > max_size)
    normalized_paras: list[str] = []
    for p in raw_paras:
        if len(p) <= max_size:
            normalized_paras.append(p)
        else:
            normalized_paras.extend(_split_oversized_paragraph(p, max_size))

    # Group paragraphs up to max_size
    chunks: list[Chunk] = []
    current_buf: list[str] = []
    current_len = 0
    idx = 0

    for p in normalized_paras:
        # Check if adding p exceeds max_size
        additional_len = len(p) + (2 if current_buf else 0)
        if current_buf and (current_len + additional_len > max_size):
            chunk_text = "\n\n".join(current_buf).strip()
            chunk_id = f"{page.document_id}_p{page.page}_para{idx}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=chunk_text,
                    metadata={
                        **page.metadata,
                        "chunk_id": chunk_id,
                        "chunk_index": idx,
                    },
                )
            )
            idx += 1
            current_buf = [p]
            current_len = len(p)
        else:
            current_buf.append(p)
            current_len += additional_len

    if current_buf:
        chunk_text = "\n\n".join(current_buf).strip()
        chunk_id = f"{page.document_id}_p{page.page}_para{idx}"
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata={
                    **page.metadata,
                    "chunk_id": chunk_id,
                    "chunk_index": idx,
                },
            )
        )

    return chunks
