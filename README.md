# Nautilus Quant Research

A skill for an agent doing factor research, strategy portfolios, and
backtesting on [NautilusTrader](https://nautilustrader.io/), for crypto
perpetuals. It covers the full loop: data intake, factor evaluation,
single-strategy backtests, walk-forward validation, portfolio combination,
and live readiness.

## Who it is for

- Personal quant trading on Hyperliquid perpetuals at minute-level horizons
  (1m-15m signals, holding minutes to hours), small caps, a few thousand USD
- Multi-strategy portfolios: momentum + mean reversion + funding carry,
  cross-sectional market neutral, volatility-adaptive sizing

## Install

Clone this repo into your Muse custom skills directory:

```bash
git clone https://github.com/zhengui666/nautilus-quant-research.git \
  ~/workspace/custom-skills/nautilus_quant_research
```

## How it works

The skill runs a gated pipeline. Work stops at the first gate that fails,
and the failure is reported with evidence instead of proceeding.

1. **Data intake** - vendor data into a `ParquetDataCatalog`, instrument
   defined by hand, dynamic point-in-time universe
2. **Factor evaluation** - IC / ICIR / decay / turnover / net IC after costs.
   Factor families are **not limited**: any family is admitted or rejected
   by the same gates
3. **Single-strategy backtest** - everything through the Nautilus engine,
   never a vectorized pandas backtest; costs are never zero
4. **Validation** - walk-forward analysis (mandatory), combinatorial purged
   cross-validation, deflated Sharpe, probability of backtest overfitting
5. **Portfolio combination** - equal weight or inverse volatility to start,
   hierarchical risk parity as the only optimization worth upgrading to
6. **Live readiness** - testnet first, builder fee approval, monitoring and
   kill switch

## Version pin

The skill targets **nautilus_trader 1.231.0** on Python 3.12. Every code
snippet was verified against an installed 1.231.0 package, including a full
end-to-end backtest. Version 2.x is pre-release and changes several names,
so 1.x and 2.x code must not be mixed.

Key verified facts that differ from the docs: fees live on the instrument
(`maker_fee` / `taker_fee` on `CryptoPerpetual`), the catalog has only the
generic `write_data` method, `BacktestNode` lives in
`nautilus_trader.backtest.node`, and the example strategy is `EMACross`.

## Layout

```text
skill.yaml                  skill descriptor
SKILL.md                    pipeline, gates, hard rules, acceptance checklist
references/
  factor-evaluation.md      universal factor criteria, illustrative taxonomy
  costs-hyperliquid.md      fee / funding / slippage model
  validation.md             walk-forward, CPCV, DSR, PBO, acceptance tiers
  portfolio.md              weighting, risk budgets, drawdown control
  nautilus-api.md           version-pinned API notes and strategy skeleton
scripts/
  check_lookahead.py        scan strategy and factor files for look-ahead bias
  factor_eval.py            IC / ICIR / turnover / decay report from a CSV
  run_walkforward.py        run a backtest over rolling walk-forward windows
evals/
  should-trigger.txt        requests that should trigger this skill
  should-not-trigger.txt    requests that should not
```

## Scripts

```bash
# Reject look-ahead patterns before reporting any result
python scripts/check_lookahead.py path/to/strategy.py

# Evaluate a factor from factor values and forward returns
python scripts/factor_eval.py factor.csv --min-periods 30

# Walk-forward a backtest script that accepts --start --end --out
python scripts/run_walkforward.py backtest.py \
  --start 2026-07-01 --end 2026-11-01 --is-days 60 --oos-days 30 --step-days 30
```

## Costs modeled

Hyperliquid Tier 0: maker 0.015%, taker 0.045% on notional, minimum order
10 USD notional, funding settles hourly. The fill model defaults (100%
fill, zero slippage) are never used as-is.

## License

MIT. See [LICENSE](LICENSE).
