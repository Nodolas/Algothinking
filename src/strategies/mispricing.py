"""Mispricing strategy: Z-score of current mid vs rolling mean/std."""
from __future__ import annotations


def mispricing_signal(
    mean_price: float,
    std_price: float,
    current_price: float,
    *,
    z_threshold: float = 2.0,
) -> tuple[str, float]:
    """
    Returns (signal, abs_z): OVERPRICED, UNDERPRICED, or FAIR and confidence (abs z-score).
    """
    if not std_price or std_price <= 0:
        return "FAIR", 0.0
    z = (current_price - mean_price) / std_price
    abs_z = abs(z)
    if z > z_threshold:
        return "OVERPRICED", min(abs_z / 3.0, 1.0)
    if z < -z_threshold:
        return "UNDERPRICED", min(abs_z / 3.0, 1.0)
    return "FAIR", abs_z / z_threshold
