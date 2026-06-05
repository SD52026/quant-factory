"""
Chuẩn bị dữ liệu cho chiến lược funding carry.

Ghép OHLCV (1h) với funding rate (8h) thành một frame, tạo 2 cột:
  - 'funding'     : rate đặt tại đúng bar có sự kiện funding, 0 ở các bar khác.
                    Engine dùng cột này để tính lợi nhuận funding.
  - 'funding_avg' : trung bình funding qua N sự kiện GẦN NHẤT (chỉ dùng quá khứ),
                    forward-fill lên từng giờ. Chiến lược dùng cột này để quyết
                    định có vào carry hay không.

Cả hai đều không nhìn trước (rolling dùng quá khứ; ffill mang giá trị cũ tới).
"""
from __future__ import annotations

import pandas as pd

from data import store


def align_funding(price_index: pd.DatetimeIndex, funding: pd.DataFrame) -> pd.Series:
    """Đưa funding rate lên index giá: rate tại bar có funding, 0 chỗ khác."""
    aligned = pd.Series(0.0, index=price_index)
    f = funding["funding_rate"].copy()
    f.index = f.index.floor("h")
    f = f[~f.index.duplicated(keep="first")]
    common = f.index.intersection(price_index)
    aligned.loc[common] = f.loc[common]
    return aligned


def funding_avg_signal(
    price_index: pd.DatetimeIndex, funding: pd.DataFrame, n_events: int = 9
) -> pd.Series:
    """Trung bình funding qua N sự kiện gần nhất, forward-fill lên từng giờ."""
    sig = funding["funding_rate"].rolling(n_events).mean()
    sig.index = sig.index.floor("h")
    sig = sig[~sig.index.duplicated(keep="first")]
    return sig.reindex(price_index, method="ffill").fillna(0.0)


def prepare_carry_frame(
    ohlcv: pd.DataFrame, funding: pd.DataFrame, n_events: int = 9
) -> pd.DataFrame:
    df = ohlcv.copy()
    df["funding"] = align_funding(df.index, funding)
    df["funding_avg"] = funding_avg_signal(df.index, funding, n_events)
    return df


def load_carry_frame(
    symbol_tag: str, exchange: str = "binanceusdm", n_events: int = 9
) -> pd.DataFrame:
    """Đọc OHLCV + funding từ PIT store và chuẩn bị frame carry.

    symbol_tag ví dụ 'BTCUSDT' -> đọc:
      {exchange}_{symbol_tag}_1h_ohlcv  và  {exchange}_{symbol_tag}_funding
    """
    ohlcv = store.load(f"{exchange}_{symbol_tag}_1h_ohlcv")
    funding = store.load(f"{exchange}_{symbol_tag}_funding")
    return prepare_carry_frame(ohlcv, funding, n_events)
