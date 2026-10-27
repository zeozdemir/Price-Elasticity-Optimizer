# PriceOptix – Price Elasticity & Revenue Optimizer

PriceOptix is a Python-based web application for analyzing price elasticity and exploring revenue and profit optimization using retail transaction data.

The project combines statistical regression, economic pricing models, and interactive visualizations to help users understand how price changes may affect sales and revenue. It also includes a supply-and-demand simulation for exploring market equilibrium under different assumptions.

## Key Features

- **Price Elasticity Analysis:** Estimate price elasticity using log-log regression.
- **Statistical Diagnostics:** Examine coefficient estimates, standard errors, p-values, confidence intervals, and R².
- **Revenue Optimization:** Use a log-quadratic demand model to estimate a revenue-maximizing price.
- **Profit Optimization:** Calculate candidate profit-maximizing prices based on demand elasticity and unit cost.
- **Interactive Dashboard:** Select products, adjust prices, and explore pricing scenarios using Plotly.js.
- **Supply-and-Demand Simulation:** Explore market equilibrium using an assumed supply elasticity.
- **Data Import:** Upload CSV and Excel files for analysis.
- **Automated Testing:** Test the application using pytest.

## Dashboard

The dashboard allows users to explore product-level results, review estimated price elasticity, and compare potential revenue and profit outcomes under different pricing scenarios.

<!-- Add a screenshot of your dashboard to docs/dashboard.png and uncomment the next line. -->
<!-- ![PriceOptix Dashboard](docs/dashboard.png) -->

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Application logic and data analysis |
| Flask | Web application and API |
| Pandas | Data loading and manipulation |
| NumPy | Numerical calculations |
| Statsmodels | Statistical modeling and regression analysis |
| SciPy | Numerical optimization and root finding |
| Plotly.js | Interactive visualizations |
| HTML, CSS, JavaScript | Frontend development |
| pytest | Automated testing |
| Docker | Containerization |
| GitHub Actions | Continuous integration |

## How It Works

The application follows a workflow from data preparation to pricing analysis.

1. **Data Loading:** Import retail transaction data from a CSV or Excel file.
2. **Data Preparation:** Normalize column names and prepare the relevant price and quantity fields.
3. **Elasticity Estimation:** Use regression analysis to estimate the relationship between price and quantity sold.
4. **Model Diagnostics:** Review statistical results and identify estimates that may require further investigation.
5. **Price Optimization:** Explore revenue and profit optimization using the selected demand models.
6. **Visualization:** Examine the results through interactive charts and pricing scenarios.

## Methodology

### 1. Price Elasticity Estimation

Price elasticity of demand measures how responsive the quantity demanded is to a change in price.

PriceOptix uses a log-log regression model:

\[
\ln(Q) = \beta_0 + \beta_1\ln(P) + \varepsilon
\]

Where:

- \(Q\) is the quantity sold.
- \(P\) is the product price.
- \(\beta_0\) is the intercept.
- \(\beta_1\) is the estimated price elasticity in this model.
- \(\varepsilon\) is the error term.

The coefficient \(\beta_1\) represents the estimated percentage change in quantity associated with a 1% change in price, within the fitted model.

The application also reports standard errors, t-statistics, p-values, 95% confidence intervals, and R² to help users assess the regression results.

### 2. Revenue Optimization

Revenue is calculated as:

\[
R(P) = P \cdot Q(P)
\]

Under a constant-elasticity demand model:

\[
Q(P) = AP^\beta
\]

Revenue becomes:

\[
R(P) = AP^{1+\beta}
\]

This model does not generally produce a unique interior revenue-maximizing price. Instead, revenue is monotonic in price when \(\beta \neq -1\), assuming the model applies across the price range being considered.

To explore an interior revenue maximum, PriceOptix also uses a log-quadratic demand model:

\[
\ln(Q) = \beta_0 + \beta_1\ln(P) + \beta_2(\ln(P))^2
\]

The corresponding candidate revenue-maximizing price is:

\[
P^* = \exp\left(-\frac{1+\beta_1}{2\beta_2}\right)
\]

An interior maximum exists when \(\beta_2 < 0\), provided the model is appropriate and the resulting price lies within a meaningful range.

### 3. Profit Optimization

Revenue and profit are different objectives. A price that maximizes revenue does not necessarily maximize profit.

The profit function is:

\[
\Pi(P) = (P-c)Q(P)
\]

Where \(c\) represents the unit cost.

For a constant-elasticity demand model:

\[
Q(P) = AP^\beta
\]

The analytical profit-maximizing price is:

\[
P^* = c\frac{|\beta|}{|\beta|-1}
\]

This solution requires a positive unit cost and an estimated elasticity satisfying \(|\beta|>1\), under the assumptions of the model.

The result helps illustrate how demand elasticity and unit cost affect potential pricing decisions.

### 4. Supply-and-Demand Simulation

PriceOptix includes a simplified supply-and-demand simulation to explore market equilibrium.

The supply function is defined as:

\[
S(P) = c_sP^{\varepsilon_s}
\]

Where:

- \(S(P)\) is the quantity supplied.
- \(c_s\) is a scaling parameter.
- \(\varepsilon_s\) is the assumed supply elasticity.

The default supply elasticity is 0.8.

The equilibrium price is found by solving:

\[ S(P^*) - D(P^*) = 0 \]

The implementation uses Brent's root-finding method to find a solution within a suitable interval.

This simulation is intended for scenario analysis. Since the supply elasticity is assumed rather than estimated directly from transaction data, the result should not be interpreted as an empirically established market equilibrium.

## Model Diagnostics

Regression results need to be interpreted in the context of the data and the assumptions behind the model.

PriceOptix includes statistical diagnostics intended to highlight estimates that may require further investigation.

| Diagnostic | Purpose |
|---|---|
| Coefficient estimates | Describe the estimated relationship between variables |
| P-values | Assess statistical evidence against a zero-coefficient null hypothesis |
| Confidence intervals | Show uncertainty around coefficient estimates |
| R² | Measure the proportion of observed variation explained by the fitted regression |
| Sample size | Help assess whether sufficient observations are available |

Statistically insignificant coefficients or low R² values may indicate that a model requires further review. However, neither measure alone determines whether a model is useful or reliable.

## Limitations and Assumptions

Several limitations should be considered when interpreting the results.

**Observational data and causality**

Retail transaction data records observed sales rather than controlled price experiments. Prices and quantities may also be affected by promotions, seasonality, inventory, customer characteristics, and other factors.

Therefore, the estimated relationship between price and quantity does not necessarily represent the causal effect of changing a product's price.

**Bulk purchasing and price variation**

In some retail and wholesale datasets, larger orders receive volume discounts. This can distort the estimated relationship between price and quantity and may produce positive price coefficients.

Such patterns should be investigated before drawing conclusions about customer behavior.

**Optimization assumptions**

The estimated optimal prices depend on the selected demand model and its assumptions. Real-world pricing decisions may also depend on competition, operating costs, inventory, and customer retention.

**Supply-and-demand simulation**

The supply elasticity is an assumption rather than a value estimated from the transaction data. The simulated equilibrium should therefore be treated as an illustrative scenario.

**Model reliability**

Statistical significance and model fit do not guarantee accurate predictions. Additional validation may be necessary before using the results to support real-world pricing decisions.

## Getting Started

### Requirements

- Python 3.10 or later
- pip
- Git
- Docker and Docker Compose (optional)

### Option 1: Run Locally

**1. Clone the repository**

```bash
git clone https://github.com/zeozdemir/fiyatopt.git
cd fiyatopt
```

**2. Create a virtual environment**

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Linux or macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install the dependencies**

```bash
pip install -r requirements.txt
```

**4. Start the application**

```bash
python app.py
```

Open the application in your browser:

http://127.0.0.1:5000

The application is designed to use the bundled sample dataset when no external dataset is provided.

### Option 2: Run with Docker

If Docker and Docker Compose are installed, run:

```bash
docker compose up --build
```

Open http://127.0.0.1:5000 in your browser.

To stop the containers, run:

```bash
docker compose down
```

### Option 3: Download the Full Dataset

The project includes a script for downloading the UCI Online Retail II dataset.

Run the following commands:

```bash
python scripts/download_data.py
python app.py
```

The dataset contains historical online retail transactions. Depending on the available memory and preprocessing requirements, working with the full dataset may require additional resources.

## Running the Tests

The project uses pytest for unit and API testing.

Run the test suite with:

```bash
python -m pytest -v
```

### Test Coverage

**`tests/test_elasticity.py`**

- Tests elasticity estimation using synthetic data with a known coefficient.
- Checks confidence interval behavior.
- Tests the handling of positive estimated slopes.
- Covers small-sample edge cases.

**`tests/test_optimizer.py`**

- Tests revenue optimization with a concave log-quadratic demand model.
- Checks profit optimization against the analytical solution under the specified assumptions.
- Tests price interpolation across simulation grids.

**`tests/test_api.py`**

- Tests successful API requests and selected error conditions.
- Checks HTTP status codes and JSON response structures.

These tests cover selected model behaviors and API functionality. Passing the test suite does not guarantee that the models will perform accurately on real-world data.

## Continuous Integration

The repository includes a GitHub Actions workflow for running automated checks across supported Python versions.

[View the CI workflow](https://github.com/zeozdemir/fiyatopt/actions/workflows/ci.yml)

## Project Structure

```text
fiyatopt/
├── .github/
│   └── workflows/
│       └── ci.yml
├── data/
│   ├── sample/
│   │   └── sample_retail.csv
│   ├── raw/
│   └── data_loader.py
├── models/
│   ├── elasticity.py
│   ├── optimizer.py
│   └── supply_demand.py
├── plots/
│   └── plot_generator.py
├── scripts/
│   └── download_data.py
├── static/
│   ├── dashboard.js
│   └── style.css
├── templates/
│   └── index.html
├── tests/
│   ├── test_elasticity.py
│   ├── test_optimizer.py
│   └── test_api.py
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .gitignore
```

## Potential Business Applications

Price elasticity analysis can help businesses explore pricing scenarios and better understand product-level demand patterns.

Potential applications include:

- **Pricing Analysis:** Compare estimated price sensitivity across products.
- **Revenue Planning:** Explore how different prices may affect revenue.
- **Margin Analysis:** Compare candidate prices against unit costs.
- **Product Analysis:** Identify products whose estimated demand relationships require further investigation.
- **Scenario Analysis:** Visualize the potential outcomes of different pricing assumptions.

The results are intended to support analysis and decision-making, not to replace business judgment or independent model validation.
