# Validation

## Walk forward analysis

- Walk forward analysis is the non negotiable gate for any profit and loss backtest.

- Optimize on the in sample window, test on the immediately following out of sample window, roll forward, and concatenate the out of sample results.

- Use an anchored expanding in sample window for stable structural edges and mean reversion, and a rolling fixed length in sample window when regimes shift.

- A typical split is 70 percent in sample and 30 percent out of sample, or 80 percent and 20 percent.

- Keep parameter selection strictly inside the in sample window, and treat any out of sample window you looked at and then modified the strategy for as no longer out of sample.

- Report the walk forward efficiency, which is the out of sample Sharpe divided by the in sample Sharpe.

- Walk forward efficiency above 0.8 is excellent, above 0.6 is deployable, above 0.4 is reduced allocation, and below 0.4 is paper trade only.

- Parameter stability across windows is itself a test. Wild swings across windows mean overfitting.

## Combinatorial purged cross validation

- Use combinatorial purged cross validation for factor and model validation, not for profit and loss backtests, since training on data after the test fold is never acceptable for profit and loss.

- Split the series into N groups and test all combinations of N choose k. With N equal to 10 and k equal to 2 there are 45 paths.

- Purge training observations whose label window overlaps any test label window, using a purge width near the maximum holding period.

- Embargo about 1 percent of observations after each test fold to absorb serial correlation in features.

- Report the distribution of path Sharpes, not the mean. More than 80 percent of paths profitable is Tier 1, more than 65 percent is Tier 2, and under 50 percent is a reject.

## Deflated Sharpe and overfitting probability

- After just 1000 independent skill free backtests, the expected best Sharpe is already 3.26.

- With N trials at a 5 percent significance level, the probability of at least one false positive is 40 percent at N equal to 10, 64 percent at N equal to 20, 92 percent at N equal to 50, and 99.4 percent at N equal to 100.

- The deflated Sharpe ratio adjusts the best Sharpe for the number of trials, the sample length, the skewness, and the kurtosis.

- Minimum Sharpe for significance on 5 years of daily data is 0.40 for 1 trial, 0.70 for 10 trials, 0.95 for 50 trials, 1.10 for 100 trials, and 1.40 for 1000 trials.

- Record all trials, including discarded ones, since the trial count is the single most important number in a backtest and is almost never disclosed.

- Try no more than about 45 independent configurations on 5 years of data.

- A new factor must clear a t statistic above 3.0, not the conventional 2.0, after accounting for the hundreds of factors already tried.

- Published signals lose about 58 percent of excess returns out of sample.

- In one replication of 50000 real costed crypto strategies, the best annualized Sharpe was 2.00, but the expected maximum under the null was 2.72, the deflated Sharpe was 0.029, and the median probability of backtest overfitting was 0.28. The best of 50000 failed deflation in all three markets tested.

- On purely random prices, the best of 174 moving average crossover variants showed an in sample Sharpe of 0.68 and an out of sample Sharpe of 0.00, and lost money in 48 percent of runs.

## Minimum backtest length

- The minimum backtest length in years is about 1.96 divided by the Sharpe, squared, plus 1.

- A Sharpe of 0.5 needs 16.4 years, a Sharpe of 1.0 needs 4.8 years, a Sharpe of 1.5 needs 2.7 years, and a Sharpe of 2.0 needs 2.0 years.

- With only about 14 months of Hyperliquid minute data, only a Sharpe above about 1.5 is statistically distinguishable from zero, unless breadth genuinely adds independent observations.

- Bars within one regime are correlated, not independent, so minute bar counts must never masquerade as independent samples.

- Keep observations per free parameter above 50, ideally above 100, and prefer the simpler version when removing half the parameters keeps most of the Sharpe.

## Regime split testing

- Report performance separately in bull, bear, and choppy segments, defined before the test, for example by BTC trend or realized volatility percentile.

- Demand cross asset validation, so a factor must work on at least 2 independent coins or sets.

- Never accept a single holdout that happens to be a bull run.

## Acceptance tiers

- Tier 1 deploys at full size. It needs a deflated Sharpe p value under 0.05, more than 80 percent of combinatorial purged paths profitable, walk forward efficiency above 0.6, a clear economic rationale, and validation on at least 2 independent datasets.

- Tier 2 deploys at reduced size. It needs a deflated Sharpe p value under 0.10, more than 65 percent of paths profitable, and walk forward efficiency above 0.4.

- Tier 3 is paper trade only. It needs a deflated Sharpe p value under 0.20, more than 50 percent of paths profitable, and walk forward efficiency under 0.4.

- Reject when the deflated Sharpe is not significant at p under 0.20, when fewer than 50 percent of paths are profitable, or when there is no rationale.

## Realistic expectations

- A robust systematic strategy has a Sharpe of 0.8 to 1.5. The S and P 500 sits near 0.4 to 0.5, and Buffett near 0.7 to 0.8.

- A backtest Sharpe above 2.0 for a long only strategy is almost certainly broken, and a Sharpe above 2.5 for daily strategies is suspicious.

- Multiply a backtested Sharpe by 0.5 to estimate live performance.

- A backtest showing 25 percent per year and a Sharpe of 2.5 typically degrades to about 8 to 12 percent and a Sharpe of 0.4 to 0.6 after correcting biases and costs.

- For small capital, small cap, minute level, multi strategy work, 50 to 100 percent annualized is already excellent, and 500 percent is a good year outcome, not a plan.

- Backtested drawdowns are underestimates. Live drawdowns run deeper through slippage, spreads, and illiquidity. Under 15 percent is conservative, 15 to 30 percent is moderate, 30 to 50 percent is aggressive and psychologically very hard, and above 50 percent most traders quit before recovery.

## Self deception patterns

- The beautiful equity curve on random data comes from taking the best of many trials on noise.

- Look ahead by one bar is the single most common and most damaging bug, and fixing it has moved a mean reversion Sharpe from 2.1 to 0.7 in a documented case.

- Survivorship by construction comes from testing only todays listed coins.

- Cost free fills come from the Nautilus default fill model, which fills limit orders with probability 1.0 and zero slippage.

- Funding ignored means a carry backtest misses the largest cost for held perpetuals.

- Sharpe of a near zero volatility carry is a volatility artifact, so judge carry by net return and tail risk.

- Regime cherry picked out of sample means the holdout happens to be a bull run, so demand per regime reporting.

- Parameter count creep means every added filter and threshold is another trial, so count them all.

- Breadth confused with independence means 1000 minute bars in one choppy week are not 1000 independent bets.

- Publication and crowding decay means signals lose 30 to 50 percent after publication, so monitor rolling IC and retire factors whose IC has halved.
