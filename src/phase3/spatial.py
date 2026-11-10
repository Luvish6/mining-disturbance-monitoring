"""Deterministic metric blocks with conservative interior-only patch retention."""
import hashlib
import math


def block_for(bounds, block_m=5000, buffer_m=120):
    if not math.isfinite(block_m) or not math.isfinite(buffer_m) or not 0 <= buffer_m < block_m / 2:
        raise ValueError('Invalid block size/buffer')
    x0, y0, x1, y1 = bounds
    if not all(math.isfinite(x) for x in bounds) or x1 <= x0 or y1 <= y0:
        raise ValueError('Invalid projected bounds')
    bx, by = math.floor(x0 / block_m), math.floor(y0 / block_m)
    if (x0 < bx * block_m + buffer_m or y0 < by * block_m + buffer_m
            or x1 > (bx + 1) * block_m - buffer_m or y1 > (by + 1) * block_m - buffer_m):
        return None
    return f'{bx}:{by}'


def partition(block_id, seed=42):
    number = int(hashlib.sha256(f'{seed}:{block_id}'.encode()).hexdigest()[:16], 16) / 2**64
    return 'train' if number < .6 else 'validation' if number < .8 else 'test'
