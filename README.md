# quant-factory

Nhà máy nghiên cứu & thử nghiệm bot trader có **edge thật** — Crypto + FX, mid-frequency.

> Triết lý: xây một *nhà máy sản xuất & sàng lọc alpha*, không phải một con bot
> thiên tài. Thắng nhờ breadth (nhiều cược độc lập) + kỷ luật chống overfit,
> không nhờ một tín hiệu xuất sắc.

## Cài đặt

```bash
pip install -e ".[dev]"
```

## Chạy thử ngay (chưa cần data thật)

```bash
python scripts/run_demo.py   # chạy chiến lược demo trên dữ liệu giả lập
pytest                       # chạy test, gồm test chống lookahead
```

Demo dùng chiến lược MA-cross trên dữ liệu **vô hướng** (mu=0). Đây là phép thử
kiểu "âm tính": một chiến lược lành mạnh KHÔNG nên ăn tiền trên nhiễu trắng.
Deflated Sharpe sẽ cho thấy nó **trượt** cổng kiểm định — đúng như kỳ vọng.

## Kiến trúc (Phase 0)

| Module | Vai trò |
|---|---|
| `engine/strategy.py` | Interface chuẩn — mọi alpha cắm vào đây |
| `engine/backtest.py` | Backtest vectorized, có shift chống lookahead |
| `engine/reality.py` | Reality Engine — mô hình chi phí (spread/slippage/fee/funding) |
| `engine/metrics.py` | Sharpe, max DD, và **Deflated/Probabilistic Sharpe** (chống overfit) |
| `engine/validation.py` | Purged K-Fold CV + embargo, walk-forward |
| `engine/data.py` | Generator dữ liệu giả lập (tạm thời) |
| `alpha/strategies/` | Các chiến lược (hiện có 1 demo) |

## Nguyên tắc bất biến

Đọc `CLAUDE.md` — chứa các luật không bao giờ vi phạm (chống lookahead, chi phí
thật, giả thuyết kinh tế, Deflated Sharpe, không commit khóa API).

## Bước tiếp theo (lộ trình)

1. Thay generator giả lập bằng **tầng data point-in-time thật** (crypto trước).
2. Thêm các họ alpha có giả thuyết kinh tế (funding carry, momentum...).
3. Tổ hợp danh mục + risk (`portfolio/`).
4. Lắp đội agent trên Antigravity tự động hóa vòng lặp nghiên cứu.
5. Execution + paper trading -> live vốn nhỏ.
