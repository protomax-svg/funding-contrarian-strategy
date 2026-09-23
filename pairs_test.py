"""#7b with group-matched pairs: inside every group, #longs == #shorts at equal size.

Each day, inside each group, pair the lowest-7d-funding coin (long) with the highest (short), 2nd lowest with
2nd highest, ... Then keep the N pairs with the widest funding gap across all groups. Each pair gets 1/N of
the book (0.5/N long, 0.5/N short), so every group is net zero. Groups:
  A) hand-made sector labels (known today -> mild hindsight in the labels themselves)
  B) price clusters: hierarchical clustering of trailing 90d return correlation, refit every 30 days (no hindsight)
"""
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

import lab

COST = 7.0
P = lab.load("1D")
U = lab.universe(P, 30)
F7 = P["funding"].rolling(7).mean()
R = P["ret"]
OOS = slice(lab.SPLIT, None)
IS = slice(None, lab.SPLIT - pd.Timedelta("1ns"))

SECTORS = {
    "majors/payments": "BTC ETH BNB XRP LTC BCH ETC XLM TRX EOS",
    "L1": "SOL ADA AVAX DOT ATOM NEAR ALGO XTZ FTM APT SUI SEI INJ TIA WAVES LUNA",
    "L2": "MATIC POL ARB OP",
    "DeFi/oracle": "UNI AAVE SUSHI CRV COMP SNX 1INCH SRM LINK",
    "meme": "DOGE 1000SHIB 1000PEPE",
    "gaming/media": "AXS SAND MANA THETA",
    "infra/other": "FIL VET WLD FTT",
}
SECTOR_OF = {f"{c}USDT": g for g, cs in SECTORS.items() for c in cs.split()}
assert set(SECTOR_OF) >= set(P["close"].columns) - {"PEPEUSDT"}, set(P["close"].columns) - set(SECTOR_OF)


def cluster_labels(k=6, window=90, every=30):
    """Per-date group label from trailing correlation clusters (refit every `every` days)."""
    out = pd.DataFrame(index=R.index, columns=R.columns, dtype=object)
    lab_now = {}
    for i in range(len(R)):
        if i >= window and i % every == 0:
            syms = [c for c in R.columns if U.iloc[i][c] and R.iloc[i - window:i][c].notna().sum() >= window * 0.8]
            if len(syms) >= k * 2:
                cm = R.iloc[i - window:i][syms].corr().fillna(0).values
                d = squareform(np.clip(1 - cm, 0, 2), checks=False)
                lab_now = dict(zip(syms, fcluster(linkage(d, "average"), k, "maxclust")))
        out.iloc[i] = pd.Series({c: lab_now.get(c) for c in R.columns})
    return out


def paired_weights(group_of, n_pairs=5):
    """group_of(date_index, sym) -> group label or None."""
    W = np.zeros(F7.shape)
    cols = list(F7.columns)
    f7, um = F7.values, U.values
    for i in range(len(F7)):
        groups = {}
        for j, c in enumerate(cols):
            if um[i, j] and np.isfinite(f7[i, j]):
                g = group_of(i, c)
                if g is not None:
                    groups.setdefault(g, []).append((f7[i, j], j))
        cand = []
        for g, members in groups.items():
            members.sort()
            for k in range(len(members) // 2):
                lo, hi = members[k], members[-1 - k]
                if hi[0] > lo[0]:
                    cand.append((hi[0] - lo[0], lo[1], hi[1], g))
        cand.sort(reverse=True)
        pick = cand[:n_pairs]
        for _, jl, js, _ in pick:
            W[i, jl] += 0.5 / len(pick)
            W[i, js] -= 0.5 / len(pick)
    return pd.DataFrame(W, index=F7.index, columns=cols)


def evaluate(name, w):
    b = lab.backtest(w, P, COST)
    x = b["net"]
    x = x[b["gross_exp"].gt(0).cumsum() > 0]
    eq = (1 + x).cumprod()
    dd = eq / eq.cummax() - 1
    t = dd.idxmin()
    pk = eq.loc[:t].idxmax()
    pos = w.shift(1)
    worst_coin_day = (pos * R.fillna(0)).min().min()
    return {"variant": name, "Sharpe_all": round(lab.sharpe(x, 365), 2), "IS": round(lab.sharpe(x.loc[IS], 365), 2),
            "OOS": round(lab.sharpe(x.loc[OOS], 365), 2),
            "OOS@15bps": round(lab.sharpe(lab.backtest(w, P, 15)["net"].loc[OOS], 365), 2),
            "OOS +1d": round(lab.sharpe(lab.backtest(w.shift(1).fillna(0), P, COST)["net"].loc[OOS], 365), 2),
            "ann_ret": round(x.mean() * 365, 3), "ann_vol": round(x.std() * 365 ** 0.5, 3),
            "maxDD": round(dd.min(), 3), "DD_period": f"{pk.date()} -> {t.date()}",
            "worst_1coin_day": round(worst_coin_day, 3),
            "OOS_price": round(b["gross"].loc[OOS].mean() * 365, 3), "OOS_funding": round(-b["fund"].loc[OOS].mean() * 365, 3),
            "avg_pairs_long": round(float((w > 0).sum(axis=1)[w.abs().sum(axis=1) > 0].mean()), 1)}, x


rows, curves = [], {}
base = lab.xs_rank_weights(-F7, U)
r, curves["base (tested)"] = evaluate("base: top/bottom 20%, no pairing (what the fronttest runs)", base)
rows.append(r)
print("base done", flush=True)
for n in (5, 6):
    w = paired_weights(lambda i, c: SECTOR_OF.get(c), n)
    r, curves[f"sector N={n}"] = evaluate(f"A) sector pairs, N={n}", w)
    rows.append(r)
    print(r["variant"], "done", flush=True)
CL = cluster_labels()
clv = CL.values
colpos = {c: j for j, c in enumerate(CL.columns)}
for n in (5, 6):
    w = paired_weights(lambda i, c: clv[i, colpos[c]], n)
    r, curves[f"cluster N={n}"] = evaluate(f"B) price-cluster pairs, N={n}", w)
    rows.append(r)
    print(r["variant"], "done", flush=True)

res = pd.DataFrame(rows)
yr = pd.DataFrame({k: v.groupby(v.index.year).apply(lambda s: round(lab.sharpe(s, 365), 2)) for k, v in curves.items()}).T
corr = pd.DataFrame(curves).corr().round(2)
# which sector pairs does the sector version actually trade? (share of pair-days per group)
wA = paired_weights(lambda i, c: SECTOR_OF.get(c), 5)
longs = (wA > 0).sum()
share = pd.Series({g: sum(longs.get(f"{c}USDT", 0) for c in cs.split()) for g, cs in SECTORS.items()})
share = (share / share.sum()).round(3).sort_values(ascending=False)

open("results_pairs.md", "w").write(
    "# Funding contrarian with group-matched pairs\n\nIn every group: #longs == #shorts, equal size. "
    "7 bps/side, real funding, top-30 universe, IS 2020-2023, OOS 2024-01..2026-08.\n\n"
    + res.to_markdown(index=False)
    + "\n\n## Sharpe by year\n\n" + yr.to_markdown()
    + "\n\n## Correlation of daily returns\n\n" + corr.to_markdown()
    + "\n\n## Sector version: where the pairs are (share of pair-days)\n\n" + share.to_frame("share").to_markdown()
    + "\n\nSector labels: " + "; ".join(f"**{g}**: {c}" for g, c in SECTORS.items()) + "\n")
print(res.to_string())
print(yr.to_string())
print(share.to_string())
