"""
Test quản lý vòng đời alpha — chứng minh "thu hoạch khi béo, giảm khi nén, loại khi chết".
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from portfolio.lifecycle import classify_edge, lifecycle_weights


def test_classify_edge_levels() -> None:
    assert classify_edge("a", 1.4, 1.5).status == "HEALTHY"      # còn nguyên
    assert classify_edge("b", 0.6, 1.5).status == "COMPRESSING"  # nén một phần
    assert classify_edge("c", 0.2, 1.5).status == "DECAYED"      # nén mạnh
    assert classify_edge("d", -0.1, 1.5).action == "RETIRE"      # chết -> loại


def test_lifecycle_desizes_by_health() -> None:
    n = 24 * 365
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.01, n)
    noise -= noise.mean()  # căn giữa -> mean thực = hằng số ta cộng vào

    edges = {
        "healthy": {"live_returns": pd.Series(noise + 2e-4, index=idx), "baseline_sharpe": 1.5},
        "compress": {"live_returns": pd.Series(noise + 6e-5, index=idx), "baseline_sharpe": 1.5},
        "dead": {"live_returns": pd.Series(noise - 5e-5, index=idx), "baseline_sharpe": 1.5},
    }
    weights, statuses = lifecycle_weights(edges)

    assert weights["healthy"] > weights["compress"] > weights["dead"]
    assert weights["dead"] == 0.0                       # edge chết bị loại hẳn
    assert abs(sum(weights.values()) - 1.0) < 1e-9      # chuẩn hóa
    by_name = {s.name: s for s in statuses}
    assert by_name["healthy"].status == "HEALTHY"
    assert by_name["dead"].action == "RETIRE"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
