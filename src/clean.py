"""Step 3 of the pipeline: apply the data-quality decisions in DECISIONS.md.

clean() takes the raw tables and returns:
  - the cleaned tables (same structure; visits gain a "period" column)
  - dq_log: one row for every record removed, changed or flagged, and why

The raw files are never modified. Decision numbers (D1, D2, ...) match DECISIONS.md.
"""

import pandas as pd

from src.checks import PRE_DAYS, RESPONSE_DAYS


class DQLog:
    """Collects one log row per affected record."""

    def __init__(self):
        self.rows = []

    def add(self, table, ids, issue, action, decision):
        for record_id in ids:
            self.rows.append({
                "table": table,
                "record_id": record_id,
                "issue": issue,
                "action": action,
                "decision": decision,
            })

    def to_frame(self):
        return pd.DataFrame(self.rows, columns=["table", "record_id", "issue", "action", "decision"])


def _drop_exact_duplicates(df, table, id_col, log):
    """D1: identical rows -> keep one copy."""
    dupes = df[df.duplicated(keep="first")]
    log.add(table, dupes[id_col], "exact duplicate row", "removed extra copy", "D1")
    return df.drop_duplicates(keep="first")


def clean_assignments(a, log):
    a = _drop_exact_duplicates(a, "assignments", "assignment_id", log)

    # D2: same assignment_id with conflicting values (e.g. two different segments) -> exclude
    conflicting = a[a["assignment_id"].duplicated(keep=False)]
    log.add("assignments", conflicting["assignment_id"].unique(),
            "same ID, conflicting values", "excluded player", "D2")
    a = a[~a["assignment_id"].isin(conflicting["assignment_id"])]

    # D3: missing player_segment -> exclude
    missing = a[a["player_segment"].isna()]
    log.add("assignments", missing["assignment_id"], "missing player_segment", "excluded player", "D3")
    a = a[a["player_segment"].notna()]

    return a


def clean_visits(v, raw_assignments, assignments, log):
    v = _drop_exact_duplicates(v, "visits", "visit_id", log)

    # D4: same visit_id with conflicting values (e.g. two revenue amounts) -> drop all copies
    conflicting = v[v["visit_id"].duplicated(keep=False)]
    log.add("visits", conflicting["visit_id"].unique(),
            "same ID, conflicting values", "removed all copies", "D4")
    v = v[~v["visit_id"].isin(conflicting["visit_id"])]

    # D5: player not in the assignments file at all -> drop
    unknown = v[~v["player_id"].isin(raw_assignments["player_id"])]
    log.add("visits", unknown["visit_id"], "player not in assignments", "removed", "D5")
    v = v[v["player_id"].isin(raw_assignments["player_id"])]

    # Cascade: visits by players excluded in D2/D3 -> drop with the player
    excluded = v[~v["player_id"].isin(assignments["player_id"])]
    log.add("visits", excluded["visit_id"], "player excluded (D2/D3)", "removed with player", "D2/D3")
    v = v[v["player_id"].isin(assignments["player_id"])]

    # Label each visit by its timing relative to the player's assignment date.
    v = v.merge(assignments[["player_id", "assigned_date"]], on="player_id", how="left")
    days = (v["visit_date"] - v["assigned_date"]).dt.days
    v["days_from_assignment"] = days
    v["period"] = "outside"
    v.loc[(days >= -PRE_DAYS) & (days < 0), "period"] = "pre"
    v.loc[(days >= 0) & (days < RESPONSE_DAYS), "period"] = "response"

    # D6: outside both periods -> keep, but flag (ignored by the analysis)
    outside = v[v["period"] == "outside"]
    log.add("visits", outside["visit_id"], "outside pre-period and response window",
            "kept, labeled 'outside'", "D6")

    return v.drop(columns="assigned_date")


def clean_redemptions(r, raw_assignments, assignments, visits, log):
    r = _drop_exact_duplicates(r, "redemptions", "redemption_id", log)

    # Attach the assignment and visit each redemption points to.
    r = (r.merge(assignments[["assignment_id", "player_id", "property", "group", "offer_value", "assigned_date"]],
                 on="assignment_id", how="left")
          .merge(visits[["visit_id", "player_id", "property", "visit_date"]],
                 on="visit_id", how="left", suffixes=("", "_visit")))

    # D7: same redemption_id with conflicting values -> keep the copy whose cost matches the offer
    dup_id = r["redemption_id"].duplicated(keep=False)
    wrong_copy = r[dup_id & (r["promo_cost"] != r["offer_value"])]
    log.add("redemptions", wrong_copy["redemption_id"], "same ID, conflicting values",
            "removed copy whose cost doesn't match the offer value", "D7")
    r = r.drop(index=wrong_copy.index)

    # D9: assignment_id not in the assignments file -> drop
    unknown = r[~r["assignment_id"].isin(raw_assignments["assignment_id"])]
    log.add("redemptions", unknown["redemption_id"], "assignment_id not found", "removed", "D9")
    r = r.drop(index=unknown.index)

    # Cascade: assignment excluded in D2/D3, or visit removed in D4/D5 -> drop
    no_assignment = r[r["group"].isna()]
    log.add("redemptions", no_assignment["redemption_id"], "assignment excluded (D2/D3)",
            "removed with player", "D2/D3")
    r = r.drop(index=no_assignment.index)
    no_visit = r[r["visit_date"].isna()]
    log.add("redemptions", no_visit["redemption_id"], "visit not found or removed",
            "removed", "D4/D5")
    r = r.drop(index=no_visit.index)

    # D10: redeemed by a holdout player -> drop the redemption; player stays in holdout
    holdout = r[r["group"] == "holdout"]
    log.add("redemptions", holdout["redemption_id"], "redeemed by a holdout player",
            "removed redemption; player kept in holdout group", "D10")
    r = r.drop(index=holdout.index)

    # D11: visit belongs to a different player or property, or is outside the window -> drop
    days = (r["visit_date"] - r["assigned_date"]).dt.days
    bad_link = r[(r["player_id"] != r["player_id_visit"])
                 | (r["property"] != r["property_visit"])
                 | (days < 0) | (days >= RESPONSE_DAYS)]
    log.add("redemptions", bad_link["redemption_id"],
            "visit doesn't match the assignment's player, property or window", "removed", "D11")
    r = r.drop(index=bad_link.index)

    # D8: more than one redemption per assignment -> keep the earliest (by visit date, then ID)
    r = r.sort_values(["assignment_id", "visit_date", "redemption_id"])
    extra = r[r["assignment_id"].duplicated(keep="first")]
    log.add("redemptions", extra["redemption_id"], "more than one redemption per assignment",
            "removed; kept the earliest", "D8")
    r = r.drop(index=extra.index)

    # D12: negative promo_cost -> replace with the offer value (conservative)
    negative = r["promo_cost"] < 0
    log.add("redemptions", r.loc[negative, "redemption_id"], "negative promo_cost",
            "cost set to offer value", "D12")
    r.loc[negative, "promo_cost"] = r.loc[negative, "offer_value"]

    # Return only the original redemption columns.
    return r[["redemption_id", "assignment_id", "visit_id", "promo_cost"]].sort_values("redemption_id")


def clean(tables):
    """Apply all decisions. Returns (clean_tables, dq_log)."""
    log = DQLog()
    raw_a = tables["assignments"]

    assignments = clean_assignments(raw_a, log)
    visits = clean_visits(tables["visits"], raw_a, assignments, log)
    redemptions = clean_redemptions(tables["redemptions"], raw_a, assignments, visits, log)

    clean_tables = {"assignments": assignments, "visits": visits, "redemptions": redemptions}
    return clean_tables, log.to_frame()


if __name__ == "__main__":
    # Clean the raw data and re-run the checks: python -m src.clean
    from src.checks import run_checks
    from src.load import load_raw

    raw = load_raw("data/raw")
    cleaned, dq_log = clean(raw)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 70)
    print("=== Data-quality log ===")
    print(dq_log.to_string(index=False))

    print("\n=== Row counts: raw -> clean ===")
    for name in raw:
        print(f"{name:12} {len(raw[name]):>7,} -> {len(cleaned[name]):>7,}")

    print("\n=== Checks on the cleaned data ===")
    findings = run_checks(cleaned)
    print(findings[findings["rows_flagged"] > 0].to_string(index=False))
    errors = findings[(findings["severity"] == "error") & (findings["rows_flagged"] > 0)]
    print(f"\n{len(errors)} errors remaining (warnings are allowed).")