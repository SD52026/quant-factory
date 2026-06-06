# PHASE2_KICKOFF.md — Phát súng mở màn Nhà máy Tự động

Cách dùng: mở folder `C:\Quant-factory` trong Antigravity, đảm bảo agent đọc được
`RESEARCH_PROTOCOL.md` và `CLAUDE.md`, rồi **dán nguyên khối PROMPT bên dưới** vào agent.
Chọn một hướng cơ chế ở Phụ lục (hoặc để agent tự đề xuất, miễn có cơ chế thật).

---

## PROMPT (dán vào agent)

```
VAI TRÒ: Bạn là nhà nghiên cứu quant trong một nhà máy alpha. Mọi việc của bạn bị
chi phối bởi RESEARCH_PROTOCOL.md. ĐỌC TOÀN BỘ file đó và CLAUDE.md trước khi làm gì.

MỆNH LỆNH TỐI CAO: Nhà máy này là một CỖ MÁY PHỦ ĐỊNH, không phải cỗ máy săn kẻ thắng.
Bạn KHÔNG khai thác dữ liệu mù. Bạn đề xuất MỘT chiến lược có CƠ CHẾ KINH TẾ thật, rồi
cố GIẾT nó. Báo cáo trung thực — phần lớn ứng viên sẽ trượt, và một thất bại được ghi
chép rõ ràng LÀ một kết quả thành công. Đừng tô vẽ một chiến lược đã chết cho giống còn sống.

NHIỆM VỤ:
1. Đọc RESEARCH_PROTOCOL.md + CLAUDE.md. Nghiên cứu engine/ , một chiến lược ĐÃ GIỮ
   (alpha/strategies/funding_carry.py) + script vet của nó (scripts/vet_funding_carry.py)
   + test, để học quy ước repo và interface Strategy. TÁI SỬ DỤNG engine/ và
   engine/metrics.py — không phát minh lại.
2. Đề xuất MỘT ứng viên (từ Phụ lục, hoặc của riêng bạn NẾU có cơ chế thật). TRƯỚC khi
   viết code, viết Hồ sơ mục 1.1–1.2: cơ chế kinh tế (AI trả tiền, vì sao BUỘC phải trả)
   và phân loại edge + tuổi thọ kỳ vọng. KHÔNG nêu được cơ chế thật -> DỪNG LẠI.
3. Cài đặt:
   - alpha/strategies/<ten>.py  — lớp con Strategy; docstring = cơ chế + phân loại + đặc
     tả chính xác; MỌI tham số hiện rõ và đặt TIÊN NGHIỆM.
   - tests/test_<ten>.py — unit test trên ví dụ TỰ DỰNG TAY (phát hiện đúng + near-miss
     KHÔNG kích hoạt) + chặn miền vị thế.
   - scripts/vet_<ten>.py — gauntlet đầy đủ (Sharpe, CAGR, MaxDD, DSR ở n_trials TRUNG
     THỰC, Sharpe từng giai đoạn) + NEGATIVE CONTROL (random walk) + OOS holdout (30%
     cuối, chỉ chạm DUY NHẤT một lần ở cuối).
4. Chạy BỘ THỬ-GIẾT (Protocol §2) lên chính ứng viên của bạn. Báo cáo TẤT CẢ kết quả,
   kể cả những cái giết nó.
5. Áp cổng quyết định (§3) và tuyên phán quyết: LOẠI hay THĂNG-hạng-ứng-viên, kèm lý lẽ.

LUẬT CỨNG (tội chết — vi phạm bất kỳ = công việc vô hiệu):
- Không cơ chế -> không ứng viên.
- KHÔNG fit/tối ưu tham số vào backtest. Nếu có dò tìm, khai n_trials trung thực và DSR
  phải dùng đúng n_trials đó.
- KHÔNG đụng OOS holdout cho tới lần chạy cuối duy nhất.
- KHÔNG mượn backtest của chiến lược khác làm bằng chứng.
- Báo cáo thất bại trung thực.

XONG = pytest tất cả pass, vet_<ten>.py chạy trọn vẹn, hồ sơ đầy đủ, phán quyết đã nêu.
Rồi giao lại cho người (PM) review logic + (nếu thăng hạng) chạy lượt adversary độc lập.

DỮ LIỆU: máy này vào được Binance qua ccxt. Cần coin/thị trường mới thì mở rộng
scripts/fetch_*.py và XỬ LÝ survivorship (đưa cả coin đã chết/delist vào) theo ghi chú
mở rộng universe — nếu không sẽ phóng đại edge một cách nguy hiểm.
```

---

## Phụ lục — 3 hướng cơ chế (đánh giá thành thật)

### Hướng 2 (KHUYẾN NGHỊ làm TRƯỚC): Carry funding cross-sectional, dollar-neutral
- **Cơ chế:** cùng phần bù mất cân bằng đòn bẩy như carry ta đã GIỮ, nhưng thu hoạch
  trên cả RỔ coin, trung tính đô-la (long coin funding âm nhất / short coin funding
  dương nhất, hoặc cân theo z-score funding) → đa dạng hóa rủi ro basis/sàn của một coin.
- **Phân loại:** phần bù rủi ro + non trẻ (hái khi còn béo).
- **Khả thi:** CAO — tái dùng dữ liệu funding + logic carry sẵn có; chỉ cần thêm funding
  nhiều coin. Rủi ro cài đặt thấp nhất → ứng viên đầu tiên tốt nhất.
- **Vì sao đáng:** mở rộng đúng thứ ĐÃ hoạt động thành dạng trung tính + đa dạng hơn;
  nhiều khả năng ít tương quan với carry một-coin.

### Hướng 1: Momentum cross-sectional, dollar-neutral, nhiều coin
- **Cơ chế:** underreaction/bầy đàn (hành vi), nhưng xếp hạng coin rồi long nhóm mạnh /
  short nhóm yếu, trung tính thị trường → LOẠI BỎ beta, tức bỏ đi cái lệ-thuộc-regime
  đã giết trend time-series.
- **Phân loại:** hành vi (bền, nén chậm).
- **Khả thi:** TRUNG BÌNH — cần mở rộng universe + xử lý survivorship; tái dùng engine.
- **Vì sao đáng:** momentum cross-sectional là một trong các phần bù bền vững nhất được
  ghi nhận, và bản trung tính thị trường vững hơn HẲN bản time-series ta đã loại.

### Hướng 3 (trần cao, KHÓ — để dành): Phần bù rủi ro biến động (short vol)
- **Cơ chế:** bảo hiểm — thị trường có cấu trúc trả thừa cho phòng vệ; implied vol trung
  bình > realized vol. Phần bù giàu cơ chế và bền nhất; thật sự không tương quan với carry
  lẫn momentum.
- **Phân loại:** phần bù rủi ro (bền) NHƯNG đuôi trái tàn khốc (short vol nổ tung khi sụp).
- **Khả thi:** THẤP-TRUNG BÌNH — cần dữ liệu quyền chọn (Deribit) + bộ delta-hedge ta chưa
  có; rủi ro đuôi đòi sizing cực kỹ. Cơ chế tốt nhất, khó & nguy hiểm nhất — đừng làm đầu.

**Lộ trình đề xuất:** Hướng 2 trước (nhanh, an toàn, tái dùng cái đã work) → Hướng 1
(trụ cột trung tính thứ hai) → Hướng 3 khi muốn một trụ cột thật sự không tương quan và
đã đủ hạ tầng quyền chọn.
