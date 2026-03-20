"""Visualization module for fuel anomaly analysis.

Generates static charts using matplotlib and seaborn for report inclusion.
Uses the non-interactive Agg backend so charts render correctly in headless
environments such as Docker containers with no display attached.
"""

import matplotlib
matplotlib.use("Agg")  # must be set before importing pyplot

from pathlib import Path
from typing import List, Optional
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from .detector import Anomaly


class VisualizerError(Exception):
    """Custom exception for visualization errors."""
    pass


class FuelVisualizer:
    """Creates static visualizations for fuel anomaly analysis."""
    
    def __init__(self, output_dir: str = "output"):
        """Initialize visualizer with output directory.
        
        Args:
            output_dir: Directory to save chart images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        sns.set_style("whitegrid")
        sns.set_palette("husl")
    
    def generate_all_charts(
        self,
        df: pd.DataFrame,
        anomalies: List[Anomaly]
    ) -> List[str]:
        """Generate all standard charts for the report.
        
        Args:
            df: Enriched DataFrame with fuel data
            anomalies: List of detected anomalies
            
        Returns:
            List of paths to generated chart files
        """
        chart_paths = []
        
        try:
            chart_paths.append(self.plot_time_series(df, anomalies))
            chart_paths.append(self.plot_variance_distribution(df))
            chart_paths.append(self.plot_actual_vs_planned(df, anomalies))
            chart_paths.append(self.plot_anomaly_counts(anomalies))
        except Exception as e:
            raise VisualizerError(f"Failed to generate charts: {e}")
        
        return chart_paths
    
    def plot_time_series(
        self,
        df: pd.DataFrame,
        anomalies: List[Anomaly],
        output_file: str = "time_series.png"
    ) -> str:
        """Plot actual vs planned fuel over time.
        
        Args:
            df: DataFrame with fuel data
            anomalies: List of anomalies to highlight
            output_file: Output filename
            
        Returns:
            Path to saved chart
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        df_sorted = df.copy()
        df_sorted["date"] = pd.to_datetime(df_sorted["date"])
        df_sorted = df_sorted.sort_values("date")

        ax.plot(
            df_sorted["date"],
            df_sorted["planned_fuel_kg"],
            label="Planned Fuel",
            marker="o",
            linestyle="--",
            alpha=0.7
        )
        ax.plot(
            df_sorted["date"],
            df_sorted["actual_fuel_kg"],
            label="Actual Fuel",
            marker="s",
            linestyle="-",
            alpha=0.7
        )

        anomaly_ids = {a.flight_id for a in anomalies}
        anomaly_mask = df_sorted["flight_id"].isin(anomaly_ids)

        if anomaly_mask.any():
            ax.scatter(
                df_sorted.loc[anomaly_mask, "date"],
                df_sorted.loc[anomaly_mask, "actual_fuel_kg"],
                color="red",
                s=100,
                marker="X",
                label="Anomalies",
                zorder=5
            )

        fig.autofmt_xdate()
        ax.set_xlabel("Date / Departure Time")
        ax.set_ylabel("Fuel (kg)")
        ax.set_title("Fuel Consumption Over Time")
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        output_path = self.output_dir / output_file
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        
        return str(output_path)
    
    def plot_variance_distribution(
        self,
        df: pd.DataFrame,
        output_file: str = "variance_distribution.png"
    ) -> str:
        """Plot histogram of fuel variance percentages.
        
        Args:
            df: DataFrame with fuel_variance_pct column
            output_file: Output filename
            
        Returns:
            Path to saved chart
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if "fuel_variance_pct" not in df.columns:
            raise VisualizerError("fuel_variance_pct column not found")
        
        variance_data = df["fuel_variance_pct"].dropna()
        
        ax.hist(variance_data, bins=30, edgecolor="black", alpha=0.7)
        ax.axvline(x=0, color="green", linestyle="--", linewidth=2, label="Zero Variance")
        ax.axvline(x=20, color="orange", linestyle="--", linewidth=1.5, label="Threshold (+20%)")
        ax.axvline(x=-20, color="orange", linestyle="--", linewidth=1.5, label="Threshold (-20%)")
        
        ax.set_xlabel("Fuel Variance (%)")
        ax.set_ylabel("Frequency")
        ax.set_title("Distribution of Fuel Variance")
        ax.legend()
        ax.grid(True, alpha=0.3, axis="y")
        
        output_path = self.output_dir / output_file
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        
        return str(output_path)
    
    def plot_actual_vs_planned(
        self,
        df: pd.DataFrame,
        anomalies: List[Anomaly],
        output_file: str = "actual_vs_planned.png"
    ) -> str:
        """Scatter plot of actual vs planned fuel with anomalies highlighted.
        
        Args:
            df: DataFrame with fuel data
            anomalies: List of anomalies to highlight
            output_file: Output filename
            
        Returns:
            Path to saved chart
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        anomaly_ids = {a.flight_id for a in anomalies}
        normal_mask = ~df["flight_id"].isin(anomaly_ids)
        anomaly_mask = df["flight_id"].isin(anomaly_ids)
        
        ax.scatter(
            df[normal_mask]["planned_fuel_kg"],
            df[normal_mask]["actual_fuel_kg"],
            alpha=0.6,
            label="Normal Flights",
            s=50
        )
        
        if anomaly_mask.any():
            ax.scatter(
                df[anomaly_mask]["planned_fuel_kg"],
                df[anomaly_mask]["actual_fuel_kg"],
                color="red",
                alpha=0.8,
                label="Anomalies",
                s=100,
                marker="X"
            )
        
        max_fuel = max(df["planned_fuel_kg"].max(), df["actual_fuel_kg"].max())
        min_fuel = min(df["planned_fuel_kg"].min(), df["actual_fuel_kg"].min())
        ax.plot([min_fuel, max_fuel], [min_fuel, max_fuel], "k--", alpha=0.5, label="Perfect Match")
        
        ax.set_xlabel("Planned Fuel (kg)")
        ax.set_ylabel("Actual Fuel (kg)")
        ax.set_title("Actual vs Planned Fuel Consumption")
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        output_path = self.output_dir / output_file
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        
        return str(output_path)
    
    def plot_anomaly_counts(
        self,
        anomalies: List[Anomaly],
        output_file: str = "anomaly_counts.png",
        group_by: str = "route"
    ) -> str:
        """Bar chart of anomaly counts by route or aircraft type.
        
        Args:
            anomalies: List of detected anomalies
            output_file: Output filename
            group_by: Group by 'route' or 'aircraft_type'
            
        Returns:
            Path to saved chart
        """
        if not anomalies:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No anomalies detected", 
                   ha="center", va="center", fontsize=16)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            
            output_path = self.output_dir / output_file
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            plt.close()
            return str(output_path)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        anomaly_df = pd.DataFrame([
            {"route": a.route, "aircraft_type": a.aircraft_type}
            for a in anomalies
        ])
        
        if group_by == "route":
            counts = anomaly_df["route"].value_counts()
            xlabel = "Route"
        else:
            counts = anomaly_df["aircraft_type"].value_counts()
            xlabel = "Aircraft Type"
        
        counts.plot(kind="bar", ax=ax, color="coral", edgecolor="black")
        
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Number of Anomalies")
        ax.set_title(f"Anomaly Count by {xlabel}")
        ax.grid(True, alpha=0.3, axis="y")
        plt.xticks(rotation=45, ha="right")
        
        output_path = self.output_dir / output_file
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        
        return str(output_path)
