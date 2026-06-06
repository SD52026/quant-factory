# RESEARCH_PROTOCOL.md — Hiến chương Nhà máy Alpha

> Tài liệu này là **luật bắt buộc** cho mọi nghiên cứu chiến lược trong repo này,
> dù do người hay agent thực hiện. Một chiến lược KHÔNG tuân thủ hiến chương này
> thì KHÔNG được trình lên review và KHÔNG bao giờ được cấp vốn.

---

## 0. Triết lý cốt lõi

Nhà máy này **không** đi săn kẻ thắng. Nó là một **CỖ MÁY PHỦ ĐỊNH**.

- Khai thác dữ liệu mù = "thử 1000 chiến lược, giữ 1 cái THẮNG." → Cấm.
- Nhà máy thật = "lấy 1 chiến lược có CƠ CHẾ, thử 1000 cách GIẾT nó, giữ lại
  nếu không giết được." → Bắt buộc.

Hệ quả thực tế:
1. **Phần lớn ứng viên SẼ bị loại.** Đó là hệ thống hoạt động đúng, không phải thất bại.
2. **Mọi alpha PHÂN RÃ.** Ta không tìm một edge bất tử; ta xây quy trình *thu hoạch
   tập edge đang xoay vòng*: hái khi còn béo, giảm size khi nén, loại khi chết.
3. **Sống sót thống kê là CẦN, không ĐỦ.** Một edge không cơ chế là một đồng xu vừa
   ngửa nhiều lần — không có lý do gì để tin nó ngửa tiếp.

---

## 1. Hồ sơ ứng viên bắt buộc (Candidate Dossier)

Mọi chiến lược, trước khi được review, PHẢI nộp đủ các mục sau. Thiếu một mục = loại.

### 1.1 Cơ chế kinh tế (BẮT BUỘC — không có thì dừng tại đây)
Trả lời bằng văn xuôi: **Tại sao edge này TỒN TẠI?** Ai trả tiền, và vì sao họ
buộc phải trả? Nếu không trả lời được câu này, đây là khai thác dữ liệu mù → loại.

### 1.2 Phân loại edge + tuổi thọ kỳ vọng
Đánh dấu MỘT loại (quyết định tuổi thọ và cách quản trị):

| Loại | Nguồn | Cạnh tranh làm gì | Tuổi thọ |
|---|---|---|---|
| **Phần bù rủi ro** | Tiền công gánh rủi ro người khác đẩy đi | Nén về mức *công bằng (dương)*, không giết | Dài (năm) |
| **Hành vi** | Thiên kiến tâm lý dai dẳng | Nén, không giết (tâm lý không arbitrage được) | Dài |
| **Cấu trúc/dòng tiền** | Ràng buộc định chế/pháp lý ép giao dịch | Tồn tại chừng nào ràng buộc còn | Dài |
| **Kém hiệu quả tạm thời** | Một lỗi định giá / non trẻ thị trường | Cạnh tranh GIẾT về 0 | Ngắn → hái nhanh, giảm size sớm |

### 1.3 Đặc tả chính xác
Quy tắc bằng văn bản, không mơ hồ. Mọi tham số HIỆN RÕ, đặt **tiên nghiệm** bằng
lý lẽ. Nếu có dò tìm tham số → khai báo **đúng số lần thử** (`n_trials`).

### 1.4 Bằng chứng đúng logic (chống bug, không phải chống thua)
- Unit test trên ví dụ TỰ DỰNG TAY: mẫu chuẩn → vào lệnh đúng; near-miss → KHÔNG vào.
- Vị thế bị chặn đúng miền cho phép.

### 1.5 Kết quả gauntlet đầy đủ
Sharpe, CAGR (lợi nhuận gộp thật), MaxDD, **DSR ở `n_trials` trung thực**, Sharpe
từng giai đoạn (ổn định regime), và kết quả **out-of-sample holdout**.

---

## 2. Bộ thử-giết (Falsification Battery)

Ứng viên phải SỐNG SÓT qua TẤT CẢ. Mỗi cái là một nỗ lực giết nó.

1. **Negative control** — chạy trên random walk / dữ liệu xáo trộn. Nếu vẫn có edge
   → BUG/lookahead. Real phải tách biệt rõ khỏi control.
2. **Trọn chu kỳ + khủng hoảng** — gồm các giai đoạn sụp đổ (với crypto: COVID,
   LUNA, FTX). Edge biến mất khi thêm khủng hoảng = không bền.
3. **Stress chi phí** — nhân đôi spread/slippage/fee. Edge mỏng chết ở đây.
4. **Nhiễu loạn tham số** — đổi nhẹ mọi tham số. Nếu chỉ một bộ số sống = overfit.
5. **Chia regime** — Sharpe phải không lệch quá mạnh giữa các giai đoạn.
6. **Out-of-sample holdout** — giữ ~30% dữ liệu cuối, KHÔNG đụng tới khi phát triển.
   Chỉ chạy MỘT LẦN ở cuối. Sụp trên OOS = loại.
7. **Capacity/thanh khoản** — size dự kiến có khả thi với sổ lệnh không?

---

## 3. Cổng quyết định (chốt TRƯỚC, không đổi sau)

**LOẠI nếu bất kỳ:** không có cơ chế · DSR < 95% ở `n_trials` trung thực · không
tách khỏi negative control · sụp trên OOS · edge biến mất khi thêm khủng hoảng ·
chỉ một bộ tham số sống sót.

**THĂNG hạng "ứng viên cấp vốn" nếu:** sống qua TOÀN BỘ bộ thử-giết, có cơ chế rõ,
và đã phân loại tuổi thọ.

**CẤM tuyệt đối:** hồi sinh một chiến lược đã bị giết bằng lý do cảm tính; nhìn trộm
OASS sớm; dò tham số rồi báo cáo như một lần thử.

---

## 4. Cấp vốn & Thu hoạch theo vòng đời

Vào sản xuất KHÔNG phải là đích — đó là khởi đầu của giai đoạn quản trị phân rã.
(Code: `portfolio/lifecycle.py`.)

### 4.1 Size ban đầu — bị chặn bởi cái NHỎ NHẤT trong:
- Chất lượng backtest (Sharpe đã khử phồng).
- **Rủi ro không-mô-hình-hóa-được** (sàn vỡ nợ, đuôi, basis nhảy) — cái này cap
  vốn *bất kể* backtest đẹp đến đâu.
- Capacity/thanh khoản thực tế.

### 4.2 Theo dõi sức khỏe (liên tục khi chạy thật)
So **live Sharpe** (cửa sổ gần đây) với **baseline đã kiểm định**:

| Tình trạng | live/baseline | Hành động |
|---|---|---|
| HEALTHY | ≥ 0,7 | Giữ full — *thu hoạch khi còn béo* |
| COMPRESSING | 0,3 – 0,7 | Giảm size |
| DECAYED | 0 – 0,3 | Giảm mạnh |
| DEAD | ≤ 0 | Loại (size 0) |

Trọng số vốn = `health × (1/vol)`, chuẩn hóa. Code thực thi: `lifecycle_weights()`.

### 4.3 Bổ sung liên tục
Vì edge nào rồi cũng phân rã, nhà máy **luôn phải đang sinh ứng viên mới**. Một danh
mục đứng yên là một danh mục đang chết chậm.

### 4.4 Breadth = gộp các edge ĐÃ KIỂM ĐỊNH
`IR ≈ IC × √N` chỉ đúng khi N edge đều THẬT và ít tương quan. Gộp N con ma data-mined
không cho đa dạng hóa — chỉ cho N chuỗi nhiễu. Breadth là *gộp edge thật*, không phải
*tìm kiếm* edge.

---

## 5. Vai trò (đặc biệt khi dùng agent)

KHÔNG BAO GIỜ tin con số backtest THÔ của một agent.

- **Proposer (agent):** sinh cơ chế + phân loại + đặc tả + code + test + negative control.
- **Adversary/QA (agent độc lập):** chạy lại TOÀN BỘ bộ thử-giết một cách độc lập,
  *cố giết* ứng viên. Không phải xác nhận — phủ định.
- **Người (PM):** review logic quan trọng bằng mắt, ký duyệt cuối, quyết định cấp vốn.

Output của agent bị ép qua đúng bộ kiểm chứng này — *đáng tin theo cấu trúc, hoặc bị loại*.

---

## 6. Bộ khung ứng viên (điền vào chỗ trống)

```
alpha/strategies/<ten>.py   ->  class <Ten>(Strategy):  # docstring = cơ chế + phân loại + đặc tả
tests/test_<ten>.py         ->  unit test mẫu-chuẩn + near-miss + chặn miền vị thế
scripts/vet_<ten>.py        ->  gauntlet đầy đủ + negative control + OOS holdout
```

Trạng thái hiện tại của nhà máy (cập nhật khi có thay đổi):

| Chiến lược | Cơ chế | Phân loại | Phán quyết |
|---|---|---|---|
| Funding carry (TILTED) | Phe long đòn bẩy trả funding | Phần bù rủi ro + non trẻ | **GIỮ** (Sharpe ~1,5; giảm size khi nén) |
| Trend (ensemble) | Underreaction/bầy đàn | Hành vi | LOẠI (trượt DSR, lệ thuộc regime) |
| Quasimodo | (không có cơ chế thật) | — | LOẠI (= nhiễu) |
| Funding carry BASKET (delta-neutral breadth) | Y hệt carry đã giữ, thu trên nhiều coin, mỗi coin hedge spot | Phần bù rủi ro + non trẻ | **LOẠI phần mở rộng, GIỮ BTC/ETH** (hedge ĐÚNG: price-PnL book ~0; funding edge THẬT cả trên alt. Nhưng net từng sleeve alt ÂM sau chi phí alt trung thực (x5) + rebalance hedge. Rổ 8-coin (Sharpe −2.89, DSR 0%) THUA xa carry BTC/ETH (Sharpe 2.10, DSR 99.96%, MaxDD −7%). Vững qua mọi giả định rebalance: kể cả rf=0, basket 1.59 < BTC/ETH 3.84. Alt chỉ làm LOÃNG. Breadth phải là gộp edge THẬT ít tương quan — alt carry không phải edge sống sau phí) |
| Funding carry XS (dollar-neutral) | Long coin funding âm / short coin funding dương | Phần bù rủi ro + non trẻ | **LOẠI** (signal funding ISOLATED Sharpe ~11.6 & tách control sạch — edge THẬT nhưng KHÔNG hái được ở dạng perp-only: rủi ro giá tương đối nuốt nó. Với (2,2,9) khử phồng n_trials=27: net Sharpe 0.45, **CAGR −5%**, **MaxDD −99%**, DSR 16%. SURVIVORSHIP THỐNG TRỊ: thêm 2 coin chết (LUNA gốc, SRM) lật CAGR +44%→−5%, Sharpe 0.85→0.45; coin chết còn thiếu → bias dư đẩy LÊN. >50% PnL gộp từ chênh giá may rủi, không từ funding. Hướng sống tiềm năng: bản cash-and-carry hedge từng chân — ứng viên KHÁC, không hồi sinh cái này) |
