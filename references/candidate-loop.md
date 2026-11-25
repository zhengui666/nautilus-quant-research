# Candidate generation, review, and iteration

Use this workflow when a user asks for new factor ideas or a next research
iteration. It adapts the generation, quality review, and evolutionary search
loop in [CogAlpha (ACL 2026)](https://aclanthology.org/2026.acl-long.538/) and its
[prompt repository](https://github.com/OpenFinMind/CogAlpha_Prompt).
The stock experiments do not establish a minute-level crypto edge. Use the
method, not the paper's market assumptions, forecast horizons, or prompts.

## 1. Specify and generate

State the market universe, usable UTC intervals, point-in-time fields, signal
cadence, forecast horizons in minutes, and cost and turnover assumptions.
List fields that are absent. If a signal needs trades, spreads, depth, or
funding, check that this data is available at the required timestamps before
proposing to evaluate it. Keep label windows and warmups inside available data.

Ask for a small batch of economically distinct hypotheses. Start with primary
research and venue documentation; public factor libraries and practitioner
forums can suggest mechanisms, but do not establish results. Record each
candidate before screening:

| Field | What to record |
| --- | --- |
| Identity | Candidate ID, parent IDs if any, and source or rationale |
| Hypothesis | What behavior creates the signal, expected direction, and when it should fail |
| Signal | Formula, verified input fields, event availability, lookback, and forecast horizon |
| Comparison | Simple baseline, what this adds, and likely turnover or execution cost |
| Validation | Data window, universe, and one observation that would falsify the hypothesis |

## 2. Review, then measure

Review each new or revised candidate independently of generation, using a
separate pass or reviewer where available. Check the formula against the stated hypothesis, dataset schema,
event timing, rolling windows, cross-sectional eligibility, and numerical
behavior. Note violations and changes; count every candidate and repaired
variant evaluated as a distinct trial. Run the repository look-ahead checker,
but do not treat a clean static scan as evidence that timestamps or joins are
correct.

Run the factor tests in [Factor evaluation](factor-evaluation.md). Compare
with same-horizon baselines on the same dates and instruments. Fast vectorized
calculations may screen signals, but all strategy P&L and fill claims must
come from the pinned NautilusTrader engine with the modeled costs.

## 3. Combine, revise, and stop

Combine complementary mechanisms, not near-duplicates. Compare the combination
with each component and with an equal-weight or other simple baseline on matched
windows; remove one component at a time to measure incremental value. Consider
overlap in exposures and realized returns as well as signal correlation. For
example, combine a direction signal with a separate liquidity or cost signal
if the required inputs exist, then test whether the latter improves the result
beyond simply trading less. This is an illustration, not a required factor.

Feed back measured failure reasons: poor net performance, extreme turnover,
weak breadth, instability across regimes, duplicated exposure, and data or
implementation defects. Retest a repaired variant only when the change addresses
a specific defect or hypothesis. For a new variant, change one mechanism or
recombine two distinct components and record what changed. Define a bounded
trial budget before iterating. Keep the trial ledger separate from the number
of model fits and cross-validation paths.

Reserve a chronological holdout and fix the candidate and evaluation settings
before opening it. Keep its outcomes out of candidate prompts,
parameter selection, and feedback. Follow [Validation](validation.md) for
walk-forward testing. If you revise a candidate after examining a test window,
treat that window as development and require a fresh unseen test. Report failed
candidates and limits, not just winners. Stop when the budget is used, a gate
blocks further work, or no candidate adds measurable value.
