"""
Chiến lược TIME-SERIES MOMENTUM (trend) — chiến lược THẬT thứ hai.

GIẢ THUYẾT KINH TẾ:
  Xu hướng có quán tính: do thị trường phản ứng chậm với thông tin, hiệu ứng bầy
  đàn, và dòng tiền theo đà. Time-series momentum là một trong những edge được
  ghi nhận bền vững nhất qua nhiều lớp tài sản (Moskowitz/Ooi/Pedersen 2012).

  Tín hiệu: dấu của lợi nhuận qua cửa sổ lookback. Giá cao hơn `lookback` bar
  trước -> đang tăng -> long (+1); thấp hơn -> giảm -> short (−1).

KHÁC carry thế nào:
  Carry trung tính thị trường, kiếm từ funding. Trend CÓ HƯỚNG, kiếm từ chuyển
  động giá. Hai nguồn lợi nhuận khác nhau -> kỳ vọng ÍT TƯƠNG QUAN -> gộp lại
  cho danh mục mạnh hơn (đây là điểm của breadth).

  Trend giao dịch perp trực tiếp (delta_neutral=False), nên cũng chịu funding:
  long khi funding dương thì PHẢI trả funding — engine tự tính khoản này.

LƯU Ý: lookback chọn theo lý lẽ (≈30 ngày), KHÔNG tối ưu trên dữ liệu (tránh
  overfit). Trên dữ liệu vô hướng (random walk), trend KHÔNG nên có edge.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.strategy import Strategy


class TimeSeriesMomentum(Strategy):
    """Long khi xu hướng tăng, short khi giảm (dấu của lợi nhuận quá khứ)."""

    def __init__(self, lookback: int = 24 * 30) -> None:
        # lookback tính theo số bar (mặc định ~30 ngày với nến 1h).
        self.lookback = lookback
        self.name = f"tsmom_{lookback}h"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        # Lợi nhuận qua cửa sổ lookback — chỉ dùng dữ liệu quá khứ (không lookahead).
        mom = data["close"].pct_change(self.lookback)
        return pd.Series(np.sign(mom).fillna(0.0), index=data.index)
