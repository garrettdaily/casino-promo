"""Data-quality checks.

run_checks() applies every rule from the brief to a set of tables and returns
one row per check, with how many rows failed it. We run it twice:
  - on the raw data, to find the problems (profiling)
  - on the cleaned data, where every check should be 0 (validation)
"""

import pandas as pd

RESPONSE_DAYS = 14  # response window: assigned_date + 0 to 13 days
PRE_DAYS = 28  # look-back period before assignment


def _result(table, check, flagged, id_col, severity="error"):
    """Build one row of the findings table from the rows that failed a check.

    severity "error" = must be fixed before analysis; "warning" = allowed, but reported.
    """
    ids = flagged[id_col].astype(str).unique()
    return {
        "table": table,
        "check": check,
        "severity": severity,
        "rows_flagged": len(flagged),
        "example_ids": ", ".join(ids[:5]),
    }


def _duplicate_checks(df, table, id_col):
    """Exact duplicate rows, and IDs that appear more than once with different values."""
    exact_dupes = df[df.duplicated(keep="first")]

    deduped = df.drop_duplicates()
    conflicting = deduped[deduped[id_col].duplicated(keep=False)]

    return [
        _result(table, "exact duplicate row", exact_dupes, id_col),
        _result(table, "same ID, conflicting values", conflicting, id_col),
    ]


def run_checks(tables):
    """Run every check and return the findings as a DataFrame."""
    a = tables["assignments"]
    v = tables["visits"]
    r = tables["redemptions"]
    results = []

    # ---------- assignments ----------
    results += _duplicate_checks(a, "assignments", "assignment_id")
    results.append(_result("assignments", "missing player_segment",
                           a[a["player_segment"].isna()], "assignment_id"))
    multi = a.drop_duplicates("assignment_id")
    results.append(_result("assignments", "player has more than one assignment",
                           multi[multi["player_id"].duplicated(keep=False)], "player_id"))
    results.append(_result("assignments", "offer_value blank for offer / filled for holdout",
                           a[(a["group"] == "offer") == a["offer_value"].isna()], "assignment_id"))

    # ---------- visits ----------
    results += _duplicate_checks(v, "visits", "visit_id")

    # Attach each visit's assignment so we can compare player, property and dates.
    # (drop_duplicates so a duplicated assignment can't double-count visits here)
    lookup = a.drop_duplicates("assignment_id")[["player_id", "property", "assigned_date"]]
    va = v.merge(lookup, on="player_id", how="left", suffixes=("", "_assigned"))
    days = (va["visit_date"] - va["assigned_date"]).dt.days

    results.append(_result("visits", "player not in assignments",
                           va[va["assigned_date"].isna()], "visit_id"))
    results.append(_result("visits", "property differs from assigned property",
                           va[va["assigned_date"].notna() & (va["property"] != va["property_assigned"])],
                           "visit_id"))
    results.append(_result("visits", "outside pre-period and response window",
                                                      va[(days < -PRE_DAYS) | (days >= RESPONSE_DAYS)], "visit_id",
                           severity="warning"))
    # ---------- redemptions ----------
    results += _duplicate_checks(r, "redemptions", "redemption_id")

    # Attach the assignment and the visit each redemption points to.
    a_lookup = a.drop_duplicates("assignment_id")
    v_lookup = v.drop_duplicates("visit_id")
    rv = (r.merge(a_lookup, on="assignment_id", how="left")
           .merge(v_lookup, on="visit_id", how="left", suffixes=("", "_visit")))
    rdays = (rv["visit_date"] - rv["assigned_date"]).dt.days
    both = rv["group"].notna() & rv["visit_date"].notna()  # both links found

    results.append(_result("redemptions", "assignment_id not found",
                           rv[rv["group"].isna()], "redemption_id"))
    results.append(_result("redemptions", "visit_id not found",
                           rv[rv["visit_date"].isna()], "redemption_id"))
    results.append(_result("redemptions", "redeemed by a holdout player",
                           rv[rv["group"] == "holdout"], "redemption_id"))
    results.append(_result("redemptions", "visit belongs to a different player",
                           rv[both & (rv["player_id"] != rv["player_id_visit"])], "redemption_id"))
    results.append(_result("redemptions", "visit at a different property",
                           rv[both & (rv["property"] != rv["property_visit"])], "redemption_id"))
    results.append(_result("redemptions", "visit outside response window",
                           rv[both & ((rdays < 0) | (rdays >= RESPONSE_DAYS))], "redemption_id"))
    results.append(_result("redemptions", "more than one redemption per assignment",
                           r.drop_duplicates()[r.drop_duplicates()["assignment_id"].duplicated(keep=False)],
                           "redemption_id"))
    results.append(_result("redemptions", "negative promo_cost",
                           r[r["promo_cost"] < 0], "redemption_id"))
    results.append(_result("redemptions", "promo_cost differs from offer_value",
                           rv[rv["offer_value"].notna() & (rv["promo_cost"] != rv["offer_value"])],
                           "redemption_id"))

    return pd.DataFrame(results)


if __name__ == "__main__":
    # Profile the raw data: python -m src.checks
    from src.load import load_raw

    findings = run_checks(load_raw("data/raw"))
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 60)
    print(findings.to_string(index=False))
    failed = (findings["rows_flagged"] > 0).sum()
    print(f"\n{failed} of {len(findings)} checks found problems.")