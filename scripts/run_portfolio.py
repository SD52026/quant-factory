"""
Chạy PORTFOLIO: gộp carry (TILTED) + trend trên dữ liệu thật, đo hiệu ứng breadth.

Chạy:  python scripts/run_portfolio.py
(Cần đã chạy fetch_data.py + fetch_spot.py.)

Với mỗi coin: chạy carry và trend riêng, đo tương quan, rồi gộp risk-parity.
Nếu hai edge ít tương quan, Sharpe tổ hợp sẽ CAO hơn cả hai — đó là breadth.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha.strategies.funding_carry import FundingCarry
from alpha.strategies.trend import TimeSeriesMomentum
from data.prepare import load_carry_frame
from engine.backtest import Backtester
from engine.metrics import max_drawdown, sharpe_ratio, annualized_return
from engine.reality import CostModel
from portfolio.combine import combine

PPY = 24 * 365
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
_COST = CostModel(spread_bps=2.0, slippage_bps=1.0, fee_bps=5.0)
_BT = Backtester(cost_model=_COST)


def _stats(ret):
    return sharpe_ratio(ret, PPY), annualized_return(ret, PPY)


def main() -> None:
    for sym in SYMBOLS:
        try:
            df = load_carry_frame(sym, n_events=9, with_spot=True)
        except FileNotFoundError as e:
            print(f"[{sym}] {e}")
            continue
        if "spot_close" not in df.columns:
            print(f"[{sym}] chưa có spot — chạy fetch_spot.py trước.")
            continue

        # Carry (TILTED, delta-neutral, đầy đủ ma sát).
        carry = _BT.run(df, FundingCarry(threshold=0.0), delta_neutral=True,
                        cost_multiplier=2.0, rebalance=True)
        # Trend (có hướng, perp, single-leg).
        trend = _BT.run(df, TimeSeriesMomentum(lookback=24 * 30), delta_neutral=False,
                        cost_multiplier=1.0)

        combined, w, corr = combine(
            {"carry": carry.net_returns, "trend": trend.net_returns}, method="risk_parity"
        )
        eq = (1.0 + combined).cumprod()

        sc, rc = _stats(carry.net_returns)
        st, rt = _stats(trend.net_returns)
        scomb, rcomb = _stats(combined)
        r = float(corr.loc["carry", "trend"])

        print(f"\n=== {sym} — Portfolio (carry + trend) ===")
        print(f"  Carry (TILTED) : Sharpe {sc:>5.2f} | Năm {rc:>7.2%}")
        print(f"  Trend (30d)    : Sharpe {st:>5.2f} | Năm {rt:>7.2%}")
        print(f"  Tương quan carry-trend: {r:>+.2f}")
        print(f"  Trọng số risk-parity  : carry {w['carry']:.0%} / trend {w['trend']:.0%}")
        print(f"  >> TỔ HỢP        : Sharpe {scomb:>5.2f} | Năm {rcomb:>7.2%} "
              f"| MaxDD {max_drawdown(eq):>7.2%}")
        better = scomb > max(sc, st)
        print(f"  >> Tổ hợp {'TỐT HƠN' if better else 'KHÔNG tốt hơn'} cả hai chiến lược đơn lẻ "
              f"({'breadth hoạt động' if better else 'tương quan quá cao / một bên quá yếu'})")

    print("\nGhi chú: tương quan thấp -> tổ hợp nâng Sharpe. Đây là cơ chế của nhà máy.")


if __name__ == "__main__":
    main()
