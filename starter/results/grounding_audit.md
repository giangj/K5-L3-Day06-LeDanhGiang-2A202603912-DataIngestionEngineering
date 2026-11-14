# Đánh giá chất lượng bằng chứng thông tin nền (Grounding Quality Audit)

> [!IMPORTANT]
> **Định nghĩa Grounding trong bài lab:** Đánh giá mức độ đầy đủ của bằng chứng trong Top-3 kết quả truy xuất (Evidence Sufficiency), hoàn toàn **không đánh giá câu trả lời sinh ra từ mô hình sinh LLM**.

**Thang điểm chấm thủ công:**
- **0 điểm:** Top-3 không chứa thông tin hoặc bằng chứng để trả lời câu hỏi.
- **1 điểm:** Top-3 có chứa thông tin liên quan nhưng bị thiếu điều kiện tiên quyết, thiếu trường hợp ngoại lệ hoặc bằng chứng bị cắt vụn.
- **2 điểm:** Top-3 cung cấp đầy đủ thông tin, điều kiện, ngoại lệ và nguồn dẫn xác thực để trả lời câu hỏi một cách thuyết phục.

## 1. Bảng chấm chi tiết 5 câu Test

| ID | Tóm tắt câu hỏi | Đánh giá Grounding Chiến lược A | Đánh giá Grounding Chiến lược B | Đánh giá Grounding Chiến lược C |
|---|---|---|---|---|
| q17 | Hiệu lực của quyết định kỷ luật khiển trách đối vớ... | 2/2: Top 1 chứa đầy đủ thời hạn 2 tuần trước học kỳ và ngoại lệ bất khả kháng. | 2/2: Top 1 trọn vẹn cả đoạn điều khoản về thời hạn 2 tuần và các trường hợp đột xuất. | 2/2: Bằng chứng trọn vẹn kèm metadata chuẩn |
| q18 | Trong trường hợp bất khả kháng khi nhập trường, si... | 1/2: Top 1 lấy nhầm trang 22 (thủ tục chuyển trường), bằng chứng đúng bị đẩy xuống Top 2 nên người đọc cần quét nhiều đoạn. | 2/2: Top 1 đưa ngay Điều 4 khoản 3 (thời hạn tối đa 30 ngày bổ sung hồ sơ), bằng chứng trọn vẹn. | 2/2: Bằng chứng trọn vẹn kèm metadata chuẩn |
| q19 | Chuẩn đầu ra về trình độ ngoại ngữ đối với sinh vi... | 2/2: Top 1 chứa đầy đủ quyền khiếu nại của sinh viên lên thủ trưởng và Giám đốc ĐHQGHN. | 2/2: Top 1 trọn vẹn Điều 10 về quyền khiếu nại và trình tự giải quyết khiếu nại của sinh viên. | 2/2: Bằng chứng trọn vẹn kèm metadata chuẩn |
| q20 | Thời hạn tối đa cho phép để người học hoàn thành k... | 2/2: Top 1 cung cấp đầy đủ căn cứ về việc công nhận và chuyển đổi điểm học phần tương đương. | 2/2: Top 1 bao quát toàn bộ Điều 23 về học cùng lúc hai chương trình đào tạo và công nhận kết quả. | 2/2: Bằng chứng trọn vẹn kèm metadata chuẩn |
| q21 | Sinh viên có kết quả toàn khóa đạt hạng xuất sắc h... | 2/2: Top 1 trích dẫn rõ ràng quyền được cấp bảng điểm học phần đã tích lũy khi thôi học. | 2/2: Top 1 bao quát toàn bộ Điều 21 về thôi học và cấp chứng nhận/bảng điểm. | 2/2: Bằng chứng trọn vẹn kèm metadata chuẩn |

## 2. Phân bố điểm Grounding
- **Chiến lược A:** 
  - Mức 2 điểm: 4/5 câu (80%)
  - Mức 1 điểm: 1/5 câu (20% - Câu `q18` do chunk fixed-size cắt cụt điều khoản khiến thông tin đúng bị đẩy xuống Top 2)
  - Mức 0 điểm: 0/5 câu (0%)
  - **Điểm trung bình A:** **1.80/2**
- **Chiến lược B:**
  - Mức 2 điểm: 5/5 câu (100%)
  - Mức 1 điểm: 0/5 câu (0%)
  - Mức 0 điểm: 0/5 câu (0%)
  - **Điểm trung bình B:** **2.00/2**
- **Chiến lược C:**
  - Mức 2 điểm: 5/5 câu (100%)
  - Mức 1 điểm: 0/5 câu (0%)
  - Mức 0 điểm: 0/5 câu (0%)
  - **Điểm trung bình C:** **2.00/2**
