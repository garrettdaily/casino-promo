"""Step 1 of the pipeline: read the raw CSV files with explicit data types."""

from pathlib import Path

import pandas as pd

# For each file: the columns we expect, the type of each column,
# and which columns are dates. Nothing is left for pandas to guess.
SCHEMAS = {
    "assignments": {
        "types": {
            "assignment_id": "str",
            "player_id": "str",
            "campaign_id": "str",
            "campaign_name": "str",
            "property": "str",
            "player_segment": "str",
            "group": "str",
            "offer_value": "float64",  # blank for holdout players
        },
        "dates": ["assigned_date"],
    },
    "visits": {
        "types": {
            "visit_id": "str",
            "player_id": "str",
            "property": "str",
            "gaming_revenue": "float64",  # can be negative when a player wins
        },
        "dates": ["visit_date"],
    },
    "redemptions": {
        "types": {
            "redemption_id": "str",
            "assignment_id": "str",
            "visit_id": "str",
            "promo_cost": "float64",
        },
        "dates": [],
    },
}


def load_raw(raw_dir):
    """Read each CSV and return a dictionary of DataFrames, e.g. tables["visits"]."""
    raw_dir = Path(raw_dir)
    tables = {}

    for name, schema in SCHEMAS.items():
        df = pd.read_csv(
            raw_dir / f"{name}.csv",
            dtype=schema["types"],
            parse_dates=schema["dates"],
        )

        # Stop early if the file doesn't have exactly the columns we expect.
        expected = set(schema["types"]) | set(schema["dates"])
        if set(df.columns) != expected:
            raise ValueError(f"{name}.csv columns {sorted(df.columns)} != expected {sorted(expected)}")

        tables[name] = df

    return tables


if __name__ == "__main__":
    # Runs only when you call this file directly: python src/load.py
    tables = load_raw("data/raw")
    for name, df in tables.items():
        print(f"\n=== {name}: {len(df):,} rows")
        print(df.dtypes)
        print(df.head(3))