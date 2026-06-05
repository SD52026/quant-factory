"""
Demo end-to-end: sinh dữ liệu -> chạy chiến lược -> in metrics chống overfit.

Chạy:  python scripts/run_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Cho phép import package engine/alpha khi chạy trực tiếp.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha.strategies.ma_cross import MovingAverageCross
from engine.backtest import Backtester
from engine.data import generate_gbm_ohlcv
from engine.metrics import summary
from engine.reality import CostModel

PERIODS_PER_YEAR = 24 * 365  # dữ liệu nhịp giờ, crypto 24/7


def main() -> None:
    # Dữ liệu giả lập vô hướng (mu=0): chiến lược tốt KHÔNG nên ăn tiền ở đây.
    data = generate_gbm_ohlcv(n_bars=4000, mu=0.0, sigma=0.01, freq="1h")

    strategy = MovingAverageCross(fast=24, slow=72)
    cost = CostModel(spread_bps=2.0, slippage_bps=1.0, fee_bps=5.0)
    bt = Backtester(cost_model=cost)
    result = bt.run(data, strategy)

    # Giả định ta đã thử 100 biến thể (fast/slow) để tìm ra cái này
    # => Deflated Sharpe sẽ phạt mạnh nếu Sharpe chỉ là may mắn.
    stats = summary(
        result.equity,
        result.net_returns,
        n_trials=100,
        periods_per_year=PERIODS_PER_YEAR,
    )

    print(f"\n=== {strategy.name} (DEMO — không phải edge thật) ===")
    print(f"{'Annual return':<22}: {stats['annual_return']:>10.2%}")
    print(f"{'Annual vol':<22}: {stats['annual_vol']:>10.2%}")
    print(f"{'Sharpe (annualized)':<22}: {stats['sharpe']:>10.2f}")
    print(f"{'Max drawdown':<22}: {stats['max_drawdown']:>10.2%}")
    print(f"{'Total turnover':<22}: {result.total_turnover:>10.1f}")
    print(f"{'Total cost (frac)':<22}: {result.total_cost:>10.4f}")
    print("-" * 40)
    print(f"{'PSR vs 0':<22}: {stats['psr_vs_0']:>10.2%}")
    print(
        f"{'Deflated Sharpe':<22}: {stats['deflated_sharpe']:>10.2%}"
        f"   (đã giả định {stats['n_trials_assumed']} lần thử)"
    )
    print("-" * 40)
    verdict = (
        "QUA cổng kiểm định"
        if stats["deflated_sharpe"] > 0.95
        else "TRƯỢT cổng kiểm định (đúng như kỳ vọng với chiến lược demo)"
    )
    print(f"Kết luận: {verdict}\n")


if __name__ == "__main__":
    main()
