"""Step 4 of the pipeline: build the analysis table.

player_summary has one row per player (assignment) and answers the brief's questions
as columns: did they return, did they redeem, how much did they play, what did it cost.
Every player is included, even those with no visits, because the offer-vs-holdout
comparison must include everyone who was assigned (not just people who showed up).
"""

import pandas as pd


def _activity(visits, period, prefix):
    """Count visits and total revenue per player for one period ("pre" or "response")."""
    in_period = visits[visits["period"] == period]
    per_player = in_period.groupby("player_id").agg(
        visits=("visit_id", "count"),
        revenue=("gaming_revenue", "sum"),
    )
    return per_player.add_prefix(prefix)


def build_player_summary(tables):
    assignments = tables["assignments"]
    visits = tables["visits"]
    redemptions = tables["redemptions"]

    summary = (
        assignments
        .merge(_activity(visits, "pre", "pre_"), on="player_id", how="left")
        .merge(_activity(visits, "response", "response_"), on="player_id", how="left")
        .merge(redemptions[["assignment_id", "promo_cost"]], on="assignment_id", how="left")
    )

    # Players with no visits / no redemption get blanks from the left joins -> use 0.
    zero_fill = ["pre_visits", "pre_revenue", "response_visits", "response_revenue", "promo_cost"]
    summary[zero_fill] = summary[zero_fill].fillna(0)
    summary[["pre_visits", "response_visits"]] = summary[["pre_visits", "response_visits"]].astype(int)

    # Yes/no flags for the questions in the brief.
    summary["visited_pre"] = summary["pre_visits"] > 0
    summary["returned"] = summary["response_visits"] > 0  # visited during the 14-day window
    summary["redeemed"] = summary["promo_cost"] > 0
    summary["net_revenue"] = summary["response_revenue"] - summary["promo_cost"]

    _validate(summary, tables)
    return summary


def _validate(summary, tables):
    """Stop the pipeline if the summary doesn't reconcile with the cleaned tables."""
    assignments = tables["assignments"]
    visits = tables["visits"]
    redemptions = tables["redemptions"]

    # One row per player: the joins must not have duplicated or lost anyone.
    assert len(summary) == len(assignments), "row count changed during joins"
    assert summary["player_id"].is_unique, "a player appears more than once"

    # Totals must match the source tables (rounded to the cent).
    for period in ["pre", "response"]:
        source = visits.loc[visits["period"] == period, "gaming_revenue"].sum()
        modeled = summary[f"{period}_revenue"].sum()
        assert round(source, 2) == round(modeled, 2), f"{period} revenue doesn't reconcile"
    assert round(redemptions["promo_cost"].sum(), 2) == round(summary["promo_cost"].sum(), 2), \
        "promo cost doesn't reconcile"
    assert summary["redeemed"].sum() == len(redemptions), "redemption count doesn't reconcile"


if __name__ == "__main__":
    # Build the summary from cleaned data: python -m src.model
    from src.clean import clean
    from src.load import load_raw

    cleaned, _ = clean(load_raw("data/raw"))
    summary = build_player_summary(cleaned)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print(f"player_summary: {len(summary):,} rows (one per player), all reconciliation checks passed\n")
    print(summary.head(5).to_string(index=False))

    print("\n=== Quick look: offer vs holdout (per player averages) ===")
    print(summary.groupby("group")[["pre_revenue", "returned", "redeemed", "response_revenue",
                                    "promo_cost", "net_revenue"]].mean().round(2))