"""
Chạy chiến lược FUNDING CARRY trên dữ liệu THẬT trong PIT store.

Chạy:  python scripts/run_funding_carry.py
(Cần đã chạy scripts/fetch_data.py trước để có dữ liệu BTC/ETH + funding.)

Với mỗi tài sản, in 2 phiên bản để so sánh:
  - ALWAYS : luôn giữ carry (baseline, thu cả funding âm lẫn dương).
  - TILTED : chỉ giữ carry khi funding gần đây dương (tránh trả funding).
Rồi đánh giá bằng Deflated Sharpe (đã giả định số lần thử) — phán quyết trung thực.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha.strategies.funding_carry import FundingCarry
from data.prepare import load_carry_frame
from engine.backtest import Backtester
from engine.metrics import summary
from engine.reality import CostModel

PERIODS_PER_YEAR = 24 * 365  # nến 1h
N_TRIALS = 20                # số biến thể giả định đã thử -> phạt overfit
SYMBOLS = ["BTCUSDT", "ETHUSDT"]


def _run_one(df, strategy, label: str) -> None:
    # cost_multiplier=2: carry delta-neutral giao dịch 2 chân (perp + spot).
    cost = CostModel(spread_bps=2.0, slippage_bps=1.0, fee_bps=5.0)
    bt = Backtester(cost_model=cost)
    res = bt.run(df, strategy, delta_neutral=True, cost_multiplier=2.0)
    s = summary(res.equity, res.net_returns, n_trials=N_TRIALS, periods_per_year=PERIODS_PER_YEAR)
    verdict = "QUA cổng" if s["deflated_sharpe"] > 0.95 else "chưa qua cổng"
    print(
        f"  {label:<8} | Sharpe {s['sharpe']:>5.2f} | "
        f"Năm {s['annual_return']:>7.2%} | MaxDD {s['max_drawdown']:>6.2%} | "
        f"DSR {s['deflated_sharpe']:>6.2%} -> {verdict}"
    )


def main() -> None:
    for sym in SYMBOLS:
        try:
            df = load_carry_frame(sym, n_events=9)
        except FileNotFoundError as e:
            print(f"[{sym}] {e}")
            continue

        print(f"\n=== {sym} — Funding Carry (delta-neutral) ===")
        _run_one(df, FundingCarry(threshold=-1e9), "ALWAYS")   # luôn giữ carry
        _run_one(df, FundingCarry(threshold=0.0), "TILTED")    # chỉ khi funding dương

    print("\nGhi chú: mô hình bỏ qua rủi ro basis & ma sát 2 chân lệnh.")
    print("DSR > 95% mới coi là edge đáng tin sau khi trừ bias đa phép thử.")


if __name__ == "__main__":
    main()
