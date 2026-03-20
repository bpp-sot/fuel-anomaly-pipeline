"""Anomaly detection module for fuel consumption data.

Implements multiple detection strategies: threshold-based, statistical, and contextual.
"""

from dataclasses import dataclass
from typing import List, Dict, Set
import pandas as pd
import numpy as np


@dataclass
class Anomaly:
    """Represents a detected fuel anomaly."""
    flight_id: str
    date: str
    route: str
    aircraft_type: str
    anomaly_type: str
    severity: str
    planned_fuel: float
    actual_fuel: float
    variance_pct: float
    details: str


class DetectorError(Exception):
    """Custom exception for detection errors."""
    pass


class FuelAnomalyDetector:
    """Detects anomalies in fuel consumption data using multiple strategies."""
    
    def __init__(
        self,
        variance_threshold: float = 20.0,
        sigma_threshold: float = 2.5,
        min_flights_for_baseline: int = 3
    ):
        """Initialize detector with configurable thresholds.
        
        Args:
            variance_threshold: Percentage variance to flag as anomaly
            sigma_threshold: Number of standard deviations for statistical anomaly
            min_flights_for_baseline: Minimum flights needed for route baseline
        """
        self.variance_threshold = variance_threshold
        self.sigma_threshold = sigma_threshold
        self.min_flights_for_baseline = min_flights_for_baseline
        self.anomalies: List[Anomaly] = []
    
    def detect(self, df: pd.DataFrame) -> List[Anomaly]:
        """Run all anomaly detection strategies on the DataFrame.
        
        Args:
            df: Enriched DataFrame with fuel data
            
        Returns:
            List of detected anomalies
            
        Raises:
            DetectorError: If required columns are missing
        """
        required = ["flight_id", "date", "route", "planned_fuel_kg", "actual_fuel_kg"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise DetectorError(f"Missing required columns: {missing}")
        
        self.anomalies = []
        
        self._detect_high_variance(df)
        self._detect_low_variance(df)
        self._detect_statistical_outliers(df)
        self._detect_duplicate_flights(df)
        
        return self.anomalies
    
    def _detect_high_variance(self, df: pd.DataFrame) -> None:
        """Detect flights with actual fuel significantly higher than planned."""
        if "fuel_variance_pct" not in df.columns:
            return
        
        high_variance = df[df["fuel_variance_pct"] > self.variance_threshold]
        
        for _, row in high_variance.iterrows():
            severity = self._calculate_severity(row["fuel_variance_pct"])
            
            self.anomalies.append(Anomaly(
                flight_id=row["flight_id"],
                date=str(row["date"]),
                route=row["route"],
                aircraft_type=row.get("aircraft_type", "Unknown"),
                anomaly_type="high_fuel_variance",
                severity=severity,
                planned_fuel=row["planned_fuel_kg"],
                actual_fuel=row["actual_fuel_kg"],
                variance_pct=row["fuel_variance_pct"],
                details=f"Actual fuel {row['fuel_variance_pct']:.1f}% higher than planned"
            ))
    
    def _detect_low_variance(self, df: pd.DataFrame) -> None:
        """Detect flights with actual fuel significantly lower than planned.
        
        May indicate incomplete refueling data or data entry errors.
        """
        if "fuel_variance_pct" not in df.columns:
            return
        
        low_variance = df[df["fuel_variance_pct"] < -self.variance_threshold]
        
        for _, row in low_variance.iterrows():
            severity = self._calculate_severity(abs(row["fuel_variance_pct"]))
            
            self.anomalies.append(Anomaly(
                flight_id=row["flight_id"],
                date=str(row["date"]),
                route=row["route"],
                aircraft_type=row.get("aircraft_type", "Unknown"),
                anomaly_type="low_fuel_variance",
                severity=severity,
                planned_fuel=row["planned_fuel_kg"],
                actual_fuel=row["actual_fuel_kg"],
                variance_pct=row["fuel_variance_pct"],
                details=f"Actual fuel {abs(row['fuel_variance_pct']):.1f}% lower than planned"
            ))
    
    def _detect_statistical_outliers(self, df: pd.DataFrame) -> None:
        """Detect statistical outliers based on deviation from route baseline."""
        if "baseline_deviation_sigma" not in df.columns:
            return
        
        outliers = df[
            df["baseline_deviation_sigma"].abs() > self.sigma_threshold
        ].dropna(subset=["baseline_deviation_sigma"])
        
        for _, row in outliers.iterrows():
            sigma_val = row["baseline_deviation_sigma"]
            severity = "critical" if abs(sigma_val) > 3.0 else "high"
            
            self.anomalies.append(Anomaly(
                flight_id=row["flight_id"],
                date=str(row["date"]),
                route=row["route"],
                aircraft_type=row.get("aircraft_type", "Unknown"),
                anomaly_type="statistical_outlier",
                severity=severity,
                planned_fuel=row["planned_fuel_kg"],
                actual_fuel=row["actual_fuel_kg"],
                variance_pct=row.get("fuel_variance_pct", 0.0),
                details=f"Fuel consumption {sigma_val:.2f}σ from route baseline"
            ))
    
    def _detect_duplicate_flights(self, df: pd.DataFrame) -> None:
        """Detect potential duplicate flight records."""
        duplicate_cols = ["flight_id", "date"]
        
        if not all(col in df.columns for col in duplicate_cols):
            return
        
        duplicates = df[df.duplicated(subset=duplicate_cols, keep=False)]
        
        if not duplicates.empty:
            for flight_id in duplicates["flight_id"].unique():
                dup_rows = duplicates[duplicates["flight_id"] == flight_id]
                first_row = dup_rows.iloc[0]
                
                self.anomalies.append(Anomaly(
                    flight_id=flight_id,
                    date=str(first_row["date"]),
                    route=first_row["route"],
                    aircraft_type=first_row.get("aircraft_type", "Unknown"),
                    anomaly_type="duplicate_record",
                    severity="medium",
                    planned_fuel=first_row["planned_fuel_kg"],
                    actual_fuel=first_row["actual_fuel_kg"],
                    variance_pct=first_row.get("fuel_variance_pct", 0.0),
                    details=f"Found {len(dup_rows)} duplicate records for this flight"
                ))
    
    def _calculate_severity(self, variance_pct: float) -> str:
        """Calculate severity level based on variance percentage."""
        abs_variance = abs(variance_pct)
        
        if abs_variance > 50:
            return "critical"
        elif abs_variance > 30:
            return "high"
        elif abs_variance > 20:
            return "medium"
        else:
            return "low"
    
    def get_anomaly_summary(self) -> Dict[str, int]:
        """Return summary statistics of detected anomalies.
        
        Returns:
            Dictionary with counts by anomaly type and severity
        """
        if not self.anomalies:
            return {"total": 0}
        
        summary = {
            "total": len(self.anomalies),
            "by_type": {},
            "by_severity": {}
        }
        
        for anomaly in self.anomalies:
            summary["by_type"][anomaly.anomaly_type] = \
                summary["by_type"].get(anomaly.anomaly_type, 0) + 1
            summary["by_severity"][anomaly.severity] = \
                summary["by_severity"].get(anomaly.severity, 0) + 1
        
        return summary
    
    def get_anomalies_df(self) -> pd.DataFrame:
        """Convert anomalies list to DataFrame for analysis.
        
        Returns:
            DataFrame with all detected anomalies
        """
        if not self.anomalies:
            return pd.DataFrame()
        
        return pd.DataFrame([
            {
                "flight_id": a.flight_id,
                "date": a.date,
                "route": a.route,
                "aircraft_type": a.aircraft_type,
                "anomaly_type": a.anomaly_type,
                "severity": a.severity,
                "planned_fuel_kg": a.planned_fuel,
                "actual_fuel_kg": a.actual_fuel,
                "variance_pct": a.variance_pct,
                "details": a.details
            }
            for a in self.anomalies
        ])
