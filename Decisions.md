''''
# Data-quality decisions

The raw files contain a small number of imperfections. `src/checks.py` finds them, and
`src/clean.py` applies the decisions below. Every affected record is written to the
data-quality log (`dq_log`) with its decision number.

## General rules

1. **Raw files are never edited.** All fixes happen in code, so they are visible and repeatable.
2. **Every removed, changed or flagged record is logged** with the reason.
3. **If the correct value can't be verified, exclude rather than guess.**
4. **When money is uncertain, be conservative:** overstate cost rather than understate it.
5. **Players are analyzed in the group they were assigned to** (offer or holdout), even if
   something went wrong after assignment. This protects the randomized comparison.

## Decisions

| # | Problem | Records | Decision | Reasoning |
|---|---|---|---|---|
| D1 | Exact duplicate rows | A000010, V000010, R000010 | Keep one copy | Identical data; nothing is lost. |
| D2 | Assignment listed twice with different segments (New vs. Core) | A000020 | Exclude the player | The true segment can't be determined, and segment is one of the groups randomization was done within. |
| D3 | Missing player segment | A024001 | Exclude the player | Same reasoning as D2. D2 and D3 together remove 2 of 24,001 players. |
| D4 | Visit listed twice with different revenue ($90.01 vs. $190.01) | V000020 | Remove both copies | Neither value can be verified. One pre-period visit out of ~15,000. |
| D5 | Visit by a player not in the assignments file | V999001 | Remove | Can't be attributed to any campaign. |
| D6 | Visit 49 days after assignment | V999002 | Keep, labeled `outside` | Not an error, just outside both analysis periods. Reported as a warning and ignored by the analysis. |
| D7 | Redemption listed twice with different costs ($15 vs. $20) | R000020 | Keep the $15 copy | It matches the campaign's offer value. |
| D8 | Second redemption for the same assignment | R999005 | Keep the earliest (R000001), remove this one | The brief allows at most one redemption per assignment. |
| D9 | Redemption for an assignment that doesn't exist | R999001 | Remove | Can't be linked to a campaign. |
| D10 | Redemption by a holdout player | R999002 | Remove the redemption; keep the player in the holdout group | Holdout players shouldn't redeem. Logged as possible contamination; the player stays in their assigned group (rule 5). |
| D11 | Redemption linked to another player's visit at another property | R999003 | Remove | The link is broken and it's unclear which part is wrong. |
| D12 | Negative promo cost (−$5) | R999004 | Keep the redemption; set cost to the offer value ($15) | The redemption links correctly; only the cost is invalid. Using the full offer value is conservative. |
| D13 | Negative and zero gaming revenue | ~766 visits | Keep as is | The brief states negative revenue is valid when a player wins. |

**Cascade rule:** when a player is excluded (D2, D3), their visits and redemptions are
removed too, and logged as "removed with player." This removed one visit (V000025).

## Result

| Table | Raw rows | Clean rows |
|---|---|---|
| assignments | 24,003 | 23,999 |
| visits | 30,318 | 30,313 |
| redemptions | 4,974 | 4,968 |

Running the same checks on the cleaned data returns **0 errors** and 1 warning (V999002, D6).
''''# Data-quality decisions

The raw files contain a small number of imperfections. `src/checks.py` finds them, and
`src/clean.py` applies the decisions below. Every affected record is written to the
data-quality log (`dq_log`) with its decision number.

## General rules

1. **Raw files are never edited.** All fixes happen in code, so they are visible and repeatable.
2. **Every removed, changed or flagged record is logged** with the reason.
3. **If the correct value can't be verified, exclude rather than guess.**
4. **When money is uncertain, be conservative:** overstate cost rather than understate it.
5. **Players are analyzed in the group they were assigned to** (offer or holdout), even if
   something went wrong after assignment. This protects the randomized comparison.

## Decisions

| # | Problem | Records | Decision | Reasoning |
|---|---|---|---|---|
| D1 | Exact duplicate rows | A000010, V000010, R000010 | Keep one copy | Identical data; nothing is lost. |
| D2 | Assignment listed twice with different segments (New vs. Core) | A000020 | Exclude the player | The true segment can't be determined, and segment is one of the groups randomization was done within. |
| D3 | Missing player segment | A024001 | Exclude the player | Same reasoning as D2. D2 and D3 together remove 2 of 24,001 players. |
| D4 | Visit listed twice with different revenue ($90.01 vs. $190.01) | V000020 | Remove both copies | Neither value can be verified. One pre-period visit out of ~15,000. |
| D5 | Visit by a player not in the assignments file | V999001 | Remove | Can't be attributed to any campaign. |
| D6 | Visit 49 days after assignment | V999002 | Keep, labeled `outside` | Not an error, just outside both analysis periods. Reported as a warning and ignored by the analysis. |
| D7 | Redemption listed twice with different costs ($15 vs. $20) | R000020 | Keep the $15 copy | It matches the campaign's offer value. |
| D8 | Second redemption for the same assignment | R999005 | Keep the earliest (R000001), remove this one | The brief allows at most one redemption per assignment. |
| D9 | Redemption for an assignment that doesn't exist | R999001 | Remove | Can't be linked to a campaign. |
| D10 | Redemption by a holdout player | R999002 | Remove the redemption; keep the player in the holdout group | Holdout players shouldn't redeem. Logged as possible contamination; the player stays in their assigned group (rule 5). |
| D11 | Redemption linked to another player's visit at another property | R999003 | Remove | The link is broken and it's unclear which part is wrong. |
| D12 | Negative promo cost (−$5) | R999004 | Keep the redemption; set cost to the offer value ($15) | The redemption links correctly; only the cost is invalid. Using the full offer value is conservative. |
| D13 | Negative and zero gaming revenue | ~766 visits | Keep as is | The brief states negative revenue is valid when a player wins. |

**Cascade rule:** when a player is excluded (D2, D3), their visits and redemptions are
removed too, and logged as "removed with player." This removed one visit (V000025).

## Result

| Table | Raw rows | Clean rows |
|---|---|---|
| assignments | 24,003 | 23,999 |
| visits | 30,318 | 30,313 |
| redemptions | 4,974 | 4,968 |

Running the same checks on the cleaned data returns **0 errors** and 1 warning (V999002, D6).