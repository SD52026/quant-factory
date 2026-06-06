"""
GAUNTLET kiểm định chiến lược TREND — vạch trần đến tận cùng.

Chạy:  python scripts/vet_trend.py
(Cần fetch_data.py + fetch_spot.py.)

Cho mỗi coin:
  1. So NAIVE (1 khung, nhị phân) vs ROBUST (tổ hợp khung + vol-scaling).
  2. In đủ: Sharpe, annual SỐ HỌC vs CAGR THẬT (lộ ảo giác vol-drag), MaxDD, DSR.
  3. Ổn định theo giai đoạn: chia dữ liệu thành các đoạn liên tiếp, in Sharpe từng
     đoạn — edge bền qua các regime hay chỉ là một giai đoạn may mắn?
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha.strategies.trend import EnsembleTrend, TimeSeriesMomentum
from data.prepare import load_carry_frame
from engine.backtest import Backtester
from engine.metrics import cagr, max_drawdown, sharpe_ratio, summary
from engine.reality import CostModel

PPY = 24 * 365
N_TRIALS = 15
N_PERIODS = 4  # số đoạn để kiểm tra ổn định
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
_BT = Backtester(cost_model=CostModel(spread_bps=2.0, slippage_bps=1.0, fee_bps=5.0))


def _full_line(res, label: str) -> None:
    s = summary(res.equity, res.net_returns, n_trials=N_TRIALS, periods_per_year=PPY)
    verdict = "QUA cổng" if s["deflated_sharpe"] > 0.95 else "chưa qua"
    print(
        f"  {label:<8} | Sharpe {s['sharpe']:>5.2f} | annual(số học) {s['annual_return']:>7.2%} "
        f"| CAGR(thật) {s['cagr']:>7.2%} | MaxDD {s['max_drawdown']:>7.2%} "
        f"| DSR {s['deflated_sharpe']:>6.2%} -> {verdict}"
    )


def _stability(res, label: str) -> None:
    chunks = np.array_split(res.net_returns.dropna(), N_PERIODS)
    parts = " | ".join(f"{sharpe_ratio(c, PPY):>5.2f}" for c in chunks)
    print(f"  {label:<8} Sharpe từng đoạn: {parts}")


def main() -> None:
    for sym in SYMBOLS:
        try:
            df = load_carry_frame(sym, n_events=9, with_spot=True)
        except FileNotFoundError as e:
            print(f"[{sym}] {e}")
            continue

        naive = _BT.run(df, TimeSeriesMomentum(24 * 30), delta_neutral=False, cost_multiplier=1.0)
        robust = _BT.run(df, EnsembleTrend(), delta_neutral=False, cost_multiplier=1.0)

        print(f"\n=== {sym} — Trend gauntlet ===")
        _full_line(naive, "NAIVE")
        _full_line(robust, "ROBUST")
        print("  --- ổn định qua các giai đoạn (out-of-sample theo thời gian) ---")
        _stability(robust, "ROBUST")

    print("\nĐọc: CAGR << annual số học = vol-drag (lợi nhuận thật thấp hơn nhiều).")
    print("Sharpe từng đoạn lệch mạnh = edge phụ thuộc regime, không ổn định.")


if __name__ == "__main__":
    main()
