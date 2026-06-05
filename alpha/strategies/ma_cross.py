"""
Chiến lược DEMO — Moving Average Crossover.

MỤC ĐÍCH: minh họa cách một chiến lược cắm vào engine qua interface Strategy.
ĐÂY KHÔNG PHẢI EDGE THẬT. Crossover trung bình động là chiến lược kinh điển và
gần như chắc chắn không có lợi thế bền vững sau chi phí. Dùng nó để kiểm thử
đường ống, KHÔNG dùng để giao dịch thật.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.strategy import Strategy


class MovingAverageCross(Strategy):
    """Long khi MA nhanh > MA chậm, short khi ngược lại."""

    def __init__(self, fast: int = 24, slow: int = 72) -> None:
        if fast >= slow:
            raise ValueError("fast phải nhỏ hơn slow")
        self.fast = fast
        self.slow = slow
        self.name = f"ma_cross_{fast}_{slow}"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        fast_ma = data["close"].rolling(self.fast).mean()
        slow_ma = data["close"].rolling(self.slow).mean()
        # +1 long / -1 short. Rolling chỉ dùng dữ liệu quá khứ => không lookahead.
        signal = np.where(fast_ma > slow_ma, 1.0, -1.0)
        return pd.Series(signal, index=data.index)
