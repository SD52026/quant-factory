"""
Cross-Sectional Funding Carry (Dollar-Neutral) strategy.

═══════════════════════════════════════════════════════════════════════════
§1.1 CƠ CHẾ KINH TẾ — Ai trả tiền, vì sao buộc phải trả?
═══════════════════════════════════════════════════════════════════════════

Trên perpetual futures, funding rate là cơ chế BẮT BUỘC do sàn cài cứng, thanh
toán mỗi 8h. Nhà đầu cơ đòn bẩy (chủ yếu retail) giao dịch vì lý do phi kinh
tế (FOMO, thrill-seeking) và KHÔNG tối ưu theo funding cost → sẵn sàng trả
funding cao miễn là kỳ vọng giá đúng chiều.

- Coin "nóng" (meme rallying): retail long FOMO → funding dương → phe long trả
  cho phe short.
- Coin "lạnh" (bán tháo): funding âm → phe short trả cho phe long.

Cross-sectional carry = SHORT coin funding dương nhất + LONG coin funding âm nhất
→ thu cả hai chiều funding, dollar-neutral (market beta ≈ 0).

So với single-coin carry (đã GIỮ): XS loại bỏ exposure tới mặt bằng funding
chung; khi toàn thị trường funding tăng/giảm đồng loạt, vị thế net ≈ 0.
Đa dạng hóa rủi ro basis/sàn trên nhiều coin thay vì dồn vào 1.

═══════════════════════════════════════════════════════════════════════════
§1.2 PHÂN LOẠI EDGE + TUỔI THỌ KỲ VỌNG
═══════════════════════════════════════════════════════════════════════════

Loại:         Phần bù rủi ro + Kém hiệu quả tạm thời (non trẻ)
Nguồn:        Tiền công gánh rủi ro mất cân bằng đòn bẩy retail + thị trường
              perp còn non trẻ
Cạnh tranh:   Nén phần bù về mức "công bằng" (dương), không giết — vì retail
              không arbitrage được (trade vì FOMO, không vì Sharpe)
Tuổi thọ:     Dài (bền chừng nào perp + retail còn); biên nén dần khi thêm
              quỹ carry vào
Quản trị:     Hái khi còn béo (spread funding rộng), giảm size khi nén

═══════════════════════════════════════════════════════════════════════════
§1.3 ĐẶC TẢ CHÍNH XÁC
═══════════════════════════════════════════════════════════════════════════

Tham số (hiện rõ, tiên nghiệm):
  n_long    = 2   Long 2 coin funding_avg âm nhất (cân bằng tập trung/loãng).
  n_short   = 2   Short 2 coin funding_avg dương nhất (đối xứng với n_long).
  min_coins = 4   Cần ≥ 4 coin có dữ liệu tại mỗi thời điểm để rank.

  n_events  = 9   (tham số data-prep, trùng carry đã GIỮ) Rolling trung bình
                   funding qua 9 sự kiện gần nhất (~72h). Backward-looking,
                   forward-fill lên hourly. Được truyền vào data prep, không
                   phải tham số nội tại của strategy.

Quy tắc:
  1. Tại mỗi bar t, thu thập funding_avg cho mỗi coin có dữ liệu (non-NaN).
  2. Nếu số coin có dữ liệu < min_coins → tất cả weight = 0 (đứng ngoài).
  3. Xếp hạng ascending. Long n_long coin thấp nhất. Short n_short coin cao nhất.
  4. Equal-weight trong mỗi nhóm: mỗi long = +1/n_long, mỗi short = -1/n_short.
     ⇒ Σ|long weights| = 1, Σ|short weights| = -1 → dollar-neutral (net = 0).
  5. Mỗi coin weight ∈ [-1, 1].

CHỐNG LOOKAHEAD:
  - funding_avg tại t = rolling mean funding events ≤ t, forward-filled.
    Không gồm funding events tương lai.
  - Engine shift 1 bar: position[t] = target[t-1]. Position tại t dùng ranking
    từ t-1, chỉ dùng thông tin đã biết trước t.
"""
from __future__ import annotations

import pandas as pd

from engine.strategy import Strategy


class FundingCarryXS(Strategy):
    """Cross-sectional funding carry, dollar-neutral.

    Short coin funding dương nhất, long coin funding âm nhất.
    Dollar-neutral (net exposure ≈ 0). Reuses engine per-coin.

    Usage:
        strategy = FundingCarryXS(n_long=2, n_short=2, min_coins=4)
        strategy.prepare(funding_panel)  # DataFrame (time × coin)
        for coin in coins:
            strategy.set_coin(coin)
            result = backtester.run(coin_data, strategy, ...)
    """

    name = "funding_carry_xs"

    def __init__(
        self,
        n_long: int = 2,
        n_short: int = 2,
        min_coins: int = 4,
    ) -> None:
        if n_long < 1:
            raise ValueError(f"n_long must be >= 1, got {n_long}")
        if n_short < 1:
            raise ValueError(f"n_short must be >= 1, got {n_short}")
        if min_coins < n_long + n_short:
            raise ValueError(
                f"min_coins ({min_coins}) must be >= n_long + n_short "
                f"({n_long + n_short})"
            )
        self.n_long = n_long
        self.n_short = n_short
        self.min_coins = min_coins
        self.name = f"funding_carry_xs_L{n_long}S{n_short}"
        self._coin_weights: dict[str, pd.Series] = {}
        self._current_coin: str = ""

    def prepare(self, funding_panel: pd.DataFrame) -> None:
        """Pre-compute cross-sectional weights from funding_avg panel.

        Parameters
        ----------
        funding_panel : DataFrame with DatetimeIndex, columns = coin tags,
                        values = funding_avg. NaN for coins not yet listed.

        ANTI-LOOKAHEAD GUARANTEE:
        funding_avg at time t is computed by data.prepare.funding_avg_signal()
        using a backward-looking rolling window on funding events, then
        forward-filled to hourly resolution. It contains ONLY information
        available at or before time t. The engine's position shift (target[t-1])
        adds one more bar of delay, so positions at t use ranking from t-1.
        """
        coins = funding_panel.columns.tolist()
        weights = pd.DataFrame(
            0.0, index=funding_panel.index, columns=coins
        )

        for i in range(len(funding_panel)):
            row = funding_panel.iloc[i].dropna()
            n_avail = len(row)
            if n_avail < self.min_coins:
                continue

            # Rank ascending: most negative funding first.
            ranked = row.sort_values(kind="mergesort")  # stable sort for ties

            # Ensure no overlap between long and short groups.
            nl = min(self.n_long, n_avail // 2)
            ns = min(self.n_short, n_avail // 2)
            if nl == 0 or ns == 0:
                continue

            long_coins = ranked.index[:nl]
            short_coins = ranked.index[-ns:]

            # Equal weight, dollar-neutral.
            # Long side total = +1, short side total = -1, net = 0.
            for c in long_coins:
                weights.iat[i, coins.index(c)] = 1.0 / nl
            for c in short_coins:
                weights.iat[i, coins.index(c)] = -1.0 / ns

        self._coin_weights = {col: weights[col] for col in coins}

    def set_coin(self, coin: str) -> None:
        """Set which coin generate_signals returns weights for."""
        self._current_coin = coin

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Return pre-computed weight series for the current coin.

        MUST call prepare() and set_coin() before this method.
        Returns 0 for coins not in the pre-computed universe.
        """
        if self._current_coin not in self._coin_weights:
            return pd.Series(0.0, index=data.index)
        w = self._coin_weights[self._current_coin]
        return w.reindex(data.index).fillna(0.0).clip(-1.0, 1.0)
