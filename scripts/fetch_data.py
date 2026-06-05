"""
Nạp dữ liệu crypto thật về máy và lưu vào PIT store.

Chạy:  python scripts/fetch_data.py

Mặc định: Binance USDⓈ-M perp, BTC/USDT + ETH/USDT, nến 1h, từ 2023-01-01,
kèm lịch sử funding rate. Sửa SYMBOLS / TIMEFRAME / SINCE bên dưới nếu cần.

LƯU Ý: script này cần internet (gọi API sàn). Lần đầu có thể mất vài phút do
phân trang lấy lịch sử dài.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.ingestion.crypto import fetch_funding_history, fetch_ohlcv
from data import store

EXCHANGE = "binanceusdm"
SYMBOLS = ["BTC/USDT", "ETH/USDT"]
TIMEFRAME = "1h"
SINCE = "2023-01-01T00:00:00Z"


def main() -> None:
    for symbol in SYMBOLS:
        tag = f"{EXCHANGE}_{symbol}_{TIMEFRAME}".replace("/", "")

        print(f"[OHLCV]   {symbol} {TIMEFRAME} ...", flush=True)
        ohlcv = fetch_ohlcv(symbol, TIMEFRAME, since=SINCE, exchange_id=EXCHANGE)
        p1 = store.save(ohlcv, f"{tag}_ohlcv")
        print(f"          {len(ohlcv)} nến  ->  {p1}")

        print(f"[FUNDING] {symbol} ...", flush=True)
        funding = fetch_funding_history(symbol, since=SINCE, exchange_id=EXCHANGE)
        p2 = store.save(funding, f"{EXCHANGE}_{symbol}_funding".replace("/", ""))
        print(f"          {len(funding)} dòng  ->  {p2}")

    print("\nXong. Dữ liệu đã nằm trong data/pit_store/ (định dạng Parquet).")


if __name__ == "__main__":
    main()
