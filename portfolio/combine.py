"""
Lớp PORTFOLIO — gộp nhiều chiến lược thành một danh mục.

Đây là nơi breadth thành hiện thực: nhiều edge KHÔNG tương quan gộp lại cho
Sharpe cao và ổn định hơn từng cái. Định luật: IR ≈ IC × √breadth.

Gộp theo RISK PARITY (mặc định): mỗi chiến lược nhận trọng số tỉ lệ nghịch với
biến động của nó, sao cho mỗi cái đóng góp rủi ro ngang nhau — không để chiến
lược động nhất lấn át.
"""
from __future__ import annotations

import pandas as pd


def combine(
    returns_by_name: dict[str, pd.Series], method: str = "risk_parity"
) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    """
    Gộp các chuỗi lợi nhuận theo bar thành một chuỗi danh mục.

    Trả về (combined_returns, weights, correlation_matrix).
    """
    df = pd.DataFrame(returns_by_name).dropna()
    if df.shape[1] == 0:
        raise ValueError("Không có chuỗi lợi nhuận nào để gộp")

    if method == "risk_parity":
        vol = df.std()
        inv = 1.0 / vol.replace(0.0, pd.NA)
        weights = (inv / inv.sum()).fillna(0.0)
    elif method == "equal":
        weights = pd.Series(1.0 / df.shape[1], index=df.columns)
    else:
        raise ValueError(f"method không hợp lệ: {method}")

    combined = (df * weights).sum(axis=1)
    return combined, weights, df.corr()
