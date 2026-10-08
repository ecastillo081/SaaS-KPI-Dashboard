# SaaS Growth Economics

Self-directed portfolio project using **synthetic** subscription data. This is not a client engagement and does not describe results for a live company.

## Business Question

Is ARR growth sustainable given current retention, customer mix, and acquisition economics?

## Architecture

```
data/saas_kpi_data.xlsx
        → DuckDB (warehouse/saas_kpi.duckdb)
        → SQL finance models (sql/)
        → validation controls
        → local outputs and charts
        → HTML / PDF case study (case-study/)
```

Reproduction is fully local:

- no credentials
- no environment variables
- no cloud database
- no Mode Analytics
- no Supabase

## Reproduce

```bash
python -m pip install -r requirements.txt
python build.py
python build.py --report
```

| Command | What it does |
|---|---|
| `python build.py` | Load the golden workbook, build DuckDB models, run controls, write `outputs/*.csv` |
| `python build.py --report` | Same analytics build, then generate charts and the case-study PDF |

Paths are repo-relative. Chrome or Edge is used only for `--report` PDF printing.

### Frozen as-of date

Default analysis cutoff: **2025-09-30**.

Optional override:

```bash
python build.py --as-of YYYY-MM-DD
python build.py --report --as-of YYYY-MM-DD
```

Portfolio results do not depend on the system calendar.

## Case study

[Download the case-study PDF](case-study/SaaS_Growth_Economics_Case_Study.pdf)

Source:

- `case-study/saas-growth-economics.html`
- `case-study/case-study.css`

## Metric definitions

| Metric | Definition |
|---|---|
| MRR | Month-end snapshot of active subscription `price_mrr` |
| ARR | Run-rate ARR = MRR × 12 (not recognized revenue) |
| New MRR | `event_type = new` |
| Expansion MRR | `event_type = upgrade` only |
| Reactivation MRR | `event_type = reactivation` — **separate from expansion** |
| Contraction MRR | `event_type = downgrade` |
| Churn MRR | `event_type = churn` |
| GRR | (Beginning MRR − contraction − churn) / beginning MRR |
| NRR | (Beginning MRR − contraction − churn + expansion) / beginning MRR. Excludes new and reactivation |
| CAC payback | CAC per new customer ÷ (ARPU × 80% gross margin) |

Gross margin is a modeled assumption of 80%.

## Validated conclusions

From the synthetic data through **2025-09-30**:

- ARR peaked at **$73,560** in July 2025 and ended September at **$59,400**
- Mean NRR / GRR approximately **95.5%**
- Upgrade-driven expansion revenue was **$0**
- Mean estimated CAC payback approximately **11.1 months**
- Growth depended on continued customer acquisition, with reactivation as a smaller offset

These conclusions are from synthetic data and do not describe a real company.

## Repository layout

| Path | Role |
|---|---|
| `data/saas_kpi_data.xlsx` | Validated synthetic source workbook |
| `sql/` | DuckDB finance models |
| `src/` | Load, build, validate, chart, and PDF helpers |
| `build.py` | Orchestrator |
| `outputs/` | Generated CSVs and charts (gitignored except `.gitkeep`) |
| `warehouse/` | Generated DuckDB file (gitignored except `.gitkeep`) |
| `case-study/` | HTML/CSS source and published PDF |
| `requirements.txt` | `duckdb`, `pandas`, `openpyxl`, `matplotlib`, `pypdf` |

---

**More finance projects and management-ready case studies: [efrainfinance.com](https://efrainfinance.com/)**
