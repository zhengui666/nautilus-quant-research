# Factor Evaluation

## The taxonomy is illustrative only

- Never treat the families below as a whitelist. Any factor family is admissible if it passes the evaluation gates in this document.

- Judge a new family by the same gates, not by whether it resembles a listed category.

- Price, volume, order flow, funding, microstructure, cross sectional, and alternative data are all open.

## Example families

- Price momentum compares the close to a delayed close and ranks it cross sectionally each bar.

- Mean reversion fades extremes measured by a z score of the close against its trailing mean and standard deviation.

- Volume signals compare current volume to its trailing mean, or measure illiquidity as the absolute return divided by volume.

- VWAP deviation compares the close to the volume weighted average price.

- Order book imbalance compares bid and ask size over the top levels of the book.

- Order flow imbalance measures changes in the best bid and ask price multiplied by size.

- Trade flow imbalance compares buy volume to sell volume over a window, using the aggressor side from tick trades.

- Spread and depth signals use the relative spread, the depth imbalance at N levels, and price impact per unit of signed volume.

- Funding carry shorts high funding and longs low funding in a dollar neutral cross section, or trades the funding z score.

- Basis signals trade the mean reversion of the perpetual price against the index price.

- Open interest signals read the change in open interest together with the price direction.

- Volatility signals use Parkinson or Garman Klass estimators from open high low close data, or realized volatility, or ATR normalized returns.

- Cross sectional signals rank any of the above within the universe each bar, optionally neutralized against BTC beta or the market return.

- Alternative data covers sentiment scores, exchange inflows, liquidation cascades, and on chain flows, judged by the gates below and not by family.

## Measured facts about microstructure factors

- Order book imbalance is real but decays fast. On Hyperliquid the top 8 liquid assets showed an average rank IC of 0.0498 at 1 minute, falling to 0.0224 at 5 minutes, 0.0113 at 15 minutes, and 0.0030 at 60 minutes.

- Order book imbalance is strongest on the most liquid books and weakest on thin alts, since on a thin book one resting order distorts the ratio without directional intent.

- Depth based features should be prioritized on majors. On small caps they are mostly noise, so steer small cap factor mining toward funding, cross sectional, and volatility families and treat L2 signals as secondary there.

- A BTC decile spread of 2.25 bps per minute sits inside the 4.5 bps taker fee, so harvesting it requires maker execution and queue position control.

## Universal criteria

- Report the Spearman rank IC for every factor, computed per period as the correlation of ranked signal values with ranked next period returns, then averaged.

- Judge IC against the same horizon baseline. Daily conventions call 0.02 to 0.05 useful and 0.05 strong, while above 0.15 is suspicious, but minute level ICs are larger, so never apply daily thresholds to minute bars.

- Report the ICIR, which is the mean IC divided by its standard deviation. Values above 0.5 are usable and above 1.0 are strong in daily convention, so aggregate minute level IC to daily buckets before judging stability.

- Report the IC decay at horizons 1, 5, 10, 20, and 60 bars, and fit the half life. The optimal holding is near where IC times the square root of horizon is maximized. Fast decay under 5 bars needs low costs, slow decay is capacity friendly, and non monotonic decay can signal reversal.

- Check quantile monotonicity by sorting into 5 to 10 buckets by factor value and taking the mean forward return per bucket. The result must be monotonic, and a result driven by one extreme bucket is fragile.

- Neutralize known factors by regressing out the market or BTC beta, size, momentum, and funding, and report the residual IC. If the signal disappears after neutralization, it is a repackaging of existing exposure.

- Report turnover as the sum of absolute weight changes divided by 2 per period. A common target is 5 to 15 percent daily.

- Compute the break even cost as gross alpha divided by turnover. If it sits below the actual round trip cost, the factor is unprofitable.

- Report the net IC after costs, which subtracts cost per unit of turnover times turnover from the IC. The net IC must stay positive after Hyperliquid maker 0.015 percent, taker 0.045 percent, and slippage.

- Report capacity as the capital at which IC degrades by about 50 percent. At a few thousand USD, capacity is rarely binding, but per trade slippage on thin books is the binding constraint, not assets under management.

- Report IC and IR separately in bull, bear, and choppy segments. A factor that only works in one regime is a regime bet, not alpha, and more than 55 percent of periods positive suggests consistency.

- Report the correlation of the new factor to every factor already in the library. A new factor highly correlated with an existing one adds nothing, so drop it or orthogonalize it.

- Start from an economic rationale, and demand a higher burden of proof from any factor with no rationale.

## The Fundamental Law

- The Fundamental Law of Active Management states that the information ratio equals IC times the square root of breadth times the transfer coefficient.

- Breadth is the number of independent bets per year, and the transfer coefficient is the implementation efficiency from 0 to 1.

- A weak signal with an IC of 0.03 across 20 to 50 coins rebalanced many times a day can still produce a strong strategy if the transfer coefficient survives costs.

- Breadth and turnover discipline matter more than finding a single magic factor.
