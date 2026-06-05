"""
Test logic funding & delta-neutral của engine (dữ liệu giả lập, không cần mạng).

Kiểm tra hai điều cốt lõi:
  1. delta_neutral=True triệt tiêu lợi nhuận giá (chỉ còn funding).
  2. Vị thế short THU được funding khi funding dương.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha.strategies.funding_carry import FundingCarry
from engine.backtest import Backtester
from engine.reality import CostModel
from engine.strategy import Strategy


def _frame(close, funding=None, funding_avg=None):
    n = len(close)
    idx = pd.date_range("2023-01-01", periods=n, freq="h", tz="UTC")
    df = pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close,
         "volume": [1.0] * n},
        index=idx,
    )
    if funding is not None:
        df["funding"] = funding
    if funding_avg is not None:
        df["funding_avg"] = funding_avg
    return df


class _AlwaysShort(Strategy):
    name = "always_short"

    def generate_signals(self, data):
        return pd.Series(-1.0, index=data.index)


def test_delta_neutral_zeroes_price_pnl() -> None:
    # Giá tăng đều. Short trần (delta_neutral=False) phải LỖ.
    close = list(np.linspace(100, 200, 200))
    df = _frame(close)
    bt = Backtester(CostModel(0, 0, 0))

    naked = bt.run(df, _AlwaysShort(), delta_neutral=False)
    hedged = bt.run(df, _AlwaysShort(), delta_neutral=True)

    assert float(naked.equity.iloc[-1]) < 1.0          # short giá lên -> lỗ
    assert abs(float(hedged.equity.iloc[-1]) - 1.0) < 1e-9  # delta-neutral -> phẳng


def test_short_collects_positive_funding() -> None:
    # Giá phẳng, funding +0.01% mỗi 8 bar, luôn giữ carry short delta-neutral.
    n = 100
    close = [100.0] * n
    funding = pd.Series(0.0, index=range(n))
    funding.iloc[::8] = 0.0001  # dương
    df = _frame(close, funding=funding.to_numpy(), funding_avg=[0.0001] * n)

    bt = Backtester(CostModel(0, 0, 0))
    res = bt.run(df, FundingCarry(threshold=-1e9), delta_neutral=True)

    assert float(res.equity.iloc[-1]) > 1.0  # short THU được funding dương


def test_basis_risk_appears_with_spot() -> None:
    # perp tăng nhanh hơn spot -> basis giãn -> carry (short perp) LỖ phần basis.
    n = 50
    perp = list(np.linspace(100, 110, n))   # perp +10%
    spot = list(np.linspace(100, 105, n))   # spot +5%
    df = _frame(perp)                        # close = perp
    df["spot_close"] = spot
    df["funding"] = 0.0
    res = Backtester(CostModel(0, 0, 0)).run(df, _AlwaysShort(), delta_neutral=True)
    assert float(res.equity.iloc[-1]) < 1.0  # rủi ro basis hiện ra -> lỗ


def test_no_basis_when_spot_equals_perp() -> None:
    # spot trùng perp -> basis return = 0 -> price PnL = 0 dù giá chạy mạnh.
    n = 50
    px = list(np.linspace(100, 130, n))
    df = _frame(px)
    df["spot_close"] = px
    df["funding"] = 0.0
    res = Backtester(CostModel(0, 0, 0)).run(df, _AlwaysShort(), delta_neutral=True)
    assert abs(float(res.equity.iloc[-1]) - 1.0) < 1e-9


def test_rebalancing_cost_reduces_equity() -> None:
    # Giá biến động mạnh, spot==perp (basis=0), funding dương cố định.
    # rebalance=True phải cho equity THẤP hơn (tốn phí tái cân bằng hedge).
    rng = np.random.default_rng(0)
    n = 500
    px = list(100 * np.exp(np.cumsum(rng.normal(0, 0.02, n))))
    df = _frame(px)
    df["spot_close"] = px
    df["funding"] = [0.0001] * n
    bt = Backtester(CostModel(spread_bps=2, slippage_bps=1, fee_bps=5))
    no_rebal = bt.run(df, _AlwaysShort(), delta_neutral=True, cost_multiplier=2.0, rebalance=False)
    with_rebal = bt.run(df, _AlwaysShort(), delta_neutral=True, cost_multiplier=2.0, rebalance=True)
    assert float(with_rebal.equity.iloc[-1]) < float(no_rebal.equity.iloc[-1])


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
