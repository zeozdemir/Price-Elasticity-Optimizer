"""
app.py  –  Price Elasticity & Revenue Optimizer Flask Application
Production-grade backend with econometric modeling, secure uploads,
and dynamic Plotly.js visualization endpoints.
"""

import sys
import os
import io
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from flask import Flask, render_template, jsonify, request
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np

from data.data_loader import load_and_clean, get_top_products
from models.elasticity import calculate_elasticity, estimate_product_elasticity
from models.optimizer import optimize_revenue, simulate_price
from models.supply_demand import supply_demand_equilibrium

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024  # 250 MB
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

# Thread-safe in-memory state
_state = {
    "df": None,
    "top_products": [],
    "elasticity": {},
    "summary": {},
    "dataset_name": "Bundled Retail Sample",
    "currency_symbol": "£",
}


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _update_state(df: pd.DataFrame, dataset_name: str = "Active Dataset", currency: str = "£"):
    """Update global dataset state and precompute summary and elasticity diagnostics."""
    _state["df"] = df
    _state["dataset_name"] = dataset_name
    _state["currency_symbol"] = currency

    top_prods = get_top_products(df, n=20)
    _state["top_products"] = top_prods

    elasticity_map = calculate_elasticity(df, top_prods)
    _state["elasticity"] = elasticity_map

    total_rev = float(df["Revenue"].sum())
    total_tx = int(df["InvoiceNo"].nunique()) if "InvoiceNo" in df.columns else len(df)
    avg_price = float(df["UnitPrice"].mean())
    date_min = str(df["InvoiceDate"].min())[:10] if "InvoiceDate" in df.columns else "N/A"
    date_max = str(df["InvoiceDate"].max())[:10] if "InvoiceDate" in df.columns else "N/A"

    top_country = "Global"
    if "Country" in df.columns:
        top_country = str(df.groupby("Country")["Revenue"].sum().idxmax())

    # Calculate valid elasticity average
    valid_e = [
        abs(item["elasticity"])
        for item in elasticity_map.values()
        if isinstance(item.get("elasticity"), (int, float)) and item.get("reliability_badge") == "reliable"
    ]
    avg_e = round(float(np.mean(valid_e)), 2) if valid_e else None

    # Best reliable revenue boost
    top_prod = top_prods[0] if top_prods else None
    best_boost = 0.0
    for p in top_prods[:5]:
        opt = optimize_revenue(df, p)
        if "error" not in opt and opt.get("revenue_increase_pct", 0) > best_boost:
            best_boost = opt["revenue_increase_pct"]

    _state["summary"] = {
        "dataset_name": dataset_name,
        "total_revenue": round(total_rev, 2),
        "total_transactions": total_tx,
        "avg_price": round(avg_price, 2),
        "date_range": f"{date_min} to {date_max}",
        "top_country": top_country,
        "top_product": top_prod if top_prod else "N/A",
        "best_revenue_boost_pct": round(best_boost, 1),
        "avg_elasticity": avg_e,
        "top_products": top_prods,
        "total_rows": len(df),
        "currency_symbol": currency,
    }


def _startup():
    """Load default dataset cleanly on server launch."""
    print("[app] Initializing Price Elasticity & Revenue Optimizer engine...")
    try:
        df = load_and_clean()
        _update_state(df, dataset_name="Online Retail Dataset (Verified)", currency="£")
        print(f"[app] Engine initialized successfully with {len(df):,} transactions.")
    except Exception as e:
        print(f"[app] Startup warning: Could not load initial data: {e}")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template(
        "index.html",
        top_products=_state["top_products"],
        summary=_state["summary"],
        currency=_state["currency_symbol"],
    )


@app.route("/api/summary")
def api_summary():
    return jsonify(_state["summary"])


@app.route("/api/elasticity")
def api_elasticity():
    return jsonify(_state["elasticity"])


@app.route("/api/product_diagnostics")
def api_product_diagnostics():
    product = request.args.get("product", "")
    df = _state["df"]
    if df is None:
        return jsonify({"error": "No dataset loaded."}), 503
    if not product:
        return jsonify({"error": "Parameter 'product' is required."}), 400

    diag = estimate_product_elasticity(df, product)
    if diag is None:
        return jsonify({"error": f"Insufficient data for product '{product}'"}), 404
    return jsonify(diag)


@app.route("/api/optimize")
def api_optimize():
    product = request.args.get("product", "")
    df = _state["df"]
    if df is None:
        return jsonify({"error": "No dataset loaded."}), 503
    if not product:
        return jsonify({"error": "Parameter 'product' is required."}), 400

    margin_str = request.args.get("cost_margin", "0.65")
    try:
        margin = float(margin_str)
    except ValueError:
        margin = 0.65

    res = optimize_revenue(df, product, cost_margin=margin)
    return jsonify(res)


@app.route("/api/simulate")
def api_simulate():
    product = request.args.get("product", "")
    price_str = request.args.get("price", "")
    df = _state["df"]
    if df is None:
        return jsonify({"error": "No dataset loaded."}), 503
    if not product or not price_str:
        return jsonify({"error": "'product' and 'price' parameters are required."}), 400

    try:
        price = float(price_str)
        if price <= 0:
            return jsonify({"error": "Price must be strictly positive."}), 400
    except ValueError:
        return jsonify({"error": "Invalid price value."}), 400

    res = simulate_price(df, product, price)
    return jsonify(res)


@app.route("/api/supply_demand")
def api_supply_demand():
    product = request.args.get("product", "")
    df = _state["df"]
    if df is None:
        return jsonify({"error": "No dataset loaded."}), 503
    if not product:
        return jsonify({"error": "Parameter 'product' is required."}), 400

    res = supply_demand_equilibrium(df, product)
    return jsonify(res)


@app.route("/api/time_series")
def api_time_series():
    df = _state["df"]
    if df is None or "YearMonth" not in df.columns:
        return jsonify({"error": "No time series data available."}), 503

    monthly = (
        df.groupby("YearMonth")["Revenue"]
        .sum()
        .reset_index()
        .sort_values("YearMonth")
    )
    return jsonify({
        "dates": monthly["YearMonth"].tolist(),
        "revenues": [round(float(r), 2) for r in monthly["Revenue"].tolist()]
    })


@app.route("/api/price_distribution")
def api_price_distribution():
    df = _state["df"]
    if df is None or "UnitPrice" not in df.columns:
        return jsonify({"error": "No price data available."}), 503

    p99 = float(df["UnitPrice"].quantile(0.98))
    prices = df["UnitPrice"].clip(upper=p99).dropna().tolist()

    # Downsample for JSON transfer if large
    if len(prices) > 4000:
        prices = list(np.random.choice(prices, size=4000, replace=False))

    return jsonify({
        "prices": [round(float(p), 2) for p in prices],
        "mean": round(float(df["UnitPrice"].mean()), 2),
        "median": round(float(df["UnitPrice"].median()), 2),
        "p99": round(p99, 2)
    })


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Secure multi-file upload for CSV and Excel files."""
    if "files" not in request.files:
        return jsonify({"error": "No file stream received."}), 400

    files = request.files.getlist("files")
    if not files or len(files) == 0:
        return jsonify({"error": "No files selected."}), 400

    if len(files) > 10:
        return jsonify({"error": "Maximum file batch limit is 10."}), 400

    currency = request.form.get("currency", "£")
    dfs = []
    file_names = []

    for file in files:
        if not file.filename:
            continue
        fname = secure_filename(file.filename)
        ext = os.path.splitext(fname)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": f"Unsupported file type: {fname}. Allowed types: CSV, XLSX, XLS."}), 400

        try:
            content = file.read()
            if ext == ".csv":
                try:
                    df_single = pd.read_csv(io.BytesIO(content), encoding="utf-8", low_memory=False)
                except Exception:
                    df_single = pd.read_csv(io.BytesIO(content), encoding="unicode_escape", low_memory=False)
            else:
                df_single = pd.read_excel(io.BytesIO(content))

            if not df_single.empty:
                dfs.append(df_single)
                file_names.append(fname)
        except Exception as e:
            return jsonify({"error": f"Failed to parse file '{fname}': {str(e)}"}), 400

    if not dfs:
        return jsonify({"error": "No valid data rows found in uploaded files."}), 400

    try:
        from data.data_loader import _clean_dataframe
        combined = pd.concat(dfs, ignore_index=True)
        cleaned = _clean_dataframe(combined)

        if len(cleaned) < 5:
            return jsonify({"error": "Insufficient valid transaction rows (UnitPrice and Quantity must be positive)."}), 400

        label = file_names[0] if len(file_names) == 1 else f"{len(file_names)} Files ({file_names[0]}...)"
        _update_state(cleaned, dataset_name=label, currency=currency)

        return jsonify({
            "success": True,
            "message": f"Successfully loaded and analyzed {len(file_names)} files ({len(cleaned):,} rows).",
            "summary": _state["summary"],
            "top_products": _state["top_products"],
            "currency_symbol": currency
        })
    except Exception as e:
        return jsonify({"error": f"Data cleaning failed: {str(e)}"}), 400


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _startup()
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    app.run(debug=False, port=port, host=host)
