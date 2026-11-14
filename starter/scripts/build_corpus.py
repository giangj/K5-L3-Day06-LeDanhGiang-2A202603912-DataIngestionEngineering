"""Build corpus PDFs and manifest.json from raw data."""
import json
import unicodedata
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pypdf

# Register TrueType font with full Vietnamese support
pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def create_pdf_from_pages(pages_dict: dict[str, str], output_pdf: Path) -> None:
    c = canvas.Canvas(str(output_pdf), pagesize=A4)
    width, height = A4
    margin_left = 50
    margin_top = height - 50
    margin_bottom = 50
    line_height = 14

    for page_num_str in sorted(pages_dict.keys(), key=lambda x: int(x)):
        page_text = pages_dict[page_num_str]
        text_obj = c.beginText(margin_left, margin_top)
        text_obj.setFont("Arial", 9)
        
        lines = page_text.split("\n")
        y = margin_top
        for line in lines:
            # Simple line wrapping if line is too long
            while len(line) > 95:
                sub = line[:95]
                # Try to break at space
                space_idx = sub.rfind(" ")
                if space_idx > 60:
                    chunk = line[:space_idx]
                    line = line[space_idx + 1:]
                else:
                    chunk = sub
                    line = line[95:]
                text_obj.textLine(chunk)
                y -= line_height
                if y < margin_bottom:
                    break
            text_obj.textLine(line)
            y -= line_height
            if y < margin_bottom:
                # Still within same logical page in PDF
                pass
        c.drawText(text_obj)
        # Add footer page number
        c.setFont("Arial", 8)
        c.drawRightString(width - 50, 30, f"Trang {page_num_str}")
        c.showPage()
    c.save()
    print(f"Generated {output_pdf.name} with {len(pages_dict)} pages.")


def main():
    # 1. Merge daotao 2022
    p1 = json.loads((DATA_DIR / "raw_daotao_2022_p1_25.json").read_text(encoding="utf-8"))
    p2 = json.loads((DATA_DIR / "raw_daotao_2022_p26_52.json").read_text(encoding="utf-8"))
    daotao_pages = {**p1["pages"], **p2["pages"]}
    daotao_json = {
        "document_id": "quiche_daotao_2022",
        "title": "Quy chế Đào tạo đại học tại Đại học Quốc gia Hà Nội (2022)",
        "year": 2022,
        "scope": "dao_tao_dai_hoc",
        "pages": daotao_pages
    }
    (DATA_DIR / "raw_daotao_2022.json").write_text(json.dumps(daotao_json, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. Build PDFs
    pdf_daotao = DATA_DIR / "quiche_daotao_2022.pdf"
    create_pdf_from_pages(daotao_pages, pdf_daotao)

    ctsv_json = json.loads((DATA_DIR / "raw_ctsv_2014.json").read_text(encoding="utf-8"))
    pdf_ctsv = DATA_DIR / "quiche_ctsv_2014.pdf"
    create_pdf_from_pages(ctsv_json["pages"], pdf_ctsv)

    # 3. Verify text extraction and calculate metrics for manifest
    manifest_entries = []
    docs = [
        ("quiche_daotao_2022", "Quy chế Đào tạo đại học tại Đại học Quốc gia Hà Nội", pdf_daotao, 2022, "dao_tao_dai_hoc", "Quyết định số 3626/QĐ-ĐHQGHN ngày 21/10/2022 của Giám đốc ĐHQGHN"),
        ("quiche_ctsv_2014", "Quy chế Công tác sinh viên tại Đại học Quốc gia Hà Nội", pdf_ctsv, 2014, "cong_tac_sinh_vien", "Quyết định số 5248/QĐ-ĐHQGHN ngày 27/12/2014 của Giám đốc ĐHQGHN")
    ]

    total_valid_pages = 0
    total_valid_chars = 0

    for doc_id, title, pdf_path, year, scope, license_info in docs:
        reader = pypdf.PdfReader(str(pdf_path))
        num_physical = len(reader.pages)
        content_pages = []
        doc_chars = 0
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            norm_text = unicodedata.normalize("NFC", text).strip()
            # If text has meaningful length (> 50 chars), count as content page
            if len(norm_text) > 50:
                content_pages.append(idx + 1)
                doc_chars += len(norm_text)
        
        total_valid_pages += len(content_pages)
        total_valid_chars += doc_chars

        manifest_entries.append({
            "source_id": doc_id,
            "title": title,
            "source_path": f"data/{pdf_path.name}",
            "source_url": "https://vnu.edu.vn",
            "license_or_permission": f"Văn bản pháp quy công khai của ĐHQGHN ({license_info})",
            "accessed_at": "2026-11-14",
            "total_physical_pages": num_physical,
            "content_pages": len(content_pages),
            "content_page_list": content_pages,
            "total_chars_after_normalize": doc_chars,
            "metadata_fields": {
                "year": year,
                "scope": scope,
                "institution": "DHQGHN"
            }
        })

    manifest_path = DATA_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manifest written to {manifest_path.name}")
    print(f"Total documents: {len(manifest_entries)}")
    print(f"Total physical pages: {sum(m['total_physical_pages'] for m in manifest_entries)}")
    print(f"Total content pages: {total_valid_pages} (Requirement >= 30: {'PASSED' if total_valid_pages >= 30 else 'FAILED'})")
    print(f"Total characters: {total_valid_chars}")


if __name__ == "__main__":
    main()
