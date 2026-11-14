"""Read and normalize source data."""
import logging
import re
import unicodedata
from pathlib import Path
import pypdf
from .models import DocumentPage

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize Unicode (NFC) and whitespace while preserving paragraph structure."""
    if not text:
        return ""
    # 1. Unicode NFC normalization
    text = unicodedata.normalize("NFC", text)
    # 2. Standardize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 3. Replace non-breaking spaces and zero-width spaces
    text = text.replace("\xa0", " ").replace("\u200b", "")
    # 4. Clean line by line
    cleaned_lines = []
    for line in text.split("\n"):
        cleaned_line = re.sub(r"[ \t]+", " ", line).strip()
        cleaned_lines.append(cleaned_line)
    text = "\n".join(cleaned_lines)
    # 5. Collapse excessive blank lines: more than 2 newlines -> 2 newlines (preserve paragraphs)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_pdf(path: Path, document_id: str, source: str, metadata: dict | None = None) -> list[DocumentPage]:
    """Extract physical pages from PDF, retaining page numbers and metadata.

    Logs any empty pages encountered.
    """
    reader = pypdf.PdfReader(str(path))
    pages: list[DocumentPage] = []
    base_meta = metadata or {}

    for idx, pdf_page in enumerate(reader.pages):
        page_num = idx + 1
        raw_text = pdf_page.extract_text() or ""
        clean_text = normalize_text(raw_text)

        if not clean_text:
            logger.warning("Empty or unextractable text on page %d of %s", page_num, path)

        page_meta = {
            **base_meta,
            "document_id": document_id,
            "source": source,
            "page": page_num,
        }
        pages.append(
            DocumentPage(
                document_id=document_id,
                source=source,
                page=page_num,
                text=clean_text,
                metadata=page_meta,
            )
        )

    logger.info("Loaded %d pages from %s (document_id=%s)", len(pages), path, document_id)
    return pages
