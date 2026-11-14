# Đánh giá tính hữu dụng của Metadata (Metadata Usefulness Audit)

**Phương pháp:** Kiểm tra chi tiết 5 câu hỏi tập Test $\times$ Top-3 kết quả truy xuất (tổng cộng 15 bản ghi) trên Chiến lược C. Xác minh tính đầy đủ và tính chính xác của các trường metadata (`document_id`, `page`, `source`, `year`, `scope`) so với tài liệu gốc.

## 1. Bảng kiểm tra 15 bản ghi Top-3 của 5 câu Test

| Câu hỏi (Thứ hạng) | Document ID | Trang thực tế | Nguồn lưu trữ | Đánh giá |
|---|---|---|---|---|
| q17 (Top 1) | `quiche_ctsv_2014` | Trang 19 | `data/quiche_ctsv_2014.pdf` | Đúng & Đủ |
| q17 (Top 2) | `quiche_ctsv_2014` | Trang 17 | `data/quiche_ctsv_2014.pdf` | Đúng & Đủ |
| q17 (Top 3) | `quiche_daotao_2022` | Trang 35 | `data/quiche_daotao_2022.pdf` | Đúng & Đủ |
| q18 (Top 1) | `quiche_ctsv_2014` | Trang 20 | `data/quiche_ctsv_2014.pdf` | Đúng & Đủ |
| q18 (Top 2) | `quiche_ctsv_2014` | Trang 22 | `data/quiche_ctsv_2014.pdf` | Đúng & Đủ |
| q18 (Top 3) | `quiche_daotao_2022` | Trang 22 | `data/quiche_daotao_2022.pdf` | Đúng & Đủ |
| q19 (Top 1) | `quiche_daotao_2022` | Trang 11 | `data/quiche_daotao_2022.pdf` | Đúng & Đủ |
| q19 (Top 2) | `quiche_daotao_2022` | Trang 11 | `data/quiche_daotao_2022.pdf` | Đúng & Đủ |
| q19 (Top 3) | `quiche_daotao_2022` | Trang 29 | `data/quiche_daotao_2022.pdf` | Đúng & Đủ |
| q20 (Top 1) | `quiche_daotao_2022` | Trang 14 | `data/quiche_daotao_2022.pdf` | Đúng & Đủ |
| q20 (Top 2) | `quiche_daotao_2022` | Trang 14 | `data/quiche_daotao_2022.pdf` | Đúng & Đủ |
| q20 (Top 3) | `quiche_daotao_2022` | Trang 14 | `data/quiche_daotao_2022.pdf` | Đúng & Đủ |
| q21 (Top 1) | `quiche_daotao_2022` | Trang 49 | `data/quiche_daotao_2022.pdf` | Đúng & Đủ |
| q21 (Top 2) | `quiche_daotao_2022` | Trang 21 | `data/quiche_daotao_2022.pdf` | Đúng & Đủ |
| q21 (Top 3) | `quiche_daotao_2022` | Trang 19 | `data/quiche_daotao_2022.pdf` | Đúng & Đủ |

## 2. Kết quả định lượng
- **Tỷ lệ Metadata Đúng & Đủ:** **15/15** (100.0%). 100% bản ghi đều lưu vết chính xác số trang vật lý của file PDF, ID tài liệu và đường dẫn file nguồn, không có bản ghi nào bị rỗng hoặc mất trang.
- **Tỷ lệ tuân thủ Metadata Filter (Filter Compliance):**
  - Trong tập Test, câu `q22` có điều kiện lọc ngữ cảnh: `filter = {'scope': 'cong_tac_sinh_vien'}`.
  - **Chiến lược A & B:** Không kích hoạt bộ lọc metadata -> Không áp dụng (N/A) hoặc có nguy cơ lấy nhầm văn bản quy chế khác.
  - **Chiến lược C:** Top-3 chunk trả về đều thuộc đúng phạm vi quy chế yêu cầu -> **1/1 câu tuân thủ tuyệt đối (100%)**.

## 3. Phân tích giá trị và hạn chế của Metadata
- **Giá trị thực tế:**
  1. *Truy vết nguồn gốc (Traceability):* Nhờ có trường `page` và `document_id`, hệ thống có thể dẫn thẳng người dùng đến số trang chính xác trong văn bản PDF để kiểm chứng (Fact-checking).
  2. *Thu hẹp không gian tìm kiếm (Search Scope Pruning):* Trường metadata `scope` (`dao_tao_dai_hoc` vs `cong_tac_sinh_vien`) giúp ngăn chặn hoàn toàn việc nhầm lẫn giữa hai bộ quy chế có các thuật ngữ tương đồng (như cùng nói về khen thưởng, kỷ luật hoặc hồ sơ sinh viên).
- **Hạn chế:** Metadata phụ thuộc vào chất lượng trích xuất ban đầu. Nếu văn bản không có mục lục chuẩn hoặc không phân tách rõ năm ban hành thì việc gán nhãn thủ công tốn thời gian và dễ sai sót nếu người tạo manifest không đọc kỹ văn bản.
