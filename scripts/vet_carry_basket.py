"""
GAUNTLET — Funding carry DELTA-NEUTRAL nhiều coin (mở rộng breadth của carry ĐÃ GIỮ).

Chạy:  python scripts/vet_carry_basket.py
(Cần: fetch_xs_universe.py + fetch_xs_spot.py đã chạy xong.)

ĐÂY KHÔNG PHẢI EDGE MỚI. Tái sử dụng NGUYÊN bộ máy của carry single-coin đã GIỮ:
  - Chiến lược: alpha.strategies.funding_carry.FundingCarry(0.0)  [TILTED]  (KHÔNG sửa)
  - Engine    : Backtester.run(..., delta_neutral=True, rebalance=True)       (KHÔNG sửa)
  - Data      : data.prepare.load_carry_frame(with_spot=True)                 (KHÔNG sửa)
  - Gộp       : portfolio.combine.combine(method="risk_parity")              (KHÔNG sửa)
Khác biệt DUY NHẤT: chạy trên NHIỀU coin (mỗi coin delta-neutral: short perp +
long spot), rồi gộp risk-parity để lấy breadth (IR ≈ IC × √N — CHỈ đúng nếu các
sleeve THẬT và ít tương quan).

Vì sao kỳ vọng tốt hơn ứng viên XS perp-only đã LOẠI: delta-neutral (hedge spot)
CHỦ ĐÍCH triệt rủi ro giá idiosyncratic (price PnL ~ 0, chỉ còn basis + funding) —
đúng cái đuôi giá đã giết XS perp-only.

CHI PHÍ ALT (tiên nghiệm, KHÔNG fit):
  Major (BTC/ETH): cost_multiplier = 2.0  (hai chân perp+spot, spread chặt) — y
                   hệt FULL của carry đã giữ.
  Alt            : cost_multiplier = 5.0  (= 2.5× major; spread/slippage alt rộng
                   hơn). Bảo thủ. KHÔNG dùng chi phí BTC cho alt.
  rebalance_fraction = 1.0 (tái cân bằng liên tục ở phí taker — cận trên bi quan,
                   y hệt carry đã giữ).

n_trials TRUNG THỰC = 20 (kế thừa đúng số của carry đã giữ; params (threshold=0,
n_events=9) tiên nghiệm, KHÔNG dò). Universe = QUY TẮC "mọi major có spot sạch",
KHÔNG cherry-pick subset -> không thêm DOF dò tìm; vẫn ghi "chọn coin" là 1 DOF.

SURVIVORSHIP (nhẹ hơn XS perp-only): delta-neutral KHÔNG nuốt cú sập giá coin chết
(hedge spot triệt giá). Nhưng còn (a) rủi ro THANH LÝ chân short khi giá nhảy dữ
(mô hình ở đây CHƯA bắt) và (b) coin delist không lấy được spot -> vắng mặt. Ghi rõ.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha.strategies.funding_carry import FundingCarry
from data.prepare import load_carry_frame
from engine.backtest import Backtester
from engine.metrics import sharpe_ratio, summary
from engine.reality import CostModel
from portfolio.combine import combine

PPY = 24 * 365
N_TRIALS = 20
N_PERIODS = 5
N_EVENTS = 9            # tiên nghiệm, kế thừa carry đã giữ
REBAL_FRAC = 1.0
MAJOR_MULT = 2.0        # hai chân, spread chặt (BTC/ETH)
ALT_MULT = 5.0          # = 2.5× major (alt spread/slippage rộng hơn)

MAJORS = ["BTCUSDT", "ETHUSDT"]
ALTS = ["SOLUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT"]
UNIVERSE = MAJORS + ALTS

_COST = CostModel(spread_bps=2.0, slippage_bps=1.0, fee_bps=5.0)
_BT = Backtester(cost_model=_COST)


def _mult(tag: str, stress: float = 1.0) -> float:
    return (MAJOR_MULT if tag in MAJORS else ALT_MULT) * stress


def run_sleeve(tag: str, stress: float = 1.0, rebal_frac: float = REBAL_FRAC) -> dict | None:
    """Chạy carry delta-neutral FULL cho một coin. Trả net + tách funding/price.

    Loại coin không có spot sạch (None). delta_neutral=True, rebalance=True —
    y hệt FULL của carry đã giữ.
    """
    try:
        df = load_carry_frame(tag, n_events=N_EVENTS, with_spot=True)
    except FileNotFoundError:
        return None
    if "spot_close" not in df.columns:
        return None

    res = _BT.run(
        df, FundingCarry(0.0), delta_neutral=True,
        cost_multiplier=_mult(tag, stress), rebalance=True, rebalance_fraction=rebal_frac,
    )
    pos = res.positions
    perp_ret = df["close"].pct_change().fillna(0.0)
    spot_ret = df["spot_close"].pct_change().fillna(0.0)
    funding = df["funding"].reindex(df.index).fillna(0.0)
    price_pnl = pos * (perp_ret - spot_ret)            # basis (như engine delta-neutral)
    funding_pnl = -pos * funding
    return {
        "net": res.net_returns, "funding": funding_pnl, "price": price_pnl,
        "cost": res.costs, "equity": res.equity,
    }


def _stats(returns: pd.Series, label: str, n_trials: int = N_TRIALS) -> dict:
    eq = (1.0 + returns.fillna(0.0)).cumprod()
    s = summary(eq, returns, n_trials=n_trials, periods_per_year=PPY)
    verdict = "QUA cổng" if s["deflated_sharpe"] > 0.95 else "chưa qua"
    print(
        f"  {label:<26} | Sharpe {s['sharpe']:>5.2f} | CAGR {s['cagr']:>8.2%} "
        f"| MaxDD {s['max_drawdown']:>8.2%} | DSR {s['deflated_sharpe']:>6.2%} -> {verdict}"
    )
    return s


def combine_book(sleeves: dict[str, dict]) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    nets = {t: s["net"] for t, s in sleeves.items()}
    return combine(nets, method="risk_parity")


def _decompose(sleeves: dict[str, dict], weights: pd.Series, index: pd.Index, label: str) -> None:
    """Tách funding vs price của BOOK gộp (cùng trọng số risk-parity)."""
    f = pd.Series(0.0, index=index)
    p = pd.Series(0.0, index=index)
    for t, s in sleeves.items():
        w = float(weights.get(t, 0.0))
        f = f.add(w * s["funding"].reindex(index).fillna(0.0), fill_value=0.0)
        p = p.add(w * s["price"].reindex(index).fillna(0.0), fill_value=0.0)
    cf, cp = float(f.sum()), float(p.sum())
    frac = abs(cf) / (abs(cf) + abs(cp)) if (cf or cp) else 0.0
    print(f"  [{label}] tách PnL book (delta-neutral -> price phải ~0):")
    print(f"     funding = {cf:>+8.4f}  (Sharpe {sharpe_ratio(f, PPY):>5.2f})")
    print(f"     price   = {cp:>+8.4f}  (Sharpe {sharpe_ratio(p, PPY):>5.2f})  <- basis; lớn = hedge sai/đáng ngại")
    print(f"     -> funding chiếm {frac:.1%} của |funding|+|price|")


def main() -> None:
    print("=== Tải sleeve carry delta-neutral từng coin ===")
    sleeves: dict[str, dict] = {}
    dropped: list[str] = []
    for tag in UNIVERSE:
        s = run_sleeve(tag)
        if s is None:
            dropped.append(tag)
            continue
        sleeves[tag] = s
        sh = sharpe_ratio(s["net"], PPY)
        print(f"  {tag:<10} sleeve Sharpe {sh:>5.2f}  ({len(s['net'])} bars)  cost x{_mult(tag):g}")
    if dropped:
        print(f"  LOẠI (thiếu spot sạch): {', '.join(dropped)}")
    if len(sleeves) < 2:
        print("!! Cần >= 2 sleeve có spot. Chạy fetch_xs_spot.py trước.")
        return

    # ── GỘP BOOK (risk-parity) ────────────────────────────────────────────
    combined, weights, corr = combine_book(sleeves)
    print(f"\n=== BOOK gộp risk-parity ({len(sleeves)} coin) ===")
    print(f"  Cửa sổ chung (combine dropna): {combined.index[0].date()} -> {combined.index[-1].date()} "
          f"({len(combined)} bars ≈ {len(combined)/PPY:.1f} năm)")
    print("  Trọng số risk-parity: " + ", ".join(f"{t}={w:.2f}" for t, w in weights.items()))

    print("\n  Ma trận tương quan giữa các sleeve (breadth chỉ thật nếu corr THẤP):")
    print(corr.round(2).to_string().replace("\n", "\n  "))
    off = corr.where(~np.eye(len(corr), dtype=bool))
    print(f"  -> corr trung bình (ngoài đường chéo): {off.stack().mean():.2f} "
          f"| max: {off.stack().max():.2f}")

    # ── [1] GAUNTLET BOOK GỘP ─────────────────────────────────────────────
    print("\n=== [1] BOOK GỘP — gauntlet (n_trials=20) ===")
    _stats(combined, "BASKET full")
    _decompose(sleeves, weights, combined.index, "BASKET")

    # ── [2] SO SÁNH QUYẾT ĐỊNH: BASKET vs BTC/ETH-only ────────────────────
    print("\n=== [2] SO SÁNH: rổ GỘP vs carry CHỈ BTC/ETH (sau chi phí alt thật) ===")
    be = {t: sleeves[t] for t in MAJORS if t in sleeves}
    be_combined, _, _ = combine_book(be)
    _stats(be_combined, "BTC/ETH-only")
    _stats(combined, "BASKET (8 coin)")
    # so trên cùng cửa sổ chung để công bằng
    common = combined.index.intersection(be_combined.index)
    s_be_c = _stats(be_combined.reindex(common).dropna(), "BTC/ETH (cửa sổ chung)")
    s_all_c = _stats(combined.reindex(common).dropna(), "BASKET (cửa sổ chung)")

    # ── [3] STRESS CHI PHÍ ────────────────────────────────────────────────
    print("\n=== [3] STRESS CHI PHÍ (×1 / ×2 trên nền chi phí alt đã cao) ===")
    for stress in (1.0, 2.0):
        st_sleeves = {t: run_sleeve(t, stress) for t in sleeves}
        st_sleeves = {t: v for t, v in st_sleeves.items() if v is not None}
        c, _, _ = combine_book(st_sleeves)
        _stats(c, f"BASKET cost ×{stress:g}")

    # ── [3b] SENSITIVITY rebalance_fraction (chống TỰ over-reject) ─────────
    # rf=1.0 (tái cân bằng liên tục, taker) phạt nặng coin vol cao (alt). Kiểm
    # tra phán quyết có VỮNG khi giả định chi phí hedge rẻ hơn không. Nếu ngay cả
    # rf=0 (bỏ hẳn phí rebalance) alt vẫn thua xa major -> loại alt là vững.
    print("\n=== [3b] SENSITIVITY rf (BASKET vs BTC/ETH; chống tự over-reject) ===")
    for rf in (1.0, 0.25, 0.10, 0.0):
        all_s = {t: run_sleeve(t, 1.0, rf) for t in sleeves}
        all_s = {t: v for t, v in all_s.items() if v is not None}
        be_s = {t: all_s[t] for t in MAJORS if t in all_s}
        c_all, _, _ = combine_book(all_s)
        c_be, _, _ = combine_book(be_s)
        cm = c_all.index.intersection(c_be.index)
        sh_all = sharpe_ratio(c_all.reindex(cm).dropna(), PPY)
        sh_be = sharpe_ratio(c_be.reindex(cm).dropna(), PPY)
        print(f"  rf={rf:<4} | BASKET Sharpe {sh_all:>6.2f} | BTC/ETH {sh_be:>6.2f} "
              f"-> {'basket thắng' if sh_all > sh_be else 'BTC/ETH thắng'}")

    # ── [4] ỔN ĐỊNH REGIME ────────────────────────────────────────────────
    print("\n=== [4] ỔN ĐỊNH QUA REGIME (Sharpe từng đoạn) ===")
    chunks = np.array_split(combined.dropna(), N_PERIODS)
    parts = " | ".join(f"{sharpe_ratio(c, PPY):>5.2f}" for c in chunks)
    print(f"  {N_PERIODS} đoạn liên tiếp: {parts}")

    # ── [5] OOS HOLDOUT — CHẠM MỘT LẦN ────────────────────────────────────
    print("\n=== [5] OOS HOLDOUT 30% cuối (chạm MỘT LẦN) ===")
    n = len(combined)
    split = int(n * 0.70)
    print(f"  IS  : {combined.index[0].date()} -> {combined.index[split-1].date()}  ({split} bars)")
    print(f"  OOS : {combined.index[split].date()} -> {combined.index[-1].date()}  ({n-split} bars)")
    _stats(combined.iloc[:split], "IN-SAMPLE (70%)")
    _stats(combined.iloc[split:], "OUT-OF-SAMPLE (30%)")

    # ── PHÁN QUYẾT NHANH ──────────────────────────────────────────────────
    print("\n" + "=" * 70)
    better = (s_all_c["sharpe"] > s_be_c["sharpe"]) and (s_all_c["deflated_sharpe"] >= s_be_c["deflated_sharpe"])
    print(f"BASKET có THẮNG BTC/ETH risk-adjusted (cùng cửa sổ)? "
          f"Sharpe {s_all_c['sharpe']:.2f} vs {s_be_c['sharpe']:.2f} | "
          f"DSR {s_all_c['deflated_sharpe']:.1%} vs {s_be_c['deflated_sharpe']:.1%} "
          f"-> {'CÓ' if better else 'KHÔNG'}")
    print("Nếu KHÔNG (alt làm loãng / bị chi phí ăn): LOẠI phần mở rộng, GIỮ carry BTC/ETH.")


if __name__ == "__main__":
    main()
