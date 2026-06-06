"""
portfolio/lifecycle.py — Quản lý VÒNG ĐỜI alpha.

Triết lý: MỌI alpha phân rã. Vốn rót vào một edge phải tỉ lệ với SỨC KHỎE HIỆN
TẠI của nó so với baseline đã kiểm định — KHÔNG phải với vinh quang backtest quá
khứ. Thu hoạch khi còn béo, giảm size khi nén lại, loại bỏ khi đã chết.

Sizing = health (live Sharpe / baseline Sharpe) × risk-parity (1/vol), chuẩn hóa.
  - HEALTHY    : live ~ baseline           -> giữ full size (thu hoạch)
  - COMPRESSING: live tụt một phần         -> giảm size
  - DECAYED    : live tụt mạnh             -> giảm mạnh
  - DEAD       : live <= 0                 -> loại (size 0)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine.metrics import sharpe_ratio

PPY = 24 * 365


@dataclass
class EdgeStatus:
    name: str
    live_sharpe: float
    baseline_sharpe: float
    health: float          # live/baseline, kẹp [0, 1]
    status: str            # HEALTHY / COMPRESSING / DECAYED / DEAD
    action: str            # HOLD_FULL / REDUCE / RETIRE


def classify_edge(
    name: str,
    live_sharpe: float,
    baseline_sharpe: float,
    healthy_ratio: float = 0.7,
    decayed_ratio: float = 0.3,
) -> EdgeStatus:
    """Phân loại sức khỏe một edge từ live Sharpe so với baseline đã kiểm định."""
    ratio = live_sharpe / baseline_sharpe if baseline_sharpe > 0 else 0.0
    health = float(np.clip(ratio, 0.0, 1.0))
    if ratio >= healthy_ratio:
        status, action = "HEALTHY", "HOLD_FULL"
    elif ratio >= decayed_ratio:
        status, action = "COMPRESSING", "REDUCE"
    elif ratio > 0:
        status, action = "DECAYED", "REDUCE"
    else:
        status, action = "DEAD", "RETIRE"
    return EdgeStatus(name, float(live_sharpe), float(baseline_sharpe), health, status, action)


def lifecycle_weights(
    edges: dict[str, dict], ppy: int = PPY
) -> tuple[dict[str, float], list[EdgeStatus]]:
    """
    Tính trọng số vốn theo vòng đời.

    edges: { name: {"live_returns": pd.Series, "baseline_sharpe": float} }
    Trả về (weights, statuses). Trọng số = health × (1/vol), chuẩn hóa; DEAD -> 0.
    """
    statuses: list[EdgeStatus] = []
    raw: dict[str, float] = {}
    for name, e in edges.items():
        r = pd.Series(e["live_returns"]).dropna()
        live_sharpe = sharpe_ratio(r, ppy) if len(r) > 1 else 0.0
        st = classify_edge(name, live_sharpe, e["baseline_sharpe"])
        statuses.append(st)
        vol = float(r.std()) if len(r) > 1 else 0.0
        inv_vol = 1.0 / vol if vol > 0 else 0.0
        raw[name] = st.health * inv_vol          # sức khỏe × risk-parity

    total = sum(raw.values())
    if total <= 0:
        weights = {n: 0.0 for n in edges}
    else:
        weights = {n: v / total for n, v in raw.items()}
    return weights, statuses
