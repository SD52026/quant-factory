"""
Backtest engine — vectorized, mid-frequency.

Quy trình:
  1. Lấy vị thế mục tiêu từ strategy.generate_signals(data).
  2. CHỐNG LOOKAHEAD: shift vị thế 1 bar — vị thế quyết định tại t chỉ áp vào
     lợi nhuận từ t -> t+1. Đây là kỷ luật bắt buộc, không bao giờ bỏ.
  3. Áp chi phí giao dịch (theo turnover) + chi phí nắm giữ (funding).
  4. Trả về equity curve + chuỗi lợi nhuận net + thống kê turnover.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine.reality import CostModel
from engine.strategy import Strategy


@dataclass
class BacktestResult:
    """Kết quả một lần backtest."""

    equity: pd.Series          # đường vốn tích lũy (bắt đầu = 1.0)
    net_returns: pd.Series     # lợi nhuận net từng bar
    gross_returns: pd.Series   # lợi nhuận gross (chưa trừ chi phí)
    positions: pd.Series       # vị thế thực tế đã áp (đã shift)
    turnover: pd.Series        # |Δ position| mỗi bar
    costs: pd.Series           # tổng chi phí mỗi bar

    @property
    def total_turnover(self) -> float:
        return float(self.turnover.sum())

    @property
    def total_cost(self) -> float:
        return float(self.costs.sum())


class Backtester:
    """Chạy một Strategy trên dữ liệu giá với một CostModel."""

    def __init__(self, cost_model: CostModel | None = None) -> None:
        self.cost_model = cost_model or CostModel()

    def run(self, data: pd.DataFrame, strategy: Strategy) -> BacktestResult:
        if "close" not in data.columns:
            raise ValueError("data phải có cột 'close'")

        # 1. Tín hiệu vị thế mục tiêu từ chiến lược.
        target = strategy.generate_signals(data).reindex(data.index).fillna(0.0)
        target = target.clip(-1.0, 1.0)

        # 2. Chống lookahead: vị thế tại t áp cho lợi nhuận t -> t+1.
        positions = target.shift(1).fillna(0.0)

        # 3. Lợi nhuận tài sản.
        asset_ret = data["close"].pct_change().fillna(0.0)
        gross = positions * asset_ret

        # 4. Chi phí.
        turnover = positions.diff().abs().fillna(positions.abs())
        tx_cost = self.cost_model.transaction_cost(turnover)
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
