"""Tests for the validator module."""

import pytest
import pandas as pd
import numpy as np

from src.validator import FuelDataValidator, ValidatorError, ValidationError


class TestFuelDataValidator:
    """Test cases for FuelDataValidator class."""
    
    @pytest.fixture
    def valid_df(self):
        """Create a valid DataFrame for testing."""
        return pd.DataFrame({
            "flight_id": ["JT001", "JT002"],
            "date": ["2026-02-01 08:30", "2026-02-02 14:15"],
            "route": ["LBA-ALC", "MAN-PMI"],
            "aircraft_type": ["737-800", "737-800"],
            "planned_fuel_kg": [4500, 4200],
            "actual_fuel_kg": [4520, 4180],
            "duration_min": [165, 150],
            "passengers": [180, 175],
            "cargo_weight_kg": [1200, 1100],
            "catering_weight_kg": [150, 145],
            "wind_speed_kts": [15, 10],
            "temperature_c": [18, 20]
        })
    
    def test_validate_valid_data(self, valid_df):
        """Test validation of valid data."""
        validator = FuelDataValidator(strict=True)
        result = validator.validate(valid_df)
        
        assert isinstance(result, pd.DataFrame)
        assert len(validator.errors) == 0
    
    def test_validate_missing_required_columns(self):
        """Test validation fails when required columns are missing."""
        df = pd.DataFrame({
            "flight_id": ["JT001"],
            "date": ["2026-02-01 08:30"]
        })
        
        validator = FuelDataValidator(strict=True)
        
        with pytest.raises(ValidatorError, match="Missing required columns"):
            validator.validate(df)
    
    def test_validate_missing_values_in_critical_columns(self, valid_df):
        """Test detection of missing values in critical columns."""
        valid_df.loc[0, "flight_id"] = np.nan
        
        validator = FuelDataValidator(strict=False)
        validator.validate(valid_df)
        
        assert len(validator.errors) > 0
        assert any(err.error_type == "missing" for err in validator.errors)
    
    def test_validate_out_of_range_values(self, valid_df):
        """Test detection of out-of-range values."""
        valid_df.loc[0, "planned_fuel_kg"] = -1000
        
        validator = FuelDataValidator(strict=False)
        validator.validate(valid_df)
        
        assert len(validator.errors) > 0
        assert any(err.error_type == "range" for err in validator.errors)
    
    def test_validate_non_numeric_in_numeric_column(self):
        """Test detection of non-numeric values in numeric columns."""
        df = pd.DataFrame({
            "flight_id": ["JT001", "JT002"],
            "date": ["2026-02-01 08:30", "2026-02-02 14:15"],
            "route": ["LBA-ALC", "MAN-PMI"],
            "aircraft_type": ["737-800", "737-800"],
            "planned_fuel_kg": [4500, 4200],
            "actual_fuel_kg": [4520, 4180],
            "duration_min": [165, 150],
            "passengers": ["invalid", 175],
            "cargo_weight_kg": [1200, 1100],
            "catering_weight_kg": [150, 145],
            "wind_speed_kts": [15, 10],
            "temperature_c": [18, 20]
        })
        
        validator = FuelDataValidator(strict=False)
        validator.validate(df)
        
        assert len(validator.errors) > 0
    
    def test_strict_mode_raises_exception(self, valid_df):
        """Test that strict mode raises exception on errors."""
        valid_df.loc[0, "planned_fuel_kg"] = -500
        
        validator = FuelDataValidator(strict=True)
        
        with pytest.raises(ValidatorError, match="Validation failed"):
            validator.validate(valid_df)
    
    def test_get_errors(self, valid_df):
        """Test retrieving validation errors."""
        valid_df.loc[0, "flight_id"] = np.nan
        
        validator = FuelDataValidator(strict=False)
        validator.validate(valid_df)
        
        errors = validator.get_errors()
        assert len(errors) > 0
        assert all(isinstance(err, ValidationError) for err in errors)
