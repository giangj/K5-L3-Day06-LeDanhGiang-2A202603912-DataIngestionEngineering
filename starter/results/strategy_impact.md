# Phân tích tác động của Chiến lược Dữ liệu (Data Strategy Impact)

Báo cáo phân tích đối chứng giữa các chiến lược dữ liệu trên cùng một bộ Corpus (76 trang quy chế ĐHQGHN), cùng một Embedding Model (`gemini-embedding-001`, 768 chiều) và cùng bộ câu hỏi Benchmark (22 câu).

---

## 1. So sánh Chiến lược A (Fixed-size 500/50) và Chiến lược B (By-paragraph max 500)

* **Về mặt chunking:**
  - Chiến lược A chia mù theo độ dài 500 ký tự với 50 ký tự gối đầu (overlap), sinh ra **346 chunks**.
  - Chiến lược B tôn trọng ranh giới đoạn văn (`

`) và đề mục quy chế (Điều, Khoản), chỉ cắt nhỏ khi đoạn vượt quá 500 ký tự, sinh ra **370 chunks**.
* **Hiệu quả truy xuất (Retrieval Accuracy):**
  - **Dev:** Chiến lược A đạt Hit@1 = **15/16 (93.75%)**; Chiến lược B đạt Hit@1 = **16/16 (100.0%)**.
  - **Test:** Chiến lược A đạt Hit@1 = **4/6 (66.67%)**; Chiến lược B đạt Hit@1 = **6/6 (100.0%)**.
* **Tính mạch lạc (Coherence):**
  - Chiến lược A chỉ đạt trung bình **0.10/2** do thường xuyên cắt đứt ngang từ ngữ tiếng Việt ('học tập' -> 'họ', 'giao nhiệm vụ' -> 'giao nh', 'chương trình' -> 'chương tr').
  - Chiến lược B đạt trung bình **1.80/2** nhờ giữ nguyên vẹn câu văn và điều khoản pháp lý.
* **Đánh đổi tài nguyên:** Chiến lược B tăng nhẹ 6.9% số lượng chunk (370 so với 346), thời gian nạp tăng không đáng kể (~4.7s so với ~4.2s), nhưng đổi lại sự gia tăng vượt trội về độ chính xác Hit@1 trên tập Test (+33.33%).

---

## 2. So sánh Chiến lược B (By-paragraph, No Filter) và Chiến lược C (By-paragraph + Metadata Filter)

* **Thiết kế biến số cô lập (Controlled Variable):**
  - Chiến lược C sử dụng **100% cùng các chunk và vector nhúng của Chiến lược B** (thời gian nạp chỉ mất 4.14s, chi phí thêm = 0).
  - Biến số duy nhất thay đổi là: Khi câu hỏi có metadata filter (ví dụ lọc theo `scope` hoặc `year`), hệ thống kích hoạt điều kiện lọc SQL `WHERE metadata @> ...::jsonb`.
* **Hiệu quả thực tế:**
  - Cả B và C đều đạt Hit@1 = 16/16 (Dev) và 6/6 (Test).
  - Tuy nhiên, Chiến lược C tạo ra sự **đảm bảo tuyệt đối về mặt phạm vi (Deterministic Scope Guarantee)**: Với câu hỏi chỉ đích danh quy chế nào, 100% top-3 chunk của Chiến lược C đều thuộc về văn bản đó, loại bỏ hoàn toàn rủi ro mô hình bị ảo giác hoặc trích nhầm điều khoản trùng tên từ văn bản khác.

---

## 3. Phân tích chi tiết 2 trường hợp thất bại (Failure Analysis)

### Ví dụ lỗi 1: Câu `q13` (Tập Dev)
* **ID câu hỏi:** `q13`
* **Nội dung:** *"Theo quy chế đào tạo đại học năm 2022, sinh viên cần đạt điểm trung bình chung tích lũy toàn khóa tối thiểu bao nhiêu để được xếp hạng tốt nghiệp loại Giỏi?"*
* **Nguồn Gold:** `quiche_daotao_2022.pdf`, Trang 49 (Điều 44: Xếp hạng tốt nghiệp, quy định điểm từ 3.20 đến 3.59).
* **Hiện tượng ở Chiến lược A:**
  - Top 1 truy xuất được: `quiche_daotao_2022.pdf`, Trang 47 (Điều 42: Điều kiện xét tốt nghiệp) với score 0.2371.
  - Chunk chứa đáp án đúng ở Trang 49 bị đẩy xuống **Rank 2 (score 0.2452)** và **Rank 3 (score 0.2573)** -> **Fail Hit@1**.
* **Nguyên nhân gốc rễ (Root Cause):** Do cửa sổ cắt cứng 500 ký tự cắt ngang bảng tiêu chuẩn xếp hạng tốt nghiệp ở Điều 44, làm tách rời tiêu đề "Điều 44. Xếp hạng tốt nghiệp" với bảng điểm quy định cụ thể. Mặt khác, Trang 47 có chứa cụm từ "chuẩn đầu ra", "điều kiện tốt nghiệp" nằm trọn trong 500 ký tự nên có khoảng cách cosine nhỏ hơn so với query.
* **Khắc phục ở Chiến lược B/C:** B gom trọn vẹn cả Điều 44 vào một chunk độc lập, giúp vector đại diện chứa đầy đủ cả tiêu đề lẫn các thang điểm Xuất sắc/Giỏi/Khá, nhờ đó vươn lên Top 1 với độ tương đồng vượt trội.

### Ví dụ lỗi 2: Câu `q18` (Tập Test)
* **ID câu hỏi:** `q18`
* **Nội dung:** *"Trong trường hợp bất khả kháng khi nhập trường, sinh viên được phép nộp bổ sung hồ sơ trong thời gian tối đa bao nhiêu ngày?"*
* **Nguồn Gold:** `quiche_ctsv_2014.pdf`, Trang 20 (Điều 4: Hồ sơ sinh viên, khoản 3 quy định tối đa 30 ngày).
* **Hiện tượng ở Chiến lược A:**
  - Top 1 truy xuất được: `quiche_ctsv_2014.pdf`, Trang 22 (Điều 8: Tiếp nhận sinh viên chuyển trường) với score 0.2790.
  - Trang 20 chứa đáp án đúng bị đẩy xuống **Rank 2 (score 0.2896)** -> **Fail Hit@1**.
* **Nguyên nhân gốc rễ (Root Cause):** Đoạn quy định về hồ sơ nhập học ở Trang 20 bị cắt thành 2 chunk vụn ở ký tự thứ 500, trong đó từ khóa "hồ sơ sinh viên" nằm ở chunk trước còn "thời gian tối đa 30 ngày" lại rơi vào chunk sau. Chunk ở Trang 22 về chuyển trường lại chứa trọn vẹn cụm từ "nộp hồ sơ trong thời hạn" nên mô hình embedding chấm điểm cao hơn.
* **Khắc phục ở Chiến lược B/C:** B giữ nguyên toàn bộ Điều 4 khoản 3 trong 1 chunk paragraph duy nhất, liên kết trực tiếp giữa "hồ sơ nhập trường", "lý do bất khả kháng" và "tối đa 30 ngày", đạt Rank 1 chính xác tuyệt đối.

---

## 4. Kết luận và Khuyến nghị
- **Chiến lược được chọn:** **Chiến lược C (Paragraph-based chunking + Metadata filtering)** là lựa chọn tối ưu nhất cho hệ thống RAG văn bản pháp quy/học vụ.
- **Lý do:** Đạt điểm tuyệt đối trên cả Dev và Test (100% Hit@1, 100% Hit@3), điểm Coherence cao (1.80/2), điểm Grounding tuyệt đối (2.0/2), đồng thời kiểm soát chặt chẽ phạm vi truy xuất thông qua metadata.
