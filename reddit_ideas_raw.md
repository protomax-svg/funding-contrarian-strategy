# r/algotrading crypto-relevant strategy ideas — harvested via RSS

Method: fetched r/algotrading top(year/all)/hot RSS feeds + 20 search-RSS queries (crypto, bitcoin,
funding rate, perpetual, basis, liquidation, mean reversion, momentum, binance, on-chain, volatility,
market making, order book, pairs trading, stat arb, edge, profitable, regime), merged/deduped 1332
unique posts, filtered to crypto+concrete-rule keyword matches, then fetched full post bodies + top
comments (via `.rss` comment feeds) for the 33 most promising candidates. Reddit RSS does not expose
post score, so "score" is omitted below (not available via this access path) — dates are post times
from the Atom feed. Nothing below is invented; all rules/quotes are paraphrased/quoted from what was
actually read.

---

## 1. Bitcoin Dual-Signal Trend Sentinel (Z-score trend/regime filter)
**Source:** https://www.reddit.com/r/algotrading/comments/1qgcq2h/sharing_my_bitcoin_systematic_strategy_6592_cagr/ (2026-01-18)
**Rule:** Daily BTC spot. Baseline = 65-period EMA of close. Volatility = 65-period stdev of close.
Z = (close − baseline) / volatility. Z > "Bull Filter" threshold → go long. Z < "Bear Filter" threshold
→ exit to cash. Between thresholds → hold state. (Exact numeric thresholds not disclosed — author says
they were "eyeballed," not grid-searched.) Claimed: CAGR 65.92% vs B&H 56.18%, MDD 26.79% vs 75%, 53
trades over 11.66y, win rate 47.2%, avg win/loss ratio 8.19:1.
**Why it might work / pushback:** Normalizing BTC's absolute moves by rolling volatility lets one
threshold work across price regimes ($1k vs $100k). Pushback (thekoonbear, RoozGol, pale-blue-dotter):
results are dominated by BTC's early explosive growth (2014-17); author himself conceded recent-cycle
backtest CAGR is closer to ~30%, not 66%, and expects continued alpha decay as the market
institutionalizes/matures. "Of course any strategy is profitable" in BTC's biggest historical bull run.
**Data for crypto test:** Daily BTC OHLC — free/keyless (Binance, CoinGecko, Yahoo Finance).
**Testability: 4/5** (mechanics fully specified except exact z-thresholds, which are gridsearchable).
**Plausibility: 3/5** (known technique category; live edge likely much smaller than headline number).

## 2. Bollinger Band + VWAP Breakout with ADX/RSI filter, BTCUSD H1
**Source:** https://www.reddit.com/r/algotrading/comments/1lmrjl6/updated_bollinger_band_vwap_breakout_strategy/ (2025-06-28), follow-up to https://www.reddit.com/r/algotrading/comments/1lka4qh/simple_bollinger_band_breakout_strategy_75_year/ (2025-06-25)
**Rule:** BTC/USD, H1. Indicators: BB(42, 2.5σ), VWAP, ADX(5), RSI(5); up to 3 concurrent trades.
Long: close ≥ upper BB, OR (close>VWAP for last 6 candles AND RSI>55 AND ADX>45). Short: mirror.
Exit: TP 3%, SL 1.5%, time-exit after 1075 min (~18h), or mean-reversion exit (candle re-closes inside
band after being outside). Commission 0.025%/trade. v1 (BB only): 285.76% return, 41.4% WR, -39.8% MDD,
11,069 trades. v2 (+VWAP/ADX/RSI filter): 289.46% return, 48.4% WR, -29.8% MDD, 6,284 trades.
**Why it might work / pushback:** Trend-confirmation filters (VWAP position, ADX strength, RSI) aim to
cut false breakouts vs raw BB touch. Pushback: accused of being an ad for the "Moon Tester" backtest
platform (ToS/IP concerns raised in comments); no out-of-sample/walk-forward shown; parameter set
(BB 42/2.5, ADX(5), RSI(5)) looks hand-tuned to commenters; mvstartdevnull asks whether drawdowns
cluster below EMA(200) (regime dependence untested).
**Data for crypto test:** BTC/USD hourly OHLCV + volume for VWAP — free/keyless (Binance klines).
**Testability: 5/5** (every parameter given). **Plausibility: 2/5** (unusual tuned params, no OOS test,
flagged by the community itself as overfit-smelling).

## 3. SMA(50)/EMA(7) trend filter + RSI(2) vs ADX(2) crossover
**Source:** https://www.reddit.com/r/algotrading/comments/1lmu1qp/bitcoin_strategy_that_outperformed_buy_hold/ (2025-06-28)
**Rule:** Daily BTCUSD/BTCEUR/ETHUSD, long-only. Entry: Close > SMA(50) AND Close > EMA(7) AND
RSI(2) > ADX(2). Exit: RSI(2) < ADX(2). Backtest 2012-2025, no slippage/fees included (author's own
disclosure).
**Why it might work / pushback:** Fast trend/momentum confirmation stack. Pushback: Astr0_G0d flags
that comparing RSI(2) numerically against ADX(2) has no clear rationale ("don't get an idea about
rsi>adx") — two oscillators with different meanings being compared as if commensurable; justV_2077
notes no train/test split disclosed → overfitting risk; Astr0_G0d separately notes crypto's structure
changed post-2020 (perp adoption) and post-2024 (spot ETF), so old backtest years may not transfer.
**Data for crypto test:** Daily BTC/ETH OHLC — free/keyless.
**Testability: 5/5** (trivial to code). **Plausibility: 2/5** (ad hoc indicator comparison, no
fee/slippage modeling, unvetted by community beyond skepticism).

## 4. RSI(5) momentum breakout (long while RSI stays elevated)
**Source:** https://www.reddit.com/r/algotrading/comments/1gdjxdg/best_backtested_bitcoin_strategy_i_found/ (2024-10-27)
**Rule:** Daily BTC (Coinbase). Buy when RSI(5) > 70. Close when RSI(5) < 70.
**Why it might work / pushback:** Inverts the usual "RSI>70 = overbought, fade it" heuristic and
instead treats sustained RSI>70 as confirmation of a strong momentum regime — consistent with
documented momentum persistence in trending crypto assets. Pushback: thread has essentially no
technical scrutiny (mostly people asking to DM for "the system") — treat as **unvetted by the
community**, a real gap worth flagging.
**Data for crypto test:** Daily BTC OHLC — free/keyless.
**Testability: 5/5** (one-line rule). **Plausibility: 2/5** (extremely simple single-indicator rule,
classic shape of a strategy that happens to work in one bull regime; needs adversarial multi-regime
testing since the community never actually challenged it).

## 5. Kalman Filter Pairs Trade, BTC/ETH
**Source:** https://www.reddit.com/r/algotrading/comments/obbb5d/kalman_filter_stat_arb/ (2021-07-01)
**Rule:** 4H BTC & ETH data (1035 days tested). Kalman-filter regression estimates a time-varying hedge
ratio (beta) between BTC and ETH (method from Ernie Chan's *Algorithmic Trading*). Spread
S = BTC − beta×ETH. Z-score S via rolling mean/std (lookback ~10, or Kalman-derived half-life).
Long spread at Z ≤ −2, short spread at Z ≥ 2, exit at Z crossing 0. ~27% time-in-market.
**Why it might work / pushback:** Time-varying hedge ratio adapts to a shifting BTC/ETH relationship
better than static OLS beta. Pushback: dank34rt / amado88 debate whether Binance-level fees (~0.1%/side
×2 legs) erase the edge; zbanga adds spread/slippage and perp-funding costs as further uncounted drag;
private_donkey directly challenges the core assumption — Kalman filters assume a Markovian state, and
crypto prices arguably aren't; Tacoslim (author) notes buy-and-hold is a poor benchmark for a
market-neutral strategy (should compare to cash rate, not BTC HODL).
**Data for crypto test:** BTC & ETH OHLCV, 4H or finer — free/keyless (Binance/Bybit).
**Testability: 4/5** (fully specified except exact Kalman noise params). **Plausibility: 3/5**
(legitimate category; live viability hinges entirely on fee/funding drag, which the community flags
directly, and BTC/ETH cointegration stability is itself disputed — see #6).

## 6. Cointegration/Z-score Pairs Trading across the crypto universe — *documented negative result*
**Source:** https://www.reddit.com/r/algotrading/comments/voidav/statistical_arbitrage_in_cryptocurrencies/ (2022-06-30) + follow-up https://www.reddit.com/r/algotrading/comments/vqmv7u/my_basic_code_to_find_cointegration_in_crypto/ (2022-07-03)
**Rule:** For each pair in a broad crypto universe (author used FTX, 5m candles, ~7 months / ~50k
candles per market), run Engle-Granger cointegration (statsmodels `ts.coint`) or Johansen test on close
prices. Keep pairs with p<0.05, compute OLS hedge ratio beta, spread = priceX − beta×priceY, trade
z-score extremes with mean-reversion exit at Z=0.
**Why it might work / pushback:** Classic, well-established stat-arb structure — but this thread is
valuable precisely because the **author reports it mostly failing**: across hundreds of crypto pairs,
only a handful passed p<0.05, and even those didn't look visually stationary. zarray91 explains why:
crypto pairs mostly lack the fundamental economic linkage (e.g. Pepsi/Coke) that makes cointegration
durable — it's frequently a spurious regression ("you will be there catching falling knives").
biminisurfer, a live practitioner, reports relationships "fell apart after 60 days" on average and
required continuous pair-universe refresh — cointegration in crypto is a moving target, not a stable
structural relationship.
**Data for crypto test:** 5m-1h OHLC across 50-100+ symbols — free/keyless (Binance/Bybit).
**Testability: 5/5** (statistical test is cheap and exactly specified).
**Plausibility: 2/5** — logged here explicitly as a **cautionary/negative finding**, not a
ready-to-deploy edge: rolling pair-universe re-selection every ~60 days appears necessary, and the
underlying relationships are fragile.

## 7. Perp funding-rate cash-and-carry + funding mean-reversion signal
**Source:** https://www.reddit.com/r/algotrading/comments/1s2lz9m/perpetuals_funding_rate_modeling/ (2026-03-24), comment by /u/NoodlesOnTuesday
**Rule:** Classic cash-and-carry — long spot, short perp when funding is positive, collect funding.
Separately claimed: funding rate itself tends to mean-revert over multi-day horizons, and extreme
positive funding readings can be used as a contrarian directional signal (exact threshold/logic was
cut off in the RSS excerpt and not recoverable from this access path).
**Why it might work / pushback:** Funding reflects crowd leverage/positioning skew; extremes are a
textbook "overheated longs" signal. Pushback, directly from the same comment: the basic funding arb
"did work consistently for a while" but "everyone figured it out and the spreads have compressed
significantly on the major pairs" — BTC/ETH funding arb is "still viable but margins are thin enough
now that your execution costs matter a lot." The OP (StationImmediate530) separately reports the
*opposite* empirical pattern on Deribit (persistently positive, not mean-reverting funding) — the
relationship is exchange/instrument-dependent, not universal.
**Data for crypto test:** Historical funding rate + spot/perp OHLCV — Binance
(`/fapi/v1/fundingRate`) and Bybit both expose this free/keyless.
**Testability: 4/5** (basic carry trade fully testable; the mean-reversion-signal variant needs the
threshold reconstructed since it wasn't given).
**Plausibility: 3/5** (real but crowded/margin-compressed on majors; directional variant plausible but
unconfirmed exact rule, and contradicted on at least one exchange by the OP's own data).

## 8. Staking + short-perp delta-neutral yield arbitrage
**Source:** https://www.reddit.com/r/algotrading/comments/sk3z5p/example_lowrisk_arbitrage_strategy_with_a/ (2022-02-04)
**Rule:** Put ~40% of capital into a stakeable coin (locked, earning staking APY — quoted ~62.84% APY
example at the time), put remaining ~60% as margin backing a perpetual short covering the staked
notional. Nets staking yield + funding carry (positive when funding is negative) while remaining
delta-neutral. Theoretical example: 22.5% annualized before fees (funding was −6.57% annualized on the
example coin then, i.e. shorts got paid).
**Why it might work / pushback:** Genuine delta-neutral yield-farming category. Pushback: derOwl
**actually ran this live for 2 months** and reports realized yield of only ~12% annualized (well under
the 22.5% theoretical figure), requiring constant monitoring as funding shifts; multiple commenters
flag uncompensated protocol/smart-contract risk (cites the real Wormhole bridge hack) and counterparty
risk; rook785 warns of liquidation risk on the short leg during sharp up-moves ("picking up pennies in
front of a steamroller"); works best in bear/flat markets with negative funding, breaks down when
funding flips positive in a bull run. Some exchanges (KuCoin) already sell this as a packaged "funding
fee arbitrage bot."
**Data for crypto test:** Staking APY history (protocol/project-specific, less standardized than
OHLCV), perp funding history (free/keyless, Binance/Bybit), spot/perp price for hedge sizing.
**Testability: 3/5** (mechanics clear; staking-yield time series is the messy part).
**Plausibility: 3/5** (real category, but live-tested realized return undershot the theoretical claim
by nearly half).

## 9. Short-term futures basis (near-contract spread) reversal
**Source:** https://www.reddit.com/r/algotrading/comments/1ma12j1/we_tested_a_new_paper_that_finds_predictable/ (2025-07-26), citing academic paper "Short-Term Basis Reversal" (Rossi, Zhang & Zhu, 2025)
**Rule:** Compute the spread between the near two futures contracts on a curve; when this spread is
unusually large (either direction) relative to its own recent distribution, take a long-short position
betting on near-term reversion toward normal. Author's write-up tested this across "dozens of futures"
plus equities, found a monotonic return pattern with strong t-stats, and explicitly said crypto futures
testing was planned but **not yet done** at time of posting.
**Why it might work / pushback:** Futures-basis dislocations reflecting temporary positioning/roll
imbalance is a long-established idea in commodities; backed by a citable 2025 academic paper.
Pushback: golden_bear_2016 flags "quantreturns" (the blog publishing the write-up) as "a well known
scam site" — the specific numbers reported should be discounted even though the underlying cited paper
is independently checkable; other commenters compare the logic to LTCM's convergence trading ("spreads
always revert until they don't" — tail-risk-in-regime-breaks critique).
**Data for crypto test:** Perp-vs-quarterly-future basis, or front/next-quarter futures basis, on
Binance/Bybit/OKX — free/keyless historical data via REST.
**Testability: 4/5** (mechanic precisely defined; exact threshold needs pulling from the source paper).
**Plausibility: 3/5** (sound academic basis; source blog's own credibility is disputed in-thread, and
no crypto-specific validation existed at post time).

## 10. Liquidation-heatmap "liquidity hunter" trend-continuation
**Source:** https://www.reddit.com/r/algotrading/comments/1witlif/am_i_still_overfitting_or_is_this_a_genuine_edge/ (2026-09-17)
**Rule (partially disclosed):** Uses live liquidation heat-map data to identify zones of clustered
leveraged-position liquidity above/below current price. Waits for price + momentum to confirm the
market is moving toward one of these zones, then enters **in the direction of the hunt**
(trend-continuation, not fade). Traded live on SOL. Self-reported: 169 resolved trades over ~1 year,
76.92% win rate, profit factor 2.24, max drawdown 10.4%, profitable across R:R configs from 1:1 to 1:5.
**Why it might work / pushback:** Liquidation cascades are a real, mechanical, non-random source of
forced order flow unique to leveraged crypto perp markets — a legitimate crypto-native inefficiency
distinct from generic TA. This is the OP's own request for scrutiny after admitting to previously
overfitting ~100 other signal variants by filtering to historical winners. Community pushback: one
year / one instrument (SOL) may still be a single regime even though price ranged $80→$230→$60 (young_picassoo,
LegendOfTheNoob); 169 trades is a modest sample; biggest named risk (Responsible_Song9196) is the
liquidation/heatmap data source changing or exchange behavior evolving, silently breaking the edge.
Consensus recommendation: live shadow-testing at reduced size with hard kill-switches — which the OP
says is already in place.
**Data for crypto test:** Real-time liquidation stream (Binance `forceOrder` websocket is free/keyless
going forward, but has essentially no free deep history) or Coinglass (free tier, requires API key —
not fully keyless) plus OHLCV for momentum confirmation.
**Testability: 2/5** (exact entry trigger/zone construction withheld as proprietary; historical
liquidation data is hard to source at all beyond a short lookback).
**Plausibility: 4/5** (liquidation cascades are a real, mechanically-grounded, crypto-specific edge
category, even though this specific implementation can't be exactly replicated from the post).

## 11. Leverage-sizing + validation methodology for a daily BTC directional signal
**Source:** https://www.reddit.com/r/algotrading/comments/1ss5btv/4_years_of_a_15xleveraged_daily_btc_signal_sharpe/ (2026-04-22)
**Note:** The underlying signal is undisclosed ("proprietary... not a single textbook indicator") — but
the **process** is concrete and reusable around any signal: (a) size leverage off the 99th-percentile of
the rolling 90-day max-drawdown distribution at 1x, not off Sharpe/return maximization; (b) validate
parameter robustness via ±20% perturbation of every input, reject anything that breaks; (c) use real
historical perp funding payments (not theoretical cost-of-carry) when backtesting — author says an
earlier version "looked amazing until I subtracted real 8h funding"; (d) short-train/long-test
walk-forward (6-month train / 1-month test, rolling) instead of long-memory 12/3 splits, on the premise
crypto regimes shift every 3-6 months; (e) signal-level ablation — replace each input with noise, drop
any whose removal changes Sharpe by <10%.
**Why it might work / pushback:** This is a risk-management/validation framework, not an alpha signal.
Its value is candidly demonstrated: author reports actual live underperformance (6 weeks) vs backtest,
attributed concretely to funding cost running ~2pp worse live than modeled and maker-fill slippage
~1pp worse. Pushback (Henry_old, PapersWithBacktest): 15x leverage on *any* signal is one API hiccup
or exchange outage from ruin; leverage-sizing off historical drawdown distributions still can't capture
unprecedented tail events. OP concedes this is the "biggest unknown" and has not lived through a
2022-analog drawdown live.
**Data for crypto test:** BTC perp OHLCV + historical funding rate — free/keyless (Bybit/Binance).
**Testability: 2/5** for the alpha itself (signal withheld); the scaffolding around it is directly
reusable. **Plausibility: 4/5** for the methodology (funding-cost realism, ablation, short-window
walk-forward are all genuinely sound and crypto-appropriate practices); the leveraged-return claim
itself is unverifiable pending a longer live track record.

## 12. Daily-bar IBS + range-contraction mean reversion (equities-tested, crypto-portable rule)
**Source:** https://www.reddit.com/r/algotrading/comments/1rjvxjy/found_a_simple_mean_reversion_setup_with_70_win/ (2026-03-03)
**Rule:** Daily bars (tested on SPY/QQQ/AAPL/ABNB, **not** crypto in the original post). Entry:
close < (10-day high − 2.5 × (25-day avg-high − 25-day avg-low)) AND IBS < 0.3, where
IBS = (close−low)/(high−low). Exit: close > yesterday's high. SPY 2006-2026 backtest: CAGR 7.75%, win
rate 75.0% (180W/60L), profit factor 2.02, max DD 15.26%, time-in-market 21%. Similar pattern on QQQ
(70.7% WR) and AAPL (70.3% WR).
**Why it might work / pushback:** Combines a volatility-normalized "deep pullback" filter with an
intraday-weakness filter (IBS) — both well-studied mean-reversion primitives (IBS-style setups are a
documented Larry-Connors-lineage edge). Only trades ~20% of the time (selective). Pushback: Bellman_
recommends walk-forward split around regime changes (2020 crash, 2022-23 rate-hike cycle) specifically
because mean-reversion strategies are known to break in trending/shock regimes; ar_tyom2000 pushes back
that mean-reversion "looks good backtesting" but live "signals are very delayed, and you cannot get the
stocks with the signaled prices" — an execution-latency critique.
**Data for crypto test:** Daily BTC/ETH/alt OHLC — free/keyless (Binance daily klines). Note: this is
an equities rule, not yet validated on crypto — the 2.5× multiplier and 0.3 IBS threshold would very
likely need re-fitting given crypto's higher volatility and 24/7 trading, not a direct transplant.
**Testability: 5/5** (fully mechanical, trivial to code and test on crypto data).
**Plausibility: 3/5** (statistically well-grounded pattern class generally; unverified on crypto
specifically, and the community explicitly flags regime-fragility).

## 13. Regime-classified overnight/session mean reversion (adaptable to crypto session structure)
**Source:** https://www.reddit.com/r/algotrading/comments/1ob5xao/built_a_regimebased_overnight_mean_reversion/ (2025-10-20)
**Rule (equities/leveraged-ETF context; exact thresholds not disclosed):** Classify each trading day
into one of 5 regimes (strong bull/weak bull/bear/sideways/unpredictable) using momentum (moving
averages) and volatility (VIX-style) indicators at a fixed daily checkpoint; maintain a 10-year
backtested table of statistically-significant Bayesian probabilities of overnight reversal per
(stock, regime, intraday-move-magnitude) bucket; when a high-volatility instrument shows a
significant reversal tendency, buy near session close, sell at next session open. Live 3-month
results (self-reported): 24% return, 64.7% win rate over 85 trades, Sharpe 3.51, correlation to
S&P500 of 0.172.
**Why it might work / pushback:** Overreact-then-partially-correct around liquidity-thin close/open
windows is a documented microstructure pattern; regime-conditioning avoids applying one static edge
across incompatible market states. Pushback: Fun_Locksmith7647 immediately asks for out-of-sample
backtest stats and explicitly worries "hope you dont select stocks by seeing whole historical data"
(look-ahead/selection-bias concern), which the excerpt doesn't resolve; thread devolves into a broader
(unresolved) debate about whether any historical-data-driven stock selection can ever be unbiased.
**Data for crypto test:** No natural "close/open" in a 24/7 market — would need to substitute session
boundaries (e.g. funding-settlement timestamps 00:00/08:00/16:00 UTC, or Asia/EU/US session handoffs)
and a crypto-specific regime classifier (realized-vol regime, funding-rate regime) in place of VIX.
Needs BTC/alt OHLCV + a realized-vol proxy — computable directly from OHLCV, free/keyless.
**Testability: 3/5** (concept clear; regime classifier and reversal-probability table not disclosed,
so exact replication requires rebuilding the taxonomy from scratch).
**Plausibility: 3/5** (the overnight-reversal effect is real in equities; whether an analogous
"session" effect exists in a 24/7 crypto market is an open, testable, unproven question).

## 14. Order-book imbalance (OBI) / order-flow imbalance (OFI) microstructure regime strategy
**Source:** https://www.reddit.com/r/algotrading/comments/1pgsphr/algo_only_based_on_orderbook_imbalance_could_it/ (2025-12-07)
**Rule (concept concrete, exact thresholds proprietary):** No price/candle inputs. Classify a live
"orderbook regime" (buy/sell/neutral) purely from OBI (resting bid vs ask volume near touch). Use OFI
(net aggressive buy vs sell flow) to filter noise in OBI and confirm/extend the regime. All entry
distances, exit targets and safety limits derived directly from live depth (no fixed constants).
Maker-only (limit orders for both entry and exit, never taker). Currently long-only. Explicitly
grounded in cited literature: Cont/Kukanov/Stoikov "The price impact of order book events"; Silantyev
"Order-flow-analysis-of-cryptocurrency-markets"; Stoikov "The micro-price."
**Why it might work / pushback:** OBI is one of the most empirically validated short-horizon
price-direction predictors in market-microstructure research; maker-only execution avoids the spread
cost that kills most retail microstructure strategies. Pushback: one commenter flags directly "no
orderbook imbalance is easily manipulated" (spoofing — large resting orders can be pulled before
execution, biasing OBI without real intent to trade); blitzkriegjz agrees the academic grounding is
sound but names the core failure mode precisely: "the order book becomes least reliable precisely when
imbalances appear strongest" — adverse selection and liquidity withdrawal cluster exactly when the
signal looks best.
**Data for crypto test:** Full L2/L3 order-book depth + trade tape at high frequency. Real-time depth
is free/keyless via Binance/Bybit websocket streams, but **historical L2 depth is generally not free**
— needs self-collection going forward or a paid vendor (e.g. Tardis.dev). OHLCV alone is insufficient.
**Testability: 2/5** (conceptually clear but historical L2 data isn't free/keyless).
**Plausibility: 4/5** (well-grounded in published microstructure research, and the community's
adverse-selection caveat is realistic/specific, not generic skepticism).

## 15. Liquidity-zone + momentum reversal (FX-validated, author claims transferable)
**Source:** https://www.reddit.com/r/algotrading/comments/1gmzz3a/69_nice_win_rate_with_liquidity_zones_algo/ (2024-11-09)
**Rule (partially disclosed):** Using ~8-10 tunable parameters (momentum-indicator thresholds,
minimum pip-move-magnitude requirements), identify "liquidity zones" — price regions where a fast,
large move originated — on the premise that abrupt large moves reveal an underlying order-flow
imbalance. Store zones until invalidated. Entry requires price to revisit a stored zone AND a momentum
indicator showing a reversal-like reading (author found a momentum-indicator proxy worked better than
waiting for actual price reversal). Fixed SL/TP sized off zone length; time-boxed hold blocking new
signals. Backtested EUR/USD, 4.5 years of 1-min data: ~4.3%/month, 69% win rate; author reports it's
"tradable but pretty mid" on other USD pairs without re-tuning.
**Why it might work / pushback:** Conceptually the same logic as #10 (liquidation hunting) applied to
FX — abrupt high-magnitude moves marking a real supply/demand imbalance that price tends to revisit —
which has informal retail-TA precedent ("fair value gaps"/liquidity zones) and some order-flow-research
grounding. Pushback: TX_RU harshly calls it "an essay of rules that are barely followable" (too many
hand-tuned params to trust); author concedes an earlier ChatGPT-optimized parameter set failed
out-of-sample — direct evidence of a prior overfitting episode even if the current version claims to
be corrected; m264 and Free_Butterscotch_86 both push for a real walk-forward test ("pretend today is
Aug 1, refit only on prior data, run forward 3 months"), since the author's described validation
(15min×40 days initial fit → "refined" on 4.5y of 1-min data) is not a genuine train/test split; 4.5
years is called "nothing" for validating an intraday strategy.
**Data for crypto test:** 1-minute crypto OHLCV — free/keyless (Binance klines); doesn't need full L2
depth since the method is price-derived.
**Testability: 3/5** (logic re-implementable at a conceptual level; exact zone-construction/
invalidation rules withheld as "sauce").
**Plausibility: 2/5** (community consensus leans toward overfitting given parameter count and an
admitted prior overfit episode).

## 16. MACD trend-following, bear/chop-regime conditional
**Source:** https://www.reddit.com/r/algotrading/comments/buipe2/macd_based_crypto_trading_outperforms_the_market/ (2019-05-29)
**Rule:** Standard MACD(12,26,9) crossover trend-following on crypto, evaluated as outperforming in
bear/sideways regimes vs underperforming buy-and-hold in strong bull regimes. A commenter (whynotsurf)
offers a concrete variant: 5 EMA crossing above 13 EMA = long, crossing below = short/exit, optionally
confirmed with ADX crosses.
**Why it might work / pushback:** Trend-followers are expected to underperform B&H in one-way bull
markets (chopped/exit-early) but outperform on a risk-adjusted/drawdown-limited basis in choppy or
declining markets — a standard, well-understood trend-follower behavior pattern rather than a novel
edge. Pushback: insearchofmoon confirms the strategy "did not catch the huge 2018 upswing" (i.e. the
favorable test window was cherry-picked-by-circumstance); tending calls the specific 12/26 MACD
parameterization overfit-smelling, though insearchofmoon/deeteegee counter that 12/26/9 are the
industry-standard defaults (not tuned), which weakens that specific overfitting concern; Pytesting
states flatly "this strategy would not outperform if the last bull run didn't happen" — the
outperformance claim is regime-conditional, not general.
**Data for crypto test:** Daily/hourly BTC or alt close prices (MACD needs close only) — free/keyless.
**Testability: 5/5** (fully standard and mechanical).
**Plausibility: 3/5** (legitimate risk-management pattern, not a hidden edge; must be tested across
full bull/bear/chop cycles, not cherry-picked bear windows).

## 17. Cross-sectional crypto momentum (rebalance into prior-period winners)
**Source:** https://www.reddit.com/r/algotrading/comments/7japbm/relative_strength_momentum_with_cryptos/ (2017-12-12)
**Rule:** Rank a universe of cryptocurrencies by trailing return over lookback window X; go long only
the top 1-2 ranked coins; rebalance daily (or weekly, per the cited papers). Two academic sources
surfaced in-thread: SSRN 3055498 (buying the previous week's best-return coin, holding 1 week, beats an
equal-weight benchmark of all coins) and SSRN 2949379 (time-series + cross-sectional crypto momentum,
though limited to only 18 months of data in that specific paper).
**Why it might work / pushback:** Cross-sectional momentum ("winners keep winning" over days-to-weeks)
is one of the most replicated factors across asset classes (equities, futures, FX, commodities); crypto
alts historically show pronounced momentum/beta-chasing in trending markets. Pushback: no direct
debunking in this (short, old) thread, but the requester himself flags the second cited paper as thin
(18 months of data only); the thread also flags fee drag as the first-order practical risk for daily
rebalancing across only 1-2 positions ("fees are killer... but many exchanges charge 0 fees" for
maker/limit orders) — turnover cost, not the signal, is the likely main risk to a realized edge.
**Data for crypto test:** Daily OHLCV across a broad crypto universe (need 50-100+ symbols to rank
cross-sectionally) — free/keyless (Binance/CoinGecko); must explicitly handle survivorship bias from
delisted alts, since a live exchange's symbol list won't include them.
**Testability: 5/5** (fully mechanical: rank, pick top-N, rebalance on schedule).
**Plausibility: 4/5** (momentum is one of the best-replicated cross-asset factors in the academic
literature; main risk is turnover cost and survivorship bias in the coin universe, not the underlying
signal).

## 18. Bitcoin Difficulty Ribbon (cost-of-production valuation ribbon) — concept transfer
**Source:** https://www.reddit.com/r/algotrading/comments/m72zpo/introducing_the_cattle_difficulty_ribbon_my_first/ (2021-03-17)
**Note:** This specific post applies the idea to cattle/livestock, not BTC directly — it is explicitly
modeled by the author on Willy Woo's real **Bitcoin Difficulty Ribbon**, which is a genuine, actively
used on-chain crypto valuation indicator, so the general method is included here since it maps
directly back onto BTC.
**Rule (general form, matching how the real BTC indicator works):** Compute several moving averages of
Bitcoin network mining-difficulty growth (the real indicator commonly uses EMAs at roughly
9/14/25/40/60/90/128-day windows). When the "ribbon" compresses or inverts (short-period MA falls
toward/below longer-period MAs), it signals miner capitulation — high-cost miners shutting down because
production costs exceed revenue — historically coinciding with BTC cyclical price bottoms.
**Why it might work / pushback:** Mining difficulty is a genuine on-chain, keyless-source fundamental
input (not derived from price) reflecting the real capital-cost/exit decisions of the most
price-insensitive sellers (miners), giving it a plausible causal mechanism rather than being pure
pattern-matching. Pushback (from the cattle-market version of this exact thread, directly
transferable): RedHawk pushes the author to actually test causality rather than eyeballing two overlaid
line charts — "plotting two series isn't going to tell you much... dive into basic time series analysis
(see Granger causality)"; a second commenter flags that simple moving averages are lagging indicators,
suggesting an EWMA might respond faster. Applied back to BTC specifically: the difficulty ribbon is a
low-frequency, cycle-bottom-timing overlay, not a high-frequency trading signal — testability is
inherently limited by the small number of full BTC halving cycles observed (~4 to date).
**Data for crypto test:** Bitcoin network mining-difficulty history — free/keyless (blockchain.com
charts API, mempool.space API) + BTC daily price.
**Testability: 3/5** (mechanically simple to compute; only ~4 full cycle observations exist, so
statistical confidence from any backtest is inherently weak — a small-N problem, not an implementation
problem).
**Plausibility: 3/5** (grounded in a real cost-structure mechanism and actively used by on-chain
analysts, but the small historical sample means it's more of a macro-timing overlay than a
standalone, frequently-tradeable signal).

---

## Notes on what was screened out
- Several posts were pure Q&A with no concrete rule given (e.g. "Spot-Perpetual Arbitrage",
  "Statistical Arbitrage in crypto" [8h0p2q], "Using perpetuals or futures to hedge exposure",
  "Built a low-latency C++ funding-rate capturing system" — architecture/execution post, no signal).
  These were read but excluded from the ranked list for lacking a testable rule, though their comment
  threads contributed context folded into #7-9 above.
- "Never underestimate the power of a simple bollinger band strategy" (t1n265, crypto 1-min BB
  cross) was read and excluded: the top comment thread **debunks it directly** — jwmoz calls it "a
  garbage backtest, does not work when tested correctly," accusing the author's variable-threshold
  exit logic of masking negative-skew tail risk ("trading a facade... you will be hit by negative
  skew when live"). Included here only as a named negative data point, not a ranked idea.
- "Do support and resistance zones really weaken with every touch?" (1vtkunw) and the triangular-arb
  paper (1hm5ucj) and the Polymarket cross-venue arb (1u17e2v) were read in full but are not
  crypto-perp/spot trading rules per se (a market-structure finding, an academic obstacles-paper, and
  a prediction-market execution post respectively) — worth knowing about but didn't fit the "concrete
  tradeable rule" bar as cleanly as the 18 above.
