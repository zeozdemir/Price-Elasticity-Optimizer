"""
tests/test_optimizer.py
Unit tests for economic price & profit optimization.
"""

import numpy as np
import pandas as pd
import pytest
from models.optimizer import optimize_revenue, simulate_price, fit_log_quadratic_demand


def test_log_quadratic_interior_peak():
    """
    Test that log-quadratic demand finds a true interior peak:
    ln(Q) = 6.0 + 1.0 * ln(P) - 0.8 * (ln(P))^2
    Theoretical revenue peak:
    ln(P*) = -(1 + 1.0) / (2 * -0.8) = 2.0 / 1.6 = 1.25 => P* = exp(1.25) ≈ 3.49
    """
    prices = np.linspace(1.5, 8.0, 50)
    lp = np.log(prices)
    lq = 6.0 + 1.0 * lp - 0.8 * (lp ** 2)
    qty = np.exp(lq)

    df = pd.DataFrame({
        "Description": ["Concave Widget"] * len(prices),
        "UnitPrice": prices,
        "Quantity": qty
    })

    result = optimize_revenue(df, "Concave Widget")
    assert "error" not in result
    assert result["has_interior_peak"] is True

    theoretical_p = float(np.exp(1.25))
    # Optimized price must match theoretical peak within reasonable precision
    assert pytest.approx(result["optimal_price"], abs=0.4) == theoretical_p
    assert result["optimal_price"] > 1.5
    assert result["optimal_price"] < 8.0


def test_profit_maximization_lerner_rule():
    """
    Verify profit maximization respects the marginal cost lower bound:
    Optimal profit price must always be strictly greater than unit marginal cost.
    """
    prices = [10.0, 15.0, 20.0, 25.0, 30.0] * 10
    quantities = [100.0, 70.0, 45.0, 30.0, 20.0] * 10

    df = pd.DataFrame({
        "Description": ["Retail Product"] * len(prices),
        "UnitPrice": prices,
        "Quantity": quantities
    })

    unit_cost = 8.0
    result = optimize_revenue(df, "Retail Product", custom_cost=unit_cost)

    assert "error" not in result
    assert result["profit_optimal_price"] > unit_cost
    assert result["unit_cost"] == unit_cost


def test_price_simulator_interpolation():
    """Simulate price at current and optimal points."""
    prices = [10.0, 20.0, 30.0] * 10
    quantities = [100.0, 50.0, 25.0] * 10

    df = pd.DataFrame({
        "Description": ["Sim Item"] * len(prices),
        "UnitPrice": prices,
        "Quantity": quantities
    })

    sim = simulate_price(df, "Sim Item", target_price=20.0)
    assert "error" not in sim
    assert sim["simulated_price"] == 20.0
    assert sim["estimated_quantity"] > 0
    assert sim["estimated_revenue"] > 0
