"""
Test tầng data: PIT store (roundtrip) và logic phân trang ingestion (mock sàn).

Không gọi mạng — sàn được giả lập để kiểm tra parsing & phân trang an toàn.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data import store
from data.ingestion import crypto


def test_store_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(store, "PIT_DIR", tmp_path)
    idx = pd.date_range("2023-01-01", periods=3, freq="h", tz="UTC")
    df = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=idx)

    store.save(df, "x")
    assert store.exists("x")
    assert len(store.load("x")) == 3

    # append phải khử trùng theo index (không nhân đôi).
    store.append(df, "x")
    assert len(store.load("x")) == 3


class _FakeExchange:
    """Sàn giả lập: trả 1 batch đầy rồi 1 batch ngắn để test phân trang."""

    rateLimit = 0

    def __init__(self) -> None:
        self._calls = 0

    def load_markets(self) -> None:  # pragma: no cover
        pass

    def parse8601(self, _s: str) -> int:
        return 0

    def fetch_ohlcv(self, symbol, timeframe, since, limit):
        self._calls += 1
        if self._calls == 1:
            return [[i * 3_600_000, 1, 2, 0.5, 1.5, 10] for i in range(limit)]
        if self._calls == 2:
            return [[(limit + i) * 3_600_000, 1, 2, 0.5, 1.5, 10] for i in range(5)]
        return []


def test_ohlcv_pagination(monkeypatch) -> None:
    monkeypatch.setattr(crypto, "_make_exchange", lambda _eid: _FakeExchange())
    df = crypto.fetch_ohlcv("BTC/USDT", "1h")
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 1005  # 1000 + 5 (đã ghép 2 trang)
    assert str(df.index.tz) == "UTC"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
