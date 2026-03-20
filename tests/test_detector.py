"""Tests for the detector module."""

import pytest
import pandas as pd

from src.detector import FuelAnomalyDetector, Anomaly, DetectorError


class TestFuelAnomalyDetector:
    """Test cases for FuelAnomalyDetector class."""
    
    @pytest.fixture
    def normal_df(self):
        """Create DataFrame with normal fuel consumption."""
        return pd.DataFrame({
            "flight_id": ["JT001", "JT002"],
            "date": ["2026-02-01", "2026-02-02"],
            "route": ["LBA-ALC", "MAN-PMI"],
            "planned_fuel_kg": [4500, 4200],
            "actual_fuel_kg": [4520, 4180],
            "fuel_variance_pct": [0.44, -0.48]
        })
    
    @pytest.fixture
    def anomalous_df(self):
        """Create DataFrame with anomalous fuel consumption."""
        return pd.DataFrame({
            "flight_id": ["JT001", "JT002", "JT003"],
            "date": ["2026-02-01", "2026-02-02", "2026-02-03"],
            "route": ["LBA-ALC", "MAN-PMI", "LBA-ALC"],
            "planned_fuel_kg": [4500, 4200, 4500],
            "actual_fuel_kg": [7800, 2800, 4520],
            "fuel_variance_pct": [73.33, -33.33, 0.44],
            "baseline_deviation_sigma": [3.5, -2.8, 0.1]
        })
    
    def test_detect_no_anomalies(self, normal_df):
        """Test detection on normal data returns no anomalies."""
        detector = FuelAnomalyDetector(variance_threshold=20.0)
        anomalies = detector.detect(normal_df)
        
        assert len(anomalies) == 0
    
    def test_detect_high_variance_anomaly(self, anomalous_df):
        """Test detection of high fuel variance."""
        detector = FuelAnomalyDetector(variance_threshold=20.0)
        anomalies = detector.detect(anomalous_df)
        
        high_variance_anomalies = [
            a for a in anomalies if a.anomaly_type == "high_fuel_variance"
        ]
        assert len(high_variance_anomalies) > 0
        assert high_variance_anomalies[0].flight_id == "JT001"
    
    def test_detect_low_variance_anomaly(self, anomalous_df):
        """Test detection of low fuel variance."""
        detector = FuelAnomalyDetector(variance_threshold=20.0)
        anomalies = detector.detect(anomalous_df)
        
        low_variance_anomalies = [
            a for a in anomalies if a.anomaly_type == "low_fuel_variance"
        ]
        assert len(low_variance_anomalies) > 0
        assert low_variance_anomalies[0].flight_id == "JT002"
    
    def test_detect_statistical_outliers(self, anomalous_df):
        """Test detection of statistical outliers."""
        detector = FuelAnomalyDetector(sigma_threshold=2.5)
        anomalies = detector.detect(anomalous_df)
        
        outliers = [
            a for a in anomalies if a.anomaly_type == "statistical_outlier"
        ]
        assert len(outliers) > 0
    
    def test_detect_duplicate_flights(self):
        """Test detection of duplicate flight records."""
        df = pd.DataFrame({
            "flight_id": ["JT001", "JT001"],
            "date": ["2026-02-01", "2026-02-01"],
            "route": ["LBA-ALC", "LBA-ALC"],
            "planned_fuel_kg": [4500, 4500],
            "actual_fuel_kg": [4520, 4520],
            "fuel_variance_pct": [0.44, 0.44]
        })
        
        detector = FuelAnomalyDetector()
        anomalies = detector.detect(df)
        
        duplicates = [
            a for a in anomalies if a.anomaly_type == "duplicate_record"
        ]
        assert len(duplicates) > 0
    
    def test_detect_missing_required_columns(self):
        """Test that detection fails with missing required columns."""
        df = pd.DataFrame({"flight_id": ["JT001"]})
        
        detector = FuelAnomalyDetector()
        
        with pytest.raises(DetectorError, match="Missing required columns"):
            detector.detect(df)
    
    def test_get_anomaly_summary(self, anomalous_df):
        """Test anomaly summary generation."""
        detector = FuelAnomalyDetector()
        detector.detect(anomalous_df)
        
        summary = detector.get_anomaly_summary()
        
        assert "total" in summary
        assert summary["total"] > 0
        assert "by_type" in summary
        assert "by_severity" in summary
    
    def test_get_anomalies_df(self, anomalous_df):
        """Test conversion of anomalies to DataFrame."""
        detector = FuelAnomalyDetector()
        detector.detect(anomalous_df)
        
        anomalies_df = detector.get_anomalies_df()
        
        assert isinstance(anomalies_df, pd.DataFrame)
        assert len(anomalies_df) > 0
        assert "flight_id" in anomalies_df.columns
        assert "anomaly_type" in anomalies_df.columns
    
    def test_custom_thresholds(self, anomalous_df):
        """Test detector with custom thresholds."""
        detector = FuelAnomalyDetector(
            variance_threshold=50.0,
            sigma_threshold=3.0
        )
        anomalies = detector.detect(anomalous_df)
        
        assert len(anomalies) < len(FuelAnomalyDetector().detect(anomalous_df))
