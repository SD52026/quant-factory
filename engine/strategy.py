"""
Strategy interface — hợp đồng chuẩn giữa ENGINE và ALPHA.

Nguyên tắc kiến trúc bất biến:
  - Engine KHÔNG bao giờ biết chiến lược cụ thể.
  - Chiến lược cắm vào engine CHỈ qua interface này.
  => Nhờ vậy hàng trăm chiến lược chạy qua cùng một bộ kiểm định mà không sửa engine.

Luật chống lookahead (CỰC KỲ QUAN TRỌNG):
  generate_signals() chỉ được dùng dữ liệu TÍNH ĐẾN thời điểm hiện tại (t).
  Vị thế tại t sẽ được engine áp vào lợi nhuận từ t -> t+1 (đã shift 1 bar).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """Lớp cơ sở cho mọi chiến lược. Mọi alpha phải kế thừa lớp này."""

    #: Tên định danh chiến lược (override ở lớp con).
    name: str = "unnamed_strategy"

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Sinh vị thế mục tiêu cho từng bar.

        Tham số
        --------
        data : DataFrame có index thời gian và tối thiểu các cột:
               ['open', 'high', 'low', 'close', 'volume']

        Trả về
        -------
        pd.Series : vị thế mục tiêu trong khoảng [-1.0, 1.0], cùng index với data.
                    +1 = long tối đa, -1 = short tối đa, 0 = đứng ngoài.
                    CHỈ được dùng dữ liệu tại hoặc trước mỗi thời điểm (no lookahead).
        """
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Strategy {self.name}>"
