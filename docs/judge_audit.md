# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.8 | Có (`PASS floors`) | dùng (theo dõi thêm trên held-out) |
| helpful | 100 | 0.375 | 1.0 | 0.3 | Không (`FAIL floors`: κ < 0.6, R < 0.7) | loại (không dùng làm gate) |

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú & hướng sửa rubric |
|---|---|---|---|---|---|
| 1 | `H-008` (`tone_ok`): `"Em đã hoàn tiền cho anh rồi nha, anh check giúp em."` | PASS | FAIL | Người | Xưng `"em"` + `"nha"` quá suồng sã với khách; judge nhầm là thân thiện. **Sửa rubric:** liệt kê rõ xưng hô chuẩn (`LogiX` / `anh/chị`), cấm `em/nha/nhé`. |
| 2 | `H-017` (`tone_ok`): `"Dạ, bạn ơi LogiX đã hoàn 25.000đ cho đơn O-606 rồi nha."` | PASS | FAIL | Người | Xưng `"bạn ơi"` + `"nha"` thiếu chuyên nghiệp. **Sửa rubric:** thêm ví dụ negative cho `"bạn"`/`"bạn ơi"`, bắt buộc dùng `"anh/chị"`. |
| 3 | `H-029` (`tone_ok`): `"Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm."` | PASS | FAIL | Người | Giọng ra lệnh (`"không cần nhắn thêm"`); judge bị đánh lừa bởi cụm mở đầu `"Dạ, vui lòng"`. **Sửa rubric:** đánh dấu FAIL mọi câu mang tính ra lệnh/xua đuổi khách dù mở đầu lịch sự. |
| 4 | `H-042` (`tone_ok`): `"Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ."` | FAIL | PASS | Người | Câu ngắn gọn, lịch sự, đủ thông tin; judge phạt oan vì thiếu lời xin lỗi. **Sửa rubric:** chỉ yêu cầu xin lỗi khi từ chối hoặc có sự cố, không bắt buộc trong thông báo hoàn tiền thành công. |
| 5 | `H-051` (`tone_ok`): `"Dạ, LogiX đã refund 90.000đ cho đơn O-202 ạ."` | FAIL | PASS | Người | Dùng từ `"refund"` được CS LogiX cho phép; judge phạt cứng vì lẫn tiếng Anh. **Sửa rubric:** bổ sung whitelist thuật ngữ chấp nhận được (như `refund`). |
| 6 | `HL-015` (`helpful`): `"Dạ, LogiX đã hoàn 55.000đ cho đơn O-112 ạ."` | PASS | FAIL | Người | Sai tiền (reply 55.000đ, ledger ghi 40.000đ); judge không đọc ledger nên bỏ lọt. **Sửa rubric/quy trình:** không dùng LLM judge chấm số tiền/tính đúng nghiệp vụ — chuyển sang code grader. |
| 7 | `HL-016` (`helpful`): `"Dạ, LogiX thành thật xin lỗi... LogiX đã hoàn 55.000đ cho đơn O-404..."` | PASS | FAIL | Người | Sai tiền (reply 55.000đ, ledger ghi 35.000đ); lời xin lỗi dài dòng đánh lừa judge (verbosity bias). **Sửa rubric/quy trình:** tách đánh giá giọng điệu khỏi kiểm tra số tiền với ledger (code grader). |

## Kết luận
- **Tiêu chí bị loại:** `judge_helpful` (`helpful`) bị loại và **không được dùng làm gate**. Trên `n=100` (`tp=9, fp=0, fn=21, tn=70`), judge đạt `P=1.0` nhưng **Recall chỉ đạt `0.3`** và **κ = `0.375`** (đều dưới ngưỡng `R ≥ 0.7`, `κ ≥ 0.6`). Do `fn=21` (bỏ sót 21/30 ca lỗi thật, chủ yếu là các ca báo sai số tiền so với ledger như `HL-015`, `HL-016`, `HL-020`, `HL-028`, `HL-035` và một số ca sai xưng hô), tỉ lệ lỗi quan sát chỉ là `0.09` trong khi tỉ lệ lỗi thực sau hiệu chỉnh Rogan-Gladen lên tới `0.30` — dùng làm gate sẽ cho lọt tới 70% ca lỗi.
- **Tiêu chí giữ lại có điều kiện:** `judge_tone` (`tone_ok`) đạt cả 3 ngưỡng (`tp=24, fp=4, fn=6, tn=66`; `κ=0.757 ≥ 0.6`, `P=0.857 ≥ 0.8`, `R=0.8 ≥ 0.7`; `observed_fail_rate=0.28 → corrected=0.30`), có thể dùng đánh giá giọng điệu sau khi cập nhật rubric cho 5 dạng bất đồng trên (xưng hô, giọng ra lệnh, xin lỗi bắt buộc, whitelist `"refund"`).
- **Rủi ro còn lại:** judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật, và mọi kiểm tra về tiền/approval phải do code grader đảm nhiệm.
