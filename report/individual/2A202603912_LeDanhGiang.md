# Báo cáo cá nhân — Day 6: Data Ingestion Engineering

- **Học viên:** Lê Danh Giang
- **Mã số sinh viên (MSSV):** 2A202603912
- **Lớp:** L3B
- **Repository nộp bài:** [giangj/K5-L3-Day06-LeDanhGiang-2A202603912-DataIngestionEngineering](https://github.com/giangj/K5-L3-Day06-LeDanhGiang-2A202603912-DataIngestionEngineering)

---

## 1. Dữ liệu và pipeline

- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  - *Chủ đề:* Hệ thống văn bản quy chế đào tạo đại học và công tác sinh viên chính thức tại Đại học Quốc gia Hà Nội (ĐHQGHN).
  - *Nguồn và quyền tái phân phối:* Văn bản pháp quy công khai, truy cập hợp pháp từ cổng thông tin ĐHQGHN gồm:
    1. `quiche_daotao_2022.pdf`: Quyết định số 3626/QĐ-ĐHQGHN ngày 21/10/2022 của Giám đốc ĐHQGHN ban hành Quy chế đào tạo đại học (áp dụng từ khóa QH.2022).
    2. `quiche_ctsv_2014.pdf`: Quyết định số 5248/QĐ-ĐHQGHN ngày 16/12/2014 của Giám đốc ĐHQGHN ban hành Quy chế công tác sinh viên.
  - *Quy mô và quy tắc tính trang:* Tổng cộng **76 trang vật lý** (52 trang file Đào tạo + 24 trang file CTSV). Cả 76 trang đều là trang nội dung có chữ hữu ích (không có trang bìa rỗng hay trang quảng cáo), chứa tổng cộng **141.939 ký tự** sau chuẩn hóa (trung bình ~1.867 ký tự/trang, vượt xa yêu cầu tối thiểu 30 trang của đề bài). Chi tiết danh sách trang được lưu tại `data/manifest.json`.

- **Chuẩn hóa, lỗi và giới hạn:**
  - *Chuẩn hóa Unicode:* Sử dụng `unicodedata.normalize('NFC', text)` đưa toàn bộ văn bản về dạng chuẩn dựng sẵn (NFC).
  - *Làm sạch ký tự trắng:* Chuẩn hóa dấu ngắt dòng `\r\n` -> `\n`, loại bỏ khoảng trắng không ngắt (`\xa0`) và zero-width space (`\u200b`). Dọn khoảng trắng lặp `[ \t]+` -> ` `, nén các dòng trống liên tiếp thành `\n\n` để bảo toàn cấu trúc phân đoạn đoạn văn.
  - *Xử lý lỗi trích xuất:* Kiểm tra và ghi log các trang rỗng; cả 76 trang đều trích xuất thành công 100% văn bản nguyên bản qua `pypdf`.

- **Embedding model, Vector store, Metric, Lệnh chạy và Chi phí:**
  - *Embedding Model:* Google Gemini Embedding API, model `models/gemini-embedding-001`, vector kích thước **768 chiều** (cấu hình `outputDimensionality: 768`). Tích hợp SQLite cache lưu trên ổ đĩa (`data/gemini_embeddings_cache.sqlite`) và cơ chế exponential backoff khi gặp HTTP 429.
  - *Vector Store:* **PostgreSQL 16.16** tích hợp extension **`pgvector` 0.8.7**, triển khai trên Docker container local (`image: pgvector/pgvector:0.8.7-pg16`) tại cổng `127.0.0.1:55433`, kết nối qua driver pure-python `pg8000`.
  - *Distance Metric:* Cosine distance (`<=>`).
  - *Lệnh chạy:*
    ```powershell
    cd starter
    .\.venv\Scripts\Activate.ps1
    python -m src.run
    ```
  - *Chi phí:* **0 VNĐ (0.00$)** — Tận dụng gói miễn phí Google Gemini API Free Tier và Docker Desktop chạy local.

- **Metadata bắt buộc và trường lọc bổ sung:**
  - *Trường bắt buộc:* `document_id` (`quiche_daotao_2022`, `quiche_ctsv_2014`), `source` (đường dẫn file), `page` (số trang vật lý từ 1 đến N).
  - *Trường lọc bổ sung:*
    - `scope` (`dao_tao_dai_hoc` hoặc `cong_tac_sinh_vien`): Phân loại phạm vi áp dụng quy chế.
    - `year` (`2022` hoặc `2014`): Năm ban hành văn bản.
    - `title`: Tên chính thức của văn bản.
  - *Lý do chọn:* Hai văn bản quy chế của ĐHQGHN có nhiều thuật ngữ dùng chung (như "khen thưởng", "kỷ luật", "hồ sơ nhập học", "thôi học"). Việc gắn trường `scope` và `year` giúp phân tách rành mạch không gian vector, ngăn ngừa hiện tượng tìm nhầm quy chế cũ hoặc sai phạm vi nghiệp vụ.

---

## 2. Cấu hình và benchmark

- **Mô tả 3 Chiến lược (A / B / C):**
  - **Chiến lược A (Fixed-size):** Cắt văn bản theo cửa sổ cố định `size=500` ký tự, độ gối đầu `overlap=50` ký tự. Không áp dụng bộ lọc metadata (`filters=None`).
  - **Chiến lược B (By-paragraph):** Tách văn bản theo cấu trúc đoạn văn (`\n\n`) và đề mục điều khoản luật (`max_size=500` ký tự). Nếu đoạn vượt quá 500 ký tự thì chia tách có nhận thức về ranh giới câu (`.`, `!`, `?`, `;`). Không áp dụng bộ lọc metadata (`filters=None`).
  - **Chiến lược C (Paragraph + Filter):** Tái sử dụng **100% cùng các chunk và vector nhúng của Chiến lược B** (đảm bảo biến số cô lập kiểm soát khoa học). Khi câu hỏi có khai báo `filter` (ví dụ `scope` hoặc `year`), hệ thống thực hiện lọc tiền truy vấn trong cơ sở dữ liệu qua cú pháp SQL `WHERE metadata @> ...::jsonb`.

- **Bộ câu hỏi Benchmark (≥20 câu):**
  - Xây dựng **22 câu hỏi** (16 câu tập `dev`, 6 câu tập `test`) lưu tại `data/benchmark_questions.json`.
  - Có 3 câu hỏi kiểm tra metadata filter: `q13`, `q16` (thuộc `dev`) và `q22` (thuộc `test`).
  - 100% các câu hỏi đều có `gold_source_id`, `gold_page` và trích dẫn nguyên văn bằng chứng `evidence_quote` được kiểm chứng tồn tại thực tế trên trang PDF nguồn sau chuẩn hóa.

- **Tiêu chí chọn chiến lược chốt trước khi xem test:**
  - Tiêu chí 1: Evidence Hit@3 trên tập test phải đạt $\ge 90\%$.
  - Tiêu chí 2: Grounding Quality trên tập test phải đạt điểm trung bình $\ge 1.8/2$.
  - Tiêu chí 3: Chunk Coherence phải đạt $\ge 1.5/2$ để đảm bảo người đọc và LLM hiểu trọn vẹn ngữ cảnh điều khoản.
  - Tiêu chí 4: Khả năng kiểm soát phạm vi và tính cô lập rủi ro thông qua metadata filter.

---

## 3. Kết quả thực nghiệm

### Bảng 1: Hiệu năng truy xuất và Tài nguyên (Quantitative Metrics)

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian Upsert | Chi phí |
|---|---|---|---|---|---|---|
| **A (Fixed-size 500/50)** | Dev | 15/16 (93.8%) | 16/16 (100.0%) | 346 | 4.19s | 0$ |
| **A (Fixed-size 500/50)** | Test | 4/6 (66.7%) | 6/6 (100.0%) | 346 | 4.19s | 0$ |
| **B (By-paragraph)** | Dev | 16/16 (100.0%) | 16/16 (100.0%) | 370 | 4.71s | 0$ |
| **B (By-paragraph)** | Test | 6/6 (100.0%) | 6/6 (100.0%) | 370 | 4.71s | 0$ |
| **C (Paragraph + Filter)** | Dev | 16/16 (100.0%) | 16/16 (100.0%) | 370 | 4.14s | 0$ |
| **C (Paragraph + Filter)** | Test | 6/6 (100.0%) | 6/6 (100.0%) | 370 | 4.14s | 0$ |

*Kiểm tra tính Idempotency:* Nạp lại toàn bộ dữ liệu lần 2, tổng số chunk trong bảng `document_chunks` của PostgreSQL vẫn giữ nguyên chính xác: `strategy_a`: 346 chunks, `strategy_b`: 370 chunks, `strategy_c`: 370 chunks (hoàn toàn không bị nhân đôi dữ liệu).

---

### Bảng 2: Đánh giá thủ công 5 Tiêu chí (Manual Audit)

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| **A (Fixed-size)** | **0.10/2** (10 vị trí) | 15/15 (100%) | N/A (Không bật filter) | 0 câu 0đ, 1 câu 1đ, 4 câu 2đ -> **1.80/2** |
| **B (By-paragraph)** | **1.80/2** (10 vị trí) | 15/15 (100%) | N/A (Không bật filter) | 0 câu 0đ, 0 câu 1đ, 5 câu 2đ -> **2.00/2** |
| **C (Paragraph + Filter)** | **1.80/2** (10 vị trí) | 15/15 (100%) | **1/1 (100%)** | 0 câu 0đ, 0 câu 1đ, 5 câu 2đ -> **2.00/2** |

- **Đường dẫn vết thực nghiệm và báo cáo Audit chi tiết:**
  - Dữ liệu trace: [`results/traces_strategy_a.json`](file:///e:/AI_vin20k/K5-L3-Day06-DataIngestionEngineering-main/K5-L3-Day06-DataIngestionEngineering-main/results/traces_strategy_a.json), [`results/traces_strategy_b.json`](file:///e:/AI_vin20k/K5-L3-Day06-DataIngestionEngineering-main/K5-L3-Day06-DataIngestionEngineering-main/results/traces_strategy_b.json), [`results/traces_strategy_c.json`](file:///e:/AI_vin20k/K5-L3-Day06-DataIngestionEngineering-main/K5-L3-Day06-DataIngestionEngineering-main/results/traces_strategy_c.json)
  - Tổng hợp chỉ số: [`results/metrics_summary.json`](file:///e:/AI_vin20k/K5-L3-Day06-DataIngestionEngineering-main/K5-L3-Day06-DataIngestionEngineering-main/results/metrics_summary.json), [`artifacts/experiment_log.csv`](file:///e:/AI_vin20k/K5-L3-Day06-DataIngestionEngineering-main/K5-L3-Day06-DataIngestionEngineering-main/artifacts/experiment_log.csv)
  - Báo cáo Audit mạch lạc: [`results/coherence_audit.md`](file:///e:/AI_vin20k/K5-L3-Day06-DataIngestionEngineering-main/K5-L3-Day06-DataIngestionEngineering-main/results/coherence_audit.md)
  - Báo cáo Audit metadata: [`results/metadata_audit.md`](file:///e:/AI_vin20k/K5-L3-Day06-DataIngestionEngineering-main/K5-L3-Day06-DataIngestionEngineering-main/results/metadata_audit.md)
  - Báo cáo Audit grounding: [`results/grounding_audit.md`](file:///e:/AI_vin20k/K5-L3-Day06-DataIngestionEngineering-main/K5-L3-Day06-DataIngestionEngineering-main/results/grounding_audit.md)
  - Báo cáo Phân tích tác động & ca lỗi: [`results/strategy_impact.md`](file:///e:/AI_vin20k/K5-L3-Day06-DataIngestionEngineering-main/K5-L3-Day06-DataIngestionEngineering-main/results/strategy_impact.md)

---

## 4. Phân tích và kết luận

### 1. So sánh Chiến lược A–B và B–C
- **A vs B (Tác động của phương pháp Chunking):**
  - Cắt cửa sổ cố định (A) cắt đứt cơ học ở đúng 500 ký tự, thường xuyên xé vụn các từ ngữ tiếng Việt ngay giữa từ (như 'học tập' thành 'họ', 'chương trình' thành 'chương tr') và tách rời tiêu đề điều khoản với nội dung chi tiết. Hệ quả là điểm Coherence của A rớt xuống mức **0.10/2**, và độ chính xác Hit@1 trên tập Test giảm mạnh từ 100% xuống **66.7%** (4/6 câu).
  - Phân tách theo đoạn văn (B) tôn trọng cấu trúc pháp quy, giúp điểm Coherence tăng vọt lên **1.80/2**, bảo toàn 100% câu văn và nâng Hit@1 lên **100.0%** trên cả hai tập.
- **B vs C (Tác động của Metadata Filtering):**
  - B và C cùng đạt 100% Hit@1 trên tập benchmark do các câu hỏi kiểm thử được thiết kế tương đối rõ nét.
  - Tuy nhiên, Chiến lược C vượt trội ở khả năng **ngăn chặn rủi ro xâm lấn chéo văn bản (Cross-document Contamination)**: Nhờ có mệnh đề `WHERE metadata @> '{"scope": "cong_tac_sinh_vien"}'::jsonb`, Chiến lược C loại bỏ triệt để các chunk từ quy chế đào tạo khi người dùng chỉ hỏi về quy chế công tác sinh viên, đảm bảo tuân thủ filter tuyệt đối 100%.

### 2. Phân tích 2 ví dụ thất bại có ID câu và nguồn dẫn

#### Ví dụ 1: Câu `q13` (Tập Dev — Thất bại ở Chiến lược A)
- **ID câu:** `q13`
- **Nội dung:** *"Theo quy chế đào tạo đại học năm 2022, sinh viên cần đạt điểm trung bình chung tích lũy toàn khóa tối thiểu bao nhiêu để được xếp hạng tốt nghiệp loại Giỏi?"*
- **Nguồn Gold:** `quiche_daotao_2022.pdf`, Trang 49 (Điều 44: Xếp hạng tốt nghiệp, quy định điểm từ 3.20 đến 3.59).
- **Hiện tượng lỗi:** Chiến lược A trả về Top 1 là Trang 47 (Điều 42: Điều kiện tốt nghiệp) với score 0.2371. Bằng chứng đúng ở Trang 49 bị đẩy xuống **Rank 2 (score 0.2452)** và **Rank 3 (score 0.2573)**.
- **Nguyên nhân gốc rễ:** Cửa sổ cắt cứng 500 ký tự cắt đôi bảng quy định xếp hạng tốt nghiệp tại Điều 44, làm tách rời tiêu đề "Điều 44. Xếp hạng tốt nghiệp" khỏi phần thân bảng điểm. Ngược lại, đoạn text ở Trang 47 chứa đầy đủ cụm "chuẩn đầu ra", "điều kiện tốt nghiệp" nằm trọn vẹn trong một chunk 500 ký tự nên có khoảng cách cosine nhỏ hơn so với query.
- **Khắc phục:** Chiến lược B/C gom toàn bộ Điều 44 vào một chunk đoạn văn hoàn chỉnh, giữ trọn vẹn cả tiêu đề lẫn các điều kiện thang điểm, giúp câu này đạt Top 1 chính xác.

#### Ví dụ 2: Câu `q18` (Tập Test — Thất bại ở Chiến lược A)
- **ID câu:** `q18`
- **Nội dung:** *"Trong trường hợp bất khả kháng khi nhập trường, sinh viên được phép nộp bổ sung hồ sơ trong thời gian tối đa bao nhiêu ngày?"*
- **Nguồn Gold:** `quiche_ctsv_2014.pdf`, Trang 20 (Điều 4: Hồ sơ sinh viên, khoản 3 quy định tối đa 30 ngày).
- **Hiện tượng lỗi:** Chiến lược A trả về Top 1 là Trang 22 (Điều 8: Tiếp nhận sinh viên chuyển trường) với score 0.2790. Trang 20 chứa đáp án đúng bị đẩy xuống **Rank 2 (score 0.2896)**.
- **Nguyên nhân gốc rễ:** Quy định về hồ sơ nhập học ở Trang 20 bị ngắt đôi ở ký tự 500, khiến cụm từ "hồ sơ sinh viên" và "thời gian tối đa 30 ngày" nằm ở hai chunk khác nhau. Trong khi đó, chunk ở Trang 22 về thủ tục chuyển trường lại chứa trọn cụm "nộp hồ sơ trong thời hạn" nên mô hình embedding bị đánh lừa ngữ nghĩa.
- **Khắc phục:** Chiến lược B/C giữ nguyên Điều 4 khoản 3 trong 1 chunk duy nhất, bảo toàn mối liên hệ trực tiếp giữa "hồ sơ nhập học", "bất khả kháng" và "tối đa 30 ngày", đạt Rank 1 tuyệt đối.

### 3. Chiến lược được chọn, Đánh đổi và Điều kiện áp dụng
- **Chiến lược được chọn:** **Chiến lược C (Paragraph-based chunking + Metadata filtering)**.
- **Đánh đổi:** Số lượng chunk tăng nhẹ từ 346 lên 370 (+6.9%), chi phí lưu trữ tăng không đáng kể nhưng mang lại tính mạch lạc cao gấp 18 lần (1.80 vs 0.10), nâng Hit@1 trên tập Test từ 66.7% lên 100%, và bảo đảm cô lập nghiệp vụ tuyệt đối.
- **Điều kiện áp dụng:** Rất phù hợp cho các hệ thống hỏi đáp quy chế học vụ, tài liệu pháp lý, sổ tay nhân viên và chính sách doanh nghiệp — nơi mà cấu trúc điều/khoản/mục mang tính quyết định đến tính đúng đắn của câu trả lời.

### 4. Hạn chế của dữ liệu và thử nghiệm
- Bộ câu hỏi kiểm thử test gồm 6 câu là quy mô mẫu minh họa ban đầu (Proof of Concept), chưa thể đại diện hết toàn bộ các góc khuất ngữ nghĩa của hai cuốn quy chế dày 76 trang.
- Metadata `scope` và `year` hiện tại được gán ở cấp độ trang/tài liệu; chưa mở rộng sang gắn metadata chi tiết đến từng Chương/Mục nhỏ bên trong văn bản.

### 5. Hướng cải tiến mở rộng (Next Steps)
1. **Tìm kiếm lai (Hybrid Retrieval):** Kết hợp Dense vector search (`gemini-embedding-001`) với Thư viện tìm kiếm từ khóa thưa BM25 (Sparse Vector) sử dụng thuật toán Reciprocal Rank Fusion (RRF) để tối ưu các câu hỏi chứa mã học phần hoặc con số chính xác.
2. **Tái xếp hạng (Reranking):** Bổ sung một mô hình Cross-Encoder (như BGE-Reranker) cho Top-10 kết quả trước khi đưa vào ngữ cảnh của LLM.
3. **Chunking đa cấp (Hierarchical / Parent-Child Chunking):** Lưu các chunk con nhỏ (150–200 ký tự) để embedding đạt độ chính xác cao nhất, nhưng khi retrieve thì trả về toàn bộ Điều/Khoản cha (Parent Chunk) để LLM có ngữ cảnh hoàn chỉnh 100%.
