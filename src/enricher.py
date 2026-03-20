"""Data enrichment module for fuel logs.

Adds derived columns and calculates baseline metrics for anomaly detection.
"""

import pandas as pd
import numpy as np
from typing import Dict


class EnricherError(Exception):
    """Custom exception for enrichment errors."""
    pass


class FuelDataEnricher:
    """Enriches fuel data with derived columns and baseline calculations."""
    
    def __init__(self):
        """Initialize enricher with baseline cache."""
        self.baselines: Dict[str, pd.DataFrame] = {}
    
    def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived columns to the DataFrame.
        
        Args:
            df: Input DataFrame with raw fuel data
            
        Returns:
            Enriched DataFrame with additional columns
            
        Raises:
            EnricherError: If required columns are missing
        """
        required = ["planned_fuel_kg", "actual_fuel_kg", "route", "aircraft_type"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise EnricherError(f"Missing required columns for enrichment: {missing}")
        
        df = df.copy()

        if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = pd.to_datetime(df["date"])

        df = self._add_fuel_variance(df)
        df = self._add_total_weight(df)
        df = self._add_fuel_efficiency(df)
        df = self._add_baseline_expected_fuel(df)
        df = self._add_deviation_from_baseline(df)
        
        return df
    
    def _add_fuel_variance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate fuel variance percentage."""
        df["fuel_variance_pct"] = (
            (df["actual_fuel_kg"] - df["planned_fuel_kg"]) / df["planned_fuel_kg"] * 100
        )
        return df
    
    def _add_total_weight(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate total payload weight."""
        weight_cols = ["cargo_weight_kg", "catering_weight_kg"]
        
        if "passengers" in df.columns:
            avg_passenger_weight = 85
            df["passenger_weight_kg"] = df["passengers"] * avg_passenger_weight
            weight_cols.append("passenger_weight_kg")
        
        available_cols = [col for col in weight_cols if col in df.columns]
        if available_cols:
            df["total_payload_kg"] = df[available_cols].sum(axis=1)
        
        return df
    
    def _add_fuel_efficiency(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate fuel efficiency metrics."""
        if "duration_min" in df.columns and df["duration_min"].gt(0).all():
            df["fuel_per_minute"] = df["actual_fuel_kg"] / df["duration_min"]
        
        if "total_payload_kg" in df.columns and df["total_payload_kg"].gt(0).all():
            df["fuel_per_ton_payload"] = df["actual_fuel_kg"] / (df["total_payload_kg"] / 1000)
        
        return df
    
    def _add_baseline_expected_fuel(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate expected fuel consumption baseline per route and aircraft type.
        
        Uses median fuel consumption for each route-aircraft combination as baseline.
        """
        baseline = df.groupby(["route", "aircraft_type"])["actual_fuel_kg"].agg(
            expected_fuel_kg="median",
            fuel_std="std",
            flight_count="count"
        ).reset_index()
        
        self.baselines["route_aircraft"] = baseline
        
        df = df.merge(
            baseline[["route", "aircraft_type", "expected_fuel_kg", "fuel_std"]],
            on=["route", "aircraft_type"],
            how="left"
        )
        
        df["expected_fuel_kg"] = df["expected_fuel_kg"].fillna(df["planned_fuel_kg"])
        df["fuel_std"] = df["fuel_std"].fillna(df["actual_fuel_kg"].std())
        
        return df
    
    def _add_deviation_from_baseline(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate deviation from baseline in standard deviations."""
        if "expected_fuel_kg" in df.columns and "fuel_std" in df.columns:
            df["baseline_deviation_sigma"] = (
                (df["actual_fuel_kg"] - df["expected_fuel_kg"]) / df["fuel_std"]
            )
            df["baseline_deviation_sigma"] = df["baseline_deviation_sigma"].replace(
                [np.inf, -np.inf], np.nan
            )
        
        return df
    
    def get_baselines(self) -> Dict[str, pd.DataFrame]:
        """Return calculated baselines for inspection."""
        return self.baselines
