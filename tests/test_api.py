"""
tests/test_api.py
Integration tests for Flask web endpoints.
"""

import pytest
import pandas as pd
from app import app, _update_state


@pytest.fixture
def client():
    app.config["TESTING"] = True
    # Seed minimal in-memory dataset
    df = pd.DataFrame({
        "InvoiceNo": [1001, 1002, 1003, 1004, 1005, 1006],
        "Description": ["Test Cake Stand"] * 6,
        "Quantity": [10, 8, 6, 4, 3, 2],
        "UnitPrice": [2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
        "Country": ["United Kingdom"] * 6,
        "InvoiceDate": pd.to_datetime(["2011-01-01"] * 6),
        "Revenue": [25.0, 24.0, 21.0, 16.0, 13.5, 10.0],
        "YearMonth": ["2011-01"] * 6,
        "Year": [2011] * 6,
        "Month": [1] * 6
    })
    _update_state(df, dataset_name="Test Fixture Dataset", currency="£")
    with app.test_client() as client:
        yield client


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Price Elasticity &amp; Revenue Optimizer" in response.data or b"Price Elasticity & Revenue Optimizer" in response.data


def test_api_summary(client):
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.get_json()
    assert "total_revenue" in data
    assert "top_products" in data
    assert data["currency_symbol"] == "£"


def test_api_elasticity(client):
    response = client.get("/api/elasticity")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)


def test_api_optimize_missing_product(client):
    response = client.get("/api/optimize")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_api_simulate_valid(client):
    response = client.get("/api/simulate?product=Test%20Cake%20Stand&price=3.5")
    assert response.status_code == 200
    data = response.get_json()
    assert data["simulated_price"] == 3.5
    assert "estimated_quantity" in data
    assert "estimated_revenue" in data
