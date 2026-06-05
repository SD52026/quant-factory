"""
Test chống lookahead — bằng chứng kiểm tra được cho kỷ luật quan trọng nhất.

Ý tưởng: nếu một "chiến lược gian lận" nhìn trước được lợi nhuận tương lai,
nó PHẢI thua khi engine shift vị thế đúng cách. Nếu nó vẫn thắng => engine
đang rò rỉ tương lai => lỗi nghiêm trọng.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.backtest import Backtester
from engine.data import generate_gbm_ohlcv
from engine.reality import CostModel
from engine.strategy import Strategy


class _FutureCheatStrategy(Strategy):
    """Chiến lược gian lận: đặt vị thế theo lợi nhuận của CHÍNH bar đó.

    Nếu engine không shift, nó sẽ 'thấy tương lai' và lãi khủng.
    Nếu engine shift đúng, lợi thế gian lận biến mất.
    """

    name = "future_cheat"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        same_bar_ret = data["close"].pct_change()
        return pd.Series(np.sign(same_bar_ret).fillna(0.0), index=data.index)


def test_no_lookahead_kills_cheater() -> None:
    data = generate_gbm_ohlcv(n_bars=3000, mu=0.0, sigma=0.01, seed=7)
    bt = Backtester(cost_model=CostModel(spread_bps=0, slippage_bps=0, fee_bps=0))
    result = bt.run(data, _FutureCheatStrategy())
    final_equity = float(result.equity.iloc[-1])
    # Sau khi shift, gian lận không còn lãi khủng — quanh mức ~1.0, không bùng nổ.
    assert final_equity < 5.0, (
        f"Lookahead leak! equity={final_equity:.2f} — engine đang lộ tương lai."
    )


def test_zero_signal_is_flat() -> None:
    """Không có vị thế => equity phẳng đúng 1.0."""

    class _Flat(Strategy):
        name = "flat"

        def generate_signals(self, data: pd.DataFrame) -> pd.Series:
            return pd.Series(0.0, index=data.index)

    data = generate_gbm_ohlcv(n_bars=500)
    result = Backtester().run(data, _Flat())
    assert abs(float(result.equity.iloc[-1]) - 1.0) < 1e-9


if __name__ == "__main__":
    test_no_lookahead_kills_cheater()
    test_zero_signal_is_flat()
    print("OK: tất cả test chống lookahead đã qua.")
