"""
supply_demand.py
Market Clearing Price Simulation (Assumed Benchmark Supply).

In transactional retail data, supply schedules and supplier marginal costs
are unobserved (only equilibrium transaction points are recorded).
This module models a stylized short-run supply curve with an assumed
benchmark price elasticity of supply (epsilon_s = 0.8) calibrated to
historical volume, explicitly labeled as a simulation assumption.
"""

from typing import Dict
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy import stats


def supply_demand_equilibrium(df: pd.DataFrame, product: str) -> dict:
    """
    Fits empirical demand and pairs it with a stylized calibrated supply curve
    for comparative clearing price simulation.
    """
    sub = df[df["Description"] == product].copy()
    if len(sub) < 5 or sub["UnitPrice"].nunique() < 2:
        return {"error": "Insufficient data for supply-demand simulation."}

    lp = np.log(sub["UnitPrice"].clip(lower=0.01))
    lq = np.log(sub["Quantity"].clip(lower=0.01))
    mask = np.isfinite(lp) & np.isfinite(lq)
    if mask.sum() < 3:
        return {"error": "Could not fit empirical demand."}

    slope, intercept, r_val, p_val, _ = stats.linregress(lp[mask], lq[mask])

    # If demand slope is non-negative, demand curve doesn't downward-slope
    if slope >= 0:
        slope = -0.5  # standard mild elasticity fallback for clearing simulation

    mean_price = float(sub["UnitPrice"].mean())
    mean_qty = float(sub["Quantity"].mean())

    supply_elasticity = 0.8  # assumed typical manufacturing/distributor elasticity
    # Calibrate supply scaling at mean price
    c_supply = mean_qty / (mean_price ** supply_elasticity)

    def demand_fn(p):
        return np.exp(intercept) * (max(p, 0.01) ** slope)

    def supply_fn(p):
        return c_supply * (max(p, 0.01) ** supply_elasticity)

    def excess_demand(p):
        return supply_fn(p) - demand_fn(p)

    p_lo = max(0.01, mean_price * 0.1)
    p_hi = mean_price * 4.0

    try:
        eq_price = brentq(excess_demand, p_lo, p_hi, maxiter=100)
    except Exception:
        eq_price = mean_price

    eq_qty = float(demand_fn(eq_price))

    # Grid for Plotly plotting
    prices = np.linspace(p_lo, p_hi, 50)
    demand_curve = [round(float(demand_fn(p)), 2) for p in prices]
    supply_curve = [round(float(supply_fn(p)), 2) for p in prices]

    return {
        "product": product,
        "is_assumption_based": True,
        "disclaimer": "Supply curve is an econometric benchmark simulation (assumed supply elasticity epsilon_s = 0.8).",
        "equilibrium_price": round(float(eq_price), 2),
        "equilibrium_quantity": round(float(eq_qty), 1),
        "mean_historical_price": round(mean_price, 2),
        "prices": [round(float(p), 2) for p in prices],
        "demand_curve": demand_curve,
        "supply_curve": supply_curve,
    }
