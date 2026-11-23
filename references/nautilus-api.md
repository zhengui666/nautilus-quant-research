# Nautilus API Notes

## Version pinned

- This skill targets nautilus_trader 1.231.0 on Python 3.12.

- Install with `pip install 'nautilus_trader==1.231.0'`.

- Assert the version at the start of every run, and stop if it is not 1.231.0.

- Version 2.x is pre-release, needs Python 3.13 or newer, and changes several names. Do not mix 1.x and 2.x code.

- Every snippet in this file was verified against an installed 1.231.0 package, except where the text says to verify first.

## Data mapping

- Reservoir 1 second candles map to `Bar` with `BarSpecification(1, BarAggregation.SECOND, PriceType.LAST)`.

- CryptoHFTData tick trades map to `TradeTick`, where `is_buyer_maker` true means the seller was the aggressor.

- CryptoHFTData L2 updates map to `OrderBookDelta`.

- The top level of an `l2Book` snapshot maps to `QuoteTick` with best bid and ask price and size.

- Funding history maps to `FundingRateUpdate`, and mark prices map to `MarkPriceUpdate`.

- A bar type prints as `BTCUSDT-PERP.HYPERLIQUID-1-MINUTE-LAST-EXTERNAL`, which is instrument id, step, aggregation, price type, and aggregation source joined by dashes.

## Catalog

- Import the catalog from `nautilus_trader.persistence.catalog` as `ParquetDataCatalog`.

- Write the instrument definition before any market data, and write data with the generic `write_data` method, which takes a list of objects.

- Sort all vendor data by `ts_init` in ascending order before loading it.

- Read data back with `catalog.query`, and check the first and last timestamps with `query_first_timestamp` and `query_last_timestamp`.

- The catalog skips files that already exist, so delete the catalog directory when you need a clean reload.

## Instrument

- Import the instrument class from `nautilus_trader.model.instruments` as `CryptoPerpetual`.

- Use the id format `BTCUSDT-PERP.HYPERLIQUID`, which is base plus quote plus PERP on the HYPERLIQUID venue.

- Set `price_precision` and `size_precision` from the Hyperliquid `meta` and `szDecimals` fields.

- Build price increments with `Price.from_str` and size increments with `Quantity.from_str`, since the constructor expects those objects and not Decimal values.

- Set `maker_fee` and `taker_fee` on the instrument as Decimal values, using 0.00015 and 0.00045 for Hyperliquid Tier 0.

- Set `min_notional` to 10 USD, which is the Hyperliquid minimum order value.

- Prices and quantities in data must match the instrument precision exactly, or the tick or bar is skipped with a warning.

## Venue and engine

- Import the engine from `nautilus_trader.backtest.engine` as `BacktestEngine`.

- Add the venue with separate arguments, not with a config object.

```python
engine.add_venue(
    Venue("HYPERLIQUID"),
    oms_type=OmsType.HEDGING,
    account_type=AccountType.MARGIN,
    base_currency=USDT,
    starting_balances=[Money(3000, USDT)],
    fill_model=FillModel(
        prob_fill_on_limit=Decimal("0.2"),
        prob_slippage=Decimal("0.5"),
        random_seed=42,
    ),
    fee_model=MakerTakerFeeModel(),
    book_type=BookType.L1_MBP,
)
```

- The venue name must match the instrument venue, or `add_instrument` raises an invalid configuration error.

- Use `OmsType.HEDGING` for concurrent long and short positions per instrument, and `AccountType.MARGIN` for perpetuals.

- Use `BookType.L1_MBP` for bars and trades, and `BookType.L2_MBP` for order book deltas.

- Import the fee model from `nautilus_trader.backtest.models` as `MakerTakerFeeModel`, and construct it with no arguments, since it reads its rates from the instrument.

- Import the fill model from the same module as `FillModel`, and always pass `prob_fill_on_limit`, `prob_slippage`, and `random_seed`.

- Import the latency model from the same module as `LatencyModel`, and pass `base_latency_nanos` when the strategy needs a fill delay.

- Add the instrument with `engine.add_instrument(instrument)`, add data with `engine.add_data(bars)`, add the strategy with `engine.add_strategy(strategy)`, and run with `engine.run()`.

- `add_data` sorts the whole stream on each call by default, so for many instruments pass `sort=False` and sort once at the end, or batch add.

## BacktestNode path

- Import the node from `nautilus_trader.backtest.node` as `BacktestNode`, not from `nautilus_trader.backtest`.

- Build it with `BacktestNode(configs=[BacktestRunConfig(...)])` and run it with `node.run()`, which returns a list of `BacktestResult`, one per run config.

- One run config holds one venue list, one data list, and one engine config, so parameter sweeps and walk forward windows are separate run configs in one node call.

- In 1.231.0 the venue config takes importable config wrappers for its models, so prefer the engine path above unless the user asks for the node path, and verify the config shapes against the installed package first.

- Strategies reach a run config through `BacktestEngineConfig.strategies` as a list of `ImportableStrategyConfig` values, each built with a strategy path, a config path, and a config dict.

## Strategy skeleton

- Subclass `Strategy` from `nautilus_trader.trading.strategy` and its config from `StrategyConfig`.

- Subscribe in `on_start`, decide only on closed bars in `on_bar`, and never trade the bar that produced the signal.

```python
from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

class MomentumConfig(StrategyConfig):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    fast_ema_period: int = 10
    slow_ema_period: int = 20

class Momentum(Strategy):
    def __init__(self, config):
        super().__init__(config)
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type

    def on_start(self):
        self.instrument = self.cache.instrument(self.instrument_id)
        self.subscribe_bars(self.bar_type)

    def on_bar(self, bar):
        if self.portfolio.is_net_flat(self.instrument_id):
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                quantity=self.instrument.make_qty(self.config.trade_size),
            )
            self.submit_order(order)
```

- Available callbacks include `on_bar`, `on_quote_tick`, `on_trade_tick`, `on_order_book_deltas`, `on_funding_rate`, `on_mark_price`, `on_start`, `on_stop`, and the order and position event callbacks.

- Available subscriptions include `subscribe_bars`, `subscribe_quote_ticks`, `subscribe_trade_ticks`, `subscribe_order_book_deltas`, `subscribe_funding_rates`, and `subscribe_mark_prices`.

- Use `self.order_factory` for market, limit, stop market, stop limit, market to limit, market if touched, limit if touched, trailing stop market, trailing stop limit, and bracket orders.

- Manage orders with `submit_order`, `submit_order_list`, `cancel_order`, `cancel_all_orders`, `modify_order`, and `close_all_positions`.

- Check state with `self.cache.instrument(id)`, `self.portfolio.is_net_flat`, `is_net_long`, `is_net_short`, `realized_pnl`, and `unrealized_pnl`.

- Built in indicators live in `nautilus_trader.indicators`, including `ExponentialMovingAverage`, RSI, and ATR. Attach them with `register_indicator_for_bars`.

- The example strategy in the package is `EMACross` with `EMACrossConfig`, using `fast_ema_period` and `slow_ema_period`, not `fast_period` and `slow_period`.

## Results and statistics

- Read `engine.get_result()` for `stats_pnls`, `stats_returns`, `stats_general`, and `returns_series`.

- Read fills and positions from `engine.trader.generate_order_fills_report()` and `engine.trader.generate_positions_report()`, since those methods live on the Trader and not on the engine.

- Built in statistics live in `nautilus_trader.analysis`, including `SharpeRatio`, `SortinoRatio`, `MaxDrawdown`, `CAGR`, `CalmarRatio`, `WinRate`, `ProfitFactor`, `Expectancy`, `AvgWinner`, `AvgLoser`, `ReturnsVolatility`, `ExpectedShortfall`, `Alpha`, `BetaRatio`, `InformationRatio`, `TrackingError`, and `TreynorRatio`.

- Register extra statistics with `engine.portfolio.register_statistic(MaxDrawdown())`.

- `BacktestEngine.reset()` returns state to initial values while data and instruments persist, which supports repeated runs.

## Funding data

- `FundingRateUpdate` exists in `nautilus_trader.model.data`, and it carries the funding rate and the next funding timestamp.

- Load funding updates through the catalog with `write_data`, and verify that funding settlement appears in the results before trusting a carry backtest.

- Verify the exact constructor fields and the settlement behavior against the installed package before writing funding code, since the end to end funding path was not exercised during verification.

## Live trading

- The Hyperliquid adapter is a Rust adapter with Python bindings, using direct REST and WebSocket, with no external client libraries.

- Readiness is Stable for spot, perpetual futures, and HIP-3 perpetuals, and Experimental for HIP-4 outcomes.

- Instrument ids are `BTC-USD-PERP.HYPERLIQUID` for perps, `PURR-USDC-SPOT.HYPERLIQUID` for spot, and `{dex}:{Asset}-USD-PERP` for HIP-3.

- Mainnet orders carry the NautilusTrader builder code at a zero fee rate, but orders still require a one time `ApproveBuilderFee` approval or they are rejected.

- The testnet faucet serves only wallets that have deposited on mainnet first, and claims 1000 mock USDC.

- For API wallets set `HYPERLIQUID_ACCOUNT_ADDRESS` to the master address, or order status reports and user feeds come back empty.

- Validate every order type the strategy uses on the live adapter, since production readiness of an order type is the users responsibility.

## Gotchas verified against 1.231.0

- `BacktestNode` lives in `nautilus_trader.backtest.node`, not in `nautilus_trader.backtest`.

- `ParquetDataCatalog` lives in `nautilus_trader.persistence.catalog`, and its only write method is the generic `write_data`.

- `CryptoPerpetual` is the instrument class, not `PerpetualFuture`.

- `MakerTakerFeeModel` takes no rate arguments. Fees live on the instrument.

- `FillModel` and `ProbabilisticFillModel` both exist in 1.231.0 and take `prob_fill_on_limit`, `prob_slippage`, and `random_seed`.

- `BacktestDataConfig` uses `catalog_path` in 1.231.0, while 2.x uses a catalog config object.

- `engine.add_venue` takes the venue plus separate arguments, and the venue name must match the instrument venue.

- `generate_order_fills_report` and `generate_positions_report` live on `engine.trader`, not on the engine.

- The example strategy is `EMACross`, not `EmaCross`, and its periods are `fast_ema_period` and `slow_ema_period`.

- Bar volume precision must match the instrument size precision, or the run raises an error.

- The data engine stamps built bars at close time by default, through `time_bars_timestamp_on_close` set to True.
