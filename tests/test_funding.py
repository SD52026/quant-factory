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


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
