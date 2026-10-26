"""
plot_generator.py
Generate and save all dashboard plots as PNG files (Clean Light Amethyst theme).
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats

PLOT_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "plots")

# Clean Light Amethyst Brand Colours
AMETHYST    = "#7C3AED"   # Asil kurumsal ametist
AMETHYST_LT = "#A78BFA"   # Açık wisteria
TEAL        = "#0D9488"   # Kurumsal teal
GOLD        = "#D97706"   # Vurgulu altın
GREEN       = "#16A34A"   # Pozitif yeşil
RED         = "#DC2626"   # Negatif kırmızı
TEXT_DARK   = "#0F172A"   # Koyu başlık
TEXT_MUTED  = "#475569"   # Eksen metni
BORDER_COLOR= "#E2E8F0"   # Çerçeve rengi
BG_CARD     = "#FFFFFF"   # Kart zemini
BG_AXES     = "#F8FAFC"   # Grafik içi hafif gri

plt.style.use("default")

def _save(fig, filename):
    path = os.path.join(PLOT_DIR, filename)
    fig.savefig(path, bbox_inches="tight", dpi=110, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"[plot_generator] Saved {filename}")


# ── Plot 1: Price vs Demand scatter + regression ─────────────────────────────
def plot_price_vs_demand(df: pd.DataFrame, top_products: list):
    sub = df[df["Description"].isin(top_products[:5])].copy()
    sub = sub.sample(min(5000, len(sub)), random_state=42)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.patch.set_facecolor(BG_CARD)
    ax.set_facecolor(BG_AXES)

    colors = [AMETHYST, TEAL, GOLD, "#EC4899", GREEN]
    for i, prod in enumerate(top_products[:5]):
        grp = sub[sub["Description"] == prod]
        if grp.empty:
            continue
        ax.scatter(
            grp["UnitPrice"], grp["Quantity"],
            alpha=0.45, s=22, color=colors[i % len(colors)],
            label=prod[:28],
        )
        # Regression line
        lp = np.log(grp["UnitPrice"].clip(lower=0.01))
        lq = np.log(grp["Quantity"].clip(lower=0.01))
        mask = np.isfinite(lp) & np.isfinite(lq)
        if mask.sum() > 2:
            slope, intercept, *_ = stats.linregress(lp[mask], lq[mask])
            px = np.linspace(grp["UnitPrice"].min(), grp["UnitPrice"].max(), 100)
            py = np.exp(intercept) * px ** slope
            ax.plot(px, py, color=colors[i % len(colors)], linewidth=2, alpha=0.95)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Unit Price (log scale, £)", color=TEXT_MUTED, fontsize=10, fontweight="600")
    ax.set_ylabel("Quantity (log scale)", color=TEXT_MUTED, fontsize=10, fontweight="600")
    ax.set_title("Price vs Demand — Top 5 Products", color=TEXT_DARK, fontsize=12, fontweight="700", pad=12)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    ax.spines[:].set_color(BORDER_COLOR)
    ax.legend(fontsize=8, facecolor=BG_CARD, edgecolor=BORDER_COLOR, labelcolor=TEXT_DARK, framealpha=0.95)
    ax.grid(True, alpha=0.6, color=BORDER_COLOR, linestyle="--")
    plt.tight_layout()
    _save(fig, "plot1_price_vs_demand.png")


# ── Plot 2: Revenue curve R(P) ────────────────────────────────────────────────
def plot_revenue_curve(df: pd.DataFrame, top_products: list):
    product = top_products[0]
    sub = df[df["Description"] == product].copy()

    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.patch.set_facecolor(BG_CARD)
    ax.set_facecolor(BG_AXES)

    agg = (
        sub.groupby(
            pd.cut(sub["UnitPrice"], bins=min(10, max(3, sub["UnitPrice"].nunique()))),
            observed=True,
        )
        .agg(AvgPrice=("UnitPrice", "mean"), AvgQty=("Quantity", "mean"))
        .dropna()
    )

    if len(agg) >= 3:
        lp = np.log(agg["AvgPrice"].values.astype(float))
        lq = np.log(agg["AvgQty"].values.astype(float))
        mask = np.isfinite(lp) & np.isfinite(lq)
        if mask.sum() >= 3:
            slope, intercept, *_ = stats.linregress(lp[mask], lq[mask])
            p_min = float(sub["UnitPrice"].quantile(0.05)) or 0.01
            p_max = float(sub["UnitPrice"].quantile(0.95)) * 2

            prices = np.linspace(p_min, p_max, 300)
            revenues = prices * np.exp(intercept) * prices ** slope

            ax.plot(prices, revenues, color=AMETHYST, linewidth=3, label="Revenue Curve R(P)")
            ax.fill_between(prices, revenues, alpha=0.12, color=AMETHYST)

            opt_idx = np.argmax(revenues)
            opt_p = prices[opt_idx]
            opt_r = revenues[opt_idx]
            ax.axvline(opt_p, color=GOLD, linestyle="--", linewidth=1.8, label=f"Optimal Price £{opt_p:.2f}")
            ax.scatter([opt_p], [opt_r], color=GOLD, s=110, zorder=5)
            ax.annotate(
                f"Optimal P* = £{opt_p:.2f}\nMax Rev = £{opt_r:,.0f}",
                xy=(opt_p, opt_r), xytext=(opt_p * 1.12, opt_r * 0.92),
                color=TEXT_DARK, fontsize=9, fontweight="700",
                bbox=dict(boxstyle="round,pad=0.4", fc=BG_CARD, ec=BORDER_COLOR, alpha=0.9),
                arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.5),
            )

    ax.set_xlabel("Unit Price (£)", color=TEXT_MUTED, fontsize=10, fontweight="600")
    ax.set_ylabel("Estimated Total Revenue (£)", color=TEXT_MUTED, fontsize=10, fontweight="600")
    ax.set_title(f"Revenue Curve — {product[:38]}", color=TEXT_DARK, fontsize=12, fontweight="700", pad=12)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    ax.spines[:].set_color(BORDER_COLOR)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"£{x:,.0f}"))
    ax.legend(facecolor=BG_CARD, edgecolor=BORDER_COLOR, labelcolor=TEXT_DARK, fontsize=8.5)
    ax.grid(True, alpha=0.6, color=BORDER_COLOR, linestyle="--")
    plt.tight_layout()
    _save(fig, "plot2_revenue_curve.png")


# ── Plot 3: Elasticity bar chart ──────────────────────────────────────────────
def plot_elasticity_bar(elasticity_results: dict):
    if not elasticity_results:
        return

    products = list(elasticity_results.keys())[:10]
    values   = [elasticity_results[p]["elasticity"] for p in products]
    colors   = [RED if abs(v) > 1 else TEAL for v in values]
    labels   = [p[:28] for p in products]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.patch.set_facecolor(BG_CARD)
    ax.set_facecolor(BG_AXES)

    bars = ax.barh(labels, values, color=colors, alpha=0.88, edgecolor=BORDER_COLOR, height=0.65)
    ax.axvline(0, color=TEXT_MUTED, linewidth=1, alpha=0.6)
    ax.axvline(-1, color=GOLD, linewidth=1.5, linestyle="--", label="|Ed|=1 Elasticity Threshold")
    ax.axvline(1, color=GOLD, linewidth=1.5, linestyle="--")

    for bar, val in zip(bars, values):
        ax.text(
            val + (0.06 if val >= 0 else -0.06),
            bar.get_y() + bar.get_height() / 2,
            f"{val:.2f}",
            va="center", ha="left" if val >= 0 else "right",
            color=TEXT_DARK, fontsize=8.5, fontweight="600",
        )

    ax.set_xlabel("Price Elasticity Coefficient (Ed)", color=TEXT_MUTED, fontsize=10, fontweight="600")
    ax.set_title("Price Elasticity of Demand — Top 10 Products", color=TEXT_DARK, fontsize=12, fontweight="700", pad=12)
    ax.tick_params(colors=TEXT_MUTED, labelsize=8.5)
    ax.spines[:].set_color(BORDER_COLOR)
    ax.legend(facecolor=BG_CARD, edgecolor=BORDER_COLOR, labelcolor=TEXT_DARK, fontsize=8.5)
    ax.grid(True, axis="x", alpha=0.6, color=BORDER_COLOR, linestyle="--")
    plt.tight_layout()
    _save(fig, "plot3_elasticity_bar.png")


# ── Plot 4: Supply & Demand curves ───────────────────────────────────────────
def plot_supply_demand(sd_result: dict):
    if "error" in sd_result:
        return

    prices  = sd_result["prices"]
    demand  = sd_result["demand_curve"]
    supply  = sd_result["supply_curve"]
    eq_p    = sd_result["equilibrium_price"]
    eq_q    = sd_result["equilibrium_quantity"]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.patch.set_facecolor(BG_CARD)
    ax.set_facecolor(BG_AXES)

    ax.plot(prices, demand, color=TEAL,     linewidth=2.8, label="Demand Curve D(P)")
    ax.plot(prices, supply, color=AMETHYST, linewidth=2.8, label="Supply Curve S(P)")
    ax.axvline(eq_p, color=GOLD, linestyle="--", linewidth=1.6, label=f"Equilibrium Price £{eq_p:.2f}")
    ax.axhline(eq_q, color=GOLD, linestyle=":",  linewidth=1.2, alpha=0.7)
    ax.scatter([eq_p], [eq_q], color=GOLD, s=120, zorder=5)
    ax.annotate(
        f"Equilibrium\n(£{eq_p:.2f}, {eq_q:.0f} units)",
        xy=(eq_p, eq_q), xytext=(eq_p * 1.08, eq_q * 1.18),
        color=TEXT_DARK, fontsize=9, fontweight="700",
        bbox=dict(boxstyle="round,pad=0.4", fc=BG_CARD, ec=BORDER_COLOR, alpha=0.9),
        arrowprops=dict(arrowstyle="->", color=GOLD, lw=1.5),
    )

    ax.set_xlabel("Price (£)", color=TEXT_MUTED, fontsize=10, fontweight="600")
    ax.set_ylabel("Quantity", color=TEXT_MUTED, fontsize=10, fontweight="600")
    ax.set_title(f"Supply & Demand Equilibrium — {sd_result.get('product','')[:38]}", color=TEXT_DARK, fontsize=12, fontweight="700", pad=12)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    ax.spines[:].set_color(BORDER_COLOR)
    ax.legend(facecolor=BG_CARD, edgecolor=BORDER_COLOR, labelcolor=TEXT_DARK, fontsize=8.5)
    ax.grid(True, alpha=0.6, color=BORDER_COLOR, linestyle="--")
    plt.tight_layout()
    _save(fig, "plot4_supply_demand.png")


# ── Plot 5: Monthly revenue time series ──────────────────────────────────────
def plot_time_series(df: pd.DataFrame):
    monthly = (
        df.groupby("YearMonth")["Revenue"]
        .sum()
        .reset_index()
        .sort_values("YearMonth")
    )

    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.patch.set_facecolor(BG_CARD)
    ax.set_facecolor(BG_AXES)

    ax.plot(monthly["YearMonth"], monthly["Revenue"], color=AMETHYST, linewidth=2.8, marker="o", markersize=5, label="Monthly Revenue")
    ax.fill_between(monthly["YearMonth"], monthly["Revenue"], alpha=0.12, color=AMETHYST)

    step = max(1, len(monthly) // 8)
    ax.set_xticks(monthly["YearMonth"].values[::step])
    ax.set_xticklabels(monthly["YearMonth"].values[::step], rotation=30, ha="right", color=TEXT_MUTED, fontsize=8.5)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"£{x/1e6:.1f}M"))
    ax.set_xlabel("Month", color=TEXT_MUTED, fontsize=10, fontweight="600")
    ax.set_ylabel("Total Revenue (£)", color=TEXT_MUTED, fontsize=10, fontweight="600")
    ax.set_title("Monthly Revenue Trend", color=TEXT_DARK, fontsize=12, fontweight="700", pad=12)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    ax.spines[:].set_color(BORDER_COLOR)
    ax.grid(True, alpha=0.6, color=BORDER_COLOR, linestyle="--")
    plt.tight_layout()
    _save(fig, "plot5_time_series.png")


# ── Plot 6: Price distribution histogram + KDE ───────────────────────────────
def plot_price_distribution(df: pd.DataFrame):
    prices = df["UnitPrice"].clip(upper=df["UnitPrice"].quantile(0.98))

    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.patch.set_facecolor(BG_CARD)
    ax.set_facecolor(BG_AXES)

    ax.hist(prices, bins=80, color=AMETHYST_LT, alpha=0.55, edgecolor=BORDER_COLOR, density=True)

    from scipy.stats import gaussian_kde
    kde = gaussian_kde(prices.dropna())
    x_range = np.linspace(prices.min(), prices.max(), 300)
    ax.plot(x_range, kde(x_range), color=AMETHYST, linewidth=2.6, label="Kernel Density Estimate (KDE)")

    ax.axvline(prices.mean(),   color=GOLD, linestyle="--", linewidth=1.6, label=f"Mean £{prices.mean():.2f}")
    ax.axvline(prices.median(), color=TEAL, linestyle="--", linewidth=1.6, label=f"Median £{prices.median():.2f}")

    ax.set_xlabel("Unit Price (£)", color=TEXT_MUTED, fontsize=10, fontweight="600")
    ax.set_ylabel("Density", color=TEXT_MUTED, fontsize=10, fontweight="600")
    ax.set_title("Unit Price Distribution & Density", color=TEXT_DARK, fontsize=12, fontweight="700", pad=12)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    ax.spines[:].set_color(BORDER_COLOR)
    ax.legend(facecolor=BG_CARD, edgecolor=BORDER_COLOR, labelcolor=TEXT_DARK, fontsize=8.5)
    ax.grid(True, alpha=0.6, color=BORDER_COLOR, linestyle="--")
    plt.tight_layout()
    _save(fig, "plot6_price_distribution.png")


def generate_all_plots(df: pd.DataFrame, top_products: list, elasticity_results: dict, sd_result: dict):
    """Generate and save all 6 plots."""
    os.makedirs(PLOT_DIR, exist_ok=True)
    print("[plot_generator] Generating clean light plots...")
    plot_price_vs_demand(df, top_products)
    plot_revenue_curve(df, top_products)
    plot_elasticity_bar(elasticity_results)
    plot_supply_demand(sd_result)
    plot_time_series(df)
    plot_price_distribution(df)
    print("[plot_generator] All clean light plots generated.")
