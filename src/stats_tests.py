"""The statistics behind the A/B test, kept small and readable.

Group 1 = treatment (saw the ad), group 2 = control (saw a PSA).
c = conversions, n = users.
"""
import math

import numpy as np
from scipy import stats


def wilson_ci(c: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """95% confidence interval for one conversion rate (Wilson method,
    which behaves well even for small rates like 2%)."""
    z = stats.norm.ppf(1 - alpha / 2)
    p = c / n
    centre = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return centre - half, centre + half


def two_proportion_ztest(c1: int, n1: int, c2: int, n2: int) -> tuple[float, float]:
    """Is the difference between two conversion rates bigger than chance?
    Returns (z score, two-sided p-value)."""
    p1, p2 = c1 / n1, c2 / n2
    pooled = (c1 + c2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se
    return z, 2 * (1 - stats.norm.cdf(abs(z)))


def chi_square(c1: int, n1: int, c2: int, n2: int) -> tuple[float, float]:
    """The same question asked a second way, as a check. Returns (chi2, p-value)."""
    table = [[c1, n1 - c1], [c2, n2 - c2]]
    chi2, p, _, _ = stats.chi2_contingency(table, correction=False)
    return chi2, p


def difference_ci(c1: int, n1: int, c2: int, n2: int, alpha: float = 0.05) -> tuple[float, float]:
    """95% confidence interval for (rate 1 - rate 2), in percentage points / 100."""
    p1, p2 = c1 / n1, c2 / n2
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    z = stats.norm.ppf(1 - alpha / 2)
    return (p1 - p2) - z * se, (p1 - p2) + z * se


def relative_lift_ci(c1: int, n1: int, c2: int, n2: int, alpha: float = 0.05) -> tuple[float, float]:
    """95% interval for the RELATIVE lift (rate1 / rate2 - 1), using the
    standard log-ratio formula. The dashboard uses the same formula."""
    rr = (c1 / n1) / (c2 / n2)
    se = math.sqrt((1 - c1 / n1) / c1 + (1 - c2 / n2) / c2)
    z = stats.norm.ppf(1 - alpha / 2)
    return rr * math.exp(-z * se) - 1, rr * math.exp(z * se) - 1


def bootstrap_relative_lift(c1: int, n1: int, c2: int, n2: int, draws: int = 20000,
                            seed: int = 42, alpha: float = 0.05) -> tuple[float, float]:
    """95% interval for the RELATIVE lift (rate1 / rate2 - 1).

    Simulates the experiment 20,000 times from the observed rates and looks at
    the middle 95% of the lifts. Used because a ratio's interval is lopsided,
    which a simple formula doesn't capture."""
    rng = np.random.default_rng(seed)
    r1 = rng.binomial(n1, c1 / n1, draws) / n1
    r2 = rng.binomial(n2, c2 / n2, draws) / n2
    lifts = r1 / r2 - 1
    return tuple(np.quantile(lifts, [alpha / 2, 1 - alpha / 2]))


def minimum_detectable_lift(n1: int, n2: int, p_control: float,
                            alpha: float = 0.05, power: float = 0.80) -> float:
    """Smallest RELATIVE lift this sample could reliably detect (80% of the time)."""
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    se = math.sqrt(p_control * (1 - p_control) * (1 / n1 + 1 / n2))
    return z * se / p_control


def power_achieved(c1: int, n1: int, c2: int, n2: int, alpha: float = 0.05) -> float:
    """Chance this test would detect a true difference as large as the one observed."""
    p1, p2 = c1 / n1, c2 / n2
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    return float(stats.norm.cdf(abs(p1 - p2) / se - z_crit))


def full_test(c1: int, n1: int, c2: int, n2: int, alpha: float, power: float, seed: int) -> dict:
    """Everything needed to decide, in one dictionary."""
    p1, p2 = c1 / n1, c2 / n2
    z, p_value = two_proportion_ztest(c1, n1, c2, n2)
    chi2, chi2_p = chi_square(c1, n1, c2, n2)
    diff_lo, diff_hi = difference_ci(c1, n1, c2, n2, alpha)
    lift_lo, lift_hi = relative_lift_ci(c1, n1, c2, n2, alpha)
    boot_lo, boot_hi = bootstrap_relative_lift(c1, n1, c2, n2, seed=seed, alpha=alpha)
    ci1, ci2 = wilson_ci(c1, n1, alpha), wilson_ci(c2, n2, alpha)
    return {
        "ad_users": n1, "ad_conversions": c1, "ad_rate": p1, "ad_rate_ci_low": ci1[0], "ad_rate_ci_high": ci1[1],
        "psa_users": n2, "psa_conversions": c2, "psa_rate": p2, "psa_rate_ci_low": ci2[0], "psa_rate_ci_high": ci2[1],
        "difference_pp": (p1 - p2) * 100, "difference_ci_low_pp": diff_lo * 100, "difference_ci_high_pp": diff_hi * 100,
        "relative_lift": p1 / p2 - 1, "relative_lift_ci_low": lift_lo, "relative_lift_ci_high": lift_hi,
        "bootstrap_lift_ci_low": boot_lo, "bootstrap_lift_ci_high": boot_hi,
        "z_score": z, "p_value": p_value, "chi_square": chi2, "chi_square_p_value": chi2_p,
        "significant": p_value < alpha,
        "minimum_detectable_lift": minimum_detectable_lift(n1, n2, p2, alpha, power),
        "power_achieved": power_achieved(c1, n1, c2, n2, alpha),
    }
