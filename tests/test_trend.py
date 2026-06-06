"""
Test chiến lược trend robust (EnsembleTrend) và thước đo CAGR.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha.strategies.trend import EnsembleTrend
from engine.metrics import annualized_return, cagr


def _frame(close):
    n = len(close)
    idx = pd.date_range("2020-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame({"close": close}, index=idx)


def test_ensemble_positions_bounded() -> None:
    rng = np.random.default_rng(0)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 12000)))
    pos = EnsembleTrend().generate_signals(_frame(close))
    assert pos.max() <= 1.0 + 1e-9 and pos.min() >= -1.0 - 1e-9


def test_ensemble_long_in_clear_uptrend() -> None:
    # Giá tăng đều liên tục -> mọi khung đều báo tăng -> vị thế dương về cuối.
    close = list(np.linspace(100, 400, 12000))
    pos = EnsembleTrend().generate_signals(_frame(close))
    assert float(pos.iloc[-500:].mean()) > 0.0


def test_cagr_below_arithmetic_for_volatile() -> None:
    # Với chuỗi vol cao, CAGR (gộp thật) phải THẤP hơn annual số học (vol-drag).
    rng = np.random.default_rng(1)
    n = 5000
    rets = pd.Series(rng.normal(0.0005, 0.05, n))
    equity = (1.0 + rets).cumprod()
    assert cagr(equity, periods_per_year=252) < annualized_return(rets, periods_per_year=252)


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
