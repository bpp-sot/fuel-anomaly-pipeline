"""Data validation module for fuel logs.

Validates schema, data types, required columns, and value ranges.
"""

from dataclasses import dataclass
from typing import List, Set
import pandas as pd
import numpy as np


@dataclass
class ValidationError:
    """Represents a validation error with context."""
    row_index: int
    column: str
    error_type: str
    message: str


class ValidatorError(Exception):
    """Custom exception for validation failures."""
    pass


class FuelDataValidator:
    """Validates fuel log data against expected schema and business rules."""
    
    REQUIRED_COLUMNS: Set[str] = {
        "flight_id", "date", "route", "aircraft_type",
        "planned_fuel_kg", "actual_fuel_kg", "duration_min",
        "passengers", "cargo_weight_kg", "catering_weight_kg",
        "wind_speed_kts", "temperature_c"
    }
    
    NUMERIC_COLUMNS: Set[str] = {
        "planned_fuel_kg", "actual_fuel_kg", "duration_min",
        "passengers", "cargo_weight_kg", "catering_weight_kg",
        "wind_speed_kts", "temperature_c", "departure_delay_min",
        "taxi_time_min"
    }
    
    def __init__(self, strict: bool = True):
        """Initialize validator.
        
        Args:
            strict: If True, raise exception on validation errors.
                   If False, collect errors and return them.
        """
        self.strict = strict
        self.errors: List[ValidationError] = []
    
    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate DataFrame and return cleaned version.
        
        Args:
            df: Input DataFrame to validate
            
        Returns:
            Validated DataFrame (may have rows removed if invalid)
            
        Raises:
            ValidatorError: If strict=True and validation fails
        """
        self.errors = []
        
        self._validate_schema(df)
        self._validate_data_types(df)
        self._validate_missing_values(df)
        self._validate_value_ranges(df)
        
        if self.strict and self.errors:
            error_summary = self._format_errors()
            raise ValidatorError(f"Validation failed:\n{error_summary}")
        
        return df
    
    def _validate_schema(self, df: pd.DataFrame) -> None:
        """Check that all required columns are present."""
        missing_cols = self.REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            raise ValidatorError(f"Missing required columns: {missing_cols}")
    
    def _validate_data_types(self, df: pd.DataFrame) -> None:
        """Validate that numeric columns contain numeric data and date is parseable."""
        for col in self.NUMERIC_COLUMNS:
            if col not in df.columns:
                continue
            
            if not pd.api.types.is_numeric_dtype(df[col]):
                try:
                    pd.to_numeric(df[col], errors='raise')
                except (ValueError, TypeError):
                    non_numeric = df[~df[col].apply(lambda x: isinstance(x, (int, float)) or pd.isna(x))]
                    for idx in non_numeric.index:
                        self.errors.append(ValidationError(
                            row_index=idx,
                            column=col,
                            error_type="dtype",
                            message=f"Non-numeric value in {col}: {df.loc[idx, col]}"
                        ))

        if "date" in df.columns:
            parsed = pd.to_datetime(df["date"], format="%Y-%m-%d %H:%M", errors="coerce")
            bad_mask = parsed.isna() & df["date"].notna()
            for idx in df[bad_mask].index:
                self.errors.append(ValidationError(
                    row_index=idx,
                    column="date",
                    error_type="dtype",
                    message=f"Invalid date format (expected YYYY-MM-DD HH:MM): {df.loc[idx, 'date']}"
                ))
    
    def _validate_missing_values(self, df: pd.DataFrame) -> None:
        """Check for missing values in critical columns."""
        critical_cols = ["flight_id", "planned_fuel_kg", "actual_fuel_kg"]
        
        for col in critical_cols:
            if col not in df.columns:
                continue
            
            null_mask = df[col].isna()
            if null_mask.any():
                for idx in df[null_mask].index:
                    self.errors.append(ValidationError(
                        row_index=idx,
                        column=col,
                        error_type="missing",
                        message=f"Missing value in critical column: {col}"
                    ))
    
    def _validate_value_ranges(self, df: pd.DataFrame) -> None:
        """Validate that values are within reasonable ranges."""
        range_checks = {
            "planned_fuel_kg": (0, 100000),
            "actual_fuel_kg": (0, 100000),
            "duration_min": (0, 1000),
            "passengers": (0, 500),
            "cargo_weight_kg": (0, 50000),
            "catering_weight_kg": (0, 5000),
            "wind_speed_kts": (0, 200),
            "temperature_c": (-60, 60),
        }
        
        for col, (min_val, max_val) in range_checks.items():
            if col not in df.columns:
                continue
            
            if not pd.api.types.is_numeric_dtype(df[col]):
                continue
            
            invalid_mask = (df[col] < min_val) | (df[col] > max_val)
            if invalid_mask.any():
                for idx in df[invalid_mask].index:
                    self.errors.append(ValidationError(
                        row_index=idx,
                        column=col,
                        error_type="range",
                        message=f"{col} out of range [{min_val}, {max_val}]: {df.loc[idx, col]}"
                    ))
    
    def _format_errors(self) -> str:
        """Format validation errors for display."""
        if not self.errors:
            return "No errors"
        
        lines = [f"Found {len(self.errors)} validation error(s):"]
        for i, err in enumerate(self.errors[:10], 1):
            lines.append(f"  {i}. Row {err.row_index}, {err.column}: {err.message}")
        
        if len(self.errors) > 10:
            lines.append(f"  ... and {len(self.errors) - 10} more errors")
        
        return "\n".join(lines)
    
    def get_errors(self) -> List[ValidationError]:
        """Return list of validation errors."""
        return self.errors
