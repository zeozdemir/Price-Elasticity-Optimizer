"""
elasticity.py
Econometric Price Elasticity of Demand (PED) Estimation.
Implements OLS log-log regression with statistical inference:
standard errors, t-statistics, p-values, 95% confidence intervals,
and empirical reliability diagnostics.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from scipy import stats


def estimate_product_elasticity(df: pd.DataFrame, product: str) -> Optional[dict]:
    """
    Estimate log-log elasticity for a single product with full statistical diagnostics.
    Model: ln(Quantity) = alpha + beta * ln(UnitPrice) + epsilon
    """
    sub = df[df["Description"] == product].copy()
    if len(sub) < 5 or sub["UnitPrice"].nunique() < 2:
        return None

    # Aggregate by distinct price points (or granular bins) to prevent high-frequency noise
    n_unique_prices = sub["UnitPrice"].nunique()
    if n_unique_prices > 15:
        # Quantile or equal-width binning
        bins = min(15, n_unique_prices)
        try:
            sub["PriceGroup"] = pd.qcut(sub["UnitPrice"], q=bins, duplicates="drop")
            agg = (
                sub.groupby("PriceGroup", observed=True)
                .agg(Price=("UnitPrice", "median"), Quantity=("Quantity", "mean"), Weight=("Quantity", "count"))
                .dropna()
            )
        except Exception:
            agg = (
                sub.groupby("UnitPrice")
                .agg(Price=("UnitPrice", "first"), Quantity=("Quantity", "mean"), Weight=("Quantity", "count"))
                .reset_index(drop=True)
            )
    else:
        agg = (
            sub.groupby("UnitPrice")
            .agg(Price=("UnitPrice", "first"), Quantity=("Quantity", "mean"), Weight=("Quantity", "count"))
            .reset_index(drop=True)
        )

    if len(agg) < 3:
        return None

    log_p = np.log(agg["Price"].values.astype(float))
    log_q = np.log(agg["Quantity"].values.astype(float))

    valid_mask = np.isfinite(log_p) & np.isfinite(log_q) & (agg["Quantity"].values > 0)
    if valid_mask.sum() < 3:
        return None

    x = log_p[valid_mask]
    y = log_q[valid_mask]
    n = len(x)

    # OLS estimation
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    r_squared = float(r_value ** 2)

    # 95% Confidence Interval for elasticity (t-distribution with n-2 d.o.f.)
    dof = max(1, n - 2)
    t_crit = stats.t.ppf(0.975, dof)
    ci_lower = slope - t_crit * std_err
    ci_upper = slope + t_crit * std_err

    # Economic Classification
    if slope > 0:
        classification = "Positive Response (Anomalous / Confounded)"
    elif abs(slope) < 0.9:
        classification = "Inelastic"
    elif abs(slope) <= 1.1:
        classification = "Unit Elastic"
    else:
        classification = "Elastic"

    # Statistical Reliability Assessment
    if p_value >= 0.05:
        reliability = "Insignificant (p >= 0.05)"
        reliability_badge = "unreliable"
    elif r_squared < 0.20:
        reliability = "Low Explanatory Power (R² < 0.20)"
        reliability_badge = "caution"
    elif slope > 0:
        reliability = "Confounded / Non-standard (Slope > 0)"
        reliability_badge = "caution"
    else:
        reliability = "Reliable Model (p < 0.05, R² >= 0.20)"
        reliability_badge = "reliable"

    # Scatter points for client-side rendering
    scatter_points = [
        {"price": round(float(p), 2), "qty": round(float(q), 1), "count": int(w)}
        for p, q, w in zip(agg["Price"], agg["Quantity"], agg["Weight"])
    ]

    # Fitted line points
    x_line = np.linspace(min(x), max(x), 50)
    line_p = np.exp(x_line)
    line_q = np.exp(intercept + slope * x_line)

    return {
        "product": product,
        "elasticity": round(float(slope), 3),
        "ci_lower": round(float(ci_lower), 3),
        "ci_upper": round(float(ci_upper), 3),
        "p_value": float(f"{p_value:.4e}"),
        "std_err": round(float(std_err), 3),
        "r_squared": round(float(r_squared), 3),
        "n_points": int(n),
        "intercept": round(float(intercept), 3),
        "classification": classification,
        "reliability": reliability,
        "reliability_badge": reliability_badge,
        "scatter_points": scatter_points,
        "fitted_line": [{"price": round(float(p), 2), "qty": round(float(q), 2)} for p, q in zip(line_p, line_q)],
    }


def calculate_elasticity(df: pd.DataFrame, products: List[str]) -> Dict[str, dict]:
    """Calculate elasticity with diagnostics across a list of products."""
    results = {}
    for prod in products:
        res = estimate_product_elasticity(df, prod)
        if res is not None:
            results[prod] = res
    return results
