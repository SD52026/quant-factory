"""
Unit test QUASIMODO — chứng minh logic đúng đặc tả, không phải bug.

Dùng dữ liệu TỰ DỰNG TAY (swing_window=2) mà ta biết trước câu trả lời:
  - Mẫu BEARISH chuẩn  -> phải vào SHORT.
  - Mẫu BULLISH chuẩn  -> phải vào LONG.
  - KHÔNG có sweep (H2 <= H1) -> KHÔNG được vào (near-miss).
  - KHÔNG có phá cấu trúc (không đóng dưới L1) -> KHÔNG được vào (near-miss).
Đây là cách verify một pattern strategy: kiểm tra cả CÓ và KHÔNG.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha.strategies.quasimodo import Quasimodo


def _frame(prices):
    n = len(prices)
    idx = pd.date_range("2020-01-01", periods=n, freq="h", tz="UTC")
    p = np.array(prices, float)
    return pd.DataFrame({"open": p, "high": p, "low": p, "close": p, "volume": np.ones(n)}, index=idx)


def _qm():
    return Quasimodo(swing_window=2)


def test_detects_textbook_bearish_qm() -> None:
    # H1=12, L1=8, H2=14(>H1, sweep), BOS đóng dưới 8 (=7), hồi lên chạm 12 -> SHORT.
    prices = [8, 9, 12, 9, 8, 9, 14, 9, 8, 7, 8, 10, 12, 12, 12]
    pos = _qm().generate_signals(_frame(prices))
    assert float(pos.iloc[12]) == -1.0          # vào short đúng tại điểm hồi
    assert float(pos.iloc[5]) == 0.0            # trước đó phải đang flat


def test_detects_textbook_bullish_qm() -> None:
    # Đối xứng: L1=8, H1=12, L2=6(<L1, sweep), BOS đóng trên 12, hồi xuống chạm 8 -> LONG.
    prices = [12, 11, 8, 11, 12, 11, 6, 11, 12, 13, 12, 10, 8, 8, 8]
    pos = _qm().generate_signals(_frame(prices))
    assert float(pos.iloc[12]) == 1.0


def test_no_entry_without_sweep() -> None:
    # H2=11 KHÔNG vượt H1=12 -> không có quét thanh khoản -> KHÔNG được short.
    prices = [8, 9, 12, 9, 8, 9, 11, 9, 8, 7, 8, 10, 12, 12, 12]
    pos = _qm().generate_signals(_frame(prices))
    assert (pos != -1.0).all()                  # tuyệt đối không vào short


def test_no_entry_without_break_of_structure() -> None:
    # Có sweep (H2=14) nhưng giá KHÔNG đóng dưới L1=8 -> không BOS -> KHÔNG vào.
    prices = [8, 9, 12, 9, 8, 9, 14, 9, 8, 9, 9, 10, 12, 12, 12]
    pos = _qm().generate_signals(_frame(prices))
    assert (pos != -1.0).all()


def test_positions_bounded() -> None:
    rng = np.random.default_rng(0)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 2000)))
    pos = Quasimodo(swing_window=5).generate_signals(_frame(px))
    assert set(np.unique(pos)).issubset({-1.0, 0.0, 1.0})


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
