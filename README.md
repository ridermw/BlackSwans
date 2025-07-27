# Black Swans Validation

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License: AGPL v3](https://img.shields.io/badge/license-AGPL%20v3-blue)

> Validate and extend the analysis from **"Where the Black Swans Hide & The 10 Best Days Myth"** by Faber & CQR (Aug 2011).

Repository: [https://github.com/ridermw/BlackSwans](https://github.com/ridermw/BlackSwans)

## Table of Contents

* [Overview](#overview)
* [Features](#features)
* [Requirements](#requirements)
* [Installation](#installation)
* [Usage](#usage)
* [Validation Plan](#validation-plan)
* [Extending to Present Day](#extending-to-present-day)
* [Investment Insights](#investment-insights)
* [Contributing](#contributing)
* [License](#license)
* [Contact](#contact)

---

## Overview

This project:

1. Summarizes the key claims of the 2011 white paper on fat-tailed market returns, outliers, and the "10 Best Days" myth.
2. Implements a Python-based validation of those claims using historical market data.
3. Extends the analysis through July 27, 2025 (e.g., COVID-19 crash, 2022 downturn).
4. Extracts actionable investment insights (trend-following, tail-risk hedging, dynamic allocation).

Original paper: [SSRN 1908469](https://ssrn.com/abstract=1908469)

---

## Features

* Download S\&P 500 (and other indices) daily returns via `yfinance`.
* Identify top/bottom quantile outliers (e.g., 1%, 0.1%).
* Classify market regime using 200-day moving average.
* Compute scenario returns:

  * Buy-and-hold
  * Exclude best days
  * Exclude worst days
  * Exclude both best & worst
* Perform clustering analysis and statistical significance tests.
* Generate tables and charts for each step.

---

## Requirements

* Python 3.8 or higher
* pandas
* numpy
* yfinance
* matplotlib
* scipy

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Installation

```bash
git clone https://github.com/ridermw/BlackSwans.git
cd BlackSwans
pip install -r requirements.txt
```

---

## Usage

Run the main validation script with date range parameters:

```bash
python validate_outliers.py \
  --ticker ^GSPC \
  --start 1928-09-01 \
  --end 2025-07-27 \
  --quantiles 0.99 0.01 \
  --ma-window 200
```

Outputs are saved in `/output`:

* `summary.csv`
* `clustering_stats.csv`
* `return_scenarios.csv`
* charts (`.png`)

---

## Validation Plan

1. **Data Collection**: Download daily closes & compute returns.
2. **Outlier Identification**: Flag best/worst days via quantiles.
3. **Trend Classification**: 200-day MA to label up/down regimes.
4. **Scenario Analysis**: Calculate returns for each scenario.
5. **Clustering Analysis**: Test whether outliers cluster in downtrends.
6. **Statistical Testing**: Apply chi-square or two-proportion z-tests.

---

## Extending to Present Day

To update:

1. Change `--end` parameter to the latest date.
2. Re-run `validate_outliers.py`.
3. Compare pre-2011 vs. post-2011 metrics.
4. Analyze recent crisis periods (2020, 2022).

---

## Investment Insights

* **Trend-Following**: Rotate out when price < MA.
* **Tail-Risk Hedging**: Use options or structured products in volatile regimes.
* **Dynamic Allocation**: Weight by regime-based volatility.
* **Behavioral Rules**: Automate to avoid emotional trading.

---

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/XYZ`).
3. Commit your changes (`git commit -m 'Add XYZ'`).
4. Push to the branch (`git push origin feature/XYZ`).
5. Open a Pull Request.

Please follow the [code style guidelines](CONTRIBUTING.md).

---

## License

This project is licensed under the **GNU Affero General Public License v3.0**. See [LICENSE](LICENSE) for details.

---

## Contact

Maintainer: Matthew Williams
