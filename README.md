# Business Intelligence Analytics Platform

Backend foundation, reproducible ingestion pipeline, analytics API, and React dashboard for a retail and e-commerce analytics platform. The dashboard is a historical analytics experience backed by the UCI Online Retail II dataset; it does not represent live sales.

## Technology stack

- Python 3.14+
- FastAPI and Uvicorn
- Pandas and openpyxl for bounded workbook ingestion
- SQLite for local, reproducible storage
- Pytest and HTTPX for endpoint tests
- React, TypeScript, Vite, Tailwind CSS, Recharts, and Lucide React

## Structure

```text
backend/
  main.py       FastAPI application and system endpoints
  config.py     Environment-backed application settings
  database.py   SQLite schema and database utilities
  ingestion.py  Streaming profiler and ingestion command
  api/          FastAPI route modules, including analytics routes
  models/       Pydantic API response models
  services/     Analytics query services and business logic
tests/          Automated endpoint tests
src/            React dashboard, typed API client, pages, charts, tables, and layout
  api/          Typed FastAPI client
  components/   Reusable dashboard UI, charts, tables, filters, and states
  context/      Global date/country filter state
  pages/        Overview, sales, products, customers, geography, and returns views
  types/        API response and filter types
  utils/        Formatting helpers
vite.config.ts  Vite configuration and local API proxy
```

## Dataset and ingestion

The source is the [UCI Online Retail II dataset](https://archive.ics.uci.edu/dataset/502/online+retail+ii), dataset 502, licensed CC BY 4.0. Download the official `online_retail_ii.zip` archive into `data/raw/` and extract the workbook there. The pipeline does not use synthetic data.

Profile the workbook without importing it:

```powershell
python -m backend.ingestion --input data\raw\online_retail_ii\online_retail_II.xlsx --profile-only
```

Profile and ingest into SQLite:

```powershell
python -m backend.ingestion --input data\raw\online_retail_ii\online_retail_II.xlsx --database data\database\retail.db
```

The workbook is read worksheet-by-worksheet and processed in bounded batches. Re-running the command is safe: exact duplicate records are identified by a SHA-256 content hash and ignored by the database uniqueness constraint.

### Data handling and revenue rules

- Missing `Customer ID` values are retained as `NULL`.
- Negative quantities are retained and treated as returns.
- Invoice numbers beginning with `C` are retained and treated as cancellations/returns.
- Exact duplicate source rows are counted and ignored on insert; they are not silently mixed into metrics.
- Zero/non-numeric quantities, negative/non-numeric prices, missing required identifiers, and invalid dates are retained with `validation_status = 'invalid'` and an error list. Their financial amount fields are always zero, while raw source values remain available for audit.
- For valid rows, `gross_sales = quantity * unit_price` only for positive, non-cancelled quantities. `return_amount = abs(quantity * unit_price)` for returns/cancellations. `net_sales = gross_sales - return_amount`.
- Profit and margin are not calculated because the dataset contains no product cost.

## Start the backend on Windows

From the project folder in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload
```

The API is then available at `http://localhost:8000`. Open `http://localhost:8000/docs` for the interactive API documentation.

## Start the dashboard in VS Code

Use two integrated terminals from the project folder:

Terminal 1 — backend:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload
```

Terminal 2 — React dashboard:

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`. The dashboard reads `VITE_API_BASE_URL` from the root `.env` when provided and defaults to `http://localhost:8000`. The production build can be checked with `npm run typecheck` and `npm run build`.

On Windows, if the project is opened from a path containing `&` and Vite's on-demand dependency transform reports an esbuild path-access error, use the production preview instead:

```powershell
npm run build
npm run preview -- --host 127.0.0.1 --port 4173
```

Alternatively open the same folder through a Windows junction or another path without `&` and run `npm run dev` there. This is an environment/path limitation, not an application error.

## Analytics API

All analytics endpoints accept optional `start_date`, `end_date`, and `country` query parameters. Dates are inclusive and use `YYYY-MM-DD`. List endpoints support `limit` (1–500) and `offset` pagination.

```text
GET /api/analytics/overview
GET /api/analytics/sales-trends?granularity=month
GET /api/analytics/top-products?limit=20&offset=0
GET /api/analytics/customers?limit=20&offset=0
GET /api/analytics/countries?limit=100&offset=0
GET /api/analytics/returns
GET /api/analytics/filters
```

KPI definitions:

- A transaction row is one deduplicated source line stored in `transactions`.
- An order is a distinct non-cancelled invoice with positive gross sales after filters. Multi-line invoices count once.
- Gross sales are the sum of positive, non-cancelled line revenue.
- Returns are the sum of `return_amount`, including cancellation rows.
- Net sales are `gross sales - returns` at line level.
- Average order value is the sum of net revenue for completed order invoices divided by completed order count. It is calculated after invoice-level aggregation, not as an average of line values.
- Unique customers are distinct known customer IDs across valid transaction records, excluding missing IDs and including possible return-only or cancellation-only customers.
- Repeat customers have at least two completed orders.
- Transaction-row return rate is returned/cancelled transaction rows divided by valid transaction rows in the selected scope. This is a row-based rate, not an order-, unit-, or sales-value return rate.
- Invalid rows are excluded from analytics but remain stored for audit and reconciliation. Returns and cancellations remain included in net and return metrics.

Example requests:

```powershell
Invoke-RestMethod http://localhost:8000/api/analytics/overview
Invoke-RestMethod 'http://localhost:8000/api/analytics/sales-trends?granularity=month&country=United%20Kingdom'
Invoke-RestMethod 'http://localhost:8000/api/analytics/top-products?limit=10'
```

The API does not calculate profit or margin because the source data contains no product cost.

To run the tests:

```powershell
pytest
```

Copy `.env.example` to `.env` only if local overrides are needed. Do not commit `.env` or other secret files.
