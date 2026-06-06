"""
Performance & robustness metrics.

Gồm các chỉ số cơ bản (Sharpe, max drawdown) VÀ — quan trọng nhất —
Probabilistic Sharpe Ratio (PSR) và Deflated Sharpe Ratio (DSR) theo
López de Prado. Đây là "răng nanh" chống overfit:

  - PSR: xác suất Sharpe thật > Sharpe ngưỡng, đã hiệu chỉnh skew & kurtosis.
  - DSR: PSR nhưng với ngưỡng = kỳ vọng Sharpe lớn nhất khi bạn đã thử N_trials
         chiến lược. Trả lời câu hỏi sống còn: "Sharpe này có thật, hay chỉ là
         con tốt nhất trong số rất nhiều lần thử ngẫu nhiên?"

Quy ước: returns truyền vào là chuỗi lợi nhuận theo bar (per-period), chưa
annualize. Tham số `periods_per_year` để quy đổi Sharpe sang năm.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

EULER_MASCHERONI = 0.5772156649015329


def _clean(returns: pd.Series) -> np.ndarray:
    r = pd.Series(returns).dropna().to_numpy(dtype=float)
    return r


def annualized_return(returns: pd.Series, periods_per_year: int = 252) -> float:
    r = _clean(returns)
    if r.size == 0:
        return 0.0
    return float(np.mean(r) * periods_per_year)


def annualized_vol(returns: pd.Series, periods_per_year: int = 252) -> float:
    r = _clean(returns)
    if r.size < 2:
        return 0.0
    return float(np.std(r, ddof=1) * np.sqrt(periods_per_year))


def sharpe_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    """Sharpe đã annualize (rf giả định = 0)."""
    r = _clean(returns)
    if r.size < 2 or np.std(r, ddof=1) == 0:
        return 0.0
    return float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(periods_per_year))


def max_drawdown(equity: pd.Series) -> float:
    """Mức sụt giảm tối đa từ đỉnh (giá trị âm, vd -0.25 = -25%)."""
    e = pd.Series(equity).dropna()
    if e.empty:
        return 0.0
    running_max = e.cummax()
    dd = e / running_max - 1.0
    return float(dd.min())


def cagr(equity: pd.Series, periods_per_year: int = 252) -> float:
    """Lợi nhuận GỘP THẬT (compound annual growth rate) từ đường vốn.

    Khác annualized_return (trung bình số học): CAGR là cái bạn THỰC SỰ gộp được.
    Với chiến lược vol cao, annual số học phồng to hơn CAGR rất nhiều (volatility
    drag). So hai con số này cho thấy ảo giác lợi nhuận lớn cỡ nào.
    """
    e = pd.Series(equity).dropna()
    if len(e) < 2:
        return 0.0
    total = float(e.iloc[-1] / e.iloc[0])
    years = len(e) / periods_per_year
    if total <= 0 or years <= 0:
        return -1.0
    return total ** (1.0 / years) - 1.0


def _per_period_sharpe(returns: np.ndarray) -> float:
    if returns.size < 2 or np.std(returns, ddof=1) == 0:
        return 0.0
    return float(np.mean(returns) / np.std(returns, ddof=1))


def probabilistic_sharpe_ratio(
    returns: pd.Series, benchmark_sr: float = 0.0
) -> float:
    """
    PSR: P(Sharpe thật > benchmark_sr), hiệu chỉnh skew & kurtosis.

    benchmark_sr tính theo per-period (không annualize). Trả về xác suất [0,1].
    Giá trị > 0.95 thường được coi là có ý nghĩa thống kê.
    """
    r = _clean(returns)
    n = r.size
    if n < 3:
        return 0.0
    sr = _per_period_sharpe(r)
    skew = float(stats.skew(r))
    kurt = float(stats.kurtosis(r, fisher=False))  # kurtosis thường (normal = 3)

    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2
    if denom <= 0:
        return 0.0
    z = (sr - benchmark_sr) * np.sqrt(n - 1) / np.sqrt(denom)
    return float(stats.norm.cdf(z))


def expected_max_sharpe(trials_sharpe_std: float, n_trials: int) -> float:
    """
    Kỳ vọng Sharpe LỚN NHẤT (per-period) thu được khi thử n_trials chiến lược
    độc lập, mỗi cái có Sharpe thật = 0 và độ lệch chuẩn = trials_sharpe_std.
    (Công thức López de Prado dựa trên thống kê cực trị.)
    """
    if n_trials < 2 or trials_sharpe_std <= 0:
        return 0.0
    g = EULER_MASCHERONI
    q1 = stats.norm.ppf(1.0 - 1.0 / n_trials)
    q2 = stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    return float(trials_sharpe_std * ((1.0 - g) * q1 + g * q2))


def deflated_sharpe_ratio(
    returns: pd.Series,
    n_trials: int,
    trials_sharpe_std: float | None = None,
) -> float:
    """
    DSR: PSR với ngưỡng = kỳ vọng Sharpe lớn nhất từ n_trials lần thử.

    Tham số
    --------
    n_trials : số chiến lược/biến thể bạn ĐÃ thử để tìm ra cái này.
               Càng thử nhiều, ngưỡng càng cao, DSR càng bị "phạt".
    trials_sharpe_std : độ lệch chuẩn (per-period) của Sharpe giữa các lần thử.
               Nếu None, ước lượng thận trọng từ chính chuỗi returns này.

    Trả về xác suất [0,1]; > 0.95 mới đáng tin sau khi đã trừ bias đa phép thử.
    """
    r = _clean(returns)
    if r.size < 3:
        return 0.0
    if trials_sharpe_std is None:
        # Ước lượng thận trọng: sai số chuẩn của Sharpe ~ sqrt((1+0.5*SR^2)/n).
        sr = _per_period_sharpe(r)
        trials_sharpe_std = float(np.sqrt((1.0 + 0.5 * sr ** 2) / r.size))
    sr_star = expected_max_sharpe(trials_sharpe_std, n_trials)
    return probabilistic_sharpe_ratio(r, benchmark_sr=sr_star)


def summary(
    result_equity: pd.Series,
    returns: pd.Series,
    n_trials: int = 1,
    periods_per_year: int = 252,
) -> dict:
    """Gom toàn bộ chỉ số vào một dict tiện in ra."""
    return {
        "annual_return": annualized_return(returns, periods_per_year),
        "cagr": cagr(result_equity, periods_per_year),
        "annual_vol": annualized_vol(returns, periods_per_year),
        "sharpe": sharpe_ratio(returns, periods_per_year),
        "max_drawdown": max_drawdown(result_equity),
        "psr_vs_0": probabilistic_sharpe_ratio(returns, 0.0),
        "deflated_sharpe": deflated_sharpe_ratio(returns, n_trials=n_trials),
        "n_trials_assumed": n_trials,
    }
