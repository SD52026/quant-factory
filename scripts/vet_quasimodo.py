"""
GAUNTLET kiểm định QUASIMODO trên dữ liệu thật + NEGATIVE CONTROL.

Chạy:  python scripts/vet_quasimodo.py
(Cần fetch_data.py.)

Phần 1 — dữ liệu THẬT: Sharpe, CAGR, MaxDD, DSR, ổn định theo giai đoạn, số lệnh.
Phần 2 — NEGATIVE CONTROL: chạy y hệt trên RANDOM WALK (không có mẫu hình thật).
  Nếu chiến lược có edge thật, trên random walk nó phải ~0 / trượt DSR.
  Nếu nó vẫn ra edge trên random walk -> CÓ BUG hoặc LOOKAHEAD. Đây là cách
  bắt lỗi logic mạnh nhất cho pattern strategy.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha.strategies.quasimodo import Quasimodo
from data.prepare import load_carry_frame
from engine.backtest import Backtester
from engine.metrics import sharpe_ratio, summary
from engine.reality import CostModel

PPY = 24 * 365
N_TRIALS = 15
N_PERIODS = 4
SYMBOLS = ["ETHUSDT", "BTCUSDT"]
_BT = Backtester(cost_model=CostModel(spread_bps=2.0, slippage_bps=1.0, fee_bps=5.0))


def _report(df, label: str) -> None:
    strat = Quasimodo(swing_window=5)
    res = _BT.run(df, strat, delta_neutral=False, cost_multiplier=1.0)
    s = summary(res.equity, res.net_returns, n_trials=N_TRIALS, periods_per_year=PPY)
    n_trades = int((res.positions.diff().abs() > 0).sum())
    chunks = np.array_split(res.net_returns.dropna(), N_PERIODS)
    stab = " | ".join(f"{sharpe_ratio(c, PPY):>5.2f}" for c in chunks)
    verdict = "QUA cổng" if s["deflated_sharpe"] > 0.95 else "chưa qua"
    print(f"  {label}")
    print(f"    Sharpe {s['sharpe']:>5.2f} | CAGR {s['cagr']:>7.2%} | MaxDD {s['max_drawdown']:>7.2%} "
          f"| DSR {s['deflated_sharpe']:>6.2%} -> {verdict} | ~{n_trades} lần đổi vị thế")
    print(f"    Sharpe từng đoạn: {stab}")


def _random_walk_frame(like: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Random walk cùng độ dài & vol xấp xỉ — KHÔNG có mẫu hình thật (control)."""
    rng = np.random.default_rng(seed)
    n = len(like)
    vol = float(like["close"].pct_change().std())
    close = float(like["close"].iloc[0]) * np.exp(np.cumsum(rng.normal(0, vol, n)))
    wig = np.abs(rng.normal(0, vol / 2, n))
    return pd.DataFrame(
        {"open": close, "high": close * (1 + wig), "low": close * (1 - wig),
         "close": close, "volume": np.ones(n)},
        index=like.index,
    )


def main() -> None:
    for sym in SYMBOLS:
        try:
            df = load_carry_frame(sym, with_spot=False)
        except FileNotFoundError as e:
            print(f"[{sym}] {e}")
            continue
        print(f"\n=== {sym} — Quasimodo gauntlet ===")
        _report(df, "DỮ LIỆU THẬT:")
        _report(_random_walk_frame(df, seed=1), "NEGATIVE CONTROL (random walk):")

    print("\nĐọc: nếu THẬT có edge nhưng CONTROL ~0/trượt -> đáng tin (không lookahead).")
    print("Nếu CONTROL cũng ra edge -> có bug/lookahead, KHÔNG được tin con số thật.")


if __name__ == "__main__":
    main()
