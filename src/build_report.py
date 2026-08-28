"""Fill the case-study HTML template and print the PDF."""

from __future__ import annotations

from pathlib import Path

from src.charts import generate_charts
from src.render_pdf import PDF_PATH, html_to_pdf
from src.report_metrics import ReportMetrics, load_report_metrics, money, month_label, pct
from src.settings import REPO_ROOT

TEMPLATE_PATH = REPO_ROOT / "case-study" / "saas-growth-economics.html"
RENDERED_PATH = REPO_ROOT / "case-study" / "_rendered.html"


def _channel_rows(m: ReportMetrics) -> str:
    rows = []
    for _, row in m.channel_summary.iterrows():
        rows.append(
            "<tr>"
            f"<td>{row['acquisition_channel']}</td>"
            f"<td class='num'>{int(row['new_customers'])}</td>"
            f"<td class='num'>{money(float(row['avg_cac']))}</td>"
            f"<td class='num'>{money(float(row['ch_arpu']))}</td>"
            f"<td class='num'>{float(row['payback_proxy']):.1f} mo</td>"
            "</tr>"
        )
    return "\n          ".join(rows)


def _replacements(m: ReportMetrics) -> dict[str, str]:
    rel = lambda name: f"../outputs/charts/{name}"
    return {
        "{{START_MONTH}}": month_label(m.start_month),
        "{{END_MONTH}}": month_label(m.end_month),
        "{{AS_OF_DATE}}": str(m.as_of_date)[:10],
        "{{PEAK_ARR}}": money(m.peak_arr),
        "{{PEAK_MONTH}}": month_label(m.peak_arr_month),
        "{{ENDING_ARR}}": money(m.ending_arr),
        "{{ENDING_MRR}}": money(m.ending_mrr),
        "{{EXPANSION_ARR}}": money(m.period_expansion_arr),
        "{{TOTAL_NEW_MRR}}": money(m.total_new_mrr),
        "{{TOTAL_REACT_MRR}}": money(m.total_reactivation_mrr),
        "{{TOTAL_EXPANSION_MRR}}": money(m.total_expansion_mrr),
        "{{MEAN_NRR}}": pct(m.mean_nrr),
        "{{AUG_NRR}}": pct(m.aug_nrr),
        "{{NRR_ABOVE_100}}": str(m.nrr_months_above_1),
        "{{ENDING_CUSTOMERS}}": str(m.ending_customers),
        "{{MEAN_PAYBACK}}": f"{m.mean_payback:.1f}",
        "{{MAY_ARPU}}": money(m.may_arpu, 1),
        "{{LATEST_ARPU}}": money(m.latest_arpu, 1),
        "{{CHART_ARR_TREND}}": rel("arr_trend.png"),
        "{{CHART_ARR_BRIDGE}}": rel("arr_bridge.png"),
        "{{CHART_NRR}}": rel("nrr_grr.png"),
        "{{CHART_CUSTOMERS}}": rel("active_customers.png"),
        "{{CHART_PAYBACK}}": rel("cac_payback.png"),
        "{{CHART_ARPU}}": rel("arpu_trend.png"),
        "{{CHANNEL_ROWS}}": _channel_rows(m),
    }


def render_html(m: ReportMetrics) -> Path:
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    for token, value in _replacements(m).items():
        html = html.replace(token, value)
    if "{{" in html:
        leftover = [part for part in html.split("{{")[1:]]
        raise RuntimeError(f"Unreplaced template tokens remain: {leftover[:5]}")
    RENDERED_PATH.write_text(html, encoding="utf-8")
    return RENDERED_PATH


def build_case_study() -> Path:
    metrics = load_report_metrics()
    generate_charts(metrics)
    html_path = render_html(metrics)
    return html_to_pdf(html_path, PDF_PATH)
