"""
Chạy FUNDING CARRY trên dữ liệu thật — so sánh NAIVE vs HONEST.

Chạy:  python scripts/run_funding_carry.py
(Cần đã chạy fetch_data.py VÀ fetch_spot.py.)

Với mỗi coin in hai khối:
  - NAIVE  : giả định hedge spot hoàn hảo (price PnL = 0). Sharpe phồng ảo.
  - HONEST : có rủi ro basis (price PnL = vị thế × (ret_perp − ret_spot)).
Mỗi khối chạy 2 biến thể: ALWAYS (luôn carry) và TILTED (chỉ khi funding dương).
Chênh lệch giữa NAIVE và HONEST chính là rủi ro mà mô hình cũ đã giấu đi.
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

PERIODS_PER_YEAR = 24 * 365
N_TRIALS = 20
SYMBOLS = ["BTCUSDT", "ETHUSDT"]

_COST = CostModel(spread_bps=2.0, slippage_bps=1.0, fee_bps=5.0)
_BT = Backtester(cost_model=_COST)


def _line(df, strategy, label: str) -> None:
    res = _BT.run(df, strategy, delta_neutral=True, cost_multiplier=2.0)
    s = summary(res.equity, res.net_returns, n_trials=N_TRIALS, periods_per_year=PERIODS_PER_YEAR)
    verdict = "QUA cổng" if s["deflated_sharpe"] > 0.95 else "chưa qua"
    print(
        f"    {label:<7} | Sharpe {s['sharpe']:>6.2f} | Năm {s['annual_return']:>7.2%} "
        f"| MaxDD {s['max_drawdown']:>7.2%} | DSR {s['deflated_sharpe']:>6.2%} -> {verdict}"
    )


def main() -> None:
    for sym in SYMBOLS:
        try:
            df = load_carry_frame(sym, n_events=9, with_spot=True)
        except FileNotFoundError as e:
            print(f"[{sym}] {e}")
            continue

        has_spot = "spot_close" in df.columns
        print(f"\n=== {sym} — Funding Carry (delta-neutral) ===")

        # NAIVE: bỏ cột spot_close để engine giả định hedge hoàn hảo.
        naive_df = df.drop(columns=["spot_close"]) if has_spot else df
        print("  NAIVE (giả định hedge hoàn hảo):")
        _line(naive_df, FundingCarry(threshold=-1e9), "ALWAYS")
        _line(naive_df, FundingCarry(threshold=0.0), "TILTED")

        # HONEST: có rủi ro basis (cần spot).
        if has_spot:
            print("  HONEST (có rủi ro basis):")
            _line(df, FundingCarry(threshold=-1e9), "ALWAYS")
            _line(df, FundingCarry(threshold=0.0), "TILTED")
        else:
            print("  HONEST: chưa có dữ liệu spot — chạy 'python scripts/fetch_spot.py' trước.")

    print("\nGhi chú: HONEST mới phản ánh rủi ro thật (vẫn còn thiếu execution & tail).")
    print("DSR > 95% là điều kiện CẦN, không ĐỦ — backtest vẫn có thể giấu rủi ro đuôi.")


if __name__ == "__main__":
    main()
