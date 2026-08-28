# SaaS Growth Economics

Self-directed portfolio case using **synthetic** subscription data. This is not a client engagement and does not report results for a live company.

## Business Question

How do ARR growth, retention, and acquisition efficiency interact in a subscription business, and what should finance review together in management reporting?

## Context / Data

The workbook in `data/saas_kpi_data.xlsx` is synthetic and structured to resemble a SaaS company (customers, subscriptions, events, invoices, and payments).

SQL views in `sql/` calculate:

- MRR and ARR
- NRR and GRR
- CAC, LTV, ARPU, and payback
- ARR bridge (new, expansion, contraction, churn)
- Cohort, segment, and channel views

## Approach

Postgres-compatible SQL defines the metrics. Python can load the Excel file and apply the SQL views to a local or hosted Postgres database. Mode Analytics was used to present the management dashboard.

Database credentials must come from environment variables (`PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`, `PGDATABASE`). Do not commit passwords or connection strings.

## Key Findings

Findings below are from the synthetic dataset, not from a real business:

- NRR above 100% means expansion offset churn in this model.
- CAC payback is about 6–8 months under the model's assumptions.
- ARR should be read with the bridge (new / expansion / contraction / churn), not as a single growth rate.

## Recommendation

Review ARR bridge, NRR/GRR, and payback together before treating growth as efficient.

## Visuals

The dashboard PDF includes:

1. ARR bridge
2. NRR and GRR trend
3. MRR and ARR trend
4. Executive KPI table

[Download the dashboard PDF](reports/SaaS%20KPI%20Dashboard.pdf)

## Technical Methodology

All metric logic lives in `sql/`. `queries/run_queries.py` applies those files. `supabase/excel_to_supabase.py` loads Excel into a `raw` schema. `supabase/db.py` reads connection details from the environment.

## Reproduce

1. Set `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`, and `PGDATABASE`.
2. Load `data/saas_kpi_data.xlsx` if you are using the Python loader.
3. Run the SQL files in `sql/` in filename order.
4. Open the dashboard PDF for the management view.
