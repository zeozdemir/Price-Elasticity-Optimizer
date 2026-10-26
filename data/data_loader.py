"""
data_loader.py
Portable data loader and cleaner for retail transaction records.
Loads raw files, cleans records, maps columns, and falls back to a verified sample.
"""

import os
import glob
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
RAW_DIR = os.path.join(DATA_DIR, "raw")
SAMPLE_PATH = os.path.join(DATA_DIR, "sample", "sample_retail.csv")
CLEANED_PATH = os.path.join(DATA_DIR, "cleaned_retail.csv")


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names, strip BOM, clean types and remove invalid records."""
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.replace("\ufeff", "", regex=False)
        .str.replace("\u00ef\u00bb\u00bf", "", regex=False)
        .str.encode("ascii", errors="ignore")
        .str.decode("ascii")
        .str.strip()
    )

    # Column name mapping
    col_map = {}
    for col in df.columns:
        norm = col.lower().replace(" ", "").replace("_", "")
        if norm in ["unitprice", "price", "fiyat", "birimfiyat"]:
            col_map[col] = "UnitPrice"
        elif norm in ["quantity", "qty", "miktar", "adet"]:
            col_map[col] = "Quantity"
        elif norm in ["description", "product", "productname", "urun", "urunadi"]:
            col_map[col] = "Description"
        elif norm in ["invoicedate", "date", "tarih", "orderdate"]:
            col_map[col] = "InvoiceDate"
        elif norm in ["country", "ulke"]:
            col_map[col] = "Country"
        elif norm in ["invoiceno", "invoice", "faturno"]:
            col_map[col] = "InvoiceNo"
        elif norm in ["customerid", "customer"]:
            col_map[col] = "CustomerID"

    df = df.rename(columns=col_map)

    if "UnitPrice" not in df.columns or "Quantity" not in df.columns:
        raise ValueError("Dataset must contain identifiable Price and Quantity columns.")

    if "Description" not in df.columns:
        text_cols = df.select_dtypes(include=["object", "string"]).columns
        df["Description"] = df[text_cols[0]] if len(text_cols) > 0 else "Product"

    if "InvoiceDate" not in df.columns:
        df["InvoiceDate"] = pd.Timestamp.now()
    else:
        df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce").fillna(pd.Timestamp.now())

    if "Country" not in df.columns:
        df["Country"] = "Global"

    if "InvoiceNo" not in df.columns:
        df["InvoiceNo"] = np.arange(len(df))

    # Numeric conversion & filter
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df = df.dropna(subset=["UnitPrice", "Quantity", "Description"])
    df = df[(df["UnitPrice"] > 0) & (df["Quantity"] > 0)]

    df["Description"] = df["Description"].astype(str).str.strip()
    df = df[df["Description"] != ""]

    df["Revenue"] = df["UnitPrice"] * df["Quantity"]
    df["Year"] = df["InvoiceDate"].dt.year
    df["Month"] = df["InvoiceDate"].dt.month
    df["YearMonth"] = df["InvoiceDate"].dt.to_period("M").astype(str)

    return df


def load_and_clean() -> pd.DataFrame:
    """
    Load data from available sources in order of priority:
    1. Custom path in DATA_PATH environment variable
    2. Cached cleaned dataset (data/cleaned_retail.csv)
    3. Any raw CSV or Excel files in data/raw/
    4. Bundled fallback sample (data/sample/sample_retail.csv)
    """
    custom_path = os.getenv("DATA_PATH")
    if custom_path and os.path.exists(custom_path):
        print(f"[data_loader] Loading from DATA_PATH: {custom_path}")
        ext = os.path.splitext(custom_path)[1].lower()
        df = pd.read_excel(custom_path) if ext in [".xlsx", ".xls"] else pd.read_csv(custom_path, low_memory=False)
        return _clean_dataframe(df)

    if os.path.exists(CLEANED_PATH):
        try:
            print(f"[data_loader] Loading cached data from: {CLEANED_PATH}")
            df = pd.read_csv(CLEANED_PATH, low_memory=False)
            return _clean_dataframe(df)
        except Exception as e:
            print(f"[data_loader] Cached data read failed ({e}), falling back...")

    # Check raw directory
    raw_files = glob.glob(os.path.join(RAW_DIR, "*.csv")) + glob.glob(os.path.join(RAW_DIR, "*.xlsx"))
    if raw_files:
        print(f"[data_loader] Found {len(raw_files)} files in raw directory: {RAW_DIR}")
        frames = []
        for p in raw_files:
            try:
                ext = os.path.splitext(p)[1].lower()
                f_df = pd.read_excel(p) if ext in [".xlsx", ".xls"] else pd.read_csv(p, encoding="unicode_escape", low_memory=False)
                frames.append(f_df)
            except Exception as e:
                print(f"[data_loader] Could not read {p}: {e}")
        if frames:
            combined = pd.concat(frames, ignore_index=True)
            cleaned = _clean_dataframe(combined)
            cleaned.to_csv(CLEANED_PATH, index=False)
            return cleaned

    # Fallback to bundled sample
    if os.path.exists(SAMPLE_PATH):
        print(f"[data_loader] Loading bundled sample dataset: {SAMPLE_PATH}")
        df = pd.read_csv(SAMPLE_PATH, low_memory=False)
        return _clean_dataframe(df)

    raise FileNotFoundError("No retail data found. Run `python scripts/download_data.py` or place CSV/XLSX into `data/raw/`.")


def get_top_products(df: pd.DataFrame, n: int = 20) -> list:
    """Return top-N products by total revenue with at least 5 price observations."""
    valid_prods = (
        df.groupby("Description")
        .filter(lambda x: len(x) >= 5 and x["UnitPrice"].nunique() >= 2)
    )
    if valid_prods.empty:
        return df["Description"].value_counts().head(n).index.tolist()

    top = (
        valid_prods.groupby("Description")["Revenue"]
        .sum()
        .sort_values(ascending=False)
        .head(n)
        .index.tolist()
    )
    return top
