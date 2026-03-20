"""Tests for the visualizer module."""

import pytest
import pandas as pd

from src.detector import Anomaly
from src.visualizer import FuelVisualizer, VisualizerError


@pytest.fixture
def enriched_df():
    """Create a minimal enriched DataFrame suitable for chart generation."""
    return pd.DataFrame({
        "flight_id": ["JT001", "JT002", "JT003"],
        "date": pd.to_datetime(["2026-02-01", "2026-02-02", "2026-02-03"]),
        "route": ["LBA-ALC", "LBA-ALC", "MAN-PMI"],
        "aircraft_type": ["737-800", "737-800", "737-800"],
        "planned_fuel_kg": [4500, 4500, 4200],
        "actual_fuel_kg": [4520, 5800, 4180],
        "fuel_variance_pct": [0.44, 28.9, -0.48],
    })


@pytest.fixture
def sample_anomalies():
    """A single anomaly for overlay on charts."""
    return [
        Anomaly(
            flight_id="JT002",
            date="2026-02-02",
            route="LBA-ALC",
            aircraft_type="737-800",
            anomaly_type="high_fuel_variance",
            severity="high",
            planned_fuel=4500,
            actual_fuel=5800,
            variance_pct=28.9,
            details="Actual fuel 28.9% higher than planned",
        ),
    ]


class TestFuelVisualizer:
    """Test cases for FuelVisualizer class."""

    def test_creates_output_directory(self, tmp_path):
        """Visualizer creates the output directory on init."""
        out_dir = tmp_path / "charts"
        FuelVisualizer(output_dir=str(out_dir))
        assert out_dir.is_dir()

    def test_plot_time_series(self, tmp_path, enriched_df, sample_anomalies):
        """Time series chart is saved as a PNG."""
        viz = FuelVisualizer(output_dir=str(tmp_path))
        path = viz.plot_time_series(enriched_df, sample_anomalies)
        assert path.endswith(".png")
        assert (tmp_path / "time_series.png").exists()

    def test_plot_variance_distribution(self, tmp_path, enriched_df):
        """Variance histogram is saved as a PNG."""
        viz = FuelVisualizer(output_dir=str(tmp_path))
        path = viz.plot_variance_distribution(enriched_df)
        assert path.endswith(".png")
        assert (tmp_path / "variance_distribution.png").exists()

    def test_plot_variance_distribution_missing_column(self, tmp_path):
        """Raises VisualizerError when fuel_variance_pct is missing."""
        viz = FuelVisualizer(output_dir=str(tmp_path))
        df = pd.DataFrame({"flight_id": ["JT001"]})

        with pytest.raises(VisualizerError, match="fuel_variance_pct"):
            viz.plot_variance_distribution(df)

    def test_plot_actual_vs_planned(self, tmp_path, enriched_df, sample_anomalies):
        """Scatter plot is saved as a PNG."""
        viz = FuelVisualizer(output_dir=str(tmp_path))
        path = viz.plot_actual_vs_planned(enriched_df, sample_anomalies)
        assert path.endswith(".png")
        assert (tmp_path / "actual_vs_planned.png").exists()

    def test_plot_anomaly_counts_with_anomalies(self, tmp_path, sample_anomalies):
        """Bar chart is generated when anomalies exist."""
        viz = FuelVisualizer(output_dir=str(tmp_path))
        path = viz.plot_anomaly_counts(sample_anomalies)
        assert path.endswith(".png")
        assert (tmp_path / "anomaly_counts.png").exists()

    def test_plot_anomaly_counts_empty(self, tmp_path):
        """Bar chart placeholder is generated when no anomalies exist."""
        viz = FuelVisualizer(output_dir=str(tmp_path))
        path = viz.plot_anomaly_counts([])
        assert path.endswith(".png")
        assert (tmp_path / "anomaly_counts.png").exists()

    def test_generate_all_charts(self, tmp_path, enriched_df, sample_anomalies):
        """generate_all_charts produces four PNG files."""
        viz = FuelVisualizer(output_dir=str(tmp_path))
        paths = viz.generate_all_charts(enriched_df, sample_anomalies)

        assert len(paths) == 4
        for p in paths:
            assert p.endswith(".png")

    def test_plot_time_series_no_anomalies(self, tmp_path, enriched_df):
        """Time series works with an empty anomaly list."""
        viz = FuelVisualizer(output_dir=str(tmp_path))
        path = viz.plot_time_series(enriched_df, [])
        assert (tmp_path / "time_series.png").exists()

    def test_plot_actual_vs_planned_no_anomalies(self, tmp_path, enriched_df):
        """Scatter plot works with an empty anomaly list."""
        viz = FuelVisualizer(output_dir=str(tmp_path))
        path = viz.plot_actual_vs_planned(enriched_df, [])
        assert (tmp_path / "actual_vs_planned.png").exists()
