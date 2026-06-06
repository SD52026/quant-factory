# TRADING_SYSTEM_CHARTER.md — Hiến chương Hệ thống Bot (growth-max)

> Tài liệu GOVERNING. Thay thế mục tiêu cũ trong RESEARCH_PROTOCOL.md. Mọi nghiên
> cứu/triển khai (người hay agent) tuân theo đây. RESEARCH_PROTOCOL.md vẫn áp dụng
> cho phần *kỷ luật chống tự-lừa* (mục 7); hiến chương này định nghĩa *mục tiêu* và
> *cổng + sizing*.

---

## 0. Vai trò & Mục tiêu

Vai: **Systematic Trader / Trading Systems Architect.** Xây bot → xây danh mục bot
→ tạo alpha → loại alpha yếu → điều vốn → nâng cấp hệ thống. Liên tục, tự động,
nhưng thận trọng-chắc-chắn như một kiến trúc sư định lượng.

**Mục tiêu:** TỐI ĐA HÓA TĂNG TRƯỞNG HÌNH HỌC (CAGR) của vốn cá nhân/quỹ nhỏ.
KHÔNG phải tối đa Sharpe, KHÔNG phải loại trừ hết rủi ro kiểu tổ chức tỷ đô.
**Chấp nhận DD cao để đổi CAGR cao** — trong giới hạn toán học ở §3.

---

## 1. Triết lý (giữ nguyên)

Vẫn là **cỗ máy phủ định**, không phải săn kẻ thắng. Sinh giả thuyết có cơ chế →
cố GIẾT → giữ kẻ không chết → triển khai bầy → cull liên tục. Khác biệt duy nhất so
với bản cũ: *mục tiêu growth-max* nới cổng và đổi cách size (§2, §3).

---

## 2. Cổng quyết định growth-max

Cổng cũ (DSR>95% + DD thấp) là *bảo toàn vốn tổ chức*. BỎ. Thay bằng:

### 2A. Điều kiện DEPLOY (bắt buộc đủ CẢ — không nhân nhượng)
1. **Cơ chế kinh tế thật** (nêu rõ + phân loại). Không cơ chế → loại tại cửa.
2. **Negative control sạch** — real tách khỏi random/shuffle (không lookahead/bug).
3. **n_trials trung thực** trong mọi thống kê (không fishing).
4. **OOS holdout dương** (chạm 1 lần). Edge phải sống ngoài mẫu.
5. **Kế hoạch reality-gap** — BẮT BUỘC paper-trade trước khi cấp vốn thật.

### 2B. Xếp hạng & Size (KHÔNG phải pass/fail)
- **DSR, OOS-Sharpe, CAGR, tương quan với bot hiện có** → quyết SIZE và có được suất
  trong danh mục không.
- **DD KHÔNG phải tiêu chí loại** — nó là đầu vào sizing (DD cao hơn → fraction nhỏ
  hơn cho cùng mức niềm tin).
- Niềm tin cao (DSR/OOS cao) + CAGR cao + tương quan thấp → cấp vốn lớn hơn.

> Hệ quả thành thật bạn chấp nhận: mô hình "bầy bot vừa-niềm-tin" nghĩa là MỘT SỐ
> bot SẼ là dương-tính-giả thua tiền trước khi bị cull. Đa dạng hóa + size nhỏ mỗi
> con + cull tích cực là thứ khiến KỲ VỌNG tổng dương dù có vài con sai. Đó chính là
> đánh đổi DD-cao/CAGR-cao bạn đã chọn.

---

## 3. Định luật sizing (Kelly — phục vụ chính mục tiêu của bạn)

"Chấp nhận DD cao đổi CAGR cao" ĐÚNG **tới một trần toán học**:
- Tồn tại mức rủi ro *growth-optimal* (Kelly). **Vượt nó → CAGR dài hạn GIẢM và xác
  suất về 0 TĂNG.** Over-leverage quá Kelly là kẻ giết tài khoản tăng-trưởng số một.
- **Quy tắc:** size mỗi bot ở **fraction của Kelly** (mặc định ¼–½ Kelly vì sai số
  ước lượng — "full Kelly" backtest gần như luôn bị over-estimate).
- **Cap đòn bẩy tổng danh mục** sao cho DD gộp nằm trong ngưỡng bạn chịu được.
- TUYỆT ĐỐI không vượt full Kelly. Đây không phải rụt rè — đây là toán của tăng trưởng.

---

## 4. Vòng đời bot (cull + bổ sung)

Code: `portfolio/lifecycle.py`. Vào sản xuất là *bắt đầu* giai đoạn quản phân rã.
- Theo dõi **live Sharpe vs baseline** → HEALTHY / COMPRESSING / DECAYED / DEAD.
- Size = health × growth-optimal fraction. DEAD → 0 (retire).
- **Bổ sung liên tục:** danh mục đứng yên là danh mục chết chậm. Luôn có ứng viên
  mới trong pipeline.

---

## 5. Universe (mở rộng)

- **Lõi:** BTC, ETH (đã có, delta-neutral spot+perp).
- **Alt mạnh, thanh khoản cao:** SOL, BNB, XRP, DOGE, AVAX, LINK (+ ADA, TON nếu
  thanh khoản đủ). Chi phí alt CAO HƠN — giả định spread/slippage lớn hơn, a-priori.
  Xử lý **survivorship** (đưa coin đã chết vào khi lấy được; ghi rõ phần còn sót).
- **FX / Vàng (sau):** ccxt = crypto-only. FX/XAU cần *nguồn dữ liệu khác* (broker
  API / Dukascopy / vendor daily). Đây là một dự án TÍCH HỢP DỮ LIỆU riêng — làm sau
  khi pipeline crypto chạy. Edge phù hợp: trend-following kiểu CTA + FX carry.

---

## 6. Pipeline ứng viên (tham khảo ảnh + bổ sung để không bỏ sót)

Lọc theo **cơ chế** (vẫn bắt buộc, kể cả growth-max). Test đại diện mạnh-cơ-chế;
KHÔNG test cả sở thú hình học (= data-mine; Quasimodo đại diện họ đó đã CHẾT).

| # | Ưu tiên | Ứng viên | Nguồn | Cơ chế | Kỳ vọng |
|---|---|---|---|---|---|
| 1 | P1 | Momentum cross-sectional (dollar-neutral, đa-alt) | bổ sung | Hành vi (underreaction) | Động cơ tăng trưởng số 1 |
| 2 | P1 | EnsembleTrend (MỞ LẠI) | đã xây | Hành vi (momentum) | CAGR cao/DD cao — re-vet cổng mới |
| 3 | P2 | DYNAMIC_LIQ (quét thanh khoản phiên → đảo) | ảnh | Forced-flow (thanh lý) | Flow crypto thật, đáng test |
| 4 | P2 | STP_SFP (Swing Failure Pattern, exhaustion) | ảnh | Forced-flow + kiệt sức | Đáng test |
| 5 | P2 | VSA_CLIMAX (kiệt sức theo volume) | ảnh | Kiệt sức/capitulation | Đáng test |
| 6 | P2 | EQH_EQL (cụm stop = thanh khoản) | ảnh | Quét stop (flow) | Đại diện SMC tốt nhất |
| 7 | P3 | Rổ carry delta-neutral đa-coin | đang làm | Phần bù funding | MỎ NEO vol thấp (không phải động cơ) |
| 8 | P3 | SMC_FVG_ULTRA (FVG 50% CE + lọc volume/bias) | ảnh | Hình học + lọc (yếu) | Đại diện họ hình-học; kỳ vọng nhiễu |
| — | Sau | VRP / short-vol | bổ sung | Bảo hiểm (implied>realized) | Bền nhất; cần data quyền chọn |
| — | Sau | FX/Gold trend (CTA) + FX carry | bổ sung | Momentum + phần bù rủi ro | Cần data ngoài crypto |

**BỎ-theo-prior** (hình học không-cơ-chế, cùng họ Quasimodo đã chết — chỉ quay lại
nếu EQH_EQL hoặc FVG_ULTRA bất ngờ pass): Breaker_Block, SMC_OB, MB, RECLAIMED, FTR,
TQL, THREE_DRIVE, Triangle_Compression, SMC_INVERSE_FVG, Quasimodo (DEAD).

**Backlog bổ sung** (crypto structural, đào sau): funding/basis momentum, cross-exchange
basis, liquidation-cascade nâng cao.

---

## 7. Bốn điều KHÔNG nhân nhượng (dù degen tới đâu)

Growth-max nới *ngưỡng niềm tin* và *DD* — KHÔNG nới mấy cái này, vì thiếu chúng thì
không phải "CAGR cao" mà là *ruin*:
1. **Cơ chế thật** (nhiễu ride mạnh = về zero nhanh hơn, không phải giàu nhanh hơn).
2. **Negative control sạch / không lookahead** (nếu không, live đảo chiều thành lỗ).
3. **n_trials trung thực** (đừng tự lừa).
4. **Reality-gap / paper-first** (vol cao thì slippage cắn mạnh nhất — phải đo live).

---

## 8. Bảng trạng thái nhà máy (cập nhật liên tục)

| Chiến lược | Phán quyết dưới mục tiêu MỚI |
|---|---|
| Funding carry (TILTED, BTC/ETH) | GIỮ — đổi vai thành MỎ NEO vol thấp |
| EnsembleTrend | MỞ LẠI — re-vet dưới cổng growth-max |
| Funding carry XS (perp-only directional) | LOẠI (đuôi giá −86% nuốt phần bù) |
| Quasimodo | LOẠI (= nhiễu, không cơ chế) |
