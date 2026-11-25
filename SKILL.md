# Nautilus Quant Research

## Use this skill

- Use this skill when the user asks for factor research, a backtest, a strategy portfolio, or validation of a trading idea, and the work runs on NautilusTrader.

- Use it for crypto perpetuals work, especially Hyperliquid, at minute level horizons with small capital.

- Do not use it for live order placement until the live readiness gate passes.

- Do not use it for millisecond high frequency trading or market making, since the data and the fill models in this skill cannot support that.

- Answer the user in the language the user writes in, and write all code and reports in English.

## Pin the version first

- Check the installed version before you write any code, and assert it at the start of every run.

- This skill targets nautilus_trader 1.231.0 on Python 3.12, installed with `pip install 'nautilus_trader==1.231.0'`.

- Assert the version with `importlib.metadata.version("nautilus_trader")` and stop if it is not 1.231.0.

- Do not mix 1.x and 2.x code. Version 2.x is pre-release, needs Python 3.13 or newer, and changes several names, so a snippet written for one line does not run on the other.

- Record the seed, the data SHA, the git SHA, the pip freeze output, and the NautilusTrader version with every run, so any result can be reproduced exactly.

## Follow the gated pipeline

- Work through the gates in order, and stop at the first gate that fails.

- Report the failure with evidence instead of proceeding to the next gate.

- The gates are data intake, factor evaluation, single strategy backtest, validation, portfolio combination, and live readiness.

- A factor that fails evaluation never reaches a backtest, and a strategy that fails validation never reaches a portfolio.

## Hard rules

- Run every backtest through the Nautilus engine, never through a vectorized pandas backtest and never through hand rolled profit and loss math.

- Run `scripts/check_lookahead.py` on every strategy and factor file before you report any result, and fix every hit it prints.

- Never trade the bar that produced the signal. Compute the signal on bar t and execute only after a later eligible market event for the target instrument. For minute bars alone, use the same instrument's next bar-close state, not a claimed next-open or seconds-level fill.

- Stamp every bar with its close time in `ts_init`, never with its open time, since vendor bars are usually stamped at the open and loading them unchanged makes every bar visible one interval early.

- Never run a backtest with zero costs. Every backtest must include the taker fee, the maker fee, slippage, funding, and a liquidation guard, and a missing cost item is an automatic fail.

- Use `Decimal` for all money math, including risk fractions, fees, and profit and loss, and never use float for money.

- Use one strategy implementation for backtest and live, and never maintain a separate live version of a backtested strategy.

- Keep the universe dynamic and point in time. Re-screen it on every window, include coins that were later delisted, and exclude coins before they listed, since a backtest on todays survivors only is inflated.

- Count every trial, including discarded ones, and report the count with the result, since the trial count is the single most important number in a backtest.

## Data intake

- Load vendor data into a `ParquetDataCatalog` from `nautilus_trader.persistence.catalog` with the generic `write_data` method, and write the instrument definition before any market data.

- Start minute-level research with the [published Reservoir 1-minute snapshot](https://huggingface.co/datasets/Hydromancer/hyperliquid-reservoir) when it covers the study. Report missing UTC partitions and per-instrument gaps; do not stitch interrupted periods into one continuous series. Use the approved inputs for other data types: `download_reservoir.py` for requester-pays 1-second S3 candles, `download_cryptohftdata.py` for trades and L2, and `download_funding.py` for funding and open interest.

- Sort all vendor data by `ts_init` in ascending order before loading it, since the catalog requires ascending timestamps.

- Map Hyperliquid data to Nautilus types by the mapping in `references/nautilus-api.md`, and never mix data types that cannot drive the venue book type you chose.

- Use `L1_MBP` for bars and trades, and `L2_MBP` for order book deltas, and never mix a book type with data that cannot drive it.

- Define the instrument yourself with `CryptoPerpetual` from `nautilus_trader.model.instruments`, since there is no live adapter data path for backtests.

- Set the instrument `price_precision` and `size_precision` from the Hyperliquid `meta` and `szDecimals` fields, and build prices with `Price.from_str` and quantities with `Quantity.from_str`, since mismatched ticks and bars are skipped with warnings.

- Set the instrument `maker_fee` and `taker_fee` to the real Hyperliquid rates, since in 1.231.0 the fee model reads its rates from the instrument and not from its own constructor.

- Check the data for empty seconds, duplicated fills, and timestamp misalignment before any factor work, and handle each one deliberately instead of silently.

- Record the data window, the universe rules, and the data SHA with the result.

## Generate and improve factor candidates

- For a new research direction or an iteration on prior results, use the workflow in [Candidate generation and review](references/candidate-loop.md). Generate distinct hypotheses, review their code and economic logic separately, and use measured failures to propose the next candidates.
- Use only fields verified in the admitted data. One-minute candles are appropriate for minute signals, not for measuring seconds-level fills or order-book behavior.
- Research multi-factor combinations with distinct mechanisms. Measure each component's incremental contribution against the simpler baseline, and do not count several versions of one signal as independent evidence.
- Keep candidate selection and feedback inside development windows. No LLM judgment, in-sample score, or factor-only simulation substitutes for chronological, costed NautilusTrader backtests.

## Factor evaluation

- Do not limit factor types. The taxonomy in `references/factor-evaluation.md` is illustrative examples only, never a whitelist.

- Admit or reject any factor family by the same evaluation gates, whether it comes from price, volume, order flow, funding, microstructure, cross sectional signals, or alternative data.

- Evaluate the signal first and the portfolio second, since a feature that does not predict returns cannot be rescued by position management.

- Report the Spearman rank IC, the ICIR, the IC decay by horizon, the quantile monotonicity, the residual IC after neutralization, the turnover, the regime stability, and the correlation to known factors for every factor.

- Keep predictive IC separate from execution economics: report a turnover-based cost estimate at screening, then realized net results from NautilusTrader when a strategy is tested.

- Judge minute level IC against same horizon baselines, never against daily conventions, since minute level ICs are larger and decay faster.

- Start from an economic rationale, such as adverse selection, inventory pressure, funding pressure, or crowding, and demand a higher burden of proof from any factor with no rationale.

- Read the full criteria and thresholds in `references/factor-evaluation.md` before you accept any factor.

## Single strategy backtest

- Build the strategy as a `Strategy` subclass with a `StrategyConfig` subclass, subscribe in `on_start`, and decide only on closed bars in `on_bar` or on ticks in `on_quote_tick` and `on_trade_tick`.

- Use `instrument.make_price` and `instrument.make_qty` for every order price and quantity, and never construct them from raw floats.

- Set the venue with `engine.add_venue`, pass the venue name that matches the instrument venue, and pass the fill model, the fee model, and the book type as separate arguments.

- Use a default `MakerTakerFeeModel()` in the venue, since in 1.231.0 it takes no rate arguments and reads its rates from the instrument.

- Configure the fill model explicitly with `FillModel(prob_fill_on_limit=Decimal("0.2"), prob_slippage=Decimal("0.5"), random_seed=42)`, since the defaults are 100 percent fill and zero slippage.

- State the latency assumption and use a `LatencyModel` where the data can resolve the intended delay. For bar-only execution, defer submission explicitly; a latency setting alone does not guarantee the price came from the next target-instrument event.

- Turn on `liquidity_consumption` when the strategy trades size against a thin book, since the simulated fills otherwise never consume the displayed size.

- Model funding explicitly as an hourly cash flow accrual, since Nautilus has no built in funding module and a carry backtest without funding is silently wrong.

- Enforce the 10 USD minimum notional in the sizing logic, and never open a position that cannot be closed in one order of at least 10 USD notional.

- Read the results from `engine.get_result()` and from `engine.trader.generate_order_fills_report()` and `engine.trader.generate_positions_report()`.

- Read the full API notes, the venue setup, and the strategy skeleton in `references/nautilus-api.md`, and the full cost model in `references/costs-hyperliquid.md`.

- Diagnose a failed run from its symptoms. A trade count of zero means a signal bug, a flat equity curve means a sizing bug, a NaN equity curve means a warmup leak, and an open position at the end means a missing exit.

- Fix one thing at a time, try at most three fixes, and then escalate with the evidence.

## Validation

- Walk forward analysis is mandatory. Optimize on the in sample window, test on the immediately following out of sample window, roll forward, and concatenate the out of sample results.

- Keep parameter selection strictly inside the in sample window, and treat any out of sample window you looked at and then modified the strategy for as no longer out of sample.

- Report the walk forward efficiency, which is the out of sample Sharpe divided by the in sample Sharpe, and use the tiers in `references/validation.md`.

- Validate factors with combinatorial purged cross validation, purge training observations whose label window overlaps any test label window, and embargo about 1 percent of observations after each test fold.

- Report the deflated Sharpe ratio and the probability of backtest overfitting alongside the plain Sharpe, and reject any configuration with a probability of backtest overfitting above 0.05.

- Report performance separately in bull, bear, and choppy segments, defined before the test, and demand per regime reporting instead of a single holdout that happens to be a bull run.

- Demand at least 100 to 200 completed trades before trusting any metric, and at least 500 out of sample trades for a reliable edge claim.

- Remember that with only about 14 months of Hyperliquid history, only a Sharpe above about 1.5 is statistically distinguishable from zero, unless breadth genuinely adds independent observations.

- Treat a backtest Sharpe above 2.0 for a long only strategy as almost certainly broken, and estimate live performance by halving the backtested Sharpe.

- Read the full validation method, the acceptance tiers, and the self deception patterns in `references/validation.md`.

## Portfolio combination

- Start with equal weight or inverse volatility weight across strategies, and treat hierarchical risk parity as the only optimization worth upgrading to.

- Never use mean variance optimization or full Kelly on short history, since both amplify estimation error into unstable weights.

- Use Kelly only as a position size cap, never as a prescription, and prefer half Kelly, which keeps about 75 percent of the growth with half the variance.

- Allocate by risk contribution, not by capital, and measure correlation on strategy returns, not on signals, since two signals can look different while their holdings and profits overlap.

- Target 15 to 20 percent annualized portfolio volatility, risk 0.5 to 1 percent of equity per trade, keep leverage at 1 to 2 times with a cap of 3 times, and use isolated margin.

- Rebalance strategy weights weekly and only when drift exceeds 5 percent, and keep position level trading signal driven and continuous.

- Apply the drawdown circuit breaker. Halve leverage at a 90 day rolling drawdown of minus 15 percent, pause at minus 25 percent, and resume only after the drawdown recovers and at least 10 days have passed.

- Stress test with every pairwise correlation raised by 0.3, and size positions so the portfolio survives all correlations at 1.0 inside the risk budget.

- Give each strategy enough capital that its single trades stay at 50 to 100 USD notional, well above the 10 USD minimum, and cut the number of strategies instead of diluting the capital.

- Keep all strategies running at fixed risk budgets in version one, and treat regime detection as a second stage upgrade with its own validation gate.

- Read the full weighting comparison, the risk budget structure, and the small account failure modes in `references/portfolio.md`.

## Live readiness

- Run the same strategy object on testnet before any real capital, and confirm the testnet faucet requirement, which is a prior mainnet deposit.

- Complete the one time builder fee approval before mainnet orders, or orders are rejected.

- Set the account address for API wallets, or order status reports and user feeds come back empty.

- Verify every order type the strategy uses on the live adapter, since production readiness of an order type is the users responsibility.

- Put monitoring, a kill switch, and a reconciliation check in place before the first live order, and define the conditions that pause trading.

- Never deploy a strategy that has not passed the validation gate, and never deploy a Tier 3 strategy at full size.

## Report what you found

- Report the data window, the universe rules, the trial count, the costs assumed, and the determinism pins with every result.

- Report the Sharpe, the max drawdown, the win rate, the profit factor, the trade count, the walk forward efficiency, the deflated Sharpe, and the probability of backtest overfitting.

- Report the per regime results and the acceptance tier, and end with a verdict that names the tier and the next action.

- Say what you verified against the installed package and what is still untested, and never present an unverified API call as working.

## Available connectors

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Websites

- [NautilusTrader backtest tutorial](https://nautilustrader.io/docs/latest/getting_started/backtest_high_level/) for the high level backtest flow.

- [NautilusTrader backtesting concepts](https://nautilustrader.io/docs/latest/concepts/backtesting/) for execution order, fill prices, and matching.

- [NautilusTrader loading external data](https://nautilustrader.io/docs/latest/how_to/loading_external_data/) for catalog writes and external readers.

- [NautilusTrader Hyperliquid adapter](https://nautilustrader.io/docs/nightly/integrations/hyperliquid/) for live trading, builder fees, and testnet setup.

- [NautilusTrader Python API reference](https://nautilustrader.io/docs/python-api-latest/) for exact class names and signatures. Verify every name against the installed package before you use it in code.

## Alternatives for better results

- Triage factors with fast vectorized screening in pandas or polars first, and run only the survivors through the Nautilus event driven engine.

- Expand the universe only after validation, since the data cost of expanding is negligible and a wider universe adds breadth.
