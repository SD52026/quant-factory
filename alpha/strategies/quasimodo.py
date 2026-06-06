"""
Chiến lược QUASIMODO (QM) — mẫu hình đảo chiều SMC.

"Quasimodo" là một định nghĩa MƠ HỒ (nhiều biến thể). Nên ở đây ta CHỐT MỘT
đặc tả chính xác, kiểm thử được. Các biến thể khác tồn tại — đây là phiên bản
của ta, và mọi test bám đúng nó.

ĐẶC TẢ CHÍNH XÁC (bearish, vào SHORT):
  Dựa trên các swing point đã XÁC NHẬN (pivot fractal cửa sổ w, xác nhận trễ w bar):
  1. Ba swing liên tiếp dạng  H1 (đỉnh) -> L1 (đáy) -> H2 (đỉnh), với H2 > H1
     (đỉnh sau quét thanh khoản trên đỉnh trước — "đầu" của mẫu hình).
  2. PHÁ CẤU TRÚC (BOS): sau đó giá ĐÓNG CỬA dưới L1 (đổi tính chất, xác nhận đảo).
  3. VÀO LỆNH: sau BOS, khi giá hồi lên CHẠM mức H1 (Quasimodo level) -> SHORT.
  4. Stop: trên H2 (đệm nhỏ). Target: R bội (mặc định 2R).
  5. Hủy setup nếu giá vượt H2 trước khi vào, hoặc quá max_wait bar không hồi tới.

  Bullish (LONG) là ĐỐI XỨNG: L1 -> H1 -> L2 (L2 < L1, quét đáy), đóng cửa trên
  H1 (BOS lên), hồi xuống chạm L1 -> LONG.

CHỐNG LOOKAHEAD: swing chỉ dùng khi đã xác nhận (trễ w bar); mọi quyết định tại
bar t chỉ dùng dữ liệu <= t; engine còn shift vị thế thêm 1 bar.

CẢNH BÁO: pattern strategy nhiều bậc tự do -> dễ overfit & dễ tự lừa. Phải qua
unit test (mẫu chuẩn + near-miss) VÀ negative control trước khi tin con số nào.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.strategy import Strategy


class Quasimodo(Strategy):
    def __init__(
        self,
        swing_window: int = 5,
        stop_buffer: float = 0.001,
        target_r: float = 2.0,
        max_hold: int = 24 * 14,
        max_wait: int = 24 * 30,
    ) -> None:
        self.w = swing_window
        self.stop_buffer = stop_buffer
        self.target_r = target_r
        self.max_hold = max_hold
        self.max_wait = max_wait
        self.name = f"quasimodo_w{swing_window}"

    def _confirmed_swing_events(self, high, low):
        """Trả danh sách (confirm_idx, kind, price) — pivot fractal, xác nhận trễ w."""
        n = len(high)
        w = self.w
        events = []
        for i in range(w, n - w):
            if high[i] == high[i - w : i + w + 1].max():
                events.append((i + w, "H", float(high[i])))
            if low[i] == low[i - w : i + w + 1].min():
                events.append((i + w, "L", float(low[i])))
        events.sort(key=lambda e: e[0])
        return events

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        for col in ("high", "low", "close"):
            if col not in data.columns:
                raise ValueError(f"data thiếu cột '{col}'")
        high = data["high"].to_numpy(float)
        low = data["low"].to_numpy(float)
        close = data["close"].to_numpy(float)
        n = len(close)
        pos = np.zeros(n)

        events = self._confirmed_swing_events(high, low)
        ev = 0
        zz: list[list] = []  # zigzag swing đã xác nhận: [kind, price]

        bear = None  # setup bearish đang khóa
        bull = None
        cur = 0      # vị thế hiện tại
        stop = tgt = 0.0
        held = 0

        for t in range(n):
            # 1. Nạp swing xác nhận tới bar t, cập nhật zigzag + khóa setup.
            while ev < len(events) and events[ev][0] <= t:
                _, kind, price = events[ev]
                ev += 1
                if zz and zz[-1][0] == kind:
                    if (kind == "H" and price > zz[-1][1]) or (kind == "L" and price < zz[-1][1]):
                        zz[-1][1] = price  # gộp swing cùng loại: giữ cái cực hơn
                else:
                    zz.append([kind, price])
                if len(zz) >= 3:
                    a, b, c = zz[-3], zz[-2], zz[-1]
                    if a[0] == "H" and b[0] == "L" and c[0] == "H" and c[1] > a[1]:
                        bear = {"H1": a[1], "L1": b[1], "H2": c[1], "bos": False, "wait": 0}
                    if a[0] == "L" and b[0] == "H" and c[0] == "L" and c[1] < a[1]:
                        bull = {"L1": a[1], "H1": b[1], "L2": c[1], "bos": False, "wait": 0}

            # 2. Quản lý vị thế đang mở (thoát theo stop/target/timeout).
            if cur != 0:
                held += 1
                if cur < 0 and (close[t] >= stop or close[t] <= tgt or held >= self.max_hold):
                    cur = 0
                elif cur > 0 and (close[t] <= stop or close[t] >= tgt or held >= self.max_hold):
                    cur = 0

            # 3. Tìm điểm vào (chỉ khi đang flat).
            if cur == 0 and bear is not None:
                if high[t] > bear["H2"]:
                    bear = None  # đầu bị phá -> hủy
                else:
                    if not bear["bos"] and close[t] < bear["L1"]:
                        bear["bos"] = True
                    if bear is not None and bear["bos"]:
                        bear["wait"] += 1
                        if high[t] >= bear["H1"]:
                            cur, entry, held = -1, bear["H1"], 0
                            stop = bear["H2"] * (1 + self.stop_buffer)
                            tgt = entry - self.target_r * (stop - entry)
                            bear = None
                        elif bear["wait"] > self.max_wait:
                            bear = None

            if cur == 0 and bull is not None:
                if low[t] < bull["L2"]:
                    bull = None
                else:
                    if not bull["bos"] and close[t] > bull["H1"]:
                        bull["bos"] = True
                    if bull is not None and bull["bos"]:
                        bull["wait"] += 1
                        if low[t] <= bull["L1"]:
                            cur, entry, held = 1, bull["L1"], 0
                            stop = bull["L2"] * (1 - self.stop_buffer)
                            tgt = entry + self.target_r * (entry - stop)
                            bull = None
                        elif bull["wait"] > self.max_wait:
                            bull = None

            pos[t] = cur

        return pd.Series(pos, index=data.index)
