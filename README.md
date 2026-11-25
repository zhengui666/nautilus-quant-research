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
2. **Factor research** - generate candidates, review code and logic, then use
   measured feedback to iterate. Evaluate with IC, ICIR, decay, turnover,
   and cost-aware metrics. See the [candidate workflow](references/candidate-loop.md).
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
  candidate-loop.md        hypothesis, review, feedback, and combination workflow
  factor-evaluation.md      universal factor criteria, illustrative taxonomy
  costs-hyperliquid.md      fee / funding / slippage model
  validation.md             walk-forward, CPCV, DSR, PBO, acceptance tiers
  portfolio.md              weighting, risk budgets, drawdown control
  nautilus-api.md           version-pinned API notes and strategy skeleton
scripts/
  check_lookahead.py        scan strategy and factor files for look-ahead bias
  factor_eval.py            IC / ICIR / turnover / decay report from a CSV
  run_walkforward.py        run a backtest over rolling walk-forward windows
  download_reservoir.py     Reservoir 1s candles from S3 (requester pays)
  download_cryptohftdata.py CryptoHFTData hourly trades / L2 / funding / OI
  download_funding.py       official API funding history, plus OI files
  requirements-data.txt     dependencies for the three data scripts
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

## Data scripts

Start minute-level research with Hydromancer’s [published Reservoir minute
snapshot](https://huggingface.co/datasets/Hydromancer/hyperliquid-reservoir).
It is a dated snapshot, not the live S3 archive. The scripts below are for
other data needs. Reservoir S3 requires AWS credentials and bills the requester
for requests and applicable transfer. Check the approved budget before use.

```bash
pip install -r scripts/requirements-data.txt

# 1. Main data: Reservoir 1-second candles (needs AWS credentials that can
#    pay requester-pays egress; one S3 read per day, filtered by coin)
python scripts/download_reservoir.py --symbols BTC ETH --start 2025-09-01 --end 2025-09-30
python scripts/download_reservoir.py --symbols BTC --start 2025-09-01 --end 2025-09-30 --resample 1m

# 2. Slippage modeling: CryptoHFTData tick trades, no key needed
#    (anonymous tier: 60 files/min/IP; a free key removes the limit)
python scripts/download_cryptohftdata.py --symbols BTC ETH --start 2025-09-29 --end 2025-10-31

# 3. Depth and spread: CryptoHFTData L2 order book, same command
python scripts/download_cryptohftdata.py --symbols BTC ETH --start 2025-09-29 --end 2025-10-31 \
  --data-types orderbook

# 4. Funding + open interest: official API funding history (free, deep)
#    plus CryptoHFTData hourly OI files with --oi
python scripts/download_funding.py --symbols BTC ETH --start 2025-07-28 --end 2026-11-23 --oi
```

Use `--dry-run` to inspect a download plan. For S3, request missing dates
explicitly: the script opens a day before checking local symbol outputs.
Each script documents its source and expected data format in its header.

Verified 2026-11-24: CryptoHFTData BTC 2026-09-02 downloads match the
published sample exactly (20,881 trades and 26,120 order book rows in the
12:00 UTC hour); funding history returns 90 hourly BTC rows for
2026-11-20 to 2026-11-23. The Reservoir pull was not run
end to end here because this machine has no AWS credentials; the script
fails cleanly with a 403 and a message saying credentials are required.

## License

MIT. See [LICENSE](LICENSE).
