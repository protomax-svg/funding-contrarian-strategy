"""All 2^7 combinations of the parts. Choose by IS (2020-23) only, then read OOS once."""
import itertools
import numpy as np
import pandas as pd

import combined as cb
import lab
import improve as im

rows = []
for k in itertools.product((0, 1), repeat=len(cb.PARTS)):
    on = [p for p, f in zip(cb.PARTS, k) if f]
    off = tuple(p for p, f in zip(cb.PARTS, k) if not f)
    w = cb.build(off=off)
    x = lab.backtest(w, im.P, im.COST)["net"]
    rows.append({"parts": "+".join(on) or "base", "n_parts": len(on),
                 "IS": round(lab.sharpe(x.loc[im.IS], 365), 2), "OOS": round(lab.sharpe(x.loc[im.OOS], 365), 2),
                 "maxDD": round(lab.maxdd(x), 3), **{p: f for p, f in zip(cb.PARTS, k)}})
df = pd.DataFrame(rows).sort_values("IS", ascending=False)
top = df.head(10)
# how much does each part add on average (OOS and IS), over all combos
eff = pd.DataFrame({p: {"IS gain": round(df[df[p] == 1].IS.mean() - df[df[p] == 0].IS.mean(), 2),
                        "OOS gain": round(df[df[p] == 1].OOS.mean() - df[df[p] == 0].OOS.mean(), 2),
                        "maxDD gain": round(df[df[p] == 1].maxDD.mean() - df[df[p] == 0].maxDD.mean(), 3)} for p in cb.PARTS}).T
rank_corr = df.IS.corr(df.OOS, method="spearman")
md = ("# All 128 combinations\n\nSorted by IS Sharpe (the only fair way to choose). "
      f"Spearman corr of IS vs OOS across combos: {rank_corr:.2f}. Median OOS of all combos: {df.OOS.median():.2f}; "
      f"OOS of the IS-best combo: {df.iloc[0].OOS}.\n\n## Top 10 by IS\n\n"
      + top[["parts", "IS", "OOS", "maxDD"]].to_markdown(index=False)
      + "\n\n## Average effect of each part across all combos\n\n" + eff.to_markdown() + "\n")
open("results_combo_grid.md", "w").write(md)
print(md)
