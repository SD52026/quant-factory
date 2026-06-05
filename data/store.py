"""
Point-in-time store — lưu & đọc dữ liệu dạng Parquet.

Quy ước: mọi dữ liệu thị trường lưu dưới data/pit_store/ theo tên rõ nghĩa,
ví dụ "binanceusdm_BTCUSDT_1h_ohlcv". Parquet vừa nén tốt vừa giữ kiểu dữ liệu
và index thời gian chính xác.

Nguyên tắc PIT: dữ liệu lưu đúng như nó tồn tại tại thời điểm thu thập. Khi cập
nhật, ta APPEND dữ liệu mới và khử trùng theo timestamp, KHÔNG sửa lịch sử cũ.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Thư mục lưu trữ, neo theo gốc project (…/quant-factory/data/pit_store).
PIT_DIR = Path(__file__).resolve().parent / "pit_store"


def _path(name: str) -> Path:
    safe = name.replace("/", "").replace(":", "")
    return PIT_DIR / f"{safe}.parquet"


def save(df: pd.DataFrame, name: str) -> Path:
    """Lưu DataFrame ra Parquet (ghi đè)."""
    PIT_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(name)
    df.to_parquet(path)
    return path


def load(name: str) -> pd.DataFrame:
    """Đọc DataFrame từ Parquet."""
    path = _path(name)
    if not path.exists():
        raise FileNotFoundError(f"Chưa có dữ liệu: {path}. Hãy chạy scripts/fetch_data.py trước.")
    return pd.read_parquet(path)


def append(df_new: pd.DataFrame, name: str) -> Path:
    """Nối dữ liệu mới vào dữ liệu cũ, khử trùng theo index (giữ bản cũ)."""
    path = _path(name)
    if path.exists():
        old = pd.read_parquet(path)
        combined = pd.concat([old, df_new])
        combined = combined[~combined.index.duplicated(keep="first")].sort_index()
    else:
        combined = df_new.sort_index()
    return save(combined, name)


def exists(name: str) -> bool:
    return _path(name).exists()
