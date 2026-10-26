"""
tests/test_elasticity.py
Unit and econometric validation tests for price elasticity estimation.
"""

import numpy as np
import pandas as pd
import pytest
from models.elasticity import estimate_product_elasticity, calculate_elasticity


def test_elasticity_recovery_on_synthetic_data():
    """
    Verify that OLS accurately recovers a known true elasticity coefficient
    from generated constant-elasticity data: ln(Q) = 5.0 - 1.5 * ln(P)
    """
    np.random.seed(42)
    true_elasticity = -1.5
    true_intercept = 5.0

    prices = np.repeat([10.0, 15.0, 20.0, 25.0, 30.0, 40.0], 30)
    log_q = true_intercept + true_elasticity * np.log(prices) + np.random.normal(0, 0.05, len(prices))
    quantities = np.exp(log_q)

    df = pd.DataFrame({
        "Description": ["Synthetic Widget"] * len(prices),
        "UnitPrice": prices,
        "Quantity": quantities
    })

    result = estimate_product_elasticity(df, "Synthetic Widget")
    assert result is not None
    # Estimated elasticity should be within 0.1 of true -1.5
    assert pytest.approx(result["elasticity"], abs=0.1) == true_elasticity
    assert result["classification"] == "Elastic"
    assert result["r_squared"] > 0.85
    assert result["p_value"] < 0.001
    assert result["reliability_badge"] == "reliable"
    # True elasticity must fall within the 95% confidence interval
    assert result["ci_lower"] <= true_elasticity <= result["ci_upper"]


def test_positive_elasticity_flagged_as_anomalous():
    """Verify that products with upward-sloping demand are flagged as confounded/anomalous."""
    prices = np.repeat([10.0, 20.0, 30.0, 40.0], 20)
    quantities = prices * 2.0  # Quantity increases with price

    df = pd.DataFrame({
        "Description": ["Luxury Good"] * len(prices),
        "UnitPrice": prices,
        "Quantity": quantities
    })

    result = estimate_product_elasticity(df, "Luxury Good")
    assert result is not None
    assert result["elasticity"] > 0
    assert "Positive Response" in result["classification"]
    assert result["reliability_badge"] == "caution"


def test_insufficient_data_returns_none():
    """Products with less than minimum required observations return None safely."""
    df = pd.DataFrame({
        "Description": ["Rare Item", "Rare Item"],
        "UnitPrice": [10.0, 10.0],
        "Quantity": [1, 2]
    })
    result = estimate_product_elasticity(df, "Rare Item")
    assert result is None
