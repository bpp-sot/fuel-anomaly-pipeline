"""Streamlit web UI for the Jet2 Fuel Anomaly Detection System.

Run with:
    streamlit run app.py

Reads AWS credentials from a .env file (or environment variables if already set).
"""

import io
import os
import json
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from src.loader import load_fuel_data, load_fuel_data_from_s3, LoaderError
from src.validator import FuelDataValidator, ValidatorError
from src.enricher import FuelDataEnricher, EnricherError
from src.detector import FuelAnomalyDetector, DetectorError
from src.reporter import AnomalyReporter, ReporterError
from src.visualizer import FuelVisualizer, VisualizerError


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Jet2 Fuel Anomaly Detection",
    page_icon="✈️",
    layout="wide",
)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("✈️ Jet2 Fuel Anomaly Detection System")
st.markdown("Automated fuel consumption analysis and anomaly reporting.")
st.divider()

# ── Sidebar: input configuration ─────────────────────────────────────────────

with st.sidebar:
    st.header("Configuration")

    input_mode = st.radio(
        "Data source",
        ["S3 URL", "Local CSV file"],
        index=0,
    )

    if input_mode == "S3 URL":
        s3_url = st.text_input(
            "S3 URL",
            value=os.getenv("S3_INPUT_URL", "s3://acar-flights/sample_fuel_logs.csv"),
            placeholder="s3://bucket-name/path/to/file.csv",
        )
        uploaded_file = None
    else:
        uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
        s3_url = None

    st.subheader("Detection thresholds")
    variance_threshold = st.slider(
        "Variance threshold (%)",
        min_value=5.0,
        max_value=50.0,
        value=20.0,
        step=1.0,
        help="Flag flights where actual fuel deviates from planned by more than this %",
    )
    sigma_threshold = st.slider(
        "Sigma threshold (σ)",
        min_value=1.0,
        max_value=5.0,
        value=2.5,
        step=0.1,
        help="Flag flights that deviate more than this many standard deviations from the route baseline",
    )

    generate_charts = st.checkbox("Generate charts", value=True)

    run_button = st.button("▶  Run Analysis", type="primary", use_container_width=True)

# ── Main panel ────────────────────────────────────────────────────────────────

if not run_button:
    st.info(
        "Configure your data source in the sidebar, then click **Run Analysis**.",
        icon="👈",
    )
    st.stop()

# ── Pipeline execution ────────────────────────────────────────────────────────

progress = st.progress(0, text="Starting…")
status = st.empty()


def step(n: int, total: int, msg: str):
    progress.progress(n / total, text=msg)
    status.markdown(f"**{msg}**")


try:
    # 1. Load
    step(1, 6, "Loading data…")
    if input_mode == "S3 URL":
        if not s3_url:
            st.error("Please enter an S3 URL.")
            st.stop()
        df = load_fuel_data_from_s3(s3_url)
        source_label = s3_url
    else:
        if uploaded_file is None:
            st.error("Please upload a CSV file.")
            st.stop()
        df = pd.read_csv(uploaded_file)
        source_label = uploaded_file.name

    # 2. Validate
    step(2, 6, "Validating data…")
    validator = FuelDataValidator(strict=False)
    df = validator.validate(df)

    # 3. Enrich
    step(3, 6, "Enriching data…")
    enricher = FuelDataEnricher()
    df = enricher.enrich(df)

    # 4. Detect
    step(4, 6, "Detecting anomalies…")
    detector = FuelAnomalyDetector(
        variance_threshold=variance_threshold,
        sigma_threshold=sigma_threshold,
    )
    anomalies = detector.detect(df)
    summary = detector.get_anomaly_summary()

    # 5. Report (write to /tmp so we can offer downloads)
    step(5, 6, "Generating reports…")
    tmp_dir = Path("/tmp/fuel_anomaly_output")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    reporter = AnomalyReporter(output_dir=str(tmp_dir))
    reporter.generate_text_report(anomalies, summary)
    reporter.generate_json_report(anomalies, summary)

    # 6. Charts
    if generate_charts:
        step(6, 6, "Generating charts…")
        visualizer = FuelVisualizer(output_dir=str(tmp_dir))
        visualizer.generate_all_charts(df, anomalies)

    progress.progress(1.0, text="Done!")
    status.empty()

except (LoaderError, ValidatorError, EnricherError, DetectorError,
        ReporterError, VisualizerError) as e:
    st.error(f"Pipeline error: {e}")
    st.stop()
except Exception as e:
    st.error(f"Unexpected error: {e}")
    st.stop()

# ── Results ───────────────────────────────────────────────────────────────────

total = summary.get("total", 0)
severity_counts = summary.get("by_severity", {})
type_counts = summary.get("by_type", {})

st.success(f"Analysis complete — {total} anomalies detected from **{source_label}**")
st.divider()

# KPI metrics row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Anomalies", total)
col2.metric("Critical", severity_counts.get("critical", 0), delta_color="inverse")
col3.metric("High", severity_counts.get("high", 0), delta_color="inverse")
col4.metric("Flights Analysed", len(df))

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────

if generate_charts:
    st.subheader("Visualisations")
    chart_files = {
        "Fuel Consumption Over Time": tmp_dir / "time_series.png",
        "Actual vs Planned Fuel": tmp_dir / "actual_vs_planned.png",
        "Variance Distribution": tmp_dir / "variance_distribution.png",
        "Anomaly Count by Route": tmp_dir / "anomaly_counts.png",
    }
    chart_cols = st.columns(2)
    for i, (title, path) in enumerate(chart_files.items()):
        if path.exists():
            chart_cols[i % 2].image(str(path), caption=title, use_container_width=True)

    st.divider()

# ── Anomaly table ─────────────────────────────────────────────────────────────

st.subheader(f"Anomaly Details ({total} records)")

if anomalies:
    anomaly_rows = [
        {
            "Flight ID": a.flight_id,
            "Date": a.date,
            "Route": a.route,
            "Aircraft": a.aircraft_type,
            "Type": a.anomaly_type,
            "Severity": a.severity.upper(),
            "Planned (kg)": f"{a.planned_fuel:,.0f}",
            "Actual (kg)": f"{a.actual_fuel:,.0f}",
            "Variance %": f"{a.variance_pct:+.1f}%",
            "Details": a.details,
        }
        for a in anomalies
    ]
    anomaly_df = pd.DataFrame(anomaly_rows)

    def colour_severity(val):
        colours = {"CRITICAL": "#ff4b4b", "HIGH": "#ffa500", "MEDIUM": "#ffd700", "LOW": "#90ee90"}
        return f"color: {colours.get(val, 'inherit')}"

    st.dataframe(
        anomaly_df.style.map(colour_severity, subset=["Severity"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No anomalies detected with the current thresholds.")

st.divider()

# ── Validation warnings ───────────────────────────────────────────────────────

if validator.errors:
    with st.expander(f"⚠️ {len(validator.errors)} data validation warning(s)"):
        for err in validator.errors[:20]:
            st.warning(f"Row {err.row_index} — {err.column}: {err.message}")

# ── Downloads ─────────────────────────────────────────────────────────────────

st.subheader("Download Reports")
dl_col1, dl_col2 = st.columns(2)

text_report_path = tmp_dir / "anomaly_report.txt"
if text_report_path.exists():
    dl_col1.download_button(
        label="📄 Download Text Report",
        data=text_report_path.read_bytes(),
        file_name=f"anomaly_report_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
        use_container_width=True,
    )

json_report_path = tmp_dir / "anomaly_report.json"
if json_report_path.exists():
    dl_col2.download_button(
        label="📋 Download JSON Report",
        data=json_report_path.read_bytes(),
        file_name=f"anomaly_report_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True,
    )
