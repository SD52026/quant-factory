"""
Multi-coin data preparation for cross-sectional strategies.

Builds carry frames and funding panels across a dynamic universe of coins,
handling listing dates (coins arriving at different times) correctly.

SURVIVORSHIP NOTE: this module loads only coins currently in PIT store.
Coins that were delisted (e.g., LUNA after May 2022 crash) are NOT
included unless their historical data was explicitly ingested. Any
cross-sectional backtest result is UPWARD-BIASED by this omission —
see RESEARCH_PROTOCOL §2 and strategy vet script for details.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from data import store
from data.prepare import prepare_carry_frame


# Default universe — update when adding coins.
# Gồm cả coin ĐÃ CHẾT (LUNAUSDT gốc, SRMUSDT) để chống survivorship bias — xem
# scripts/fetch_xs_universe.py và scripts/vet_funding_carry_xs.py.
DEFAULT_COIN_TAGS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT", "DOTUSDT",
    "FTTUSDT", "LUNA2USDT", "LUNAUSDT", "SRMUSDT",
]


def load_raw_coin_data(
    coin_tags: list[str] | None = None,
    exchange: str = "binanceusdm",
    spot_exchange: str = "binance",
) -> dict[str, dict[str, Any]]:
    """Load raw OHLCV, funding, and spot data for multiple coins.

    Returns dict: coin_tag -> {"ohlcv": df, "funding": df, "spot": df|None}.
    Silently skips coins whose data is not in PIT store.
    """
    coin_tags = coin_tags or DEFAULT_COIN_TAGS
    raw: dict[str, dict[str, Any]] = {}
    for tag in coin_tags:
        try:
            ohlcv = store.load(f"{exchange}_{tag}_1h_ohlcv")
            funding = store.load(f"{exchange}_{tag}_funding")
        except FileNotFoundError:
            continue
        spot = None
        try:
            spot = store.load(f"{spot_exchange}_{tag}_1h_spot")
        except FileNotFoundError:
            pass
        raw[tag] = {"ohlcv": ohlcv, "funding": funding, "spot": spot}
    return raw


def build_xs_carry_frames(
    raw: dict[str, dict[str, Any]],
    n_events: int = 9,
) -> dict[str, pd.DataFrame]:
    """Build carry frames for all coins with a given n_events.

    Each frame has: OHLCV columns + 'funding' + 'funding_avg' + optionally
    'spot_close'. Re-uses data.prepare.prepare_carry_frame for consistency
    with single-coin carry.

    Parameters
    ----------
    raw : output of load_raw_coin_data()
    n_events : rolling window for funding average signal (backward-looking).
    """
    frames: dict[str, pd.DataFrame] = {}
    for tag, data in raw.items():
        df = prepare_carry_frame(data["ohlcv"], data["funding"], n_events)
        if data["spot"] is not None:
            common = df.index.intersection(data["spot"].index)
            if len(common) > 0:
                df = df.loc[common].copy()
                df["spot_close"] = data["spot"]["close"].loc[common]
        frames[tag] = df
    return frames


def build_funding_panel(
    frames: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build a panel (timestamp × coin) of funding_avg values.

    Returns DataFrame with DatetimeIndex, columns = coin tags,
    values = funding_avg. NaN where a coin has no data yet (not listed).
    The union of all coins' time indices is used.
    """
    series: dict[str, pd.Series] = {}
    for coin, df in frames.items():
        if "funding_avg" in df.columns:
            series[coin] = df["funding_avg"]
    if not series:
        return pd.DataFrame()
    panel = pd.DataFrame(series).sort_index()
    return panel


def effective_sample_range(
    funding_panel: pd.DataFrame,
    min_coins: int = 4,
) -> tuple[pd.Timestamp | None, pd.Timestamp | None, int]:
    """Find the date range where at least min_coins coins have data.

    Returns (start, end, n_bars). Returns (None, None, 0) if never met.
    """
    valid_counts = funding_panel.notna().sum(axis=1)
    mask = valid_counts >= min_coins
    if not mask.any():
        return None, None, 0
    start = funding_panel.index[mask].min()
    end = funding_panel.index[mask].max()
    n_bars = int(mask.sum())
    return start, end, n_bars
