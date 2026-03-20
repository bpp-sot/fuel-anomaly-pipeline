"""Report generation module for anomaly detection results.

Generates text and JSON reports summarizing detected anomalies.
"""

import json
from pathlib import Path
from typing import Any, List, Dict
from datetime import datetime
from .detector import Anomaly


class ReporterError(Exception):
    """Custom exception for report generation errors."""
    pass


class AnomalyReporter:
    """Generates reports from detected anomalies."""
    
    def __init__(self, output_dir: str = "output"):
        """Initialize reporter with output directory.
        
        Args:
            output_dir: Directory to save reports (created if doesn't exist)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_text_report(
        self,
        anomalies: List[Anomaly],
        summary: Dict[str, Any],
        output_file: str = "anomaly_report.txt"
    ) -> str:
        """Generate human-readable text report.
        
        Args:
            anomalies: List of detected anomalies
            summary: Summary statistics dictionary
            output_file: Output filename
            
        Returns:
            Path to generated report file
        """
        output_path = self.output_dir / output_file
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("JET2 FUEL ANOMALY DETECTION REPORT\n")
                f.write("=" * 80 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("SUMMARY\n")
                f.write("-" * 80 + "\n")
                f.write(f"Total anomalies detected: {summary.get('total', 0)}\n\n")
                
                if "by_type" in summary:
                    f.write("Anomalies by type:\n")
                    for anom_type, count in summary["by_type"].items():
                        f.write(f"  - {anom_type}: {count}\n")
                    f.write("\n")
                
                if "by_severity" in summary:
                    f.write("Anomalies by severity:\n")
                    for severity, count in summary["by_severity"].items():
                        f.write(f"  - {severity.upper()}: {count}\n")
                    f.write("\n")
                
                if anomalies:
                    f.write("\nDETAILED ANOMALIES\n")
                    f.write("-" * 80 + "\n\n")
                    
                    for i, anomaly in enumerate(anomalies, 1):
                        f.write(f"[{i}] Flight {anomaly.flight_id} ({anomaly.date})\n")
                        f.write(f"    Route: {anomaly.route}\n")
                        f.write(f"    Aircraft: {anomaly.aircraft_type}\n")
                        f.write(f"    Type: {anomaly.anomaly_type}\n")
                        f.write(f"    Severity: {anomaly.severity.upper()}\n")
                        f.write(f"    Planned: {anomaly.planned_fuel:.0f} kg\n")
                        f.write(f"    Actual: {anomaly.actual_fuel:.0f} kg\n")
                        f.write(f"    Variance: {anomaly.variance_pct:+.1f}%\n")
                        f.write(f"    Details: {anomaly.details}\n")
                        f.write("\n")
                
                f.write("=" * 80 + "\n")
                f.write("END OF REPORT\n")
                f.write("=" * 80 + "\n")
        
        except IOError as e:
            raise ReporterError(f"Failed to write text report: {e}")
        
        return str(output_path)
    
    def generate_json_report(
        self,
        anomalies: List[Anomaly],
        summary: Dict[str, Any],
        output_file: str = "anomaly_report.json"
    ) -> str:
        """Generate machine-readable JSON report.
        
        Args:
            anomalies: List of detected anomalies
            summary: Summary statistics dictionary
            output_file: Output filename
            
        Returns:
            Path to generated report file
        """
        output_path = self.output_dir / output_file
        
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "anomalies": [
                {
                    "flight_id": a.flight_id,
                    "date": a.date,
                    "route": a.route,
                    "aircraft_type": a.aircraft_type,
                    "anomaly_type": a.anomaly_type,
                    "severity": a.severity,
                    "planned_fuel_kg": a.planned_fuel,
                    "actual_fuel_kg": a.actual_fuel,
                    "variance_pct": round(a.variance_pct, 2),
                    "details": a.details
                }
                for a in anomalies
            ]
        }
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
        except IOError as e:
            raise ReporterError(f"Failed to write JSON report: {e}")
        
        return str(output_path)
    
    def print_summary(self, summary: Dict[str, Any]) -> None:
        """Print summary to console.
        
        Args:
            summary: Summary statistics dictionary
        """
        print("\n" + "=" * 60)
        print("FUEL ANOMALY DETECTION SUMMARY")
        print("=" * 60)
        print(f"Total anomalies: {summary.get('total', 0)}")
        
        if "by_type" in summary and summary["by_type"]:
            print("\nBy type:")
            for anom_type, count in summary["by_type"].items():
                print(f"  {anom_type}: {count}")
        
        if "by_severity" in summary and summary["by_severity"]:
            print("\nBy severity:")
            for severity, count in summary["by_severity"].items():
                print(f"  {severity.upper()}: {count}")
        
        print("=" * 60 + "\n")
