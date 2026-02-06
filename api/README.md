# BlackSwans API

FastAPI backend for the BlackSwans market outlier analysis project.

## Installation

```bash
# Install API dependencies
pip install -e ".[api]"
```

## Running the Server

```bash
# Start the development server
uvicorn api.main:app --host 0.0.0.0 --port 8000

# With auto-reload (for development)
uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

### Health Check
**GET** `/api/health`

Returns server health status.

**Response:**
```json
{
  "status": "ok"
}
```

### List Tickers
**GET** `/api/tickers`

Returns all available tickers with their data files and date ranges.

**Response:**
```json
{
  "tickers": [
    {
      "ticker_code": "sp500",
      "ticker_symbol": "^GSPC",
      "data_file": "/path/to/data/_GSPC_1928-09-04_to_2025-01-31.csv",
      "start_date": "1928-09-04",
      "end_date": "2025-01-31"
    }
  ]
}
```

### Run Analysis
**GET** `/api/analysis/{ticker}`

Run outlier analysis for a specific ticker.

**Path Parameters:**
- `ticker` (string): Ticker code (e.g., "sp500", "nikkei", "ftse")

**Query Parameters:**
- `start` (string, optional): Start date (YYYY-MM-DD). Defaults to data file start date.
- `end` (string, optional): End date (YYYY-MM-DD). Defaults to data file end date.
- `ma_window` (int, optional): Moving average window (default: 200)
- `quantiles` (string, optional): Comma-separated quantiles (default: "0.99,0.999")

**Example:**
```bash
curl "http://localhost:8000/api/analysis/sp500?quantiles=0.99&ma_window=200"
```

**Response:**
```json
{
  "ticker": "sp500",
  "start_date": "1928-09-04",
  "end_date": "2025-01-31",
  "n_trading_days": 24216,
  "outlier_stats": [...],
  "scenarios": [...],
  "regime_performance": [...]
}
```

### Run Validation
**GET** `/api/validation/{ticker}`

Run full validation of Faber's 4 claims for a specific ticker.

**Path Parameters:**
- `ticker` (string): Ticker code (e.g., "sp500", "nikkei", "ftse")

**Query Parameters:**
- `start` (string, optional): Start date (YYYY-MM-DD). Defaults to data file start date.
- `end` (string, optional): End date (YYYY-MM-DD). Defaults to data file end date.

**Example:**
```bash
curl "http://localhost:8000/api/validation/sp500"
```

**Response:**
```json
{
  "ticker": "sp500",
  "period": "1928-09-04 to 2025-01-31",
  "n_trading_days": 24216,
  "claims": {
    "1_fat_tails": "CONFIRMED",
    "2_outsized_influence": "CONFIRMED",
    "3_clustering": "CONFIRMED",
    "4_trend_following": "CONFIRMED"
  },
  "claim_details": [...]
}
```

## Available Tickers

- `sp500` - S&P 500 (^GSPC)
- `nikkei` - Nikkei 225 (^N225)
- `ftse` - FTSE 100 (^FTSE)
- `dax` - DAX (^GDAXI)
- `cac` - CAC 40 (^FCHI)
- `asx` - ASX 200 (^AXJO)
- `tsx` - TSX Composite (^GSPTSE)
- `hsi` - Hang Seng (^HSI)
- `efa` - MSCI EAFE (EFA)
- `eem` - MSCI Emerging Markets (EEM)
- `reit` - REITs (VNQ)
- `bonds` - Aggregate Bonds (AGG)

## Architecture

The API is built with:
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation and serialization
- **CORS enabled** - Allows cross-origin requests (development mode)

The API integrates directly with the `blackswans` package modules:
- `blackswans.data.loaders` - Data loading and caching
- `blackswans.analysis.*` - Outlier, scenario, and regime analysis
- `blackswans.validate_claims` - Full 4-claim validation

## Error Handling

The API returns appropriate HTTP status codes:
- `200 OK` - Successful request
- `404 Not Found` - Ticker not found or data file missing
- `500 Internal Server Error` - Analysis or validation error

Error responses include details:
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Development

The API source code is organized as:
```
api/
├── __init__.py         # Package marker
├── main.py             # FastAPI app and endpoints
├── models.py           # Pydantic request/response models
└── README.md           # This file
```

## CORS Configuration

CORS is currently configured to allow all origins for development. For production deployment, update the `allow_origins` list in `api/main.py` to restrict access to specific domains.
