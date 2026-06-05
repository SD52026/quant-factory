# quant-factory — quy ước dự án

Nhà máy nghiên cứu & thử nghiệm bot trader có edge thật. Crypto + FX, mid-frequency.
Triết lý: xây NHÀ MÁY alpha, không xây "một con bot thiên tài". Breadth > brilliance.

## Tech stack
- Python >= 3.10, numpy / pandas / scipy
- pytest để test, ruff để lint
- Backtest vectorized; engine và alpha tách biệt tuyệt đối

## Cấu trúc
- `engine/`  — LÕI, code "câm", phải cực ổn định. KHÔNG biết chiến lược cụ thể.
- `alpha/strategies/` — các chiến lược, cắm vào engine qua interface `Strategy`.
- `portfolio/` — tổ hợp alpha, sizing, risk (xây sau).
- `execution/` — OMS/kết nối sàn (xây sau).
- `data/pit_store/` — dữ liệu point-in-time (chưa có data thật).
- `tests/` — test, đặc biệt test chống lookahead.

## Lệnh
- Cài: `pip install -e ".[dev]"`
- Chạy demo: `python scripts/run_demo.py`
- Test: `pytest`
- Lint: `ruff check .`

## LUẬT BẤT BIẾN (không bao giờ vi phạm)
1. CHỐNG LOOKAHEAD: vị thế quyết định tại t chỉ áp cho lợi nhuận t -> t+1.
   Engine đã shift 1 bar. Mọi feature/strategy chỉ dùng dữ liệu <= t.
2. MỌI chiến lược phải qua chi phí thật (CostModel) — không có "lãi giấy".
3. MỌI chiến lược phải có giả thuyết kinh tế vì sao edge tồn tại.
4. Đánh giá bằng Deflated Sharpe (đếm số lần thử), KHÔNG chỉ Sharpe trần.
   Sharpe cao trên dữ liệu vô hướng (mu=0) = dấu hiệu lỗi, không phải edge.
5. KHÔNG commit khóa API sàn (đã có trong .gitignore).

## Quy ước code
- Type hints đầy đủ; ưu tiên hàm thuần (pure functions) trong engine.
- Tên rõ nghĩa; docstring giải thích "vì sao", không chỉ "cái gì".
- Engine không phụ thuộc alpha; alpha import từ engine, không ngược lại.
