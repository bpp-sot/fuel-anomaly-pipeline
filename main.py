#!/usr/bin/env python3
"""Main CLI entry point for Jet2 Fuel Anomaly Detection System.

Usage:
    python main.py [options]
    
Example:
    python main.py --input data/sample_fuel_logs.csv --output output/
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from src.loader import load_fuel_data, load_fuel_data_from_s3, LoaderError
from src.validator import FuelDataValidator, ValidatorError
from src.enricher import FuelDataEnricher, EnricherError
from src.detector import FuelAnomalyDetector, DetectorError
from src.reporter import AnomalyReporter, ReporterError
from src.visualizer import FuelVisualizer, VisualizerError


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Jet2 Fuel Anomaly Detection System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "-i", "--input",
        default="data/sample_fuel_logs.csv",
        help="Path to input CSV file (default: data/sample_fuel_logs.csv)"
    )

    parser.add_argument(
        "--s3-input",
        default=None,
        metavar="S3_URL",
        help="S3 URL to input CSV file (e.g. s3://my-bucket/logs/fuel.csv). "
             "When provided, --input is ignored."
    )
    
    parser.add_argument(
        "-o", "--output",
        default="output",
        help="Output directory for reports and charts (default: output)"
    )
    
    parser.add_argument(
        "--variance-threshold",
        type=float,
        default=20.0,
        help="Variance threshold percentage for anomaly detection (default: 20.0)"
    )
    
    parser.add_argument(
        "--sigma-threshold",
        type=float,
        default=2.5,
        help="Standard deviation threshold for statistical outliers (default: 2.5)"
    )
    
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Skip chart generation"
    )
    
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Generate JSON report only (skip text report)"
    )
    
    return parser.parse_args()


def main():
    """Main execution flow."""
    args = parse_args()
    
    print("=" * 70)
    print("JET2 FUEL ANOMALY DETECTION SYSTEM")
    print("=" * 70)
    print()
    
    try:
        if args.s3_input:
            print(f"[1/6] Loading data from S3: {args.s3_input}")
            df = load_fuel_data_from_s3(args.s3_input)
        else:
            print(f"[1/6] Loading data from: {args.input}")
            df = load_fuel_data(args.input)
        print(f"      Loaded {len(df)} flight records")
        print()
        
        print("[2/6] Validating data...")
        validator = FuelDataValidator(strict=False)
        df = validator.validate(df)
        
        if validator.errors:
            print(f"      Warning: Found {len(validator.errors)} validation errors")
            for err in validator.errors[:3]:
                print(f"        - Row {err.row_index}: {err.message}")
            if len(validator.errors) > 3:
                print(f"        ... and {len(validator.errors) - 3} more")
        else:
            print("      All data valid")
        print()
        
        print("[3/6] Enriching data with derived columns...")
        original_column_count = len(df.columns)
        enricher = FuelDataEnricher()
        df = enricher.enrich(df)
        print(f"      Added {len(df.columns) - original_column_count} derived columns")
        print()
        
        print("[4/6] Detecting anomalies...")
        detector = FuelAnomalyDetector(
            variance_threshold=args.variance_threshold,
            sigma_threshold=args.sigma_threshold
        )
        anomalies = detector.detect(df)
        summary = detector.get_anomaly_summary()
        
        print(f"      Detected {summary.get('total', 0)} anomalies")
        if summary.get("by_severity"):
            for severity, count in summary["by_severity"].items():
                print(f"        - {severity.upper()}: {count}")
        print()
        
        print(f"[5/6] Generating reports in: {args.output}")
        reporter = AnomalyReporter(output_dir=args.output)
        
        report_paths = []
        
        if not args.json_only:
            text_path = reporter.generate_text_report(anomalies, summary)
            report_paths.append(text_path)
            print(f"      Text report: {text_path}")
        
        json_path = reporter.generate_json_report(anomalies, summary)
        report_paths.append(json_path)
        print(f"      JSON report: {json_path}")
        print()
        
        if not args.no_charts:
            print("[6/6] Generating visualizations...")
            visualizer = FuelVisualizer(output_dir=args.output)
            chart_paths = visualizer.generate_all_charts(df, anomalies)
            
            for chart_path in chart_paths:
                print(f"      Chart: {chart_path}")
        else:
            print("[6/6] Skipping chart generation (--no-charts)")
        
        print()
        reporter.print_summary(summary)
        
        print("✓ Analysis complete!")
        print()
        
        return 0
    
    except LoaderError as e:
        print(f"ERROR [Loader]: {e}", file=sys.stderr)
        return 1
    except ValidatorError as e:
        print(f"ERROR [Validator]: {e}", file=sys.stderr)
        return 1
    except EnricherError as e:
        print(f"ERROR [Enricher]: {e}", file=sys.stderr)
        return 1
    except DetectorError as e:
        print(f"ERROR [Detector]: {e}", file=sys.stderr)
        return 1
    except ReporterError as e:
        print(f"ERROR [Reporter]: {e}", file=sys.stderr)
        return 1
    except VisualizerError as e:
        print(f"ERROR [Visualizer]: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR [Unexpected]: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
