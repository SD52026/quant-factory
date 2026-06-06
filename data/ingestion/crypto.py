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

import json
import time
import urllib.parse
import urllib.request

import ccxt
import pandas as pd

DEFAULT_EXCHANGE = "binanceusdm"  # Binance USDⓈ-M futures (perp), có funding
DEFAULT_SINCE = "2019-01-01T00:00:00Z"  # ccxt tự trả về từ lúc dữ liệu thật bắt đầu (~9/2019)

# REST gốc của Binance USDⓈ-M. Dùng cho coin ĐÃ DELIST mà ccxt không còn market
# entry (vd LUNA gốc -> 0 tháng 5/2022). API vẫn giữ lịch sử funding/giá.
_FAPI = "https://fapi.binance.com"


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


def _get_json(path: str, params: dict) -> list:
    url = f"{_FAPI}{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310 — host cố định
        return json.load(r)


def fetch_ohlcv_raw(
    raw_symbol: str = "LUNAUSDT",
    timeframe: str = "1h",
    since: str | None = None,
) -> pd.DataFrame:
    """Lấy OHLCV qua REST gốc Binance USDⓈ-M cho coin ĐÃ DELIST (ccxt bỏ market).

    raw_symbol = ký hiệu trần của sàn, vd 'LUNAUSDT' (LUNA gốc), không phải dạng
    'BASE/QUOTE'. Phân trang theo startTime.
    """
    start_ms = ccxt.binanceusdm().parse8601(since or DEFAULT_SINCE)
    rows: list[list] = []
    while True:
        batch = _get_json(
            "/fapi/v1/klines",
            {"symbol": raw_symbol, "interval": timeframe, "startTime": start_ms, "limit": 1500},
        )
        if not batch:
            break
        rows += batch
        start_ms = batch[-1][0] + 1
        if len(batch) < 1500:
            break
        time.sleep(0.2)
    df = pd.DataFrame(
        [r[:6] for r in rows], columns=["ts", "open", "high", "low", "close", "volume"]
    )
    if df.empty:
        return df
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("ts").sort_index()
    return df[~df.index.duplicated(keep="first")]


def fetch_funding_history_raw(
    raw_symbol: str = "LUNAUSDT",
    since: str | None = None,
) -> pd.DataFrame:
    """Lấy lịch sử funding qua REST gốc cho coin ĐÃ DELIST (ccxt bỏ market)."""
    start_ms = ccxt.binanceusdm().parse8601(since or DEFAULT_SINCE)
    rows: list[dict] = []
    while True:
        batch = _get_json(
            "/fapi/v1/fundingRate",
            {"symbol": raw_symbol, "startTime": start_ms, "limit": 1000},
        )
        if not batch:
            break
        rows += batch
        start_ms = batch[-1]["fundingTime"] + 1
        if len(batch) < 1000:
            break
        time.sleep(0.2)
    df = pd.DataFrame(
        [{"ts": r["fundingTime"], "funding_rate": float(r["fundingRate"])} for r in rows]
    )
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("ts").sort_index()
    return df[~df.index.duplicated(keep="first")]
