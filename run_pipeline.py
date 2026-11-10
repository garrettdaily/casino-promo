"""Run the whole pipeline with one command:  python run_pipeline.py

raw CSVs -> load -> check -> clean -> check again -> model -> analyze -> data/output/
"""

from pathlib import Path

import pandas as pd

from src.analyze import campaign_results
from src.checks import run_checks
from src.clean import clean
from src.load import load_raw
from src.model import build_player_summary

RAW_DIR = Path("data/raw")
OUTPUT_DIR = Path("data/output")


def main():
    print("1/5 Loading raw files...")
    raw = load_raw(RAW_DIR)

    print("2/5 Checking raw data...")
    raw_checks = run_checks(raw).assign(stage="raw")

    print("3/5 Cleaning and re-checking...")
    cleaned, dq_log = clean(raw)
    clean_checks = run_checks(cleaned).assign(stage="clean")
    errors = clean_checks[(clean_checks["severity"] == "error") & (clean_checks["rows_flagged"] > 0)]
    if len(errors) > 0:
        raise RuntimeError(f"Cleaned data still fails checks:\n{errors}")

    print("4/5 Building player summary...")
    summary = build_player_summary(cleaned)

    print("5/5 Analyzing results...")
    results = campaign_results(summary)

    # Save everything Power BI needs.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "player_summary": summary,
        "visits": cleaned["visits"],
        "redemptions": cleaned["redemptions"],
        "campaign_results": results,
        "dq_log": dq_log,
        "dq_checks": pd.concat([raw_checks, clean_checks], ignore_index=True),
    }
    for name, df in outputs.items():
        df.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)

    # Short summary so anyone can confirm their run matches.
    overall = results[results["breakdown"] == "Overall"].iloc[0]
    print(f"\nDone. Wrote {len(outputs)} tables to {OUTPUT_DIR}/")
    print(f"  Raw checks failing:       {(raw_checks['rows_flagged'] > 0).sum()} of {len(raw_checks)}")
    print(f"  Records in data-quality log: {len(dq_log)}")
    print(f"  Players analyzed:         {len(summary):,}")
    print(f"  Net lift per offered player: ${overall['net_lift']:.2f} "
          f"(95% CI ${overall['net_lift_low']:.2f} to ${overall['net_lift_high']:.2f})")


if __name__ == "__main__":
    main()