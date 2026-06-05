"""
Validation — chống rò rỉ thông tin trên dữ liệu time-series.

Cross-validation thường (KFold ngẫu nhiên) RÒ RỈ thông tin trên chuỗi thời gian
vì mẫu train và test nằm gần nhau về thời gian. Hai công cụ ở đây sửa điều đó:

  - PurgedKFold: loại (purge) các mẫu train chồng lấn nhãn với test, và
    "cấm vận" (embargo) một dải mẫu ngay sau test để tránh tự tương quan.
  - walk_forward: train trên quá khứ, test trên tương lai, cuốn chiếu — mô phỏng
    sát nhất cách chiến lược thật sự được triển khai theo thời gian.
"""
from __future__ import annotations

from typing import Iterator

import numpy as np


class PurgedKFold:
    """K-Fold có purge + embargo cho dữ liệu time-series."""

    def __init__(self, n_splits: int = 5, embargo_pct: float = 0.01) -> None:
        if n_splits < 2:
            raise ValueError("n_splits phải >= 2")
        self.n_splits = n_splits
        self.embargo_pct = embargo_pct

    def split(self, n_samples: int) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        indices = np.arange(n_samples)
        embargo = int(n_samples * self.embargo_pct)
        fold_bounds = np.array_split(indices, self.n_splits)

        for test_idx in fold_bounds:
            t0, t1 = test_idx[0], test_idx[-1]
            # Train = mọi mẫu, trừ vùng test và vùng embargo quanh test.
            train_mask = np.ones(n_samples, dtype=bool)
            lo = max(0, t0)
            hi = min(n_samples, t1 + 1 + embargo)
            train_mask[lo:hi] = False
            train_idx = indices[train_mask]
            yield train_idx, test_idx


def walk_forward(
    n_samples: int,
    train_size: int,
    test_size: int,
    step: int | None = None,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """
    Sinh các cặp (train_idx, test_idx) cuốn chiếu theo thời gian.

    train_size : số mẫu dùng để train mỗi vòng.
    test_size  : số mẫu test (out-of-sample) ngay sau train.
    step       : bước trượt cửa sổ (mặc định = test_size, không chồng lấn test).
    """
    step = step or test_size
    start = 0
    while start + train_size + test_size <= n_samples:
        train_idx = np.arange(start, start + train_size)
        test_idx = np.arange(start + train_size, start + train_size + test_size)
        yield train_idx, test_idx
        start += step
