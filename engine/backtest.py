"""
Backtest engine — vectorized, mid-frequency, CÓ hỗ trợ funding.

Quy trình:
  1. Lấy vị thế mục tiêu từ strategy.generate_signals(data).
  2. CHỐNG LOOKAHEAD: shift vị thế 1 bar (vị thế tại t áp cho lợi nhuận t -> t+1).
  3. Lợi nhuận giá + lợi nhuận funding + chi phí.
  4. Trả về equity + lợi nhuận net.

FUNDING:
  Nếu data có cột 'funding' (rate tại các bar có sự kiện funding, 0 chỗ khác),
  engine cộng lợi nhuận funding = -position * funding.
    - Long (position>0), funding>0  -> TRẢ funding (lỗ).
    - Short (position<0), funding>0 -> NHẬN funding (lãi).

DELTA-NEUTRAL (carry thuần):
  delta_neutral=True giả định vị thế perp đã được phòng hộ giá bằng spot, nên
  lợi nhuận giá ~ 0; chỉ còn funding. Đây là cách cô lập edge carry thuần.
  Lưu ý: mô hình này BỎ QUA rủi ro basis và ma sát thực thi của 2 chân lệnh —
  kết quả đẹp ở đây là tín hiệu tốt, nhưng cần kiểm chứng thêm khi lên thực tế.
  cost_multiplier > 1 để xấp xỉ chi phí giao dịch cả hai chân (perp + spot).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from engine.reality import CostModel
from engine.strategy import Strategy


@dataclass
class BacktestResult:
    equity: pd.Series
    net_returns: pd.Series
    gross_returns: pd.Series
    positions: pd.Series
    turnover: pd.Series
    costs: pd.Series

    @property
    def total_turnover(self) -> float:
        return float(self.turnover.sum())

    @property
    def total_cost(self) -> float:
        return float(self.costs.sum())


class Backtester:
    def __init__(self, cost_model: CostModel | None = None) -> None:
        self.cost_model = cost_model or CostModel()

    def run(
        self,
        data: pd.DataFrame,
        strategy: Strategy,
        delta_neutral: bool = False,
        cost_multiplier: float = 1.0,
    ) -> BacktestResult:
        if "close" not in data.columns:
            raise ValueError("data phải có cột 'close'")

        target = strategy.generate_signals(data).reindex(data.index).fillna(0.0)
        target = target.clip(-1.0, 1.0)
        positions = target.shift(1).fillna(0.0)  # chống lookahead

        # Lợi nhuận giá (bị vô hiệu nếu delta-neutral vì đã phòng hộ bằng spot).
        if delta_neutral:
            price_pnl = pd.Series(0.0, index=data.index)
        else:
            asset_ret = data["close"].pct_change().fillna(0.0)
            price_pnl = positions * asset_ret

        # Lợi nhuận funding.
        if "funding" in data.columns:
            funding = data["funding"].reindex(data.index).fillna(0.0)
            funding_pnl = -positions * funding
        else:
            funding_pnl = pd.Series(0.0, index=data.index)

        gross = price_pnl + funding_pnl

        # Chi phí.
        turnover = positions.diff().abs().fillna(positions.abs())
        tx_cost = self.cost_model.transaction_cost(turnover) * cost_multiplier
        carry = self.cost_model.carry_cost(positions)
        costs = tx_cost + carry

        net = gross - costs
        equity = (1.0 + net).cumprod()

        return BacktestResult(
            equity=equity,
            net_returns=net,
            gross_returns=gross,
            positions=positions,
            turnover=turnover,
            costs=costs,
        )
