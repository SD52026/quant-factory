"""
Chiến lược FUNDING CARRY (delta-neutral) — chiến lược THẬT đầu tiên.

GIẢ THUYẾT KINH TẾ:
  Trên perp, funding rate được trả qua lại giữa long và short mỗi 8 tiếng. Trong
  crypto, dân lẻ có xu hướng đòn bẩy LONG nhiều -> funding DƯƠNG phần lớn thời
  gian -> long trả cho short. Giữ vị thế SHORT perp (đã phòng hộ giá bằng spot
  = delta-neutral) sẽ THU được dòng funding này. Đây là edge cấu trúc, không
  phải đoán giá -> có cơ hội qua cổng Deflated Sharpe.

THỰC THI Ở ĐÂY:
  Vào carry (short perp = -1) khi funding gần đây favorable (trung bình > ngưỡng),
  đứng ngoài (0) khi funding gần đây âm (để tránh phải TRẢ funding). Chạy engine
  với delta_neutral=True để cô lập đúng phần funding (lợi nhuận giá ~ 0).

LƯU Ý: bản này thu funding dương. Có thể mở rộng đối xứng (long perp khi funding
  rất âm để thu chiều ngược lại) — để sau.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.strategy import Strategy


class FundingCarry(Strategy):
    """Short perp (delta-neutral) để thu funding khi funding gần đây favorable."""

    def __init__(self, threshold: float = 0.0) -> None:
        # threshold: ngưỡng trung bình funding để vào carry (0 = chỉ cần dương).
        self.threshold = threshold
        self.name = f"funding_carry_t{threshold:g}"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if "funding_avg" not in data.columns:
            raise ValueError(
                "data thiếu cột 'funding_avg' — hãy dùng data.prepare.prepare_carry_frame()"
            )
        avg = data["funding_avg"]
        # -1 = short perp (thu funding khi funding>0); 0 = đứng ngoài.
        pos = np.where(avg > self.threshold, -1.0, 0.0)
        return pd.Series(pos, index=data.index)
