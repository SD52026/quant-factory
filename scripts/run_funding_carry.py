"""
Chạy FUNDING CARRY trên dữ liệu thật — so sánh HONEST vs FULL (có ma sát).

Chạy:  python scripts/run_funding_carry.py
(Cần đã chạy fetch_data.py VÀ fetch_spot.py.)

Hai khối mỗi coin:
  - HONEST : có rủi ro basis, NHƯNG chưa tính ma sát thực thi.
  - FULL   : thêm chi phí TÁI CÂN BẰNG hedge (tỉ lệ với biến động giá).
Khoảng cách HONEST -> FULL cho thấy ma sát bào Sharpe bao nhiêu.
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
# 1.0 = giả định tái cân bằng LIÊN TỤC ở phí taker (bi quan/cận trên). Thực tế dùng
# band + maker nên thấp hơn -> sự thật nằm GIỮA HONEST và FULL.
REBALANCE_FRACTION = 1.0

_COST = CostModel(spread_bps=2.0, slippage_bps=1.0, fee_bps=5.0)
_BT = Backtester(cost_model=_COST)


def _line(df, strategy, label: str, rebalance: bool) -> None:
    res = _BT.run(
        df, strategy, delta_neutral=True, cost_multiplier=2.0,
        rebalance=rebalance, rebalance_fraction=REBALANCE_FRACTION,
    )
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
        if "spot_close" not in df.columns:
            print(f"[{sym}] chưa có spot — chạy 'python scripts/fetch_spot.py' trước.")
            continue

        print(f"\n=== {sym} — Funding Carry (delta-neutral) ===")
        print("  HONEST (basis, chưa tính ma sát thực thi):")
        _line(df, FundingCarry(threshold=-1e9), "ALWAYS", rebalance=False)
        _line(df, FundingCarry(threshold=0.0), "TILTED", rebalance=False)
        print("  FULL (basis + ma sát tái cân bằng hedge):")
        _line(df, FundingCarry(threshold=-1e9), "ALWAYS", rebalance=True)
        _line(df, FundingCarry(threshold=0.0), "TILTED", rebalance=True)

    print(f"\nGhi chú: FULL giả định rebalance liên tục ở phí taker (fraction={REBALANCE_FRACTION},")
    print("bi quan). Sự thật nằm giữa HONEST và FULL. Vẫn chưa tính rủi ro sàn/đối tác.")


if __name__ == "__main__":
    main()
