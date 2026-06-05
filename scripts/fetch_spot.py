"""
Tải giá SPOT (Binance spot) cho BTC/ETH và lưu PIT store.

Chạy:  python scripts/fetch_spot.py
(Chạy sau fetch_data.py. Script này CHỈ tải spot, không tải lại perp/funding.)

Spot dùng để mô hình hóa rủi ro basis (perp − spot) cho funding carry.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.ingestion.crypto import fetch_ohlcv
from data import store

SPOT_EXCHANGE = "binance"   # sàn spot (khác binanceusdm là perp)
SYMBOLS = ["BTC/USDT", "ETH/USDT"]
TIMEFRAME = "1h"
SINCE = "2019-01-01T00:00:00Z"  # xa nhat co the (Binance perp bat dau ~9/2019)


def main() -> None:
    for symbol in SYMBOLS:
        tag = f"{SPOT_EXCHANGE}_{symbol}_{TIMEFRAME}_spot".replace("/", "")
        print(f"[SPOT] {symbol} {TIMEFRAME} ...", flush=True)
        ohlcv = fetch_ohlcv(symbol, TIMEFRAME, since=SINCE, exchange_id=SPOT_EXCHANGE)
        p = store.save(ohlcv, tag)
        print(f"       {len(ohlcv)} nến  ->  {p}")

    print("\nXong. Giá spot đã nằm trong data/pit_store/.")


if __name__ == "__main__":
    main()
