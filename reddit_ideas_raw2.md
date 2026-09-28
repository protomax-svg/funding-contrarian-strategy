# Reddit crypto strategy harvest #2

Method: Atom RSS search across r/algotrading, r/quant, r/CryptoCurrencyTrading,
r/BitcoinMarkets, r/defi, r/binance, r/Bitcoin and reddit-wide search, on the query
terms in the brief (funding, OI, basis, unlock, listing, airdrop, liquidation
cascade, weekend, altseason, dominance, stablecoin, on-chain, exchange inflow,
taker buy, CVD, lead-lag, delisting, Binance listing effect), plus the 12
candidate threads already queued from a prior pass. ~30 fetches total.

**Result: most threads had no concrete, quotable rule** (vague "proprietary
signal", equities-only IBS/blow-off-score/52w-high setups already excluded by
brief, liquidity-heatmap ideas needing order-book data we don't have, or pure
"look at my equity curve" posts with no stated entry/exit logic). Binance
new-listing "buy at listing" threads are literally about sub-second sniping —
not testable on daily/1h OHLCV. r/CryptoCurrencyTrading is dead (2021-era
shill/presale spam only). Only two threads cleared the bar: concrete rule +
quoted numbers + not on the exclusion list + computable from
price/volume/funding alone. Ranked below; everything else that was close but
didn't qualify is listed at the bottom for transparency.

---

## 1. Buy-the-dip sized by % drawdown from ATH (tiered DCA) vs flat weekly DCA

- **Title**: "I backtested buying BTC at 30%, 40% and 50% drawdowns vs weekly DCA"
- **URL**: https://www.reddit.com/r/Bitcoin/comments/1w81qb9/i_backtested_buying_btc_at_30_40_and_50_drawdowns/
- **Date**: 2026-09-05
- **Exact rule as posted**:
  - "30% below ATH: buy $10"
  - "40% below ATH: buy $20"
  - "50% below ATH: buy $30"
  - "Max one buy every 7 days"
  - Weekly DCA amount for the comparison period is scaled so both approaches invest "roughly the same" total dollars.
- **Claimed result** (author's numbers, % = simple return on capital invested):
  - 5y: invested $3,430 → drawdown-buys +121.62% vs weekly DCA +49.00%
  - 3y: invested $1,130 → drawdown-buys +45.03% vs weekly DCA -2.22%
  - 1y: invested $570 → drawdown-buys -8.99% vs weekly DCA -21.35%
- **Best pushback (from the thread)**: the author's own caveat — "there are periods where you're just sitting on cash waiting for a 30% drop while BTC keeps going up," i.e. cash-drag / opportunity cost isn't charged in the comparison (idle capital before a trigger fires earns nothing, and if you never see a -30% drawdown in the window you never deploy it at all — the 1y result already shows this narrowing). No commenter directly challenged the backtest methodology; the discussion mostly turned into people sharing their own personal drawdown-tiered rules (e.g. fear/greed-index-scaled DCA).
- **Why it might work / testable here**: pure price-based, no signal beyond a rolling all-time-high and % drawdown — trivially computable from Binance daily close alone across all ~850 coins and any date range 2020-2026, including delisted coins for a cross-sectional variant. Economically it's a disciplined, mechanical version of "buy fear" that back-loads size into the largest drawdowns, which is plausible in a market (BTC/majors) that has historically mean-reverted upward over multi-year windows — the edge is really "trend + convexity of buy sizing," not a genuine anomaly, so it should be tested against the null of just holding a static leverage-matched long position (its outperformance in the post may just be because tiered buying happens to buy more BTC per dollar in a period that's net up a lot). Note: mechanically adjacent to the excluded "buy-the-dip near 52w-high" idea, but the rule here is different (tiered position sizing off trailing ATH drawdown, not a single entry signal off a 52w high) — flag this overlap before running it.

## 2. Day-of-week seasonality in close-to-close returns ("weekend dump" / "settlement pump")

- **Titles/URLs**:
  - "'Weekend Dumps' and 'Settlement Pumps'? Here's a look at the statistics of price changes by hour and day." — https://www.reddit.com/r/BitcoinMarkets/comments/3tlllq/weekend_dumps_and_settlement_pumps_heres_a_look/ (2015-11-20)
  - "Yes, there is a weekend dip." — https://www.reddit.com/r/BitcoinMarkets/comments/1ue36f/yes_there_is_a_weekend_dip/ (2014-01-04)
- **Exact rule as posted** (thread 1, Bitfinex daily closes, ~1 year of data from 2014-11-24 UTC): classify each day as "Up" (closed above open) or "Down"; a chi-square independence test on day-of-week vs Up/Down came back p<0.05 ("we can conclude there is a relationship between the day of the week and how likely the price is to close at a gain"). Quoted numbers: "the price closed at a gain 67.3% of the time on Wednesdays, and closed at a loss 66.7% of the time on Fridays (UTC)." Same test repeated hour-by-hour (UTC) was also chi-square-significant categorically. Thread 2 (2013 Mt.Gox daily data) reports the largest average gains Sunday→Monday, shrinking through the week, most negative Friday→Sunday, with Wed/Fri showing the widest confidence intervals (highest volatility), and notes volume was also highest Wed-Fri.
- **Claimed result**: statistically-significant categorical (up/down) day-of-week effect; continuous (magnitude) ANOVA was NOT significant in thread 1 (p>0.05) — the author is explicit that direction-of-close is skewed by weekday but the size of the move is not distinguishable by weekday.
- **Best pushback (from the thread)**: multiple commenters correctly note the continuous-data confidence intervals overlap heavily across days, meaning you can't reject the null that mean returns differ by day — one top comment: "There is no statistical difference at all between the days," and another walks through why overlapping 95% CIs don't license the up/down-rate conclusion either, i.e. the categorical test's practical trading significance is disputed even though the p-value is real. Also: the author's own hourly version admits the huge sample size (every hour, whole year) makes it easy to get statistically-significant-but-tiny effects ("the sample size... is too large to reject the null" — meaning they suspect the significant hourly result is noise dressed up by n).
- **Why it might work / testable here**: pure calendar effect on daily close-to-close returns — directly computable on Binance BTCUSDT-perp (and any other coin) daily OHLCV for 2020-2026, no other data needed. Economic story: weekly settlement/rebalancing flows (traditional-finance-linked flows, options/futures expiries, retail activity clustering on weekdays vs weekends when liquidity is thinner) could plausibly produce a mild day-of-week bias in a 24/7 market that otherwise has no "week" structure imposed on it exogenously. Caveat: this is adjacent to the excluded "hour-of-day" strategy — it's a different granularity (weekly, not intraday) and a different underlying claim (categorical direction-of-close vs continuous return), but flag the overlap; also note both source threads are pre-2020 spot data (Bitfinex/Mt.Gox), so the specific 67.3%/66.7% numbers are not expected to transfer as-is to 2020-2026 Binance perps — treat this purely as a rule to re-test, not a result to expect.

---

### Threads found but rejected (no concrete testable rule, or excluded, or not crypto)

- 4-years-15x-leveraged BTC signal, Sharpe 2.2 (r/algotrading, 1ss5btv) — proprietary signal, no disclosed rule.
- "Am I still overfitting?" 169-trade liquidity-hunter (r/algotrading, 1witlif) — needs live liquidation-heatmap/order-book data, excluded by data constraint and by the liquidation-heatmap exclusion.
- IBS mean-reversion setup, "Blowoff Score" ≥70 filter, "5% drop near 52w high" (r/algotrading, 1rjvxjy/1wlf3mk/1ty1rch/1tzicir) — concrete rules exist but all tested on SPY/QQQ/individual stocks, not crypto, and the 52w-high dip variant is explicitly pre-excluded.
- Z-score range breakout (1shv7s6), top-3-by-volume daily rotation (1puch9n), EWMA win-rate suppression filter (1tkrfiz) — described only qualitatively; no disclosed thresholds/parameters to quote.
- Binance "buy at announcement"/"buy within 0.1-0.3s of listing" bots (qa1tdg, mm2iwk, pd9klm, pf51pn, p4rmfc) — real phenomenon (announcement-driven pre-pump) but the tradeable edge is sub-second execution, not testable on daily/1h bars.
- r/CryptoCurrencyTrading, "BTC dominance" and "altcoin season index" searches — almost entirely presale spam or narrative/news posts ("dominance at X%") with no backtested rule attached.

Notes file: /tmp/claude-1000/-home-max/df256b6a-9885-4b48-b621-ac7719ab247a/scratchpad/harvest2.md
