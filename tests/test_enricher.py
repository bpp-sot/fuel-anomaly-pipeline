"""Tests for the enricher module."""

import pytest
import pandas as pd
import numpy as np

from src.enricher import FuelDataEnricher, EnricherError


class TestFuelDataEnricher:
    """Test cases for FuelDataEnricher class."""
    
    @pytest.fixture
    def sample_df(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            "flight_id": ["JT001", "JT002", "JT003"],
            "route": ["LBA-ALC", "LBA-ALC", "MAN-PMI"],
            "aircraft_type": ["737-800", "737-800", "737-800"],
            "planned_fuel_kg": [4500, 4500, 4200],
            "actual_fuel_kg": [4520, 4550, 4180],
            "duration_min": [165, 168, 150],
            "passengers": [180, 175, 170],
            "cargo_weight_kg": [1200, 1150, 1100],
            "catering_weight_kg": [150, 145, 140]
        })
    
    def test_enrich_adds_fuel_variance(self, sample_df):
        """Test that enrichment adds fuel_variance_pct column."""
        enricher = FuelDataEnricher()
        result = enricher.enrich(sample_df)
        
        assert "fuel_variance_pct" in result.columns
        assert result.loc[0, "fuel_variance_pct"] == pytest.approx(
            (4520 - 4500) / 4500 * 100, rel=0.01
        )
    
    def test_enrich_adds_total_weight(self, sample_df):
        """Test that enrichment adds total payload weight."""
        enricher = FuelDataEnricher()
        result = enricher.enrich(sample_df)
        
        assert "total_payload_kg" in result.columns
        assert "passenger_weight_kg" in result.columns
        
        expected_total = 1200 + 150 + (180 * 85)
        assert result.loc[0, "total_payload_kg"] == expected_total
    
    def test_enrich_adds_fuel_efficiency(self, sample_df):
        """Test that enrichment adds fuel efficiency metrics."""
        enricher = FuelDataEnricher()
        result = enricher.enrich(sample_df)
        
        assert "fuel_per_minute" in result.columns
        assert result.loc[0, "fuel_per_minute"] == pytest.approx(4520 / 165, rel=0.01)
    
    def test_enrich_adds_baseline(self, sample_df):
        """Test that enrichment adds baseline expected fuel."""
        enricher = FuelDataEnricher()
        result = enricher.enrich(sample_df)
        
        assert "expected_fuel_kg" in result.columns
        assert "baseline_deviation_sigma" in result.columns
    
    def test_enrich_missing_required_columns(self):
        """Test that enrichment fails with missing required columns."""
        df = pd.DataFrame({"flight_id": ["JT001"]})
        
        enricher = FuelDataEnricher()
        
        with pytest.raises(EnricherError, match="Missing required columns"):
            enricher.enrich(df)
    
    def test_enrich_preserves_original_data(self, sample_df):
        """Test that enrichment doesn't modify original DataFrame."""
        original_cols = set(sample_df.columns)
        
        enricher = FuelDataEnricher()
        result = enricher.enrich(sample_df)
        
        assert set(sample_df.columns) == original_cols
        assert len(result.columns) > len(sample_df.columns)
    
    def test_get_baselines(self, sample_df):
        """Test retrieving calculated baselines."""
        enricher = FuelDataEnricher()
        enricher.enrich(sample_df)
        
        baselines = enricher.get_baselines()
        assert "route_aircraft" in baselines
        assert isinstance(baselines["route_aircraft"], pd.DataFrame)
