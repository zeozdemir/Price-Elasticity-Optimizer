"""
optimizer.py
Microeconomic Price & Profit Optimization Engine.

Addresses the theoretical flaw of constant-elasticity revenue monotonicity:
1. Log-Quadratic Demand Model: ln(Q) = b0 + b1*ln(P) + b2*(ln(P))^2
   Yields an endogenous interior revenue peak when b2 < 0:
   P*_revenue = exp(-(1 + b1) / (2 * b2))

2. Microeconomic Profit Maximization with Marginal Cost c:
   pi(P) = (P - c) * Q(P)
   Under constant elasticity |b| > 1, optimal price follows the Lerner Rule:
   P*_profit = c * (|b| / (|b| - 1))
"""

from typing import Dict, Optional
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy import stats


def fit_log_quadratic_demand(sub: pd.DataFrame):
    """
    Fits ln(Q) = b0 + b1*ln(P) + b2*(ln(P))^2 using polynomial regression.
    Returns (b0, b1, b2, r2) or None if underdetermined.
    """
    agg = (
        sub.groupby(pd.qcut(sub["UnitPrice"], q=min(12, sub["UnitPrice"].nunique()), duplicates="drop"), observed=True)
        .agg(Price=("UnitPrice", "median"), Quantity=("Quantity", "mean"))
        .dropna()
    )
    if len(agg) < 4:
        # Fallback to direct price points
        agg = (
            sub.groupby("UnitPrice")
            .agg(Price=("UnitPrice", "first"), Quantity=("Quantity", "mean"))
            .reset_index(drop=True)
        )

    if len(agg) < 4:
        return None

    lp = np.log(agg["Price"].values.astype(float))
    lq = np.log(agg["Quantity"].values.astype(float))
    mask = np.isfinite(lp) & np.isfinite(lq) & (agg["Quantity"].values > 0)

    if mask.sum() < 4:
        return None

    x = lp[mask]
    y = lq[mask]

    # Degree 2 polynomial: y = b2*x^2 + b1*x + b0
    coeffs = np.polyfit(x, y, deg=2)
    b2, b1, b0 = float(coeffs[0]), float(coeffs[1]), float(coeffs[2])

    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return b0, b1, b2, float(r2)


def optimize_revenue(
    df: pd.DataFrame,
    product: str,
    cost_margin: float = 0.65,
    custom_cost: Optional[float] = None
) -> dict:
    """
    Computes both Revenue-Maximizing and Profit-Maximizing optimal prices.
    
    Parameters
    ----------
    df : pd.DataFrame
        Cleaned transaction dataframe.
    product : str
        Product description.
    cost_margin : float
        Assumed cost as a fraction of current average price (default 0.65 -> 35% gross margin).
    custom_cost : float, optional
        Explicit unit cost if provided by user.
    """
    sub = df[df["Description"] == product].copy()
    if len(sub) < 5 or sub["UnitPrice"].nunique() < 2:
        return {"error": "Insufficient transaction records or price variation for optimization."}

    current_avg_price = float(sub["UnitPrice"].mean())
    current_avg_qty = float(sub["Quantity"].mean())
    unit_cost = float(custom_cost) if custom_cost is not None and custom_cost > 0 else current_avg_price * cost_margin

    p_min = max(0.05, float(sub["UnitPrice"].quantile(0.02)))
    p_max = float(sub["UnitPrice"].quantile(0.98)) * 2.0

    # 1. Fit Log-Quadratic Model
    quad_res = fit_log_quadratic_demand(sub)
    log_linear_slope, log_linear_intercept = None, None

    # Fit standard log-linear for comparison & Lerner rule
    try:
        lp_all = np.log(sub["UnitPrice"].clip(lower=0.01))
        lq_all = np.log(sub["Quantity"].clip(lower=0.01))
        m = np.isfinite(lp_all) & np.isfinite(lq_all)
        if m.sum() >= 3:
            s, i, r, p_val, se = stats.linregress(lp_all[m], lq_all[m])
            log_linear_slope = float(s)
            log_linear_intercept = float(i)
    except Exception:
        pass

    has_interior_peak = False
    revenue_optimal_price = current_avg_price
    model_type = "Log-Quadratic Dynamic Elasticity"

    if quad_res is not None:
        b0, b1, b2, quad_r2 = quad_res
        # ln(R) = b0 + (1 + b1)*ln(P) + b2*(ln(P))^2
        # d ln(R)/d ln(P) = 1 + b1 + 2*b2*ln(P) = 0 => ln(P*) = -(1 + b1) / (2*b2)
        if b2 < 0:
            ln_p_star = -(1.0 + b1) / (2.0 * b2)
            p_star = np.exp(ln_p_star)
            if p_min <= p_star <= p_max:
                revenue_optimal_price = float(p_star)
                has_interior_peak = True

    # 2. Profit Maximization via Lerner markup rule or bounded search
    # Profit Pi(P) = (P - c) * Q(P)
    def demand_est(p):
        if quad_res is not None and quad_res[2] < 0:
            b0_q, b1_q, b2_q, _ = quad_res
            lp = np.log(max(p, 0.01))
            return np.exp(b0_q + b1_q * lp + b2_q * (lp ** 2))
        elif log_linear_slope is not None and log_linear_intercept is not None:
            return np.exp(log_linear_intercept) * (max(p, 0.01) ** log_linear_slope)
        else:
            return current_avg_qty

    def neg_profit(p):
        if p <= unit_cost:
            return 1e9
        q = demand_est(p)
        if not np.isfinite(q) or q <= 0:
            return 1e9
        return -((p - unit_cost) * q)

    profit_search = minimize_scalar(
        neg_profit,
        bounds=(unit_cost * 1.05, max(p_max, unit_cost * 3)),
        method="bounded"
    )
    profit_optimal_price = float(profit_search.x) if profit_search.success else unit_cost * 1.35

    # If log-quadratic didn't find interior peak, choose profit optimal or bounded max
    if not has_interior_peak:
        model_type = "Lerner Profit Rule (c = {:.2f})".format(unit_cost)
        revenue_optimal_price = profit_optimal_price

    # Baseline vs Optimized comparisons
    base_qty = demand_est(current_avg_price)
    base_rev = current_avg_price * base_qty
    base_profit = max(0.0, (current_avg_price - unit_cost) * base_qty)

    opt_qty = demand_est(revenue_optimal_price)
    opt_rev = revenue_optimal_price * opt_qty
    opt_profit = max(0.0, (revenue_optimal_price - unit_cost) * opt_qty)

    rev_boost = round(((opt_rev - base_rev) / base_rev * 100), 2) if base_rev > 0 else 0.0
    profit_boost = round(((opt_profit - base_profit) / base_profit * 100), 2) if base_profit > 0 else 0.0

    # Curve points for interactive Plotly visualization
    prices_grid = np.linspace(p_min, p_max, 100)
    curve_data = []
    for p in prices_grid:
        q = demand_est(p)
        r = p * q
        pi = max(0.0, (p - unit_cost) * q)
        curve_data.append({
            "price": round(float(p), 2),
            "demand": round(float(q), 1),
            "revenue": round(float(r), 2),
            "profit": round(float(pi), 2)
        })

    return {
        "product": product,
        "optimal_price": round(revenue_optimal_price, 2),
        "profit_optimal_price": round(profit_optimal_price, 2),
        "current_avg_price": round(current_avg_price, 2),
        "unit_cost": round(unit_cost, 2),
        "has_interior_peak": has_interior_peak,
        "model_type": model_type,
        "revenue_increase_pct": rev_boost,
        "profit_increase_pct": profit_boost,
        "expected_revenue": round(opt_rev, 2),
        "expected_profit": round(opt_profit, 2),
        "curve_data": curve_data,
        "methodology_note": (
            "Optimized via Log-Quadratic Demand concave peak" if has_interior_peak
            else "Optimized via Microeconomic Lerner Markup with assumed unit cost c = {:.2f}".format(unit_cost)
        )
    }


def simulate_price(df: pd.DataFrame, product: str, target_price: float, unit_cost: Optional[float] = None) -> dict:
    """Simulate revenue and profit for an arbitrary price point."""
    opt_result = optimize_revenue(df, product, custom_cost=unit_cost)
    if "error" in opt_result:
        return opt_result

    # Evaluate demand at target price using the curve data
    curve = opt_result["curve_data"]
    if not curve:
        return {"error": "Could not evaluate demand."}

    # Interpolate
    prices = [c["price"] for c in curve]
    demands = [c["demand"] for c in curve]
    target_p = float(target_price)

    est_qty = float(np.interp(target_p, prices, demands))
    est_rev = target_p * est_qty
    cost = opt_result["unit_cost"]
    est_profit = max(0.0, (target_p - cost) * est_qty)

    max_rev = opt_result["expected_revenue"]
    vs_opt_pct = round(((est_rev - max_rev) / max_rev * 100), 2) if max_rev > 0 else 0.0

    return {
        "product": product,
        "simulated_price": round(target_p, 2),
        "estimated_quantity": round(est_qty, 1),
        "estimated_revenue": round(est_rev, 2),
        "estimated_profit": round(est_profit, 2),
        "optimal_price": opt_result["optimal_price"],
        "vs_optimal_pct": vs_opt_pct
    }
