"""Deep-dive on the one survivor: cross-sectional funding contrarian (#7b).
Where does the money come from (price vs funding received), which coins, which legs, is it fragile?"""
import numpy as np
import pandas as pd

import lab

P = lab.load("1D")
U = lab.universe(P, 30)
F = P["funding"]
OOS = slice(lab.SPLIT, None)


def bt(score, mask=U, q=0.2, cost=7.0, hold=1):
    return lab.backtest(lab.every(lab.xs_rank_weights(score, mask, q), hold), P, cost)


def row(name, b):
    x = b["net"]
    return {"variant": name, "Sharpe_all": round(lab.sharpe(x, 365), 2), "OOS_Sharpe": round(lab.sharpe(x.loc[OOS], 365), 2),
            "ann_net": round(x.mean() * 365, 3), "ann_price": round(b["gross"].mean() * 365, 3),
            "ann_funding_recv": round(-b["fund"].mean() * 365, 3), "ann_cost": round(b["cost"].mean() * 365, 3),
            "OOS_price": round(b["gross"].loc[OOS].mean() * 365, 3), "OOS_funding_recv": round(-b["fund"].loc[OOS].mean() * 365, 3),
            "maxdd": round(lab.maxdd(x), 3)}


s7 = -F.rolling(7).mean()
rows = [row("base lb7 q20 daily", bt(s7))]
# legs separately
w = lab.xs_rank_weights(s7, U)
for leg, ww in (("long leg only (low funding)", w.clip(lower=0)), ("short leg only (high funding)", w.clip(upper=0))):
    rows.append(row(leg, lab.backtest(ww, P, 7.0)))
# price-only: ignore funding cash flows entirely -> is there a price-reversal edge too?
rows.append(row("price only (funding off)", lab.backtest(w, P, 7.0, funding=False)))
# drop coins one at a time: max damage
base = bt(s7)["net"]
worst = []
for c in U.columns:
    m = U.copy(); m[c] = False
    worst.append((lab.sharpe(bt(s7, m)["net"], 365), c))
worst.sort()
rows.append(row(f"without {worst[0][1]} (most helpful coin)", bt(s7, U.assign(**{worst[0][1]: False}))))
rows.append(row("q=0.1 (tails only)", bt(s7, q=0.1)))
rows.append(row("q=0.33 (terciles)", bt(s7, q=1/3)))
rows.append(row("ex-2020/2021 (from 2022)", bt(s7)[lambda d: d.index >= "2022-01-01"]))
# is it just short-term reversal in disguise? residualize on lb7 return rank
r7 = P["close"] / P["close"].shift(7) - 1
rk_f, rk_r = s7.where(U).rank(axis=1, pct=True), r7.where(U).rank(axis=1, pct=True)
print("avg XS rank corr(-funding7, ret7):", round(rk_f.T.corrwith(rk_r.T).mean(), 3))
rows.append(row("7d reversal alone (for comparison)", bt(-r7)))
a = rk_f.sub(rk_f.mean(axis=1), axis=0)
b = rk_r.sub(rk_r.mean(axis=1), axis=0)
beta = (a * b).sum(axis=1) / (b * b).sum(axis=1)
rows.append(row("funding signal with 7d-return part removed", bt(a - b.mul(beta, axis=0))))
open("results_funding.md", "w").write("# Funding contrarian deep-dive\n\n" + pd.DataFrame(rows).to_markdown(index=False) + "\n")
print(pd.DataFrame(rows).to_string())
