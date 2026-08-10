"""Derive the (BETA, SE, Z) triple FALCON requires from whatever an upload has.

FALCON reads BETA, SE and Z. Uploads variously supply beta+se, beta+p, or an
explicit Z. Anything that cannot yield all three is dropped.
"""
from __future__ import annotations

import math
from statistics import NormalDist
from typing import Optional

_ND = NormalDist()
# inv_cdf(0) raises; p values that underflow to zero are clamped here. The
# resulting |Z| (~37) is far beyond any threshold that matters.
_MIN_P = 1e-300


def _z_from_p(pvalue: float, beta: float) -> float:
    p = pvalue if pvalue > _MIN_P else _MIN_P
    z = -_ND.inv_cdf(p / 2.0)          # positive by construction; only valid for p <= 1
    return math.copysign(z, beta)


def _validated(beta: float, se: float, z: float) -> Optional[tuple[float, float, float]]:
    """Reject triples unusable downstream: SE is a denominator, so it must be
    finite and strictly positive, and Z must be finite."""
    if not (math.isfinite(se) and se > 0.0):
        return None
    if not math.isfinite(z):
        return None
    return (beta, se, z)


def derive(
    beta: Optional[float],
    se: Optional[float],
    pvalue: Optional[float],
    zscore: Optional[float],
) -> Optional[tuple[float, float, float]]:
    """Return (beta, se, z), or None when the row cannot supply all three."""
    if beta is None or not math.isfinite(beta):
        return None

    if zscore is not None and math.isfinite(zscore) and zscore != 0.0:
        z = zscore
        s = se if (se is not None and se > 0.0) else abs(beta / z)
        return _validated(beta, s, z)

    if se is not None and math.isfinite(se) and se > 0.0:
        return _validated(beta, se, beta / se)

    if pvalue is not None and math.isfinite(pvalue) and 0.0 <= pvalue <= 1.0:
        z = _z_from_p(pvalue, beta)
        if z == 0.0:
            return None
        return _validated(beta, abs(beta / z), z)

    return None
