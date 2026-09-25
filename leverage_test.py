"""How much leverage does the live rule (top-100 plain) survive? Worst trades, worst periods, leverage replay."""
import numpy as np
import pandas as pd

import lab
from alltest import P, F7, OOS

w = lab.xs_rank_weights(-F7, lab.universe(P, 100))
x = lab.backtest(w, P, 7.0)["net"]
x = x[x.index >= w.abs().sum(axis=1).gt(0).idxmax()]
out = []

# ---- portfolio at 1x ----
wk = (1 + x).resample("W").prod() - 1
mo = (1 + x).resample("ME").prod() - 1
port = {"worst day %": 100 * x.min(), "worst day date": str(x.idxmin().date()), "worst week %": 100 * wk.min(),
        "worst month %": 100 * mo.min(), "max drawdown %": 100 * lab.maxdd(x),
        "days below -5%": int((x < -0.05).sum()), "days below -10%": int((x < -0.10).sum())}

# ---- single positions: worst move against us from entry, using daily high (shorts) / low (longs) ----
C, H, L = P["close"], P["high"], P["low"]
side = np.sign(w).values
cv, hv, lv = C.values, H.values, L.values
mae, dates, syms, sides = [], [], [], []
for j in range(side.shape[1]):
    s = side[:, j]
    i = 0
    while i < len(s):
        if s[i] == 0:
            i += 1; continue
        k = i
        while k + 1 < len(s) and s[k + 1] == s[i]:
            k += 1
        entry = cv[i, j]                          # decided at close i, filled ~close i
        seg = slice(i + 1, k + 2)                 # held during bars i+1 .. k+1
        if np.isfinite(entry) and entry > 0 and k + 1 < len(s):     # still open on the last bar: nothing to measure
            worst = (np.nanmax(hv[seg, j]) / entry - 1) if s[i] < 0 else (1 - np.nanmin(lv[seg, j]) / entry)
            if np.isfinite(worst):
                mae.append(worst); dates.append(C.index[i]); syms.append(C.columns[j]); sides.append("short" if s[i] < 0 else "long")
        i = k + 1
m = pd.DataFrame({"adverse": mae, "date": dates, "sym": syms, "side": sides})
pos = {"positions": len(m),
       **{f"adverse move p{q}": f"{100 * m.adverse.quantile(q / 100):.0f}%" for q in (50, 90, 99)},
       "worst long (drop from entry)": "{:.0f}% {} {}".format(100 * m[m.side == 'long'].adverse.max(), *m.loc[m[m.side == 'long'].adverse.idxmax(), ['sym', 'date']].astype(str)),
       "worst short (rise from entry)": "{:.0f}% {} {}".format(100 * m[m.side == 'short'].adverse.max(), *m.loc[m[m.side == 'short'].adverse.idxmax(), ['sym', 'date']].astype(str))}
for thr in (0.2, 0.33, 0.5, 1.0):
    pos[f"positions with adverse move >= {int(thr * 100)}%"] = int((m.adverse >= thr).sum())

# ---- leverage replay (cross margin: the whole account backs every position) ----
lev_rows = []
for Lv in (1, 2, 3, 4, 5):
    y = (x * Lv).clip(lower=-1)
    eq = (1 + y).cumprod()
    dd = eq / eq.cummax() - 1
    o = y.loc[OOS]
    lev_rows.append({"leverage (gross)": f"{Lv}x", "max drawdown %": round(100 * dd.min(), 1),
                     "worst day %": round(100 * y.min(), 1), "worst month %": round(100 * ((1 + y).resample('ME').prod() - 1).min(), 1),
                     "2024-26 total %": round(100 * ((1 + o).prod() - 1), 1),
                     "ruined (-100%)": bool((y <= -1).any() or eq.min() <= 0.01),
                     # isolated margin: a position is liquidated if its adverse move >= ~(1/L - 0.5% maint.)
                     "positions liquidated if isolated": int((m.adverse >= 1 / Lv - 0.005).sum()) if Lv > 1 else 0})
md = ("# Leverage check (live rule: top-100 plain)\n\n## Portfolio at 1x\n\n" + pd.Series(port).to_frame("value").to_markdown()
      + "\n\n## Single positions (daily high/low while held, so intraday squeezes count)\n\n" + pd.Series(pos).to_frame("value").to_markdown()
      + "\n\n## Leverage replay 2020-2026 (daily bars; intraday moves inside a day are worse)\n\n" + pd.DataFrame(lev_rows).to_markdown(index=False) + "\n")
open("results_leverage.md", "w").write(md)
print(md)
