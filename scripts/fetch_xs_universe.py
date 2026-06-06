"""
Nạp dữ liệu MULTI-COIN cho chiến lược cross-sectional funding carry.

Chạy:  python scripts/fetch_xs_universe.py
(Cần internet — gọi API Binance USDⓈ-M.)

Lấy OHLCV (1h) + funding history cho một RỔ coin perp, lưu vào PIT store với
tag chuẩn (vd 'BTCUSDT') để data/prepare_xs.py đọc lại.

SURVIVORSHIP — đây là điểm sống còn của một chiến lược XS carry:
  Chiến lược LONG coin có funding ÂM nhất = long đúng những coin mà cả thị
  trường đang short. Phần lớn những coin đó là coin ĐANG CHẾT. Nếu rổ chỉ gồm
  coin còn sống tới hôm nay, ta đã VÔ TÌNH loại bỏ đúng những thảm họa mà chiến
  lược này lẽ ra phải gánh -> kết quả backtest bị thổi phồng LÊN.

  Khắc phục (một phần): đưa vào rổ các coin đã sụp/khủng hoảng nhưng VẪN còn dữ
  liệu trên API:
    - FTT  : token FTX, sụp ~95% tháng 11/2022. Binance giữ perp niêm yết ->
             có dữ liệu funding/giá xuyên suốt cú sụp. Đây là test khủng hoảng thật.
    - LUNA2: token Terra hậu sụp đổ, biến động cực mạnh.

  GIỚI HẠN còn lại (khai báo trung thực): coin bị Binance DELIST hẳn và xoá khỏi
  API (vd Terra LUNA gốc -> 0 tháng 5/2022; symbol perp gốc không còn truy
  được) thì KHÔNG lấy được. Nên rổ này VẪN còn survivorship bias dư, và bias đó
  đẩy kết quả LÊN, không xuống. Mọi phán quyết phải tính tới điều này.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Console Windows (cp1252) không in được tiếng Việt -> ép UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data import store
from data.ingestion.crypto import (
    fetch_funding_history,
    fetch_funding_history_raw,
    fetch_ohlcv,
    fetch_ohlcv_raw,
)

EXCHANGE = "binanceusdm"
TIMEFRAME = "1h"
SINCE = "2019-01-01T00:00:00Z"  # xa nhất có thể (perp ~9/2019); gồm sụp LUNA 5/2022, FTX 11/2022

# tag chuẩn (lưu store) -> symbol ccxt (perp USDⓈ-M, dạng BASE/USDT:USDT)
UNIVERSE = {
    "BTCUSDT": "BTC/USDT:USDT",
    "ETHUSDT": "ETH/USDT:USDT",
    "BNBUSDT": "BNB/USDT:USDT",
    "SOLUSDT": "SOL/USDT:USDT",
    "XRPUSDT": "XRP/USDT:USDT",
    "DOGEUSDT": "DOGE/USDT:USDT",
    "ADAUSDT": "ADA/USDT:USDT",
    "AVAXUSDT": "AVAX/USDT:USDT",
    "LINKUSDT": "LINK/USDT:USDT",
    "LTCUSDT": "LTC/USDT:USDT",
    "BCHUSDT": "BCH/USDT:USDT",
    "DOTUSDT": "DOT/USDT:USDT",
    # --- coin khủng hoảng / survivorship (giữ niêm yết xuyên cú sụp) ---
    "FTTUSDT": "FTT/USDT:USDT",
    "LUNA2USDT": "LUNA2/USDT:USDT",
}

# Coin ĐÃ DELIST HẲN -> ccxt không còn market entry, phải lấy qua REST gốc.
# Đây là survivorship correction QUAN TRỌNG NHẤT: cả hai coin này CHẾT KÈM funding
# ÂM cực đoan (shorts trả longs điên cuồng) -> chính là loại coin mà XS carry bị
# HÚT vào phía LONG ngay trước khi chúng về ~0. Bỏ chúng = xoá đúng thảm họa.
#   LUNAUSDT : Terra LUNA gốc, $80+ -> $0.008 (5/2022), funding chạm -1%/8h.
#   SRMUSDT  : Serum (token Alameda/FTX), sụp theo FTX, funding chạm -2.5%/8h.
DELISTED = {
    "LUNAUSDT": "LUNAUSDT",
    "SRMUSDT": "SRMUSDT",
}


def main() -> None:
    for tag, symbol in UNIVERSE.items():
        try:
            print(f"[OHLCV]   {tag} ({symbol}) ...", flush=True)
            ohlcv = fetch_ohlcv(symbol, TIMEFRAME, since=SINCE, exchange_id=EXCHANGE)
            p1 = store.save(ohlcv, f"{EXCHANGE}_{tag}_1h_ohlcv")
            rng = f"{ohlcv.index[0].date()}..{ohlcv.index[-1].date()}" if len(ohlcv) else "EMPTY"
            print(f"          {len(ohlcv):>6} nến [{rng}]  ->  {p1.name}")

            print(f"[FUNDING] {tag} ...", flush=True)
            funding = fetch_funding_history(symbol, since=SINCE, exchange_id=EXCHANGE)
            p2 = store.save(funding, f"{EXCHANGE}_{tag}_funding")
            rng = f"{funding.index[0].date()}..{funding.index[-1].date()}" if len(funding) else "EMPTY"
            print(f"          {len(funding):>6} dòng [{rng}]  ->  {p2.name}")
        except Exception as e:  # noqa: BLE001 — coin lỗi/đã xoá thì bỏ qua, không chặn cả rổ
            print(f"  !! BỎ QUA {tag}: {type(e).__name__}: {str(e)[:80]}")

    print("\n--- COIN ĐÃ DELIST (REST gốc, survivorship correction) ---")
    for tag, raw_sym in DELISTED.items():
        try:
            print(f"[OHLCV*]  {tag} ({raw_sym}) ...", flush=True)
            ohlcv = fetch_ohlcv_raw(raw_sym, TIMEFRAME, since=SINCE)
            p1 = store.save(ohlcv, f"{EXCHANGE}_{tag}_1h_ohlcv")
            rng = f"{ohlcv.index[0].date()}..{ohlcv.index[-1].date()}" if len(ohlcv) else "EMPTY"
            print(f"          {len(ohlcv):>6} nến [{rng}]  ->  {p1.name}")

            print(f"[FUNDING*]{tag} ...", flush=True)
            funding = fetch_funding_history_raw(raw_sym, since=SINCE)
            p2 = store.save(funding, f"{EXCHANGE}_{tag}_funding")
            rng = f"{funding.index[0].date()}..{funding.index[-1].date()}" if len(funding) else "EMPTY"
            print(f"          {len(funding):>6} dòng [{rng}]  ->  {p2.name}")
        except Exception as e:  # noqa: BLE001
            print(f"  !! BỎ QUA {tag}: {type(e).__name__}: {str(e)[:80]}")

    print("\nXong. Dữ liệu multi-coin đã nằm trong data/pit_store/.")


if __name__ == "__main__":
    main()
