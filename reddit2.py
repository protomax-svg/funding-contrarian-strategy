"""Two more Reddit ideas (harvested 2026-09-27).

#20 Tiered drawdown buying vs weekly DCA (r/Bitcoin 1w81qb9, 2026-09): buy $10 when BTC is -30% from its ATH,
    $20 at -40%, $30 at -50%, max one buy per 7 days. Claimed 5y +121.6% vs DCA +49.0%.
    Fair test: both plans get the SAME $10/week. DCA spends it at once; the tiered plan saves it as cash and
    spends only on a trigger (as much as it has, up to the tier amount). Scored on final wealth (BTC + unspent
    cash) per $ contributed, for every monthly start date, 1y/3y/5y windows. 10 bps spot fee.
#21 Day-of-week (r/BitcoinMarkets 3tlllq, 1ue36f): "67% up closes on Wednesday, 67% down on Friday (UTC)".
    Test: IS weekday ranking -> does it persist OOS? Trade: long BTC on the IS-best 3 weekdays, else flat.
"""
import numpy as np
import pandas as pd

import lab

C = pd.read_parquet(lab.D / "all" / "close.parquet")[["BTCUSDT", "ETHUSDT"]]
C = C[(C.index >= "2020-01-01") & (C.index <= "2026-08-31")]
if C.index.tz is None:
    C.index = C.index.tz_localize("UTC")
FEE = 10 / 1e4


def plans(c, weekly=10.0, tiers=((-0.5, 30), (-0.4, 20), (-0.3, 10))):
    """Run DCA and tiered on price series c. Returns (dca_wealth, tier_wealth, contributed) at the end."""
    ath = c.cummax()
    dd = c / ath - 1
    cash = btc_t = btc_d = paid = 0.0
    last_buy = None
    for i, (t, p) in enumerate(c.items()):
        if i % 7 == 0:                                          # weekly contribution
            paid += weekly; cash += weekly; btc_d += weekly * (1 - FEE) / p
        if last_buy is not None and (t - last_buy).days < 7:
            continue
        for lvl, amt in tiers:                                 # deepest tier first
            if dd[t] <= lvl:
                spend = min(amt, cash)
                if spend > 0:
                    btc_t += spend * (1 - FEE) / p; cash -= spend; last_buy = t
                break
    p = c.iloc[-1]
    return btc_d * p, btc_t * p + cash, paid


def windows(sym):
    c = C[sym].dropna()
    rows = []
    for yrs in (1, 3, 5):
        for start in pd.date_range(c.index[0], c.index[-1] - pd.DateOffset(years=yrs), freq="MS"):
            # ATH must be known from before the window: use the full history up to each day
            seg = c.loc[:start + pd.DateOffset(years=yrs)]
            ath_before = c.loc[:start].max()
            s = seg.loc[start:]
            s_ath = np.maximum(s.cummax(), ath_before)
            d, t, paid = plans_with_ath(s, s_ath)
            rows.append({"sym": sym, "years": yrs, "start": start.date(), "DCA x": d / paid, "tiered x": t / paid})
    return pd.DataFrame(rows)


def plans_with_ath(s, ath, weekly=10.0, tiers=((-0.5, 30), (-0.4, 20), (-0.3, 10))):
    dd = s / ath - 1
    cash = btc_t = btc_d = paid = 0.0
    last = -99
    for i, (p, x) in enumerate(zip(s.values, dd.values)):
        if i % 7 == 0:
            paid += weekly; cash += weekly; btc_d += weekly * (1 - FEE) / p
        if i - last < 7:
            continue
        for lvl, amt in tiers:
            if x <= lvl:
                spend = min(amt, cash)
                if spend > 0:
                    btc_t += spend * (1 - FEE) / p; cash -= spend; last = i
                break
    return btc_d * s.iloc[-1], btc_t * s.iloc[-1] + cash, paid


def dow():
    r = C["BTCUSDT"].pct_change().dropna()
    d = pd.DataFrame({"r": r, "wd": r.index.day_name().str[:3], "IS": r.index < lab.SPLIT})
    g = d.groupby(["IS", "wd"])["r"].agg(mean_bps=lambda x: round(1e4 * x.mean(), 1), up_rate=lambda x: round((x > 0).mean(), 3),
                                           n="size")
    is_mean = g.loc[True, "mean_bps"]; oos_mean = g.loc[False, "mean_bps"]
    rank_corr = round(is_mean.rank().corr(oos_mean.rank()), 2)
    best = is_mean.nlargest(3).index
    pos = d["wd"].isin(best).astype(float)                     # the weekday is known in advance: no look-ahead
    strat = (pos * d["r"]) - pos.diff().abs().fillna(0) * 5 / 1e4
    res = {"IS best 3 days": list(best), "IS/OOS rank corr of weekday means": rank_corr,
           "strategy IS Sharpe": round(lab.sharpe(strat[d.IS], 365), 2), "strategy OOS Sharpe": round(lab.sharpe(strat[~d.IS], 365), 2),
           "BTC hold OOS Sharpe": round(lab.sharpe(d.r[~d.IS], 365), 2)}
    # the post's own claim, direction only: Wed up-rate and Fri down-rate, chi-square-ish z vs 50%
    for per, m in (("IS", d.IS), ("OOS", ~d.IS)):
        for wd in ("Wed", "Fri"):
            x = d[m & (d.wd == wd)].r
            res[f"{per} {wd} up-rate"] = f"{(x > 0).mean():.3f} (z {((x > 0).mean() - 0.5) / np.sqrt(0.25 / len(x)):.2f}, n {len(x)})"
    return g.unstack(0), res


if __name__ == "__main__":
    W = pd.concat([windows("BTCUSDT"), windows("ETHUSDT")])
    S = W.groupby(["sym", "years"]).agg(starts=("DCA x", "size"), DCA_median=("DCA x", "median"),
                                        tiered_median=("tiered x", "median"),
                                        tiered_wins=("tiered x", lambda v: 0)).reset_index()
    S["tiered beats DCA"] = W.assign(w=W["tiered x"] > W["DCA x"]).groupby(["sym", "years"])["w"].mean().round(2).values
    S = S.drop(columns="tiered_wins").round(2)
    full = {s: plans(C[s].dropna()) for s in C}
    full_t = {s: f"DCA {v[0] / v[2]:.2f}x, tiered {v[1] / v[2]:.2f}x of ${v[2]:.0f} paid (ATH from 2020 only)" for s, v in full.items()}
    g, res = dow()
    print(S.to_string(), full_t, g.to_string(), res, sep="\n")
    open("results_reddit2.md", "w").write(
        "# #20 tiered drawdown buying vs DCA, #21 day-of-week\n\n## #20 (same $10/week to both; wealth / money paid in)\n\n"
        + S.to_markdown(index=False) + "\n\nWhole period: " + str(full_t)
        + "\n\n## #21 BTC by UTC weekday (close-to-close)\n\n" + g.to_markdown() + "\n\n"
        + pd.Series(res, dtype=object).to_frame("value").to_markdown() + "\n")
