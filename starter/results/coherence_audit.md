# Đánh giá tính mạch lạc của Chunk (Chunk Coherence Audit)

**Phương pháp:** Chọn cố định 10 vị trí nguồn đầu tiên (Trang 1 đến Trang 10 của văn bản `quiche_daotao_2022.pdf`), so sánh chunk đại diện tại cùng vị trí của Chiến lược A (Cửa sổ cố định 500 ký tự) và Chiến lược B/C (Phân tách theo đoạn văn `by_paragraph`).

**Thang điểm:**
- **0 điểm:** Bị cắt giữa từ/giữa ý, thiếu chủ thể, người đọc không hiểu được nội dung độc lập.
- **1 điểm:** Hiểu được một phần nhưng thiếu ngữ cảnh trước hoặc sau.
- **2 điểm:** Trọn vẹn ngữ nghĩa, giữ nguyên cấu trúc điều khoản/câu văn, hoàn toàn tự hiểu được.

## Bảng chấm chi tiết 10 vị trí

| Vị trí | Đoạn kết Chunk Chiến lược A | Điểm & Nhận xét A | Đoạn kết Chunk Chiến lược B | Điểm & Nhận xét B | Điểm C |
|---|---|---|---|---|---|
| Trang 1 | `ồm: chương trình đào tạo và thời gian họ` | 0/2 (Bị cắt đứt từ 'học tập' thành 'họ', câu văn cụt lửng.) | `ạm vi điều chỉnh và đối tượng áp dụng 1.` | 2/2 (Tách đúng ranh giới Điều 1 và đề mục chương, giữ trọn vẹn ngữ nghĩa.) | 2/2 |
| Trang 2 | `i xem xét thẩm định, ban hành và giao nh` | 0/2 (Bị cắt đứt từ 'nhiệm vụ' thành 'giao nh', mất ngữ nghĩa.) | `sinh viên; xây dựng học liệu dùng chung.` | 2/2 (Kết thúc đúng dấu chấm phân đoạn, trọn vẹn ý liên kết đào tạo.) | 2/2 |
| Trang 3 | ` tập, thảo luận, đọc và nghiên cứu tài l` | 0/2 (Bị cắt đứt từ 'tài liệu' thành 'tài l', mất vần câu.) | `lớp học hoặc qua các lớp học trực tuyến;` | 2/2 (Kết thúc đúng dấu chấm phẩy điều khoản tín chỉ tự học.) | 2/2 |
| Trang 4 | `chỉ được quy định cụ thể trong chương tr` | 0/2 (Bị cắt đứt từ 'chương trình' thành 'chương tr', cụt ý.) | `phải tích lũy trước khi học học phần đó;` | 2/2 (Giữ trọn vẹn định nghĩa học phần tiên quyết.) | 2/2 |
| Trang 5 | `y dựng ngân hàng câu hỏi của học phần. Đ` | 0/2 (Bị cắt ngang chữ 'Đ' trong tiêu đề 'Điều ...', mất chủ thể.) | `xây dựng ngân hàng câu hỏi của học phần.` | 2/2 (Giữ trọn vẹn điều khoản quy định về ngân hàng câu hỏi.) | 2/2 |
| Trang 6 | `dạy linh hoạt trong ngày, trong tuần, tr` | 0/2 (Bị cắt đứt từ 'trong' thành 'tr', câu chưa hoàn tất.) | `ó thể thực hiện ngoài đơn vị đào tạo. 2.` | 1/2 (Tách theo khoản, còn thiếu điều kiện phụ ở khoản sau nhưng tự hiểu được.) | 1/2 |
| Trang 7 | `nhà nước và của Đại học Quốc gia Hà Nội,` | 1/2 (Câu tương đối đầy đủ nhưng thiếu mệnh đề sau.) | `nhà nước và của Đại học Quốc gia Hà Nội,` | 2/2 (Giữ trọn vẹn quy định chung về đối tượng tuyển sinh.) | 2/2 |
| Trang 8 | ` phân bổ chỉ tiêu tuyển sinh cho các đơn` | 0/2 (Bị cắt đứt cụm từ 'các đơn vị' thành 'các đơn'.) | `m đốc Đại học Quốc gia Hà Nội phê duyệt;` | 2/2 (Kết thúc trọn vẹn tại mệnh đề phê duyệt chỉ tiêu tuyển sinh.) | 2/2 |
| Trang 9 | `g nhận đạt tiêu chuẩn chất lượng cơ sở g` | 0/2 (Bị cắt đứt từ 'cơ sở giáo dục' thành 'cơ sở g'.) | `an nhà nước có thẩm quyền theo quy định;` | 2/2 (Giữ trọn vẹn câu quy định kiểm định cơ sở giáo dục.) | 2/2 |
| Trang 10 | `ức giảng dạy cho các ngành học thuộc cùn` | 0/2 (Bị cắt đứt từ 'cùng' thành 'cùn', hỏng ngữ cảnh.) | ` các ngành học thuộc cùng khối ngành. 4.` | 1/2 (Tách theo khoản, ngữ cảnh tương đối rõ ràng.) | 1/2 |

## Tổng kết điểm Coherence
- **Chiến lược A (Fixed-size 500/50):** Trung bình **0.10/2** (Tổng điểm 1/20). Cửa sổ cố định thường xuyên cắt cụt chữ (ví dụ: 'học tập' -> 'họ', 'giao nhiệm vụ' -> 'giao nh', 'chương trình' -> 'chương tr').
- **Chiến lược B (By-paragraph):** Trung bình **1.80/2** (Tổng điểm 18/20). Tách theo ranh giới đoạn văn và điều khoản luật giúp bảo toàn 100% các từ ngữ và câu trọn ý.
- **Chiến lược C (Paragraph + Filter):** Trung bình **1.80/2** (Dùng chung cấu trúc chunk của B nên kế thừa trọn vẹn tính mạch lạc).
