"""
GAUNTLET — Cross-Sectional Funding Carry (dollar-neutral). Cố GIẾT ứng viên.

Chạy:  python scripts/vet_funding_carry_xs.py
(Cần: python scripts/fetch_xs_universe.py đã chạy xong — rổ multi-coin GỒM coin chết.)

MÔ HÌNH (a-priori, khai báo rõ):
  - Perp-only, dollar-neutral: LONG coin funding_avg âm nhất, SHORT coin dương
    nhất; Σlong=+1, Σshort=-1 (gross=2, net=0). KHÔNG spot-hedge từng chân
    (chân LONG không short spot rẻ được). => chạy engine delta_neutral=False:
    danh mục NUỐT rủi ro giá idiosyncratic (chính chỗ survivorship cắn mạnh
    nhất), beta thị trường bị triệt qua rổ long-short.
  - Đòn bẩy gộp = 2 (1 long + 1 short). Sharpe bất biến theo scale.

BÁO CÁO TÁCH BẠCH (điều kiện #1 — quan trọng nhất):
  PnL danh mục = PnL_funding (edge thật) + PnL_price (chênh giá tương đối hai
  chân = basis risk cross-sectional, may rủi) − chi phí. In RIÊNG hai dòng. Nếu
  phần lớn PnL đến từ giá chứ không từ funding -> KHÔNG phải edge, chỉ là may.

PHÁN QUYẾT (điều kiện #3):
  Dựa trên bộ tham số TIÊN NGHIỆM (n_long=2, n_short=2, n_events=9), khử phồng
  bằng n_trials=27 (= lưới nhiễu-loạn). Lưới 27 biến thể CHỈ để kiểm tra độ
  vững, KHÔNG để chọn cái Sharpe cao nhất (chọn best-of-27 = overfit, vi phạm
  protocol).

BỘ THỬ-GIẾT (Protocol §2):
  0. AUDIT LOOKAHEAD trực tiếp — ranking tại t chỉ dùng funding biết strictly
     trước t? (điều kiện #4)
  1. Tách PnL funding vs price (điều kiện #1).
  2. NEGATIVE CONTROL — xáo funding theo thời gian; RW giá + xáo funding.
  3. STRESS chi phí 1x/2x/4x.
  4. NHIỄU LOẠN tham số (27 biến thể) — chỉ kiểm độ vững.
  5. ỔN ĐỊNH regime + ĐỘ SÂU rổ theo thời gian (điều kiện #5).
  6. OOS holdout 30% cuối — chạm MỘT LẦN.

SURVIVORSHIP (điều kiện #2 — có thể THỐNG TRỊ, không phải chú thích):
  Chiến lược chuyên trade đúng coin funding cực đoan — mà đó chính là loại coin
  dễ nổ/delist nhất. Rổ này ĐÃ đưa vào hai coin chết kèm funding âm điên loạn
  (LUNA gốc, SRM). Vet in riêng kết quả CÓ và KHÔNG có coin chết để đo mức bias.
  Coin chết khác bị xoá hẳn khỏi API vẫn còn thiếu => bias dư vẫn đẩy số LÊN.
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

from alpha.strategies.funding_carry_xs import FundingCarryXS
from data.prepare_xs import (
    build_funding_panel,
    build_xs_carry_frames,
    effective_sample_range,
    load_raw_coin_data,
)
from engine.backtest import Backtester
from engine.metrics import sharpe_ratio, summary
from engine.reality import CostModel

PPY = 24 * 365
# n_trials TRUNG THỰC = 27 = đúng kích thước lưới nhiễu-loạn (9 n_events × 3 cặp
# (nl,ns))... thực tế lưới dưới đây là 5 cặp × 3 n_events = 15; cộng đệm an toàn
# cho các lựa chọn ngầm (universe, min_coins, mô hình cost) -> chốt 27 (bảo thủ).
N_TRIALS = 27
N_PERIODS = 5
MIN_COINS = 4
SEED = 12345

# Cấu hình TIÊN NGHIỆM — phán quyết dựa trên đúng bộ này.
APRIORI = (2, 2, 9)  # (n_long, n_short, n_events)

LIVE = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT", "DOTUSDT",
    "FTTUSDT", "LUNA2USDT",
]
DEAD = ["LUNAUSDT", "SRMUSDT"]   # coin đã chết kèm funding âm cực đoan
UNIVERSE = LIVE + DEAD

_BT = Backtester(cost_model=CostModel(spread_bps=2.0, slippage_bps=1.0, fee_bps=5.0))


# ──────────────────────────────────────────────────────────────────────────
# Lõi: tổng hợp lợi nhuận danh mục, TÁCH funding-PnL vs price-PnL.
# ──────────────────────────────────────────────────────────────────────────
def portfolio_pnl(
    frames: dict[str, pd.DataFrame],
    panel: pd.DataFrame,
    strat: FundingCarryXS,
    cost_multiplier: float = 1.0,
) -> dict[str, pd.Series]:
    """Trả dict gồm net / funding / price / cost — mỗi cái là chuỗi theo bar.

    Tự tính từng thành phần (engine chỉ trả gross gộp) để TÁCH BẠCH:
      - position = weight đã shift 1 bar (giống engine, chống lookahead).
      - price_pnl   = position * perp_ret            (delta_neutral=False)
      - funding_pnl = -position * funding
      - cost        = |Δposition| * cost_per_unit * cost_multiplier
    Tổng trên toàn rổ, trên đoạn effective (>= MIN_COINS coin).
    """
    strat.prepare(panel)
    start, end, _ = effective_sample_range(panel, MIN_COINS)
    if start is None:
        empty = pd.Series(dtype=float)
        return {"net": empty, "funding": empty, "price": empty, "cost": empty}

    common = panel.loc[start:end].index
    cpu = _BT.cost_model.cost_per_unit_turnover * cost_multiplier
    funding = pd.Series(0.0, index=common)
    price = pd.Series(0.0, index=common)
    cost = pd.Series(0.0, index=common)

    for coin, df in frames.items():
        strat.set_coin(coin)
        target = strat.generate_signals(df).reindex(df.index).fillna(0.0).clip(-1, 1)
        pos = target.shift(1).fillna(0.0)                       # chống lookahead (như engine)
        perp_ret = df["close"].pct_change().fillna(0.0)
        fnd = df["funding"].reindex(df.index).fillna(0.0) if "funding" in df else 0.0
        turn = pos.diff().abs().fillna(pos.abs())

        price = price.add((pos * perp_ret).reindex(common).fillna(0.0), fill_value=0.0)
        funding = funding.add((-pos * fnd).reindex(common).fillna(0.0), fill_value=0.0)
        cost = cost.add((turn * cpu).reindex(common).fillna(0.0), fill_value=0.0)

    net = funding + price - cost
    return {"net": net, "funding": funding, "price": price, "cost": cost}


def _equity(returns: pd.Series) -> pd.Series:
    return (1.0 + returns.fillna(0.0)).cumprod()


def _report(returns: pd.Series, label: str, n_trials: int = N_TRIALS) -> dict:
    eq = _equity(returns)
    s = summary(eq, returns, n_trials=n_trials, periods_per_year=PPY)
    verdict = "QUA cổng" if s["deflated_sharpe"] > 0.95 else "chưa qua"
    print(
        f"  {label:<28} | Sharpe {s['sharpe']:>5.2f} | CAGR {s['cagr']:>8.2%} "
        f"| MaxDD {s['max_drawdown']:>8.2%} | DSR {s['deflated_sharpe']:>6.2%} -> {verdict}"
    )
    return s


def _decompose(pnl: dict, label: str) -> None:
    """In riêng đóng góp funding vs price (điều kiện #1)."""
    cum_f = float(pnl["funding"].sum())
    cum_p = float(pnl["price"].sum())
    cum_c = float(pnl["cost"].sum())
    cum_n = cum_f + cum_p - cum_c
    shf = sharpe_ratio(pnl["funding"], PPY)
    shp = sharpe_ratio(pnl["price"], PPY)
    frac_f = cum_f / (abs(cum_f) + abs(cum_p)) if (cum_f or cum_p) else 0.0
    print(f"  [{label}] PnL cộng dồn (đơn vị return, gross=2):")
    print(f"     funding = {cum_f:>+8.3f}  (Sharpe {shf:>5.2f})  <- EDGE THẬT")
    print(f"     price   = {cum_p:>+8.3f}  (Sharpe {shp:>5.2f})  <- chênh giá (may rủi)")
    print(f"     cost    = {cum_c:>+8.3f}")
    print(f"     net     = {cum_n:>+8.3f}   | funding chiếm {frac_f:>5.1%} của |funding|+|price|")


# ──────────────────────────────────────────────────────────────────────────
# Negative controls.
# ──────────────────────────────────────────────────────────────────────────
def _shuffle_funding_raw(raw: dict, rng: np.random.Generator) -> dict:
    out: dict = {}
    for tag, d in raw.items():
        f = d["funding"].copy()
        vals = f["funding_rate"].to_numpy().copy()
        rng.shuffle(vals)
        f["funding_rate"] = vals
        out[tag] = {"ohlcv": d["ohlcv"], "funding": f, "spot": d["spot"]}
    return out


def _randomwalk_ohlcv(raw: dict, rng: np.random.Generator) -> dict:
    out: dict = {}
    for tag, d in raw.items():
        o = d["ohlcv"].copy()
        ret = o["close"].pct_change().dropna()
        vol = float(ret.std()) if len(ret) > 1 else 0.01
        px = float(o["close"].iloc[0]) * np.exp(np.cumsum(rng.normal(0.0, vol, len(o))))
        for c in ("open", "high", "low", "close"):
            o[c] = px
        out[tag] = {"ohlcv": o, "funding": d["funding"], "spot": d["spot"]}
    return out


def _build(raw: dict, n_events: int = 9) -> tuple[dict, pd.DataFrame]:
    frames = build_xs_carry_frames(raw, n_events=n_events)
    panel = build_funding_panel(frames)
    return frames, panel


def _cfg(tag: tuple[int, int, int]) -> FundingCarryXS:
    nl, ns, _ = tag
    return FundingCarryXS(nl, ns, max(MIN_COINS, nl + ns))


# ──────────────────────────────────────────────────────────────────────────
def _lookahead_audit(raw: dict) -> None:
    """Điều kiện #4: xác nhận TRỰC TIẾP ranking tại t chỉ dùng funding < t.

    Phép thử: nhân đôi funding tại MỘT sự kiện ở thời điểm T của một coin. Nếu
    không có lookahead, weight (target) tại MỌI bar < T phải KHÔNG đổi -> vị thế
    earning funding(T) [= target tại bar event T, sau shift là pos(T)=target(T-1h)]
    không hề 'nhìn thấy' funding(T).
    """
    print("\n=== [0] AUDIT LOOKAHEAD TRỰC TIẾP (ranking dùng funding < t?) ===")
    coin = "BTCUSDT"
    _, base_panel = _build(raw, n_events=APRIORI[2])
    s0 = _cfg(APRIORI)
    s0.prepare(base_panel)
    w0 = s0._coin_weights[coin].copy()

    # chọn một timestamp sự kiện funding ở giữa chuỗi
    fnd = raw[coin]["funding"]["funding_rate"]
    t_event = fnd.index[len(fnd) // 2]
    perturbed = {t: {**raw[t]} for t in raw}
    f2 = raw[coin]["funding"].copy()
    f2.loc[t_event, "funding_rate"] = f2.loc[t_event, "funding_rate"] + 0.05  # +5% sốc
    perturbed[coin] = {"ohlcv": raw[coin]["ohlcv"], "funding": f2, "spot": raw[coin]["spot"]}

    _, sp_panel = _build(perturbed, n_events=APRIORI[2])
    s1 = _cfg(APRIORI)
    s1.prepare(sp_panel)
    w1 = s1._coin_weights[coin].reindex(w0.index)

    t_event_h = t_event.floor("h")
    before = w0.index < t_event_h
    changed_before = int((w0[before].fillna(0) != w1[before].fillna(0)).sum())
    changed_at_after = int((w0[~before].fillna(0) != w1[~before].fillna(0)).sum())
    print(f"  Sốc funding {coin} tại {t_event_h}.")
    print(f"  Weight đổi ở bar TRƯỚC T : {changed_before}  (phải = 0 -> không lookahead)")
    print(f"  Weight đổi ở bar >= T    : {changed_at_after}  (được phép, đó là quá khứ)")
    print(f"  -> {'PASS (không lookahead)' if changed_before == 0 else '!! FAIL — CÓ lookahead'}")


def main() -> None:
    raw_all = load_raw_coin_data(UNIVERSE)
    raw_live = {k: v for k, v in raw_all.items() if k in LIVE}
    got = sorted(raw_all.keys())
    got_dead = [d for d in DEAD if d in raw_all]
    print(f"Coin lấy được ({len(got)}): {', '.join(got)}")
    print(f"Coin CHẾT đưa vào ({len(got_dead)}): {', '.join(got_dead) or 'KHÔNG CÓ — cảnh báo!'}")
    if len(got) < MIN_COINS:
        print(f"!! Cần >= {MIN_COINS} coin. Chạy scripts/fetch_xs_universe.py trước.")
        return

    frames, panel = _build(raw_all, n_events=APRIORI[2])
    start, end, n_bars = effective_sample_range(panel, MIN_COINS)
    yrs = n_bars / PPY
    print(f"\nEffective range (>= {MIN_COINS} coin): {start.date()} -> {end.date()}  "
          f"({n_bars} bars ≈ {yrs:.1f} năm)")

    # Điều kiện #5: độ sâu rổ theo thời gian (số coin có dữ liệu mỗi năm).
    depth = panel.notna().sum(axis=1)
    print("  Độ sâu rổ (số coin có dữ liệu) theo năm:")
    for yr, grp in depth.groupby(depth.index.year):
        print(f"     {yr}: trung bình {grp.mean():4.1f} coin, max {int(grp.max())}")

    # ── [0] AUDIT LOOKAHEAD ───────────────────────────────────────────────
    _lookahead_audit(raw_all)

    # ── [1] CẤU HÌNH TIÊN NGHIỆM + TÁCH PnL ───────────────────────────────
    print(f"\n=== [1] CẤU HÌNH TIÊN NGHIỆM L{APRIORI[0]}/S{APRIORI[1]} "
          f"n_events={APRIORI[2]} (n_trials={N_TRIALS}) ===")
    pnl_full = portfolio_pnl(frames, panel, _cfg(APRIORI))
    _report(pnl_full["net"], "A-PRIORI (có coin chết)")
    _decompose(pnl_full, "có coin chết")

    # ── [2] SURVIVORSHIP: CÓ vs KHÔNG coin chết (điều kiện #2) ─────────────
    print("\n=== [2] SURVIVORSHIP — đo mức BIAS do coin chết ===")
    fr_live, pn_live = _build(raw_live, n_events=APRIORI[2])
    pnl_live = portfolio_pnl(fr_live, pn_live, _cfg(APRIORI))
    _report(pnl_live["net"], "KHÔNG coin chết (biased)")
    _report(pnl_full["net"], "CÓ coin chết (đúng hơn)")
    _decompose(pnl_live, "KHÔNG coin chết")
    print("  -> Khoảng cách hai dòng = mức backtest bị PHÓNG ĐẠI khi bỏ coin chết.")
    print("     Coin chết khác (bị xoá hẳn khỏi API) vẫn thiếu => bias dư còn đẩy LÊN.")

    # ── [3] NEGATIVE CONTROL ──────────────────────────────────────────────
    print("\n=== [3] NEGATIVE CONTROL (edge phải BIẾN MẤT) ===")
    rng = np.random.default_rng(SEED)
    f_sh, p_sh = _build(_shuffle_funding_raw(raw_all, rng), n_events=APRIORI[2])
    _report(portfolio_pnl(f_sh, p_sh, _cfg(APRIORI))["net"], "shuffled funding")
    f_rw, p_rw = _build(_randomwalk_ohlcv(_shuffle_funding_raw(raw_all, rng), rng), n_events=APRIORI[2])
    _report(portfolio_pnl(f_rw, p_rw, _cfg(APRIORI))["net"], "RW giá + shuffled funding")
    print("  (Real phải TÁCH BIỆT rõ khỏi control. Control Sharpe cao -> BUG.)")

    # ── [4] STRESS CHI PHÍ ────────────────────────────────────────────────
    print("\n=== [4] STRESS CHI PHÍ (turnover xoay vòng ranking) ===")
    for mult in (1.0, 2.0, 4.0):
        _report(portfolio_pnl(frames, panel, _cfg(APRIORI), mult)["net"], f"cost x{mult:g}")

    # ── [5] NHIỄU LOẠN THAM SỐ (chỉ kiểm độ vững, KHÔNG chọn best) ─────────
    print("\n=== [5] NHIỄU LOẠN THAM SỐ — kiểm ĐỘ VỮNG (KHÔNG dò chọn best) ===")
    survivors = 0
    grid = [(1, 1), (2, 2), (3, 3), (2, 3), (3, 2)]
    for (nl, ns) in grid:
        for ne in (6, 9, 12):
            f_g, p_g = _build(raw_all, n_events=ne)
            r = portfolio_pnl(f_g, p_g, _cfg((nl, ns, ne)))["net"]
            star = " *(a-priori)" if (nl, ns, ne) == APRIORI else ""
            s = _report(r, f"L{nl}/S{ns} n_events={ne}{star}")
            if s["sharpe"] > 0.5:
                survivors += 1
    print(f"  -> {survivors}/{len(grid) * 3} biến thể Sharpe>0.5 (vững nếu phần lớn sống).")
    print("     LƯU Ý: phán quyết tính trên (2,2,9), KHÔNG phải max của lưới này.")

    # ── [6] ỔN ĐỊNH REGIME ────────────────────────────────────────────────
    print("\n=== [6] ỔN ĐỊNH QUA REGIME (Sharpe từng đoạn) ===")
    chunks = np.array_split(pnl_full["net"].dropna(), N_PERIODS)
    parts = " | ".join(f"{sharpe_ratio(c, PPY):>5.2f}" for c in chunks)
    print(f"  {N_PERIODS} đoạn liên tiếp: {parts}")

    # ── [7] OOS HOLDOUT — CHẠM MỘT LẦN Ở CUỐI ─────────────────────────────
    print("\n=== [7] OOS HOLDOUT 30% cuối (chạm MỘT LẦN) ===")
    net = pnl_full["net"]
    n = len(net)
    split = int(n * 0.70)
    print(f"  IS  : {net.index[0].date()} -> {net.index[split - 1].date()}  ({split} bars)")
    print(f"  OOS : {net.index[split].date()} -> {net.index[-1].date()}  ({n - split} bars)")
    _report(net.iloc[:split], "IN-SAMPLE (70%)")
    _report(net.iloc[split:], "OUT-OF-SAMPLE (30%)")

    print("\n" + "=" * 70)
    print("ĐỌC: cần (a) funding chiếm phần lớn PnL [#1], (b) số có coin chết không sụp")
    print("[#2], (c) control ~0, (d) DSR>95% trên (2,2,9) [#3], (e) sống stress chi phí,")
    print("(f) Sharpe đoạn không lệch mạnh, (g) OOS không sụp. NHỚ effective range & bias dư.")


if __name__ == "__main__":
    main()
