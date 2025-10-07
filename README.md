# Strategic Finance Dashboard – SaaS KPIs & Growth Drivers

## Overview
This project showcases a full **end-to-end SaaS financial analytics pipeline**, built entirely with SQL and Mode Analytics.

It models how ARR growth, customer retention, and acquisition efficiency interact to drive company performance.

## Data Architecture

The dataset is **synthetic** but structured to mirror a real subscription business:
* SQL views calculate key financial metrics:
   * `mrr_extension`, `mrr`, and `arr` for recurring revenue
   * `retention_cohorts.sql` and `nrr_grr` for retention and expansion analysis
   * `cac_ltv` for unit economics (CAC, ARPU, LTV, Payback)
   * `arr_revenue_bridge` for ARR movement
   * `kpi.sql` for the final monthly summary table

All SQL views are stored in `/sql/` and can be executed in any Postgres-compatible engine or Mode query editor.

## Visuals
The Mode dashboard includes four key visuals:
1. **ARR Bridge (Waterfall)** - breaks down growth into New Customers, Expansion, Contraction, and Churn.
2. **NRR & GRR Trend** – tracks gross and net retention rates month-over-month.
3. **MRR & ARR Trend** – shows recurring revenue scale and growth trajectory.
4. **Executive KPI Table** – summarizes ARR, NRR, CAC, LTV, ARPU, and Payback with color-coded health flags.

## Key Takeaways
* **Retention**: NRR >100% indicates expansion offsetting churn.
* **Payback**: CAC is recovered in ~6–8 months, signaling efficient growth.
* **Scalability**: This SQL setup supports segmentation by product, channel, or customer tier.

## Tech Stack
* **SQL** (Postgres-compatible) for metric calculations
* **Mode Analytics** for data exploration and dashboarding

## Mode Report
You can view the live Mode report [here](https://app.mode.com/castillo/reports/f3ca2fa40b7e/runs/9134d20d2458).