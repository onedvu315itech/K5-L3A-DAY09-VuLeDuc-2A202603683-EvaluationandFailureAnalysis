# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi nhóm 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run ID `E-seeded_regression-20261117-9334` |
| Triệu chứng | `TrialPass` fail (`status resolved != denied`), `RefundAmountCorrect` fail (`ledger=20000 != expected=0`), `DbFactKept` fail (`1 override event(s)`); reply nói `"Dạ, LogiX đã hoàn 20.000đ cho đơn O-202."` và ledger ghi `20000` (nhãn `0`) |
| Bước sai đầu tiên | Event `3` `model_override`: `{"delay_days": 5}` |
| Vì sao là bước *đầu tiên* | Event `1` (`handoff` cho `C-002`) và Event `2` (`investigator` `lookup_order` trả về `O-202`, `status: "delivered"`, `delay_days: 2`) đều đúng theo DB; tới Event `3` agent mới ghi đè `delay_days` bằng con số `5` lấy từ ticket |
| Failure mode | `FM-03` (`ticket_trust — tin ticket hơn DB`) trong `docs/failure_taxonomy.md` |
| Đối chứng | Cùng `C-002@11` trên shape `fixed` (`E-fixed-20261117-9334`): không có event `model_override`; Event `3` là `quote` (`amount_vnd: 0`, `reason: "no_entitlement"`), Event `4` `reply` từ chối hợp lệ, ledger `0` |
| Regression test | `tests/test_lab9_trace_case.py::test_trace_case_c002_s11_fixed_passes_and_seeded_regression_fails` (dùng `DbFactKept` + `RefundAmountCorrect` + `lab8_pass`); fail trên `seeded_regression` và pass trên `fixed` |
| Chưa chắc chắn | Mô phỏng bằng MockLLM nên chưa đo biến thiên parse câu chữ của LLM thật khi ticket diễn đạt số ngày mơ hồ |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
