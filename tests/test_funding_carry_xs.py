"""
Unit test CROSS-SECTIONAL FUNDING CARRY — chứng minh logic đúng đặc tả (chống
bug), KHÔNG phải chống thua. Dùng panel funding TỰ DỰNG TAY mà ta biết trước
câu trả lời.

Kiểm tra:
  - Mẫu chuẩn: long coin funding ÂM nhất, short coin funding DƯƠNG nhất.
  - Dollar-neutral: tổng weight = 0, Σ|long| = Σ|short| = 1.
  - Near-miss: < min_coins coin có dữ liệu -> đứng ngoài (toàn bộ weight = 0).
  - Chặn miền vị thế: mọi weight ∈ [-1, 1]; long/short KHÔNG chồng lấn coin.
  - generate_signals an toàn khi chưa prepare / coin lạ.
  - Chống lookahead: weight tại hàng i chỉ phụ thuộc dữ liệu <= i.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha.strategies.funding_carry_xs import FundingCarryXS
from data.prepare import funding_avg_signal


def _panel(rows: list[dict], n: int = 1) -> pd.DataFrame:
    """Dựng panel funding_avg (time × coin). Mỗi dict = một timestamp.

    Lặp lại mỗi hàng `n` lần để có chuỗi dài khi cần.
    """
    idx = pd.date_range("2023-01-01", periods=len(rows) * n, freq="h", tz="UTC")
    expanded = [r for r in rows for _ in range(n)]
    return pd.DataFrame(expanded, index=idx)


def _ohlcv(index: pd.DatetimeIndex) -> pd.DataFrame:
    p = np.full(len(index), 100.0)
    return pd.DataFrame(
        {"open": p, "high": p, "low": p, "close": p, "volume": np.ones(len(index))},
        index=index,
    )


def test_longs_most_negative_shorts_most_positive() -> None:
    # 4 coin: A âm nhất, D dương nhất. Mặc định n_long=2,n_short=2.
    panel = _panel([{"A": -0.003, "B": -0.001, "C": 0.001, "D": 0.003}])
    strat = FundingCarryXS()  # n_long=2, n_short=2, min_coins=4
    strat.prepare(panel)

    w = {c: strat._coin_weights[c].iloc[0] for c in "ABCD"}
    assert w["A"] == 0.5 and w["B"] == 0.5      # 2 coin âm nhất -> LONG
    assert w["C"] == -0.5 and w["D"] == -0.5    # 2 coin dương nhất -> SHORT


def test_dollar_neutral_and_bounded() -> None:
    panel = _panel([{"A": -0.003, "B": -0.001, "C": 0.001, "D": 0.003}])
    strat = FundingCarryXS()
    strat.prepare(panel)

    row = np.array([strat._coin_weights[c].iloc[0] for c in "ABCD"])
    assert abs(row.sum()) < 1e-12                          # net = 0 (dollar-neutral)
    assert abs(row[row > 0].sum() - 1.0) < 1e-12           # Σ long = +1
    assert abs(row[row < 0].sum() + 1.0) < 1e-12           # Σ short = -1
    assert np.all(np.abs(row) <= 1.0)                      # miền vị thế ∈ [-1,1]


def test_below_min_coins_stays_flat() -> None:
    # Chỉ 3 coin có dữ liệu (D = NaN) < min_coins=4 -> đứng ngoài hoàn toàn.
    panel = _panel([{"A": -0.003, "B": -0.001, "C": 0.003, "D": np.nan}])
    strat = FundingCarryXS()
    strat.prepare(panel)

    row = np.array([strat._coin_weights[c].iloc[0] for c in "ABCD"])
    assert np.all(row == 0.0)


def test_no_overlap_when_groups_would_collide() -> None:
    # n_long=1, n_short=3 nhưng chỉ 4 coin: short bị giới hạn còn n_avail//2=2
    # để long/short KHÔNG chồng lấn. Vẫn dollar-neutral.
    panel = _panel([{"A": -0.003, "B": -0.001, "C": 0.001, "D": 0.003}])
    strat = FundingCarryXS(n_long=1, n_short=3, min_coins=4)
    strat.prepare(panel)

    w = {c: strat._coin_weights[c].iloc[0] for c in "ABCD"}
    longs = [c for c in "ABCD" if w[c] > 0]
    shorts = [c for c in "ABCD" if w[c] < 0]
    assert set(longs).isdisjoint(shorts)               # không coin nào vừa long vừa short
    assert longs == ["A"]                              # long coin âm nhất
    assert shorts == ["C", "D"]                        # short 2 coin dương nhất (bị giới hạn)
    row = np.array([w[c] for c in "ABCD"])
    assert abs(row.sum()) < 1e-12                      # vẫn dollar-neutral


def test_generate_signals_safe_before_prepare_and_unknown_coin() -> None:
    idx = pd.date_range("2023-01-01", periods=10, freq="h", tz="UTC")
    strat = FundingCarryXS()
    # Chưa prepare -> coin lạ -> trả 0, không vỡ.
    strat.set_coin("BTCUSDT")
    assert (strat.generate_signals(_ohlcv(idx)) == 0.0).all()


def test_no_lookahead_weights_depend_only_on_past() -> None:
    # Weight tại hàng i phải GIỐNG nhau dù panel có bị cắt cụt sau i hay không.
    # => prepare() không hề dùng dữ liệu tương lai.
    rows = [
        {"A": -0.003, "B": -0.001, "C": 0.001, "D": 0.003},
        {"A": 0.004, "B": -0.002, "C": -0.005, "D": 0.001},
        {"A": -0.001, "B": 0.003, "C": 0.002, "D": -0.004},
    ]
    full = _panel(rows)
    truncated = full.iloc[:2]

    s_full = FundingCarryXS()
    s_full.prepare(full)
    s_trunc = FundingCarryXS()
    s_trunc.prepare(truncated)

    for c in "ABCD":
        np.testing.assert_array_equal(
            s_full._coin_weights[c].iloc[:2].to_numpy(),
            s_trunc._coin_weights[c].to_numpy(),
        )


def test_funding_avg_ranking_uses_only_past_settlements() -> None:
    # Điều kiện #4: funding_avg dùng để RANK không được nhìn trước. Sốc một sự
    # kiện funding tại T -> funding_avg chỉ đổi ở các bar >= T (do rolling-mean
    # gồm T rồi ffill về sau), KHÔNG bao giờ đổi ở bar < T.
    events = pd.date_range("2023-01-01", periods=12, freq="8h", tz="UTC")
    rates = np.linspace(0.0001, 0.0006, 12)
    funding = pd.DataFrame({"funding_rate": rates}, index=events)
    price_index = pd.date_range("2023-01-01", periods=12 * 8, freq="h", tz="UTC")

    base = funding_avg_signal(price_index, funding, n_events=3)

    shocked = funding.copy()
    t_shock = events[6]
    shocked.loc[t_shock, "funding_rate"] += 1.0  # sốc cực lớn
    after = funding_avg_signal(price_index, shocked, n_events=3)

    t_shock_h = t_shock.floor("h")
    before = price_index < t_shock_h
    assert (base[before].to_numpy() == after[before].to_numpy()).all()   # quá khứ BẤT BIẾN
    assert (base[~before].to_numpy() != after[~before].to_numpy()).any() # tương lai có đổi


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
