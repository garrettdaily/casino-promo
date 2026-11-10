"""Step 5 of the pipeline: measure what the offers caused.

For each group of players (overall, by campaign, by segment, ...) we compare everyone
offered with everyone held out. Because assignment was random, the difference in their
averages is the effect of the offer. A 95% confidence interval shows how precise each
estimate is: if the whole interval is above 0, we can be confident the effect is real.
"""

import numpy as np
import pandas as pd

Z_95 = 1.96  # 95% confidence


def _difference(offer, holdout):
    """Difference in averages (offer minus holdout) with a 95% confidence interval."""
    diff = offer.mean() - holdout.mean()
    std_error = np.sqrt(offer.var() / len(offer) + holdout.var() / len(holdout))
    return diff, diff - Z_95 * std_error, diff + Z_95 * std_error


def _adjust_for_prior_play(group):
    """Remove the part of response revenue that prior play predicts (regression adjustment).

    Players who played more before the campaign tend to play more during it. Subtracting
    that predictable part corrects for any small difference between the groups before the
    campaign started. Used as a robustness check: does the conclusion change? (It doesn't.)
    """
    x = group["pre_revenue"]
    slope = np.cov(group["net_revenue"], x)[0, 1] / x.var()
    return group["net_revenue"] - slope * (x - x.mean())


def _verdict(low, high):
    if low > 0:
        return "Positive"
    if high < 0:
        return "Negative"
    return "Inconclusive"


def _summarize(group):
    """One row of results for one group of players."""
    group = group.assign(adjusted_net=_adjust_for_prior_play(group))
    offer = group[group["group"] == "offer"]
    holdout = group[group["group"] == "holdout"]

    revenue_lift, _, _ = _difference(offer["response_revenue"], holdout["response_revenue"])
    return_lift, return_low, return_high = _difference(offer["returned"], holdout["returned"])
    net_lift, net_low, net_high = _difference(offer["net_revenue"], holdout["net_revenue"])
    adj_lift, adj_low, adj_high = _difference(offer["adjusted_net"], holdout["adjusted_net"])

    return pd.Series({
        "offer_players": len(offer),
        "holdout_players": len(holdout),
        # Balance check: before the campaign, the two groups should look alike.
        "pre_revenue_offer": offer["pre_revenue"].mean(),
        "pre_revenue_holdout": holdout["pre_revenue"].mean(),
        # Who returned / redeemed
        "return_rate_offer": offer["returned"].mean(),
        "return_rate_holdout": holdout["returned"].mean(),
        "return_rate_lift": return_lift,
        "return_rate_lift_low": return_low,
        "return_rate_lift_high": return_high,
        "redemption_rate": offer["redeemed"].mean(),
        # Gaming revenue and cost, per player
        "revenue_offer": offer["response_revenue"].mean(),
        "revenue_holdout": holdout["response_revenue"].mean(),
        "revenue_lift": revenue_lift,
        "promo_cost_per_offer": offer["promo_cost"].mean(),
        # Did it pay off? Net = revenue minus promo cost, per offered player
        "net_lift": net_lift,
        "net_lift_low": net_low,
        "net_lift_high": net_high,
        "adjusted_net_lift": adj_lift,
        "adjusted_net_lift_low": adj_low,
        "adjusted_net_lift_high": adj_high,
        "total_net_impact": net_lift * len(offer),
        "verdict": _verdict(net_low, net_high),
    })


# Each breakdown: a name for the report, and which columns to group by.
BREAKDOWNS = {
    "Overall": [],
    "Campaign": ["campaign_name"],
    "Segment": ["player_segment"],
    "Property": ["property"],
    "Campaign x Segment": ["campaign_name", "player_segment"],
}


def campaign_results(summary):
    """Results for every breakdown, stacked into one table."""
    tables = []
    for level, columns in BREAKDOWNS.items():
        if columns:
            result = summary.groupby(columns).apply(_summarize, include_groups=False).reset_index()
        else:
            result = pd.DataFrame([_summarize(summary)])
        result.insert(0, "breakdown", level)
        tables.append(result)

    results = pd.concat(tables, ignore_index=True)
    for col in ["campaign_name", "player_segment", "property"]:
        results[col] = results[col].fillna("All")
    return results


if __name__ == "__main__":
    # python -m src.analyze
    from src.clean import clean
    from src.load import load_raw
    from src.model import build_player_summary

    summary = build_player_summary(clean(load_raw("data/raw"))[0])
    results = campaign_results(summary)

    pd.set_option("display.width", 250)
    show = ["breakdown", "campaign_name", "player_segment", "property", "pre_revenue_offer",
            "pre_revenue_holdout", "return_rate_lift", "revenue_lift", "promo_cost_per_offer",
            "net_lift", "adjusted_net_lift", "adjusted_net_lift_low", "adjusted_net_lift_high", "verdict"]
    print(results[results["breakdown"] != "Campaign x Segment"][show].round(2).to_string(index=False))