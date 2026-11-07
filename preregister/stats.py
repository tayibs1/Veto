"""Statistical referee calculations:
1. Effective Independent Trials (K_eff) from trial excess-return correlation matrix
   (Bailey & Lopez de Prado correlation participation formula).
2. Exact Two-Sided Binomial Sign Test (p_raw) & Trial-Adjusted p-value (p_adj = 1 - (1 - p)^K_eff).
3. Probabilistic & Deflated Sharpe Ratio (DSR, Bailey & Lopez de Prado 2012, 2014).
4. Minimum Detectable Excess Return (MDE) in bps.
"""

from __future__ import annotations

import math


def normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_ppf(p: float) -> float:
    """Rational approximation (Beasley-Springer-Moro / Acklam) to inverse standard normal CDF."""
    p = min(max(p, 1e-12), 1.0 - 1e-12)
    # Rational approximation
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1.0 - plow
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if phigh < p:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    )


def sign_test_p_value(wins: int, losses: int) -> float:
    """Two-sided exact binomial test of wins vs losses (ties excluded) at p=0.5."""
    n = wins + losses
    if n <= 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def pearson_corr(xs: list[float], ys: list[float]) -> float:
    """Sample Pearson correlation between two equal-length vectors."""
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    mx = sum(xs[:n]) / n
    my = sum(ys[:n]) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = sum((xs[i] - mx) ** 2 for i in range(n))
    dy = sum((ys[i] - my) ** 2 for i in range(n))
    if dx <= 1e-12 or dy <= 1e-12:
        return 1.0 if xs[:n] == ys[:n] else 0.0
    return max(-1.0, min(1.0, num / math.sqrt(dx * dy)))


def effective_independent_trials(trial_vectors: list[list[int | float]]) -> float:
    """Compute K_eff from the K x M matrix of trial excess returns across M paths.

    Uses Bailey & Lopez de Prado's correlation adjustment:
      K_eff = 1 + (K - 1) * (1 - rho_bar)
    where rho_bar is the average positive pairwise correlation across the K trials.
    """
    k = len(trial_vectors)
    if k <= 1:
        return 1.0
    pos_corrs: list[float] = []
    for i in range(k):
        for j in range(i + 1, k):
            c = pearson_corr([float(v) for v in trial_vectors[i]], [float(v) for v in trial_vectors[j]])
            pos_corrs.append(max(0.0, c))
    rho_bar = sum(pos_corrs) / len(pos_corrs) if pos_corrs else 0.0
    return max(1.0, min(float(k), 1.0 + (k - 1.0) * (1.0 - rho_bar)))


def trial_adjusted_p_value(raw_p: float, k_eff: float) -> float:
    """Sidak multiple-testing adjusted p-value across K_eff effective independent trials."""
    raw_p = min(max(raw_p, 0.0), 1.0)
    k_eff = max(1.0, k_eff)
    return 1.0 - ((1.0 - raw_p) ** k_eff)


def deflated_sharpe_probability(
    excess_returns_bps: list[int | float],
    k_eff: float,
    trial_sharpe_std: float = 0.5,
) -> tuple[float, float]:
    """Compute (observed_sharpe, deflated_sharpe_probability) per Bailey & Lopez de Prado (2014)."""
    n = len(excess_returns_bps)
    if n < 3:
        return 0.0, 0.0
    xs = [float(x) for x in excess_returns_bps]
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    std = math.sqrt(max(1e-9, var))
    sr = mean / std if std > 1e-6 else 0.0

    # Sample skewness and kurtosis
    m3 = sum(((x - mean) / std) ** 3 for x in xs) / n
    m4 = sum(((x - mean) / std) ** 4 for x in xs) / n

    # Expected max Sharpe under null across K_eff independent trials
    euler_gamma = 0.5772156649
    if k_eff <= 1.05:
        sr_zero = 0.0
    else:
        z1 = normal_ppf(1.0 - 1.0 / k_eff)
        z2 = normal_ppf(1.0 - 1.0 / (k_eff * math.e))
        sr_zero = max(0.0, trial_sharpe_std * ((1.0 - euler_gamma) * z1 + euler_gamma * z2))

    denom_sq = max(1e-6, 1.0 - m3 * sr + ((m4 - 1.0) / 4.0) * (sr**2))
    z_stat = ((sr - sr_zero) * math.sqrt(n - 1)) / math.sqrt(denom_sq)
    return round(sr, 4), round(normal_cdf(z_stat), 4)


def min_detectable_excess_bps(excess_returns_bps: list[int | float], k_eff: float) -> int:
    """Minimum median/mean excess in bps detectable at alpha=0.05 (adjusted for K_eff) and 80% power."""
    n = max(2, len(excess_returns_bps))
    xs = [float(x) for x in excess_returns_bps]
    mean = sum(xs) / n
    std = math.sqrt(max(1.0, sum((x - mean) ** 2 for x in xs) / max(1, n - 1)))
    alpha_per_trial = 1.0 - (0.95 ** (1.0 / max(1.0, k_eff)))
    z_alpha = normal_ppf(1.0 - alpha_per_trial / 2.0)
    z_beta = 0.8416  # 80% power
    return int(round((z_alpha + z_beta) * (std / math.sqrt(n))))
