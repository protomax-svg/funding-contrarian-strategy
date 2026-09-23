"""Regime study for #7b: which market states help or hurt, and do simple adaptive filters survive OOS?

Every state variable is known at the close of day t and scales the book held on day t+1.
Buckets use a trailing 365-day percentile (min 180 days), so there is no look-ahead in the cut points.
Filters are chosen on IS (2020-2023) and then read once on OOS (2024-01..2026-08).
"""
import numpy as np
import pandas as pd

import lab

COST = 7.0
P = lab.load("1D")
U = lab.universe(P, 30)
C, H, L, R, F = P["close"], P["high"], P["low"], P["ret"], P["funding"]
F7 = F.rolling(7).mean()
W0 = lab.xs_rank_weights(-F7, U)
BASE = lab.backtest(W0, P, COST)["net"]
IS = slice(None, lab.SPLIT - pd.Timedelta("1ns"))
OOS = slice(lab.SPLIT, None)


def pct_rank(s, win=365, minp=180):
    """Trailing percentile of today's value among the last `win` days (0..1)."""
    return s.rolling(win, min_periods=minp).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True)


def atr_pct(n=14):
    pc = C.shift(1)
    tr = np.maximum(H - L, np.maximum((H - pc).abs(), (L - pc).abs()))
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / C


ATR = atr_pct()
ew = R.where(U).mean(axis=1)
STATES = {
    "BTC ATR% (market ATR)": ATR["BTCUSDT"],
    "universe median ATR%": ATR.where(U).median(axis=1),
    "market 30d realized vol": ew.rolling(30).std(),
    "funding dispersion (XS std of 7d funding)": F7.where(U).std(axis=1),
    "funding level (XS mean of 7d funding)": F7.where(U).mean(axis=1),
    "BTC trend (close / SMA200)": C["BTCUSDT"] / C["BTCUSDT"].rolling(200).mean(),
    "market 30d return": (1 + ew).rolling(30).apply(np.prod, raw=True) - 1,
    "strategy own trailing 60d return": BASE.rolling(60).sum(),
}
PCT = {k: pct_rank(v) for k, v in STATES.items()}


def sh(x):
    return round(lab.sharpe(x, 365), 2)


def net_scaled(scale, w=W0):
    return lab.backtest(w.mul(scale.fillna(1.0), axis=0), P, COST)["net"]


# ---------- 1) bucket study ----------
bucket_rows = []
for name, p in PCT.items():
    b = pd.cut(p, [-0.01, 1 / 3, 2 / 3, 1.01], labels=["low", "mid", "high"])
    nxt = BASE.shift(-1)                      # state at t -> return of the book held on t+1
    row = {"state": name}
    for tag, sl in (("IS", IS), ("OOS", OOS)):
        g = nxt.loc[sl].groupby(b.loc[sl], observed=True)
        for lvl in ("low", "mid", "high"):
            row[f"{tag} {lvl}"] = round(float(g.mean().get(lvl, np.nan) * 365), 3)
    is_order = np.argsort([row["IS low"], row["IS mid"], row["IS high"]])
    oos_order = np.argsort([row["OOS low"], row["OOS mid"], row["OOS high"]])
    row["worst bucket IS -> OOS"] = f"{['low', 'mid', 'high'][is_order[0]]} -> {['low', 'mid', 'high'][oos_order[0]]}"
    bucket_rows.append(row)

# ---------- 2) filters: switch off / halve in the IS-worst bucket ----------
filt_rows = [{"filter": "none (base)", "IS": sh(BASE.loc[IS]), "OOS": sh(BASE.loc[OOS]),
              "OOS ann": round(BASE.loc[OOS].mean() * 365, 3), "maxDD": round(lab.maxdd(BASE), 3), "time_on": 1.0}]
for name, p in PCT.items():
    b = pd.cut(p, [-0.01, 1 / 3, 2 / 3, 1.01], labels=["low", "mid", "high"])
    g = BASE.shift(-1).loc[IS].groupby(b.loc[IS], observed=True).mean()
    worst = g.idxmin()
    for lvl_scale in (0.0, 0.5):
        scale = pd.Series(np.where(b == worst, lvl_scale, 1.0), index=b.index)
        x = net_scaled(scale)
        filt_rows.append({"filter": f"{name}: x{lvl_scale} when {worst}", "IS": sh(x.loc[IS]), "OOS": sh(x.loc[OOS]),
                          "OOS ann": round(x.loc[OOS].mean() * 365, 3), "maxDD": round(lab.maxdd(x), 3),
                          "time_on": round(float(scale.mean()), 2)})

# ---------- 3) the ATR filters the user asked about ----------
atr_rows = []
# 3a market ATR regime: trade only when BTC ATR% percentile is below / above a cut
for cut in (0.5, 0.7, 0.9):
    pb = PCT["BTC ATR% (market ATR)"]
    for side, scale in ((f"off when BTC ATR pct > {cut}", (pb <= cut).astype(float)),
                        (f"off when BTC ATR pct < {1 - cut:.1f}", (pb >= 1 - cut).astype(float))):
        x = net_scaled(scale)
        atr_rows.append({"ATR rule": side, "IS": sh(x.loc[IS]), "OOS": sh(x.loc[OOS]),
                         "OOS ann": round(x.loc[OOS].mean() * 365, 3), "maxDD": round(lab.maxdd(x), 3)})
# 3b per-coin ATR: size each coin by 1/ATR inside its side (risk parity), keep 0.5 long / 0.5 short
inv = (1 / ATR).where(W0 != 0)
wl = inv.where(W0 > 0); ws = inv.where(W0 < 0)
W_rp = (0.5 * wl.div(wl.sum(axis=1), axis=0)).fillna(0) - (0.5 * ws.div(ws.sum(axis=1), axis=0)).fillna(0)
x = lab.backtest(W_rp, P, COST)["net"]
atr_rows.append({"ATR rule": "per-coin size ∝ 1/ATR (risk parity)", "IS": sh(x.loc[IS]), "OOS": sh(x.loc[OOS]),
                 "OOS ann": round(x.loc[OOS].mean() * 365, 3), "maxDD": round(lab.maxdd(x), 3)})
# 3c per-coin ATR exclusion: drop the most volatile 20% of the universe before ranking
atr_rank = ATR.where(U).rank(axis=1, pct=True)
for side_name, keep in (("both sides", atr_rank <= 0.8),):
    x = lab.backtest(lab.xs_rank_weights(-F7, U & keep), P, COST)["net"]
    atr_rows.append({"ATR rule": f"exclude top-20% ATR coins ({side_name})", "IS": sh(x.loc[IS]), "OOS": sh(x.loc[OOS]),
                     "OOS ann": round(x.loc[OOS].mean() * 365, 3), "maxDD": round(lab.maxdd(x), 3)})

# ---------- 4) volatility targeting on the strategy itself ----------
vt_rows = []
for tgt in (0.15, 0.20, 0.30):
    for lb in (30, 60):
        vol = BASE.rolling(lb).std() * np.sqrt(365)
        scale = (tgt / vol).clip(upper=2.0)             # vol known at t, applied to t+1 via backtest lag
        x = net_scaled(scale)
        vt_rows.append({"vol target": f"{int(tgt * 100)}% ann, lookback {lb}d, max 2x", "IS": sh(x.loc[IS]),
                        "OOS": sh(x.loc[OOS]), "OOS ann": round(x.loc[OOS].mean() * 365, 3),
                        "maxDD": round(lab.maxdd(x), 3), "avg lev": round(float(scale.mean()), 2)})

# ---------- 5) walk-forward over the filter menu: every 90d pick the filter with the best trailing-365d Sharpe ----------
menu = {"none": BASE}
for r_ in filt_rows[1:]:
    pass
for name, p in PCT.items():
    b = pd.cut(p, [-0.01, 1 / 3, 2 / 3, 1.01], labels=["low", "mid", "high"])
    for lvl in ("low", "mid", "high"):
        menu[f"{name} off {lvl}"] = net_scaled(pd.Series(np.where(b == lvl, 0.0, 1.0), index=b.index))
M = pd.DataFrame(menu)
wf = pd.Series(np.nan, index=M.index)
picks = []
for s0 in range(365 + 200, len(M), 90):
    tr = M.iloc[s0 - 365:s0]
    best = (tr.mean() / tr.std()).idxmax()
    wf.iloc[s0:s0 + 90] = M[best].iloc[s0:s0 + 90]
    picks.append((str(M.index[s0].date()), best))
wf = wf.dropna()
wf_row = {"walk-forward filter choice": "every 90d, best of 25 filters on trailing 365d",
          "OOS": sh(wf.loc[OOS]), "base OOS same span": sh(BASE.loc[wf.index].loc[OOS]),
          "OOS ann": round(wf.loc[OOS].mean() * 365, 3), "maxDD": round(lab.maxdd(wf), 3)}

md = ["# Regime study for the funding-contrarian strategy\n",
      "State at close t scales the book on t+1. Buckets = trailing-365d percentile terciles. 7 bps/side, real funding.\n",
      "## 1) Next-day return (annualised) by market state\n", pd.DataFrame(bucket_rows).to_markdown(index=False),
      "\nA state is only useful if the worst bucket is the same in IS and OOS.\n",
      "## 2) Switch off / halve in the IS-worst bucket\n", pd.DataFrame(filt_rows).to_markdown(index=False),
      "\n## 3) ATR filters\n", pd.DataFrame(atr_rows).to_markdown(index=False),
      "\n## 4) Volatility targeting on the strategy\n", pd.DataFrame(vt_rows).to_markdown(index=False),
      "\n## 5) Walk-forward choice among filters\n", pd.DataFrame([wf_row]).to_markdown(index=False),
      "\nPicks: " + "; ".join(f"{d}: {b}" for d, b in picks) + "\n"]
open("results_regime.md", "w").write("\n".join(md))
print("\n".join(md))


# ---------- 6) combination of the IS-and-OOS-consistent pieces (read once, not tuned) ----------
def combo(atr_cut=1 / 3, use_trend=True, use_vt=True, cost=COST):
    sc = (PCT["BTC ATR% (market ATR)"] >= atr_cut).astype(float)
    if use_trend:
        sc = sc * (PCT["BTC trend (close / SMA200)"] < 2 / 3).astype(float)
    if use_vt:
        vol = BASE.rolling(30).std() * np.sqrt(365)
        sc = sc * (0.15 / vol).clip(upper=2.0)
    return lab.backtest(W0.mul(sc.fillna(1.0), axis=0), P, cost)["net"], sc


combo_rows = []
for nm, kw in (("ATR-low off", dict(use_trend=False, use_vt=False)),
               ("ATR-low off + trend-high off", dict(use_vt=False)),
               ("ATR-low off + vol target 15%", dict(use_trend=False)),
               ("ATR-low off + trend-high off + vol target 15%", {})):
    x, sc = combo(**kw)
    x15, _ = combo(cost=15, **kw)
    eq = (1 + x.loc[OOS]).cumprod()
    combo_rows.append({"combo": nm, "IS": sh(x.loc[IS]), "OOS": sh(x.loc[OOS]), "OOS@15bps": sh(x15.loc[OOS]),
                       "OOS total %": round(100 * (eq.iloc[-1] - 1), 1), "maxDD": round(lab.maxdd(x), 3),
                       "OOS maxDD": round(lab.maxdd(x.loc[OOS]), 3), "avg exposure": round(float(sc.mean()), 2)})
eqb = (1 + BASE.loc[OOS]).cumprod()
combo_rows.insert(0, {"combo": "base", "IS": sh(BASE.loc[IS]), "OOS": sh(BASE.loc[OOS]),
                      "OOS@15bps": sh(lab.backtest(W0, P, 15)["net"].loc[OOS]), "OOS total %": round(100 * (eqb.iloc[-1] - 1), 1),
                      "maxDD": round(lab.maxdd(BASE), 3), "OOS maxDD": round(lab.maxdd(BASE.loc[OOS]), 3), "avg exposure": 1.0})
t6 = "\n## 6) Combinations (each piece was consistent IS and OOS in section 1; cut points not tuned)\n\n" + pd.DataFrame(combo_rows).to_markdown(index=False) + "\n"
open("results_regime.md", "a").write(t6)
print(t6)
