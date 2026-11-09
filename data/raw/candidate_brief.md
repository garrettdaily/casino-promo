# Casino promotion data platform challenge

Our casino marketing team sends promotional offers to encourage players to visit. After a campaign, the team wants to understand what happened: who returned, who redeemed an offer, how much gaming activity occurred, and whether the results justify further investment.

Those questions require bringing together data from several sources. An offer redemption tells us something different from a visit, and players may visit without redeeming an offer. Some players receive an offer while others are held out for comparison. A useful solution should help the team make sense of those relationships and understand how much confidence to place in the results.

Your challenge is to **use the provided data to build something that helps the team understand promotional performance**. This is deliberately open ended. The questions you prioritize, the way you model the data, and the form of your solution are up to your interpretation. We are interested in your engineering judgment and how you turn source data into something useful.

## The data

The packet contains three synthetic CSV files covering four campaigns at two fictional casino properties. The extract is complete through **October 31, 2026**.

| File | What it contains |
| --- | --- |
| `assignments.csv` | About 24,000 player assignments to campaigns, including property, player segment, assignment date, offer value, and whether the player received an offer or was held out |
| `visits.csv` | About 30,000 gaming visits, including player, property, visit date, and gaming revenue |
| `redemptions.csv` | About 5,000 redemption records linking a campaign assignment to a visit and its promotional cost |

Each player belongs to one campaign assignment. The `group` field is `offer` or `holdout`, with approximately 80% receiving an offer and 20% held out. For this exercise, assume assignment was randomized within each campaign, property, and player segment. A blank `offer_value` for a holdout player is intentional.

Campaigns have an intended response window of 14 days beginning on `assigned_date`. The visit data also include the preceding 28 days, which can help you understand prior behavior. You may choose how to use these periods in your analysis; explain your choices.

Gaming revenue represents the casino's net gaming revenue for a visit. Negative values are valid when a player wins. Promotional cost is a separate, nonnegative amount. A redemption is expected to link to an offer assignment and a visit by the same player at the same property during the response window, with at most one redemption per assignment.

The source files contain some data imperfections. Use your judgment to identify and handle them, and explain any decisions that affect your results.

## Your approach

Bring the files together in a data model that makes sense to you, explore a few questions you find useful, and present the results with visualizations or a simple interface. You might compare campaigns, examine offer and holdout behavior, explore differences between player segments, or focus on the reliability of the underlying data. These are starting points; you can take another direction if you explain its value.

Choose a focused scope that demonstrates your strengths. There is no prescribed technology stack, architecture, set of metrics, or number of charts. A small application, dashboard, or notebook is welcome. We want to understand how you structure the data, validate your work, and communicate findings and limitations.

**AI tools are encouraged.** Use them as you would in your normal work, and be prepared to explain the choices and code in your submission.

## What to share

Send a repository or zip containing your project and a short README explaining how to run or view it, the questions you chose, your main findings, and any important assumptions or tradeoffs. Include a brief note on how you used AI and what you would improve next.

If you have any questions or need clarification, please reach out to Michael Wilson at 216-213-5989.
