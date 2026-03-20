"""Generate realistic synthetic fuel log data using Faker.

Usage:
    python data/generate_fuel_logs.py               # 500 rows → data/sample_fuel_logs.csv
    python data/generate_fuel_logs.py --rows 1000   # custom row count
    python data/generate_fuel_logs.py --seed 99     # reproducible output
"""

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

# ---------------------------------------------------------------------------
# Fleet and route configuration (realistic Jet2 operations)
# ---------------------------------------------------------------------------

ROUTES = {
    # route: (duration_min_range, planned_fuel_range_kg)
    "LBA-ALC": (155, 175, 4200, 4800),
    "LBA-PMI": (140, 160, 3900, 4500),
    "LBA-TFS": (225, 255, 5900, 6500),
    "LBA-AGP": (160, 180, 4600, 5100),
    "LBA-FAO": (165, 185, 4700, 5200),
    "MAN-ALC": (145, 165, 4400, 5000),
    "MAN-PMI": (140, 160, 4000, 4600),
    "MAN-TFS": (230, 255, 6100, 6700),
    "MAN-FAO": (165, 190, 5300, 5900),
    "MAN-AGP": (160, 180, 4800, 5300),
    "BHX-PMI": (145, 165, 4900, 5500),
    "BHX-ALC": (155, 175, 4800, 5400),
    "BHX-TFS": (235, 260, 6500, 7100),
    "BHX-FAO": (170, 195, 5500, 6100),
    "BHX-AGP": (165, 185, 5100, 5700),
    "EMA-PMI": (145, 170, 4600, 5200),
    "EMA-ALC": (150, 175, 4700, 5300),
    "EMA-TFS": (228, 252, 6000, 6600),
    "NCL-PMI": (160, 185, 5000, 5600),
    "NCL-TFS": (240, 265, 6300, 6900),
}

AIRCRAFT = {
    "737-800": {"pax_range": (150, 189), "cargo_range": (800, 2500)},
    "757-200": {"pax_range": (200, 235), "cargo_range": (1200, 3500)},
    "737 MAX 8": {"pax_range": (150, 189), "cargo_range": (800, 2500)},
}

AIRCRAFT_ROUTE_PREFERENCE = {
    "737-800": 0.55,
    "757-200": 0.30,
    "737 MAX 8": 0.15,
}

WEATHER_CONDITIONS = ["Clear", "Cloudy", "Windy", "Light Rain", "Overcast"]
WIND_DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

ANOMALY_RATE = 0.06  # ~6% of flights will have an injected anomaly


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def random_flight_id(rng: random.Random) -> str:
    """Return a 16-digit numeric flight ID as a string."""
    return str(rng.randint(10 ** 15, 10 ** 16 - 1))


def random_departure_datetime(rng: random.Random, base_date: datetime) -> datetime:
    """Return a departure datetime on base_date at a realistic time (05:00–23:30)."""
    departure_hour = rng.randint(5, 23)
    departure_minute = rng.choice([0, 15, 30, 45])
    return base_date.replace(hour=departure_hour, minute=departure_minute, second=0, microsecond=0)


def generate_row(fake: Faker, rng: random.Random, departure_dt: datetime) -> dict:
    route = rng.choice(list(ROUTES.keys()))
    dur_min, dur_max, fuel_min, fuel_max = ROUTES[route]

    aircraft_type = rng.choices(
        list(AIRCRAFT_ROUTE_PREFERENCE.keys()),
        weights=list(AIRCRAFT_ROUTE_PREFERENCE.values()),
    )[0]
    aircraft_cfg = AIRCRAFT[aircraft_type]

    duration_min = rng.randint(dur_min, dur_max)
    planned_fuel = rng.randint(fuel_min, fuel_max)

    # Normal actual fuel: ±8% of planned
    actual_fuel = round(planned_fuel * rng.uniform(0.92, 1.08))

    # Inject anomaly into a small fraction of flights
    if rng.random() < ANOMALY_RATE:
        anomaly_kind = rng.choice(["high", "low", "extreme"])
        if anomaly_kind == "high":
            actual_fuel = round(planned_fuel * rng.uniform(1.25, 1.60))
        elif anomaly_kind == "low":
            actual_fuel = round(planned_fuel * rng.uniform(0.45, 0.68))
        else:
            actual_fuel = round(planned_fuel * rng.uniform(1.55, 2.00))

    passengers = rng.randint(*aircraft_cfg["pax_range"])
    cargo_weight_kg = rng.randint(*aircraft_cfg["cargo_range"])
    catering_weight_kg = round(passengers * rng.uniform(0.7, 1.1))

    wind_speed_kts = rng.randint(0, 45)
    wind_direction = rng.choice(WIND_DIRECTIONS)
    temperature_c = rng.randint(-15, 38)
    visibility = rng.randint(3, 10)
    weather_conditions = rng.choice(WEATHER_CONDITIONS)
    departure_delay_min = rng.choices(
        [0, rng.randint(1, 10), rng.randint(11, 60)],
        weights=[0.6, 0.3, 0.1],
    )[0]
    taxi_time_min = rng.randint(7, 25)

    return {
        "flight_id": random_flight_id(rng),
        "date": departure_dt.strftime("%Y-%m-%d %H:%M"),
        "route": route,
        "aircraft_type": aircraft_type,
        "planned_fuel_kg": planned_fuel,
        "actual_fuel_kg": actual_fuel,
        "duration_min": duration_min,
        "passengers": passengers,
        "cargo_weight_kg": cargo_weight_kg,
        "catering_weight_kg": catering_weight_kg,
        "wind_speed_kts": wind_speed_kts,
        "wind_direction": wind_direction,
        "temperature_c": temperature_c,
        "visibility": visibility,
        "weather_conditions": weather_conditions,
        "departure_delay_min": departure_delay_min,
        "taxi_time_min": taxi_time_min,
    }


def generate_dataset(rows: int, seed: int) -> list[dict]:
    fake = Faker("en_GB")
    Faker.seed(seed)
    rng = random.Random(seed)

    # Spread flights across a 90-day window ending today
    end_date = datetime(2026, 2, 20)
    start_date = end_date - timedelta(days=89)
    date_range = [start_date + timedelta(days=d) for d in range(90)]

    records = []
    for _ in range(rows):
        base_date = rng.choice(date_range)
        departure_dt = random_departure_datetime(rng, base_date)
        records.append(generate_row(fake, rng, departure_dt))

    return records


def write_csv(records: list[dict], output_path: Path) -> None:
    fieldnames = [
        "flight_id", "date", "route", "aircraft_type",
        "planned_fuel_kg", "actual_fuel_kg", "duration_min",
        "passengers", "cargo_weight_kg", "catering_weight_kg",
        "wind_speed_kts", "wind_direction", "temperature_c",
        "visibility", "weather_conditions",
        "departure_delay_min", "taxi_time_min",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic fuel log CSV data.")
    parser.add_argument("--rows", type=int, default=500, help="Number of rows to generate (default: 500)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument(
        "--output",
        default="data/sample_fuel_logs.csv",
        help="Output CSV path (default: data/sample_fuel_logs.csv)",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.rows} rows (seed={args.seed}) → {output_path}")
    records = generate_dataset(args.rows, args.seed)
    write_csv(records, output_path)
    print(f"Done. {len(records)} rows written to {output_path}")


if __name__ == "__main__":
    main()
