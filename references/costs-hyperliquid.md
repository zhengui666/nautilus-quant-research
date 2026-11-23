# Costs on Hyperliquid

## Fees

- Hyperliquid entry tier, Tier 0 under 5M USD of 14 day volume, charges 0.045 percent taker and 0.015 percent maker on perpetuals.

- Fees are charged on notional, not on margin. A 1000 USD margin at 10 times leverage is a 10000 USD position, so one market order costs 4.50 USD and a round trip costs 0.9 percent of margin.

- The minimum order value is 10 USD notional, so enforce it in sizing logic and never open a position that cannot be closed in one order of at least 10 USD notional.

- In nautilus_trader 1.231.0 the fee model reads its rates from the instrument, so set `maker_fee` and `taker_fee` as Decimal values on the `CryptoPerpetual` instrument and use a default `MakerTakerFeeModel()` in the venue.

- Do not pass rate arguments to `MakerTakerFeeModel` in 1.231.0, since its constructor takes only an optional config and the rate arguments fail.

- Use maker assumptions only if the strategy genuinely rests limit orders, and use taker assumptions otherwise.

## Funding

- Hyperliquid settles funding hourly, not every 8 hours like most venues, so funding flips arrive faster.

- Charge or pay funding on every open position each hour in the backtest. For held positions funding is often larger than trading fees.

- Nautilus has no built in funding accrual in backtests, so model funding explicitly as a cash flow accrual, and never ignore it.

- Load `FundingRateUpdate` data through the catalog, and verify that funding settlement appears in the results before trusting a carry backtest.

- Funding carry is a directional trade in this plan, not a delta neutral basis trade. Shorting the crowded side earns funding but carries price risk, and a sharp rally can liquidate the short leg before any hedge helps.

- Judge carry by net return and tail risk, not by Sharpe, since a near zero volatility funding stream produces an inflated Sharpe that is a volatility artifact.

## Slippage

- Model slippage from L2 depth, never from a fixed basis point guess.

- A 1000 to 3000 USD market order can move a thin small cap book by several basis points.

- Assume adverse selection on maker fills, since fills happen when the price moves against the resting order.

- Sensitivity test slippage at 2 times and 3 times the base assumption. If the edge dies at 2 times, it is not an edge.

- Small cap slippage is the binding cost at a few thousand USD of capital, not the fee schedule.

## Fill models

- Nautilus defaults are optimistic and must be configured. The default fill model fills limit orders with probability 1.0 and zero slippage.

- Configure `FillModel(prob_fill_on_limit=Decimal("0.2"), prob_slippage=Decimal("0.5"), random_seed=42)` for small caps, and always set `random_seed`, since unseeded runs with slippage above zero are not reproducible.

- `ProbabilisticFillModel` takes the same arguments in 1.231.0.

- A `LatencyModel` with `base_latency_nanos` delays only the inbound leg, which covers submits, modifies, and cancels. Venue events are not delayed, and without a latency model there is no fill delay at all.

- Turn on `liquidity_consumption` in the venue config to track consumed size per level, since simulated fills otherwise never edit the historical book and the same displayed size can fill unlimited simulated orders.

- Turn on `queue_position` for displayed queue tracking when the strategy rests limit orders, since it needs book plus trade data.

- Trade driven fills are opportunistic. A print proves liquidity existed momentarily, not that it stayed.

- With an L1 book, after displayed size is exhausted a market order fills the residual one tick worse, unless it would cross the price protection points, the minimum or maximum price, or zero. Set `price_protection_points` in the venue config, where 0 disables it.

- For stop market, market if touched, and trailing stop market orders on bars, a gap through the trigger fills at the simulated market price, while an intrabar move through the trigger fills at the trigger price. Use quote, trade, or book data when gap or path precision matters.

## Execution order

- Per data point the engine runs exchange processing first, so resting orders fill against the new market state, then strategy callbacks, then venue settling for newly submitted orders.

- An order submitted inside `on_bar` cannot fill on the bar that triggered it. It fills on subsequent data, and a market order submitted on a bar close executes against the next market state.

- Bars are delivered on close, and the data engine defaults to stamping built bars at close time.
