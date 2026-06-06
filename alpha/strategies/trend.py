"""
Chiến lược TREND — họ time-series momentum.

Hai phiên bản:
  - TimeSeriesMomentum : baseline THÔ (một khung, nhị phân ±1). Giữ để so sánh.
  - EnsembleTrend      : bản ROBUST, được biện minh TIÊN NGHIỆM (không fishing):
      * Tổ hợp nhiều khung (1/3/6/12 tháng) -> trung bình hóa rủi ro chọn sai
        lookback, thay vì đặt cược một khung may mắn.
      * Vol-scaling -> chuẩn hóa rủi ro: giảm vị thế khi thị trường động mạnh.
        Đây là tiêu chuẩn của trend chuyên nghiệp (lý thuyết, không phải vì
        nó cho Sharpe cao).

GIẢ THUYẾT KINH TẾ: xu hướng có quán tính (phản ứng chậm, bầy đàn, dòng tiền).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.strategy import Strategy


class TimeSeriesMomentum(Strategy):
    """Baseline thô: dấu của lợi nhuận qua MỘT khung, vị thế nhị phân ±1."""

    def __init__(self, lookback: int = 24 * 30) -> None:
        self.lookback = lookback
        self.name = f"tsmom_{lookback}h"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        mom = data["close"].pct_change(self.lookback)
        return pd.Series(np.sign(mom).fillna(0.0), index=data.index)


class EnsembleTrend(Strategy):
    """Robust TSMOM: tổ hợp nhiều khung + vol-scaling, vị thế liên tục [-1, 1]."""

    def __init__(
        self,
        lookbacks: tuple[int, ...] = (24 * 30, 24 * 90, 24 * 180, 24 * 365),
        vol_window: int = 24 * 30,
        target_vol: float = 0.01,  # rủi ro mục tiêu/bar (tiên nghiệm, ~1%/giờ)
    ) -> None:
        self.lookbacks = lookbacks
        self.vol_window = vol_window
        self.target_vol = target_vol
        self.name = "ensemble_trend"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]

        # Tín hiệu hướng = TRUNG BÌNH dấu lợi nhuận qua các khung (-1..+1).
        sigs = [np.sign(close.pct_change(k)) for k in self.lookbacks]
        ensemble = pd.concat(sigs, axis=1).mean(axis=1)

        # Vol-scaling: nhân nghịch biến động gần đây (chỉ dùng quá khứ).
        realized_vol = close.pct_change().rolling(self.vol_window).std()
        scale = self.target_vol / realized_vol.replace(0.0, np.nan)

        pos = (ensemble * scale).clip(-1.0, 1.0)
        return pos.fillna(0.0)
