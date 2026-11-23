# Portfolio Combination

## Weighting methods

- Start with equal weight or inverse volatility weight. Both are robust on short history and often beat optimized methods out of sample.

- Inverse volatility weight sets each weight proportional to 1 divided by its volatility. It needs only volatility estimates, which are far more stable than correlations, but it ignores correlation, so correlated strategies repeat the same risk budget.

- Risk parity sets each strategy risk contribution equal, where the risk contribution of strategy i is its weight times the i-th element of the covariance matrix times the weight vector. It needs no return forecasts, but it inverts the covariance matrix, so noisy estimates make weights unstable.

- Hierarchical risk parity clusters by correlation and allocates risk recursively without inverting any matrix, which makes it structurally robust to estimation noise. It is the only optimization worth upgrading to, and it depends on the clustering method chosen.

- Mean variance optimization is not recommended. It needs an expected return forecast for every strategy, which is the noisiest input of all, and a 0.1 percent error in a return estimate can move an allocation by 35 percent.

- Full Kelly is never used. It assumes the win rate and the payoff ratio are known exactly and stationary, while in trading neither is observable, and estimation error leads to overbetting and catastrophic drawdowns.

- Fractional Kelly is a cap, never a prescription. Half Kelly keeps about 75 percent of the growth with half the variance, and a full Kelly portfolio can still draw down 30 to 50 percent even when the strategy is truly profitable.

- Use fractional Kelly by sample size. Under 50 trades use a fixed 1 percent and ignore Kelly, 50 to 150 trades use 25 percent Kelly, 150 to 300 trades use 33 percent, 300 to 500 trades use 40 to 50 percent, and above 500 trades use at most 50 percent.

- Never run an optimization on a raw sample covariance matrix. Shrink it with Ledoit Wolf toward a stable structure, and check the condition number afterwards, since a high condition number means the matrix is near singular and inversion amplifies error.

## How the three strategy families combine

- Momentum has a convex return distribution with a fat right tail, earns crisis alpha in crashes, bleeds in choppy markets, and can suffer rare but devastating momentum crashes.

- Mean reversion has a high win rate and a fat left tail, earns steadily in choppy markets, and dies by catching falling knives in trending markets.

- Funding carry earns small steady amounts most of the time with crash risk, and its return depends on leverage demand, so it decays as arbitrageurs enter. A headline 40 percent annualized carry is a sales pitch, not a plan.

- Momentum and mean reversion are naturally low or negatively correlated across regimes, since momentum wins in trends and mean reversion wins in chop. That is the point of the combination.

- Funding carry is near orthogonal to both, since its return is a yield and not a price move.

- A trend plus mean reversion teaching case moved from a single strategy swinging plus 25 percent and minus 8 percent to a combined plus 20.5 percent annualized with max drawdown cut from minus 12 percent to minus 3.5 percent.

- A meta portfolio of diversified strategies can reach a Sharpe of 1.0 to 1.5 while single strategies sit at 0.5 to 0.8.

## Correlation discipline

- Measure correlation on strategy returns, never on signals, since two signals can look different while their holdings and profits overlap.

- Treat correlation above 0.8 as do not combine, 0.5 to 0.8 as cautious, 0.2 to 0.5 as recommended, and minus 0.2 to 0.2 as excellent.

- Look at rolling correlation and downside correlation separately, since full sample correlation misleads.

- Correlations rise toward 1.0 in crises, so diversification fails exactly when it is needed most. Stress test with every pairwise correlation raised by 0.3, since a value at risk computed under a constant 0.78 correlation has understated stress losses by 15 to 20 percent in a documented case.

- Size position limits so the maximum loss with all correlations at 1.0 stays inside the risk budget.

- Track the diversification ratio, which is the weighted sum of individual volatilities divided by portfolio volatility. Adding a strategy only counts as real diversification when the ratio rises.

- Adding a strategy is about adding an uncorrelated return stream, not about adding a strategy count. Two momentum variants at 0.95 correlation combine into one strategy, while one momentum plus one mean reversion at 0.25 correlation is real diversification.

## Risk budgeting

- Target 15 to 20 percent annualized portfolio volatility, which sits below the half Kelly ceiling for a diversified futures portfolio.

- Size positions by target volatility divided by current volatility, using an EWMA volatility estimate shifted by 1 bar so only past information enters.

- Clip the scaling factor, for example between 0.5 and 1.5, to stop leverage from running away in low volatility periods.

- Run two risk layers and take the smaller size from each. The micro layer risks 0.5 to 1 percent of equity per trade, with position size equal to dollar risk divided by stop distance, where the stop is often 1.5 times ATR. The macro layer is the annualized volatility target. Running only one layer leaves the other uncontrolled.

- A 60 day volatility window reacts slowly to a new storm and stays small long after it passes, while an EWMA or short window reacts fast but noisily. Volatility clusters, so volatility targeting systematically lags at the start of a storm.

- In Hyperliquid, perpetuals are divisible and the minimum order is 10 USD notional, so there is no whole contract rounding problem. But with 3 strategies times 20 coins on a few thousand USD, single strategy single coin positions become tiny and slippage plus fees take a larger share of returns. Give each strategy enough capital that its single trades stay at 50 to 100 USD notional, or cut the number of strategies.

## Drawdown control

- Apply the circuit breaker. At a 90 day rolling drawdown of minus 15 percent cut leverage to 0.5 times, at minus 25 percent pause at 0 times, and resume at 1.0 times only when the 30 day rolling drawdown is back above minus 7.5 percent.

- After a pause, resume only when the 30 day drawdown is above minus 15 percent and at least 10 trading days have passed, since the lag and the dwell period stop repeated whipsaw.

- Fixed proportion portfolio insurance sets risky exposure equal to a multiplier times portfolio value minus a floor, with the multiplier usually 3 to 5. It only holds exactly in ideal markets with continuous trading and no gaps, and overnight gaps and discrete rebalancing break it.

- Time invariant portfolio insurance moves the floor up with new portfolio highs and uses a multiplier of 2 to 4, since above 5 the cost worsens sharply.

- Every hedge costs something. Diversification costs forgone return, options cost premium, and rule based hedges cost whipsaw. Choosing a hedge means choosing which cost to pay.

- Distinguish a strategy losing money from a strategy model failing. Losing money is normal operation, while the real failure signal is sustained worsening of the strategy own confidence metrics, such as rolling out of sample R squared or prediction error, regardless of current profit and loss. A strategy with rising prediction error is bad even while it earns, and a strategy with healthy diagnostics and bad luck should not be cut.

## Rebalancing

- There is no optimal rebalancing frequency or threshold. Monthly, quarterly, and annual rebalancing show no material difference in risk adjusted return.

- Threshold based rebalancing beats calendar based rebalancing at keeping the portfolio aligned to target risk, at similar or lower cost. During the March 2020 volatility spike, monthly calendar rebalancing let a portfolio drift 7 percent from target, while daily monitored threshold rebalancing never drifted beyond 2 percent at similar cost.

- A narrow 2 to 3 percent band tracks the target closely but trades often, and a wide 8 to 10 percent band cuts turnover but allows drift. Having a written policy and sticking to it matters more than the exact threshold value.

- Trading to the band edge costs less than trading back to target. In one 24.8 year study with a 5 percent no trade band and 10 bps cost, trading to the edge cost 0.034 percent per year across 1081 small trades, below 0.057 percent per year for monthly trading back to target.

- Rebalance strategy weights weekly and only when drift exceeds 5 percent, and keep position level trading signal driven and continuous. The two layers are different, since the weight layer is slow and the position layer is fast.

- Hyperliquid round trip costs are about 0.03 percent for limit orders and 0.09 percent for market orders at entry tier, plus small cap spread slippage of 0.1 to 0.5 percent per trade, which dominates. A full book rebalance on a few thousand USD costs only 1 to 3 USD in fees, so slippage is the real cost. Never rebalance strategy weights daily.

## Regime adaptation

- Regime dependence is real. Momentum wins in trends, mean reversion wins in chop, and transitions are unreliable for both, so cut exposure in transitions.

- A trend strategy run in a mean reverting market does not just fail to earn, it reliably and persistently loses money.

- Crypto has two extra regimes. Liquidity crises widen spreads, thin books, and break normal correlations, and euphoria shows sustained positive funding with rising open interest, often before a local top.

- Detect regimes with the Hurst exponent, where above 0.6 means trending and below 0.45 means mean reverting, with hidden Markov models over 2 to 3 states, or with ADX, where above 25 means strong trend and below 20 means chop.

- Guard against whipsaw by requiring the state to persist for 3 to 5 days before switching, or by acting only when the state probability exceeds 0.7, and by smoothing state probabilities with an EMA.

- State detection classifies the past and lags by nature, and transitions, which are exactly when judgment matters most, are the hardest moments to forecast. Hard switching adds a layer of timing risk that can itself be overfitted in backtests.

- Start with all strategies running at fixed risk budgets and let diversification carry the portfolio through regime changes. Treat regime switching as a second stage upgrade with its own validation gate, and prefer volatility scaled momentum over hard switching as the first upgrade.

## Small account failure modes

- Overfitting weights on the backtest is the first failure mode. Optimizing 8800 parameter sets on a random walk produced a best annualized Sharpe of 1.27 with a 55 percent probability of backtest overfitting and 53 percent of out of sample Sharpes negative. Every extra degree of freedom raises the overfitting probability, so 3 strategies carry only 2 weight degrees of freedom and are relatively safe, but optimizing each strategy internal parameters plus rebalance thresholds plus regime rules inflates the count fast. Defend with combinatorial symmetric cross validation, walk forward, and out of sample Sharpe significance tests.

- Too many strategies on too little capital is the second failure mode. Below the 10 USD minimum notional, adjustments are rejected, and the smaller the position, the larger the share of slippage and fees.

- Ignoring funding cost is the third failure mode. Funding settles hourly on Hyperliquid, flips faster than on 8 hour venues, and can reach extreme annualized levels on small caps. Always look at funding before holding overnight, and always include hourly funding cash flows in the backtest, net of the hedging cost of the directional exposure.

- Underestimating crash correlation is the fourth failure mode. Size by the all correlations at 1.0 worst case, never by the full sample correlation matrix.

- Short history is the fifth failure mode. Many small caps have only about 14 months of history, and minute level data is plentiful but market states are not stationary, so 14 months may cover only 1 to 2 full state cycles. Shrink weight and correlation estimates with Ledoit Wolf, use rolling windows, and test sensitivity by perturbing correlations by plus and minus 0.2 and checking whether weights change violently.

## Default configuration

- Weight the three strategies by equal risk, so each contributes about one third of portfolio volatility, using inverse volatility adjusted equal risk budgets. Do not optimize weights in sample, and only fine tune with hierarchical risk parity after out of sample validation.

- Target 15 to 20 percent annualized portfolio volatility, risk 0.5 to 1 percent per trade, keep leverage at 1 to 2 times with a cap of 3 times, and use isolated margin.

- Rebalance strategy weights weekly with a 5 percent drift threshold, and trade positions on signals continuously.

- Apply the drawdown circuit breaker at minus 15 percent and minus 25 percent, with recovery plus a 10 day dwell period.

- Keep all strategies running at fixed risk budgets in version one, and treat regime adaptation as a second stage upgrade.

- Validate any weight scheme and any strategy parameter with segmented backtests across bull, bear, and choppy periods plus walk forward, and reject any scheme with a probability of backtest overfitting above 0.05.
