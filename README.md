# Jet2 Fuel Anomaly Detection System

A Python-based tool for detecting anomalies in aircraft fuel consumption data, designed for Jet2 operations.

## Business Problem

Airlines face significant costs from fuel consumption. Anomalies in fuel data can indicate:
- Data entry errors or incomplete records
- Operational inefficiencies
- Potential fraud or misreporting
- Equipment issues requiring investigation

This tool analyzes fuel logs with contextual factors (weather, payload, route) to identify statistically significant deviations.

## Features

- **Multi-factor analysis:** Considers weather, cargo, catering, passenger load
- **Multiple detection strategies:** Threshold-based, statistical outliers, duplicate detection
- **Comprehensive error handling:** Validates data schema, types, ranges, and missing values
- **Rich data structures:** Pandas DataFrames, dataclasses, dicts, sets, lists
- **Automated reporting:** Text and JSON reports with anomaly details
- **Static visualizations:** Charts for time series, distributions, and comparisons
- **Full test coverage:** pytest suite for all modules
- **Streamlit UI:** Optional web interface (`app.py`) for interactive runs

## Architecture

```
┌─────────────┐
│   CSV File  │
└──────┬──────┘
       │
       v
┌─────────────┐     ┌──────────────┐
│   Loader    │────>│  Validator   │
└─────────────┘     └──────┬───────┘
                           │
                           v
                    ┌──────────────┐
                    │   Enricher   │ (adds derived columns)
                    └──────┬───────┘
                           │
                           v
                    ┌──────────────┐
                    │   Detector   │ (anomaly logic)
                    └──────┬───────┘
                           │
                  ┌────────┴────────┐
                  v                 v
           ┌──────────────┐  ┌──────────────┐
           │   Reporter   │  │  Visualizer  │
           └──────────────┘  └──────────────┘
```

## Installation

### Local (development)

1. Clone the repository:

```bash
git clone git@github.com:bpp-sot/fuel-anomaly-pipeline.git
cd fuel-anomaly-pipeline
```

2. (Recommended) Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install --upgrade pip
```

3. Install dependencies. For the CLI, tests, and Streamlit UI:

```bash
pip install -r requirements-dev.txt
```

For the CLI only (no Streamlit/tests extras):

```bash
pip install -r requirements.txt
```

### Docker (CLI image)

The image includes `main.py` and `src/` only. Input CSV files are **not** baked in (`data/` is excluded), so you either mount a data directory or use `--s3-input`.

Build the image:

```bash
docker build -t fuel-anomaly-detector:latest .
```

#### After you build the image

1. **Create an output folder on the host** (optional but typical):

   ```bash
   mkdir -p output
   ```

2. **Run the container** in one of these ways:

   - **Local CSV** — mount your data and output directories. Paths below assume you run the command from the project root on the host:

     ```bash
     docker run --rm \
       -v "$(pwd)/data:/app/data:ro" \
       -v "$(pwd)/output:/app/output" \
       fuel-anomaly-detector:latest \
       --input /app/data/sample_fuel_logs.csv \
       --output /app/output
     ```

     Replace `/app/data/sample_fuel_logs.csv` with `/app/data/your_file.csv` as needed.

   - **S3** — pass AWS credentials and an S3 URL (see **Docker: run with S3 input, output to local folder** under Usage below).

3. **Inspect results** on the host under `./output/` (text/JSON reports and PNG charts), or wherever you mounted the output volume.

The container entrypoint is `python main.py`; any extra arguments you append are passed straight to `main.py` (for example `--no-charts`, `--variance-threshold 25`).

## Usage

### Local usage

Run analysis against a local CSV file:

```bash
python main.py
```

This uses the default sample data (`data/sample_fuel_logs.csv`) and writes reports and charts to the `output/` directory.

### Streamlit web UI (local)

Requires `requirements-dev.txt` (includes Streamlit and `python-dotenv`). Optional: put AWS-related variables in a `.env` file in the project root for S3 defaults in the UI.

```bash
streamlit run app.py
```

### Custom local input and output

```bash
python main.py --input path/to/fuel_data.csv --output results/
```

### Load input from AWS S3

Pass an S3 URL with `--s3-input`. AWS credentials are read from environment
variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`):

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=eu-west-1

python main.py \
  --s3-input s3://your-bucket/path/to/fuel_logs.csv \
  --output output/
```

### Docker: run with S3 input, output to local folder

Reports and charts are written to `./output/` on your host machine via a
Docker volume mount:

```bash
docker run --rm \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e AWS_DEFAULT_REGION=eu-west-1 \
  -v "$(pwd)/output:/app/output" \
  fuel-anomaly-detector:latest \
  --s3-input s3://your-bucket/path/to/fuel_logs.csv \
  --output /app/output
```

### Adjust detection thresholds

```bash
python main.py --variance-threshold 25.0 --sigma-threshold 3.0
```

### Skip chart generation

```bash
python main.py --no-charts
```

### JSON report only

```bash
python main.py --json-only
```

## Data Format

Input CSV should contain the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `flight_id` | string | Unique flight identifier |
| `date` | string | Flight date (YYYY-MM-DD) |
| `route` | string | Route code (e.g., LBA-ALC) |
| `aircraft_type` | string | Aircraft model (e.g., 737-800) |
| `planned_fuel_kg` | float | Planned fuel load (kg) |
| `actual_fuel_kg` | float | Actual fuel consumed (kg) |
| `duration_min` | int | Flight duration (minutes) |
| `passengers` | int | Number of passengers |
| `cargo_weight_kg` | float | Cargo weight (kg) |
| `catering_weight_kg` | float | Catering weight (kg) |
| `wind_speed_kts` | float | Wind speed (knots) |
| `temperature_c` | float | Temperature (Celsius) |

Optional columns: `wind_direction`, `visibility`, `weather_conditions`, `departure_delay_min`, `taxi_time_min`

## Anomaly Detection Methods

1. **High Variance:** Actual fuel > planned by threshold percentage (default: 20%)
2. **Low Variance:** Actual fuel < planned by threshold percentage (indicates data errors)
3. **Statistical Outliers:** Deviation from route/aircraft baseline > sigma threshold (default: 2.5σ)
4. **Duplicate Records:** Same flight_id and date appearing multiple times

## Output

### Text Report (`output/anomaly_report.txt`)
Human-readable summary with:
- Total anomaly count
- Breakdown by type and severity
- Detailed list of each anomaly

### JSON Report (`output/anomaly_report.json`)
Machine-readable format for integration with other systems.

### Charts (PNG, 300 DPI)
- `time_series.png`: Actual vs planned fuel over time
- `variance_distribution.png`: Histogram of fuel variance percentages
- `actual_vs_planned.png`: Scatter plot with anomalies highlighted
- `anomaly_counts.png`: Bar chart of anomalies by route

## Testing

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=src --cov-report=html
```

### Troubleshooting

If you encounter a segmentation fault on macOS with numpy/pandas, try:

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

For the full local stack (tests + Streamlit), use `pip install -r requirements-dev.txt` instead.

2. Or use conda:
```bash
conda create -n fuel-anomaly python=3.11
conda activate fuel-anomaly
pip install -r requirements-dev.txt
```

## Project Structure

```
fuel-anomaly-pipeline/
├── src/
│   ├── __init__.py
│   ├── loader.py       # Data loading with error handling
│   ├── validator.py    # Schema and value validation
│   ├── enricher.py     # Derived columns and baselines
│   ├── detector.py     # Anomaly detection logic
│   ├── reporter.py     # Report generation
│   └── visualizer.py   # Chart generation
├── data/
│   ├── sample_fuel_logs.csv
│   └── generate_fuel_logs.py
├── tests/
│   ├── test_loader.py
│   ├── test_validator.py
│   ├── test_enricher.py
│   └── test_detector.py
├── output/             # Generated reports and charts (gitignored)
├── main.py             # CLI entry point
├── app.py              # Streamlit UI
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Advanced Programming Concepts Demonstrated

- **Error handling:** Custom exceptions, try/except blocks, graceful degradation
- **Data structures:** DataFrames, dataclasses, dicts, sets, lists, NamedTuples
- **Type hints:** Full type annotations for clarity and IDE support
- **Modular design:** Separation of concerns across loader, validator, enricher, detector
- **Statistical analysis:** Baseline calculation, standard deviation, outlier detection
- **Testing:** Comprehensive pytest suite with fixtures and edge cases
- **I/O operations:** File reading, writing, path validation
- **Data transformation:** Pandas groupby, merge, aggregation, derived columns

## License

See course/organization terms.

## Repository

[https://github.com/bpp-sot/fuel-anomaly-pipeline](https://github.com/bpp-sot/fuel-anomaly-pipeline)
