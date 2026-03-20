"""Tests for the reporter module."""

import json
import pytest

from src.detector import Anomaly
from src.reporter import AnomalyReporter, ReporterError


@pytest.fixture
def sample_anomalies():
    """Create a small list of anomalies for testing."""
    return [
        Anomaly(
            flight_id="JT001",
            date="2026-02-01",
            route="LBA-ALC",
            aircraft_type="737-800",
            anomaly_type="high_fuel_variance",
            severity="high",
            planned_fuel=4500,
            actual_fuel=5800,
            variance_pct=28.9,
            details="Actual fuel 28.9% higher than planned",
        ),
        Anomaly(
            flight_id="JT002",
            date="2026-02-02",
            route="MAN-PMI",
            aircraft_type="737-800",
            anomaly_type="statistical_outlier",
            severity="critical",
            planned_fuel=4200,
            actual_fuel=6100,
            variance_pct=45.2,
            details="Fuel consumption 3.10σ from route baseline",
        ),
    ]


@pytest.fixture
def sample_summary():
    """Create a matching summary dict."""
    return {
        "total": 2,
        "by_type": {"high_fuel_variance": 1, "statistical_outlier": 1},
        "by_severity": {"high": 1, "critical": 1},
    }


class TestAnomalyReporter:
    """Test cases for AnomalyReporter class."""

    def test_creates_output_directory(self, tmp_path):
        """Test that reporter creates the output directory if missing."""
        out_dir = tmp_path / "nested" / "output"
        AnomalyReporter(output_dir=str(out_dir))
        assert out_dir.is_dir()

    def test_generate_text_report(self, tmp_path, sample_anomalies, sample_summary):
        """Test that a text report is written with expected content."""
        reporter = AnomalyReporter(output_dir=str(tmp_path))
        path = reporter.generate_text_report(sample_anomalies, sample_summary)

        content = open(path, encoding="utf-8").read()
        assert "JET2 FUEL ANOMALY DETECTION REPORT" in content
        assert "Total anomalies detected: 2" in content
        assert "JT001" in content
        assert "28.9%" in content
        assert "CRITICAL" in content

    def test_generate_text_report_empty_anomalies(self, tmp_path):
        """Text report with zero anomalies still writes a valid file."""
        reporter = AnomalyReporter(output_dir=str(tmp_path))
        path = reporter.generate_text_report([], {"total": 0})

        content = open(path, encoding="utf-8").read()
        assert "Total anomalies detected: 0" in content
        assert "END OF REPORT" in content

    def test_generate_json_report(self, tmp_path, sample_anomalies, sample_summary):
        """Test that a JSON report parses correctly and contains anomalies."""
        reporter = AnomalyReporter(output_dir=str(tmp_path))
        path = reporter.generate_json_report(sample_anomalies, sample_summary)

        data = json.loads(open(path, encoding="utf-8").read())
        assert data["summary"]["total"] == 2
        assert len(data["anomalies"]) == 2
        assert data["anomalies"][0]["flight_id"] == "JT001"
        assert "generated_at" in data

    def test_generate_json_report_empty(self, tmp_path):
        """JSON report with no anomalies produces a valid structure."""
        reporter = AnomalyReporter(output_dir=str(tmp_path))
        path = reporter.generate_json_report([], {"total": 0})

        data = json.loads(open(path, encoding="utf-8").read())
        assert data["anomalies"] == []

    def test_print_summary(self, capsys, tmp_path, sample_summary):
        """Test that print_summary writes to stdout."""
        reporter = AnomalyReporter(output_dir=str(tmp_path))
        reporter.print_summary(sample_summary)

        captured = capsys.readouterr().out
        assert "Total anomalies: 2" in captured
        assert "high_fuel_variance" in captured or "CRITICAL" in captured

    def test_text_report_write_failure(self, tmp_path, sample_anomalies, sample_summary):
        """Test ReporterError when writing to an invalid path."""
        reporter = AnomalyReporter(output_dir=str(tmp_path))
        reporter.output_dir = tmp_path / "nonexistent_dir"

        with pytest.raises(ReporterError, match="Failed to write text report"):
            reporter.generate_text_report(sample_anomalies, sample_summary)

    def test_json_report_write_failure(self, tmp_path, sample_anomalies, sample_summary):
        """Test ReporterError when writing JSON to an invalid path."""
        reporter = AnomalyReporter(output_dir=str(tmp_path))
        reporter.output_dir = tmp_path / "nonexistent_dir"

        with pytest.raises(ReporterError, match="Failed to write JSON report"):
            reporter.generate_json_report(sample_anomalies, sample_summary)
