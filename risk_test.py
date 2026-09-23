"""Does Max's BTC 1h Risk Index help the funding-contrarian strategy?

Index history comes from the Risk Index API (saved to risk_1h_A.json, not in git). A candle's value is used
only after that candle closed: the value on the 1h candle opening at hh:00 is known at hh+1:00.
Tests: (1) daily filter at the 00:05 UTC rebalance, (2) intraday exit when the index spikes, both with and without
the live ATR filter. Index values exist from 2022-07-12, so the sample here is 2022-07 -> 2026-08 only.
"""
import json

import numpy as np
import pandas as pd

import lab

COST = 7.0
SPLIT = lab.SPLIT                      # IS 2022-07..2023-12, OOS 2024-01..2026-08
d = json.load(open("risk_1h_A.json"))
rk = pd.DataFrame(d["candles"])
rk.index = pd.to_datetime(rk.open_time, unit="ms", utc=True)
rk = rk.iloc[:-1]                      # last candle was still open when downloaded
rk = rk[rk.regime.notna()]
START = rk.index[0].ceil("D")

# ---------------- daily strategy on the index period ----------------
P = lab.load("1D")
U = lab.universe(P, 30)
F7 = P["funding"].rolling(7).mean()
W0 = lab.xs_rank_weights(-F7, U)
ATR_P = lab.pct_rank(lab.atr_pct(P["high"]["BTCUSDT"], P["low"]["BTCUSDT"], P["close"]["BTCUSDT"]))
ATR_ON = (ATR_P >= 1 / 3).astype(float).where(ATR_P.notna(), 1.0)

# index state at the daily decision: the 23:00 candle closes at 00:00 = our close of day D
last = rk.resample("1D").last()
day = pd.DataFrame({"zone": last.regime_zone, "regime": last.regime,
                    "zone2_24h": rk.regime_zone.eq(2).resample("1D").max().astype(float),
                    "share_elev_24h": rk.regime_zone.ge(1).resample("1D").mean()}).reindex(W0.index)
IS = slice(START, SPLIT - pd.Timedelta("1ns"))
OOS = slice(SPLIT, None)


def sh(x):
    return round(lab.sharpe(x, 365), 2)


def stats(name, x):
    x = x.loc[START:]
    return {"variant": name, "Sharpe 22-26": sh(x), "IS 22-23": sh(x.loc[IS]), "OOS 24-26": sh(x.loc[OOS]),
            "OOS total %": round(100 * ((1 + x.loc[OOS]).prod() - 1), 1), "maxDD": round(lab.maxdd(x), 3)}


def run(scale):
    return lab.backtest(W0.mul(scale.fillna(1.0), axis=0), P, COST)["net"]


rows = []
base, atr = run(pd.Series(1.0, index=W0.index)), run(ATR_ON)
rows += [stats("base (no filter)", base), stats("ATR filter (live now)", atr)]
FILTERS = {
    "pause when zone at close = 2 (p90)": day.zone.eq(2),
    "pause when zone at close >= 1": day.zone.ge(1),
    "pause when any zone-2 hour in last 24h": day.zone2_24h.eq(1),
    "pause when zone at close = 0 (inverse)": day.zone.eq(0),
}
for nm, off in FILTERS.items():
    keep = (~off.fillna(False)).astype(float)
    rows.append(stats(nm, run(keep)))
    rows.append(stats(f"ATR + {nm}", run(ATR_ON * keep)))

# next-day return by zone (does the index sort good and bad days?)
nxt = base.shift(-1)
bucket = []
for tag, sl in (("IS 22-23", IS), ("OOS 24-26", OOS)):
    g = nxt.loc[sl].groupby(day.zone.loc[sl])
    bucket.append({"period": tag, **{f"zone {int(z)} ann": round(v * 365, 3) for z, v in g.mean().items()},
                   **{f"zone {int(z)} days": int(n) for z, n in g.size().items()}})

# how much does the index overlap with the ATR regime?
ov = pd.DataFrame({"regime": day.regime, "atr_pct": ATR_P}).loc[START:].dropna()
overlap = {"corr(regime at close, BTC ATR percentile)": round(ov.corr().iloc[0, 1], 3),
           "share of zone>=1 days that the ATR filter already trades": round(float(ATR_ON.loc[START:][day.zone.loc[START:] >= 1].mean()), 3)}

# ---------------- intraday: flatten on a spike, hourly P&L ----------------
P1 = lab.load("1h")
idx = P1["ret"].index
Wh = W0.copy()
Wh.index = Wh.index + pd.Timedelta("23h")            # daily book decided at 00:00 -> held from the next bar
Wh = Wh.reindex(idx).ffill().fillna(0.0)
atr_h = ATR_ON.copy(); atr_h.index = atr_h.index + pd.Timedelta("23h")
atr_h = atr_h.reindex(idx).ffill().fillna(1.0)
zone_h = rk.regime_zone.reindex(idx)                  # known at close of that hour -> applied from the next bar
intr = []


def hourly(name, scale):
    x = lab.backtest(Wh.mul(scale, axis=0), P1, COST)["net"].loc[START:]
    xd = x.resample("1D").sum()
    intr.append({"variant": name, "Sharpe 22-26": sh(xd), "IS 22-23": sh(xd.loc[IS]), "OOS 24-26": sh(xd.loc[OOS]),
                 "OOS total %": round(100 * ((1 + xd.loc[OOS]).prod() - 1), 1), "maxDD": round(lab.maxdd(xd), 3),
                 "time in market": round(float((scale.loc[START:] > 0).mean()), 2)})


def flat_on_spike(enter_below):
    """Flatten when an hour closes in zone 2; stay flat until the zone drops to <= enter_below."""
    z = zone_h.fillna(0).values
    s = np.ones(len(z))
    off = False
    for i, v in enumerate(z):
        if v >= 2:
            off = True
        elif off and v <= enter_below:
            off = False
        s[i] = 0.0 if off else 1.0
    return pd.Series(s, index=idx)


hourly("hourly base (daily book, hourly marks)", pd.Series(1.0, index=idx))
hourly("hourly + ATR filter", atr_h)
for eb in (1, 0):
    sp = flat_on_spike(eb)
    hourly(f"flat on zone-2 hour, back when zone <= {eb}", sp)
    hourly(f"ATR + flat on zone-2 hour, back when zone <= {eb}", atr_h * sp)

md = ["# Risk Index (BTC 1h) as a filter for the funding-contrarian strategy\n",
      f"Index values from {START.date()}; IS {START.date()}..2023-12, OOS 2024-01..2026-08. 7 bps/side, real funding.\n",
      "## Daily filter at the 00:05 UTC rebalance\n", pd.DataFrame(rows).to_markdown(index=False),
      "\n## Next-day strategy return by index zone at the close (annualised)\n", pd.DataFrame(bucket).to_markdown(index=False),
      "\n## Overlap with the ATR filter\n", pd.Series(overlap).to_frame("value").to_markdown(),
      "\n## Intraday exit on a spike (hourly P&L, daily Sharpe)\n", pd.DataFrame(intr).to_markdown(index=False), ""]
open("results_risk.md", "w").write("\n".join(md))
print("\n".join(md))


# ---------------- fixed threshold (the way the index is used by hand: risk > ~0.70) ----------------
reg_h = rk.regime.reindex(idx)
fx_daily, fx_intr = [], []
dist = {f"share of hours > {t}": round(float((rk.regime > t).mean()), 3) for t in (0.6, 0.65, 0.7, 0.75, 0.8)}
nxt = base.shift(-1)
for t in (0.65, 0.70, 0.75):
    off = day.regime > t
    keep = (~off.fillna(False)).astype(float)
    r1, r2 = stats(f"pause when index at close > {t}", run(keep)), stats(f"ATR + pause when index at close > {t}", run(ATR_ON * keep))
    for tag, sl in (("IS", IS), ("OOS", OOS)):
        r1[f"{tag} next-day ann when > {t}"] = round(float(nxt.loc[sl][off.loc[sl].fillna(False)].mean() * 365), 3)
        r1[f"{tag} days > {t}"] = int(off.loc[sl].sum())
    fx_daily += [r1, r2]
    # intraday: flat from the first hour that closes above t until an hour closes back below t - 0.05
    z = reg_h.values
    s = np.ones(len(z)); flag = False
    for i, v in enumerate(z):
        if np.isfinite(v) and v > t:
            flag = True
        elif flag and np.isfinite(v) and v < t - 0.05:
            flag = False
        s[i] = 0.0 if flag else 1.0
    sp = pd.Series(s, index=idx)
    before = len(intr)
    hourly(f"flat while index > {t} (back below {t - 0.05:.2f})", sp)
    hourly(f"ATR + flat while index > {t} (back below {t - 0.05:.2f})", atr_h * sp)
    fx_intr += intr[before:]
md2 = ["\n## Fixed threshold (index > 0.65 / 0.70 / 0.75)\n", pd.Series(dist).to_frame("value").to_markdown(),
       "\n### Daily filter\n", pd.DataFrame(fx_daily).to_markdown(index=False),
       "\n### Intraday: flat while above the threshold\n", pd.DataFrame(fx_intr).to_markdown(index=False), ""]
open("results_risk.md", "a").write("\n".join(md2))
print("\n".join(md2))
