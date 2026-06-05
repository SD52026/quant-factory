"""
Nạp dữ liệu crypto qua ccxt (mặc định: Binance USDⓈ-M perpetual).

Hai nguồn:
  - OHLCV: giá nến (open/high/low/close/volume).
  - Funding rate history: lãi suất funding của perp — nguồn của chiến lược
    "funding carry" sẽ xây ở bước sau.

LƯU Ý: module này GỌI MẠNG tới sàn. Chạy trên máy bạn (có internet), không
chạy được trong môi trường sandbox bị chặn mạng. Logic phân trang đảm bảo lấy
đủ lịch sử dài (sàn giới hạn ~1000 dòng/lần gọi).
"""
from __future__ import annotations

import time

import ccxt
import pandas as pd

DEFAULT_EXCHANGE = "binanceusdm"  # Binance USDⓈ-M futures (perp), có funding
DEFAULT_SINCE = "2019-01-01T00:00:00Z"  # ccxt tự trả về từ lúc dữ liệu thật bắt đầu (~9/2019)


def _make_exchange(exchange_id: str) -> ccxt.Exchange:
    ex = getattr(ccxt, exchange_id)({"enableRateLimit": True})
    ex.load_markets()
    return ex


def fetch_ohlcv(
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    since: str | None = None,
    exchange_id: str = DEFAULT_EXCHANGE,
    max_bars: int | None = None,
) -> pd.DataFrame:
    """Lấy OHLCV với phân trang, trả DataFrame index = thời gian (UTC)."""
    ex = _make_exchange(exchange_id)
    since_ms = ex.parse8601(since or DEFAULT_SINCE)
    limit = 1000
    rows: list[list] = []

    while True:
        batch = ex.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)
        if not batch:
            break
        rows += batch
        since_ms = batch[-1][0] + 1  # tránh trùng nến cuối
        if max_bars and len(rows) >= max_bars:
            break
        if len(batch) < limit:
            break
        time.sleep(ex.rateLimit / 1000.0)

    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df


def fetch_funding_history(
    symbol: str = "BTC/USDT",
    since: str | None = None,
    exchange_id: str = DEFAULT_EXCHANGE,
    max_rows: int | None = None,
) -> pd.DataFrame:
    """Lấy lịch sử funding rate của perp, trả DataFrame index = thời gian (UTC)."""
    ex = _make_exchange(exchange_id)
    since_ms = ex.parse8601(since or DEFAULT_SINCE)
    limit = 1000
    rows: list[dict] = []

    while True:
        batch = ex.fetch_funding_rate_history(symbol, since=since_ms, limit=limit)
        if not batch:
            break
        rows += batch
        since_ms = batch[-1]["timestamp"] + 1
        if max_rows and len(rows) >= max_rows:
            break
        if len(batch) < limit:
            break
        time.sleep(ex.rateLimit / 1000.0)

    df = pd.DataFrame(
        [{"ts": r["timestamp"], "funding_rate": r["fundingRate"]} for r in rows]
    )
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df
