#!/usr/bin/env python3
"""Statistics port: trend tests with a degrading optional backend.

The two trend primitives Demand Pulse relies on, the Mann-Kendall test and the
Theil-Sen slope, are implemented here in the standard library only, so the
default path needs no third-party package. The seasonal decomposition (STL) has
no standard-library equivalent, so it sits behind ``statsmodels`` and reports
itself unavailable when that package is absent. Callers check
``stats_capabilities()`` before relying on the STL path.

References for the methods are recorded in ``references/demand-pulse.md`` (primary
sources only).
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Sequence

# Rounding for every emitted float, so two runs on the same input are byte-equal.
_ROUND = 6


def stats_capabilities() -> dict[str, bool]:
    """Return which optional statistics paths are available in this environment.

    Only STL depends on an optional package; the Mann-Kendall and Theil-Sen paths
    are always available because they are pure standard library.
    """
    return {"stl": _statsmodels_present()}


def _statsmodels_present() -> bool:
    try:
        import statsmodels.tsa.seasonal  # noqa: F401
    except ImportError:
        return False
    return True


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _normal_cdf(z: float) -> float:
    """Standard normal cumulative distribution via the error function."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def mann_kendall(values: Sequence[float]) -> dict[str, Any]:
    """Run the Mann-Kendall trend test on an ordered series.

    Returns the S statistic, its tie-corrected variance, the standardised Z, the
    two-sided p-value, Kendall's tau, and a raw direction from the sign of S. The
    p-value is ``None`` when the series is too short (n < 3) or has zero variance,
    so the caller never treats an undefined test as significant.

    The base test assumes independent observations. Monthly demand is often
    autocorrelated, which can inflate significance; this limitation is documented
    in the reference, and a variance correction is left as a future option.
    """
    n = len(values)
    base: dict[str, Any] = {
        "n": n,
        "s": 0,
        "var_s": 0.0,
        "z": None,
        "p_value": None,
        "tau": None,
        "direction": "flat",
    }
    if n < 3:
        return base

    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            s += _sign(values[j] - values[i])

    # Tie correction: subtract a term per group of equal values.
    counts: dict[float, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    tie_term = sum(t * (t - 1) * (2 * t + 5) for t in counts.values())
    var_s = (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0

    direction = "up" if s > 0 else "down" if s < 0 else "flat"
    pairs = 0.5 * n * (n - 1)
    tau = round(s / pairs, _ROUND) if pairs else None

    if var_s <= 0:
        base.update({"s": s, "var_s": round(var_s, _ROUND), "tau": tau, "direction": direction})
        return base

    if s > 0:
        z = (s - 1) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / math.sqrt(var_s)
    else:
        z = 0.0
    p_value = max(0.0, min(1.0, 2.0 * (1.0 - _normal_cdf(abs(z)))))

    return {
        "n": n,
        "s": s,
        "var_s": round(var_s, _ROUND),
        "z": round(z, _ROUND),
        "p_value": round(p_value, _ROUND),
        "tau": tau,
        "direction": direction,
    }


def theil_sen(values: Sequence[float]) -> dict[str, Any]:
    """Estimate a robust linear slope and intercept by the Theil-Sen method.

    The slope is the median of the pairwise slopes between all point pairs, taking
    the x-coordinates as evenly spaced positions 0, 1, ... , n-1. The intercept is
    the median of ``y_k - slope * k``. The estimator resists outliers far better
    than ordinary least squares, which suits noisy demand series.
    """
    n = len(values)
    if n < 2:
        return {"n": n, "slope": 0.0, "intercept": round(float(values[0]), _ROUND) if n else 0.0}

    slopes: list[float] = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            slopes.append((values[j] - values[i]) / (j - i))
    slope = statistics.median(slopes)
    intercept = statistics.median([values[k] - slope * k for k in range(n)])
    return {"n": n, "slope": round(slope, _ROUND), "intercept": round(intercept, _ROUND)}


def stl_strength(values: Sequence[float], period: int) -> dict[str, Any]:
    """Decompose a series with STL and return trend and seasonal strength.

    Uses ``statsmodels`` when present; returns ``{"available": False, ...}`` when
    the package is missing or the series is shorter than two full periods, so the
    caller can fall back without a crash. Strength is the Wang, Smith and Hyndman
    measure: ``max(0, 1 - Var(remainder) / Var(component + remainder))``, bounded
    in [0, 1].
    """
    n = len(values)
    if not _statsmodels_present():
        return {"available": False, "reason": "statsmodels not installed"}
    if period < 2 or n < 2 * period:
        return {"available": False, "reason": "series shorter than two periods"}

    from statsmodels.tsa.seasonal import STL

    result = STL(list(values), period=period, robust=True).fit()
    seasonal = list(result.seasonal)
    trend = list(result.trend)
    resid = list(result.resid)

    var_resid = statistics.pvariance(resid)
    seasonal_plus = [seasonal[i] + resid[i] for i in range(n)]
    trend_plus = [trend[i] + resid[i] for i in range(n)]

    def strength(component_plus: list[float]) -> float:
        denom = statistics.pvariance(component_plus)
        if denom <= 0:
            return 0.0
        return max(0.0, 1.0 - var_resid / denom)

    return {
        "available": True,
        "period": period,
        "seasonal_strength": round(strength(seasonal_plus), _ROUND),
        "trend_strength": round(strength(trend_plus), _ROUND),
    }
