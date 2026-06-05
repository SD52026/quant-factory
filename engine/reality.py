"""
Reality Engine — mô hình chi phí giao dịch.

Đây là tuyến phòng thủ quan trọng: một backtest chỉ "qua" khi vẫn dương
SAU KHI trừ toàn bộ chi phí thực tế. Nhiều "edge" đẹp trên giấy chết tại đây.

Chi phí tính theo turnover (tỷ lệ vốn được giao dịch lại). Mỗi đơn vị turnover
chịu: nửa spread + slippage + phí. Có thể mở rộng thêm funding (perp) và
market impact phi tuyến sau này.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class CostModel:
    """Mô hình chi phí đơn giản, tuyến tính theo turnover.

    Tham số (đơn vị: basis points, 1 bps = 0.01%)
    -----------------------------------------------
    spread_bps   : chênh lệch mua-bán; chịu một nửa mỗi lần giao dịch.
    slippage_bps : trượt giá ước tính trên mỗi lần khớp.
    fee_bps      : phí sàn (taker) trên mỗi lần giao dịch.
    funding_bps_per_bar : chi phí funding cho vị thế perp, trừ mỗi bar (mặc định 0).
    """

    spread_bps: float = 2.0
    slippage_bps: float = 1.0
    fee_bps: float = 5.0
    funding_bps_per_bar: float = 0.0

    @property
    def cost_per_unit_turnover(self) -> float:
        """Tổng chi phí cho mỗi đơn vị turnover, đổi sang tỷ lệ thập phân."""
        return (self.spread_bps / 2.0 + self.slippage_bps + self.fee_bps) / 1e4

    def transaction_cost(self, turnover: pd.Series) -> pd.Series:
        """Chi phí giao dịch theo turnover từng bar (|Δ position|)."""
        return turnover.abs() * self.cost_per_unit_turnover

    def carry_cost(self, positions: pd.Series) -> pd.Series:
        """Chi phí nắm giữ (funding) theo độ lớn vị thế mỗi bar."""
        if self.funding_bps_per_bar == 0.0:
            return pd.Series(0.0, index=positions.index)
        return positions.abs() * (self.funding_bps_per_bar / 1e4)
