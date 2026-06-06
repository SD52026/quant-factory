"""
Tải giá SPOT (Binance spot) cho RỔ coin của funding carry delta-neutral.

Chạy:  python scripts/fetch_xs_spot.py
(Chạy sau fetch_xs_universe.py. Chỉ tải spot; không đụng perp/funding.)

Delta-neutral CẦN spot từng coin để mô hình rủi ro basis (perp − spot). Coin nào
KHÔNG có spot sạch trên Binance -> loại khỏi rổ delta-neutral (ghi rõ trong vet).
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data import store
from data.ingestion.crypto import fetch_ohlcv

SPOT_EXCHANGE = "binance"
TIMEFRAME = "1h"
SINCE = "2019-01-01T00:00:00Z"

# Rổ delta-neutral carry (major có spot sạch). BTC/ETH đã có sẵn -> vẫn refetch
# để đồng bộ range, vô hại (store ghi đè, dữ liệu y hệt).
SYMBOLS = {
    "BTCUSDT": "BTC/USDT",
    "ETHUSDT": "ETH/USDT",
    "SOLUSDT": "SOL/USDT",
    "XRPUSDT": "XRP/USDT",
    "ADAUSDT": "ADA/USDT",
    "AVAXUSDT": "AVAX/USDT",
    "LINKUSDT": "LINK/USDT",
    "DOGEUSDT": "DOGE/USDT",
}


def main() -> None:
    for tag, symbol in SYMBOLS.items():
        try:
            print(f"[SPOT] {tag} ({symbol}) ...", flush=True)
            ohlcv = fetch_ohlcv(symbol, TIMEFRAME, since=SINCE, exchange_id=SPOT_EXCHANGE)
            p = store.save(ohlcv, f"{SPOT_EXCHANGE}_{tag}_1h_spot")
            rng = f"{ohlcv.index[0].date()}..{ohlcv.index[-1].date()}" if len(ohlcv) else "EMPTY"
            print(f"       {len(ohlcv):>6} nến [{rng}]  ->  {p.name}")
        except Exception as e:  # noqa: BLE001
            print(f"  !! BỎ QUA {tag}: {type(e).__name__}: {str(e)[:80]}")

    print("\nXong. Spot rổ carry đã nằm trong data/pit_store/.")


if __name__ == "__main__":
    main()
