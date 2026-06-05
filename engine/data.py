"""
Data utilities.

Hiện tại chỉ có generator dữ liệu giả lập (Geometric Brownian Motion) để bạn
chạy & test engine NGAY mà chưa cần kết nối data thật.

LƯU Ý KIẾN TRÚC: khi xây tầng data thật (Phase 0 tiếp theo), nguyên tắc tối
thượng là POINT-IN-TIME — lưu dữ liệu đúng như nó tồn tại tại mỗi thời điểm,
và bao gồm cả tài sản đã delist/sập (chống survivorship bias). Dữ liệu giả lập
dưới đây KHÔNG thay thế được điều đó; nó chỉ để kiểm thử logic engine.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def generate_gbm_ohlcv(
    n_bars: int = 2000,
    start_price: float = 100.0,
    mu: float = 0.0,
    sigma: float = 0.02,
    seed: int | None = 42,
    freq: str = "1h",
) -> pd.DataFrame:
    """
    Sinh chuỗi OHLCV giả lập theo GBM.

    Mặc định mu=0 => không có xu hướng thật (gần nhiễu trắng). Đây là chủ ý:
    một chiến lược tốt KHÔNG nên có Sharpe cao trên dữ liệu vô hướng như vậy.
    Nếu nó có => dấu hiệu lookahead hoặc lỗi, không phải edge.
    """
    rng = np.random.default_rng(seed)
    shocks = rng.normal(loc=mu, scale=sigma, size=n_bars)
    close = start_price * np.exp(np.cumsum(shocks))

    idx = pd.date_range("2020-01-01", periods=n_bars, freq=freq)
    open_ = np.concatenate([[start_price], close[:-1]])
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, sigma / 2, n_bars)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, sigma / 2, n_bars)))
    volume = rng.lognormal(mean=10, sigma=1.0, size=n_bars)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )
