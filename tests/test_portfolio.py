"""
Test lớp portfolio — chứng minh CƠ CHẾ breadth bằng số.

Hai chuỗi lợi nhuận DƯƠNG, ÍT tương quan -> tổ hợp phải cho Sharpe CAO hơn cả
hai. Đây chính là nguyên lý IR ≈ IC × √breadth ở dạng kiểm chứng được.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.metrics import sharpe_ratio
from portfolio.combine import combine


def test_diversification_raises_sharpe() -> None:
    rng = np.random.default_rng(0)
    n = 8000
    idx = pd.date_range("2020-01-01", periods=n, freq="h", tz="UTC")
    # Hai chuỗi độc lập, cùng mean dương & vol -> tương quan ~0.
    a = pd.Series(rng.normal(0.0002, 0.01, n), index=idx)
    b = pd.Series(rng.normal(0.0002, 0.01, n), index=idx)

    combined, weights, corr = combine({"a": a, "b": b}, method="risk_parity")

    sa, sb, sc = sharpe_ratio(a), sharpe_ratio(b), sharpe_ratio(combined)
    assert abs(float(corr.loc["a", "b"])) < 0.1     # gần như không tương quan
    assert sc > sa and sc > sb                       # tổ hợp vượt cả hai
    assert abs(weights.sum() - 1.0) < 1e-9           # trọng số cộng = 1


def test_risk_parity_downweights_volatile() -> None:
    rng = np.random.default_rng(1)
    n = 5000
    idx = pd.date_range("2020-01-01", periods=n, freq="h", tz="UTC")
    calm = pd.Series(rng.normal(0.0001, 0.005, n), index=idx)   # vol thấp
    wild = pd.Series(rng.normal(0.0001, 0.02, n), index=idx)    # vol cao gấp 4
    _, weights, _ = combine({"calm": calm, "wild": wild})
    assert weights["calm"] > weights["wild"]  # ít động hơn -> trọng số lớn hơn


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
