"""Tests for the loader module."""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import os

from src.loader import load_fuel_data, load_with_config, LoaderError


class TestLoadFuelData:
    """Test cases for load_fuel_data function."""
    
    def test_load_valid_csv(self, tmp_path):
        """Test loading a valid CSV file."""
        csv_file = tmp_path / "test_data.csv"
        csv_file.write_text(
            "flight_id,planned_fuel_kg,actual_fuel_kg\n"
            "JT001,4500,4520\n"
            "JT002,4200,4180\n"
        )
        
        df = load_fuel_data(str(csv_file))
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "flight_id" in df.columns
        assert df.iloc[0]["flight_id"] == "JT001"
    
    def test_load_nonexistent_file(self):
        """Test loading a file that doesn't exist."""
        with pytest.raises(LoaderError, match="File not found"):
            load_fuel_data("nonexistent_file.csv")
    
    def test_load_empty_file(self, tmp_path):
        """Test loading an empty file."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        
        with pytest.raises(LoaderError, match="empty"):
            load_fuel_data(str(csv_file))
    
    def test_load_directory_path(self, tmp_path):
        """Test that passing a directory raises error."""
        with pytest.raises(LoaderError, match="not a file"):
            load_fuel_data(str(tmp_path))
    
    def test_load_malformed_csv(self, tmp_path):
        """Test loading a malformed CSV file."""
        csv_file = tmp_path / "malformed.csv"
        csv_file.write_text(
            "flight_id,planned_fuel_kg\n"
            "JT001,4500,extra_column_value\n"
        )
        
        df = load_fuel_data(str(csv_file))
        assert isinstance(df, pd.DataFrame)
    
    def test_load_with_custom_encoding(self, tmp_path):
        """Test loading with custom encoding."""
        csv_file = tmp_path / "encoded.csv"
        csv_file.write_text("flight_id\nJT001\n", encoding="utf-8")
        
        df = load_fuel_data(str(csv_file), encoding="utf-8")
        assert len(df) == 1


class TestLoadWithConfig:
    """Test cases for load_with_config function."""
    
    def test_load_with_default_config(self, tmp_path, monkeypatch):
        """Test loading with default configuration."""
        monkeypatch.chdir(tmp_path)
        
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        csv_file = data_dir / "sample_fuel_logs.csv"
        csv_file.write_text("flight_id\nJT001\n")
        
        df = load_with_config()
        assert len(df) == 1
    
    def test_load_with_custom_config(self, tmp_path):
        """Test loading with custom configuration."""
        csv_file = tmp_path / "custom.csv"
        csv_file.write_text("flight_id\nJT999\n")
        
        config = {
            "data_path": str(csv_file),
            "encoding": "utf-8"
        }
        
        df = load_with_config(config)
        assert len(df) == 1
        assert df.iloc[0]["flight_id"] == "JT999"
