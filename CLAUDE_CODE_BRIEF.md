# CLAUDE_CODE_BRIEF.md — Lệnh chạy liên tục

Cách dùng: trong Claude Code (`cd C:\Quant-factory`, `/login` gói Max), bật
**acceptEdits** (Shift+Tab tới "auto-accept edits on") + allow-list (xem cuối file),
rồi dán khối PROMPT bên dưới.

---

## PROMPT (dán vào Claude Code)

```
VAI TRÒ: Systematic Trader / Trading Systems Architect. Tài liệu chi phối:
TRADING_SYSTEM_CHARTER.md (đọc TOÀN BỘ trước) + RESEARCH_PROTOCOL.md (mục 7,
kỷ luật chống tự-lừa). Mục tiêu: tối đa tăng trưởng vốn (growth-max), chấp nhận
DD cao đổi CAGR cao, theo cổng §2 và sizing Kelly §3 của charter.

CHẾ ĐỘ CHẠY: LIÊN TỤC, ÍT HỎI. Tự ra quyết định a-priori hợp lý và GHI LẠI thay vì
dừng hỏi. CHỈ dừng hỏi khi gặp blocker thật (thiếu nguồn dữ liệu, mâu thuẫn không
giải được). Làm xong MỖI ứng viên thì append kết quả vào PIPELINE_STATUS.md rồi
TỰ ĐỘNG sang ứng viên kế — KHÔNG chờ phê duyệt giữa các ứng viên.

NHIỆM VỤ: Làm tuần tự qua pipeline §6 charter theo thứ tự ưu tiên P1 → P2 → P3.
Với MỖI ứng viên:
1. Operationalize chính xác (đặc tả rõ, dựa spec trong ảnh/charter nếu có). Nêu
   cơ chế kinh tế + phân loại. KHÔNG cơ chế thật → ghi "LOẠI: no-mechanism" và bỏ
   qua (chỉ test đại diện hình-học EQH_EQL và FVG_ULTRA cho đủ, phần còn lại của họ
   hình học BỎ theo §6).
2. alpha/strategies/<ten>.py (lớp con Strategy; docstring=cơ chế+phân loại+đặc tả;
   tham số hiện rõ, tiên nghiệm). TÁI SỬ DỤNG engine/, không sửa engine.
3. tests/test_<ten>.py: textbook phát hiện + near-miss KHÔNG kích hoạt + chặn miền.
4. scripts/vet_<ten>.py: gauntlet theo cổng growth-max:
   - Sharpe, CAGR, MaxDD, negative control (random walk), OOS holdout 30% (chạm 1
     lần cuối), Sharpe từng giai đoạn.
   - DSR với n_trials TRUNG THỰC (tổng cấu hình thử). DSR/DD KHÔNG phải pass/fail —
     in ra để XẾP HẠNG + gợi ý size (fraction Kelly).
   - In TÁCH funding-PnL vs price-PnL nếu là chiến lược có hedge.
5. Áp cổng §2A (deploy-eligible nếu: cơ chế thật + control sạch + n_trials trung
   thực + OOS dương). Ghi verdict: DEPLOY-ELIGIBLE / LOẠI, kèm lý do + (nếu eligible)
   CAGR, OOS-Sharpe, DSR, MaxDD, và tương quan với các bot đã eligible.

UNIVERSE: BTC, ETH + alt thanh khoản (SOL, BNB, XRP, DOGE, AVAX, LINK). Chi phí alt
CAO HƠN (a-priori, khai rõ). Xử lý survivorship (đưa coin chết vào nếu lấy được).
Cần coin/spot mới → mở rộng scripts/fetch_*.py. FX/Gold: BỎ QUA lần này (cần nguồn
data ngoài ccxt — ghi vào backlog, không block).

OUTPUT: duy trì PIPELINE_STATUS.md — một bảng: ứng viên | cơ chế | CAGR | OOS-Sharpe
| DSR@n_trials | MaxDD | real-vs-control | verdict | size gợi ý (frac Kelly). Cập
nhật sau MỖI ứng viên. Cuối cùng: danh sách DEPLOY-ELIGIBLE xếp theo CAGR, kèm ma
trận tương quan giữa chúng (để chọn rổ bot ít tương quan).

LUẬT CỨNG (§7 charter): cơ chế thật + control sạch + n_trials trung thực + OOS dương.
KHÔNG fit tham số vào backtest. KHÔNG đụng OOS sớm. KHÔNG cấp vốn/đi live (chỉ tạo
bot đã vet + báo cáo; paper-trade là bước riêng sau, người duyệt). Báo cáo thất bại
trung thực — phần lớn sẽ LOẠI, đó là cổng làm đúng.

BẮT ĐẦU: từ P1 (Momentum cross-sectional dollar-neutral). Chạy liên tục tới hết
pipeline hoặc hết cửa sổ quota; khi hết quota, dừng sạch sau ứng viên đang làm,
ghi PIPELINE_STATUS.md để phiên sau tiếp tục.
```

---

## Cài để Claude Code chạy thông, ít hỏi

1. **acceptEdits:** Shift+Tab tới khi thấy `⏵⏵ accept edits on` (hết hỏi từng lần sửa file).
2. **Allow-list bash** — tạo `.claude/settings.local.json`:
```json
{
  "permissions": {
    "allow": [
      "Bash(python:*)", "Bash(python -m:*)", "Bash(pytest:*)",
      "Bash(pip:*)", "Bash(git:*)", "Bash(mkdir:*)", "Bash(dir:*)"
    ]
  }
}
```
3. Prompt đã yêu cầu *chạy liên tục, append PIPELINE_STATUS.md, không chờ duyệt giữa
   các ứng viên* — giảm tối đa điểm dừng.
4. Hết cửa sổ 5 giờ (gói Max) thì nghỉ, phiên sau gõ "tiếp tục pipeline theo
   PIPELINE_STATUS.md" là nó chạy tiếp.

KHÔNG dùng `--dangerously-skip-permissions` trên máy thật (bỏ hết phanh an toàn).
acceptEdits + allow-list là đủ.

---

## Việc của BẠN (PM) khi nó báo về

Đừng nhìn CAGR trước. Soi theo thứ tự: (1) cơ chế có thật không, (2) real-vs-control
có tách sạch không, (3) OOS có bị đụng sớm không. Sạch ba cái → mới xét CAGR/DSR/DD
để xếp hạng và size. Kẻ sống sót → đưa sang paper-trade (bước riêng) trước khi có
đồng vốn thật nào.
