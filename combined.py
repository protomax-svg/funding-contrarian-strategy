"""Everything that helped, combined, plus leave-one-out ablation. Reuses improve.py's pieces."""
import numpy as np
import pandas as pd

import improve as im
import lab

PARTS = ("atr", "buffer", "beta", "no_short_rally", "no_short_extreme", "stop50", "top40")


def build(off=()):
    on = [p for p in PARTS if p not in off]
    U = lab.universe(im.P, 40 if "top40" in on else 30)
    F7 = im.F7
    w = im.buffered(-F7, U, 0.2, 0.35) if "buffer" in on else lab.xs_rank_weights(-F7, U)
    xs_z = F7.where(U).sub(F7.where(U).mean(axis=1), axis=0).div(F7.where(U).std(axis=1), axis=0)
    r7 = im.ret7.where(U).rank(axis=1, pct=True)
    drop = pd.DataFrame(False, index=w.index, columns=w.columns)
    if "no_short_rally" in on:
        drop |= (r7 >= 0.8).fillna(False)
    if "no_short_extreme" in on:
        drop |= (xs_z > 2.5).fillna(False)
    w = im.without(w, drop_short=drop)
    if "stop50" in on:
        w = im.with_stop(w, 0.50)
    if "beta" in on:
        w = im.beta_neutral(w)
    if "atr" in on:
        w = w.mul(im.ATR_ON, axis=0)
    return w


def stats(name, w):
    b = lab.backtest(w, im.P, im.COST)
    x = b["net"]
    o = x.loc[im.OOS]
    return {"variant": name, "IS": round(lab.sharpe(x.loc[im.IS], 365), 2), "OOS": round(lab.sharpe(o, 365), 2),
            "OOS@15bps": round(lab.sharpe(lab.backtest(w, im.P, 15)["net"].loc[im.OOS], 365), 2),
            "OOS +1d": round(lab.sharpe(lab.backtest(w.shift(1).fillna(0), im.P, im.COST)["net"].loc[im.OOS], 365), 2),
            "OOS total %": round(100 * ((1 + o).prod() - 1), 1), "OOS ann %": round(100 * o.mean() * 365, 1),
            "maxDD": round(lab.maxdd(x), 3), "OOS maxDD": round(lab.maxdd(o), 3),
            "cost/yr": round(b["cost"].mean() * 365, 3), "exposure": round(float(b["gross_exp"].mean()), 2)}, x


rows, curves = [], {}
base_w = lab.xs_rank_weights(-im.F7, lab.universe(im.P, 30))
r, curves["base"] = stats("base (no filters)", base_w); rows.append(r)
r, curves["live now"] = stats("live now: base + ATR", base_w.mul(im.ATR_ON, axis=0)); rows.append(r)
full = build()
r, curves["ALL"] = stats("ALL combined", full); rows.append(r)
for p in PARTS:
    r, _ = stats(f"ALL minus {p}", build(off=(p,))); rows.append(r)
    print(p, "done", flush=True)
# only the parts that helped in BOTH periods on their own (the honest version)
r, curves["robust core"] = stats("robust core: ATR + buffer + beta", build(off=("no_short_rally", "no_short_extreme", "stop50", "top40")))
rows.append(r)

df = pd.DataFrame(rows)
yr = pd.DataFrame({k: v.groupby(v.index.year).apply(lambda s: round(100 * ((1 + s).prod() - 1), 1)) for k, v in curves.items()}).T
# placebo for the full combo: time-shift each coin's weight path
rng = np.random.default_rng(0)
real = lab.sharpe(curves["ALL"].loc[im.OOS], 365)
pl = []
for _ in range(100):
    v = full.values.copy()
    for j in range(v.shape[1]):
        v[:, j] = np.roll(v[:, j], rng.integers(200, len(v) - 200))
    pl.append(lab.sharpe(lab.backtest(pd.DataFrame(v, index=full.index, columns=full.columns), im.P, im.COST)["net"].loc[im.OOS], 365))
md = ("# Everything combined\n\nParts: " + ", ".join(PARTS) + ". 7 bps/side, real funding. IS 2020-23, OOS 2024-01..2026-08.\n\n"
      + df.to_markdown(index=False)
      + "\n\n`ALL minus X` = drop one part. If OOS goes UP when a part is dropped, that part is not pulling its weight.\n"
      + "\n## Return by calendar year (%)\n\n" + yr.to_markdown()
      + f"\n\nPlacebo (100 time-shifted copies of the ALL book): OOS Sharpe median {np.median(pl):.2f}, "
      + f"best {max(pl):.2f}; real {real:.2f}; share >= real: {np.mean(np.array(pl) >= real):.2f}\n")
open("results_combined.md", "w").write(md)
print(md)


# ---------------- the IS-chosen combination from combo_grid.py ----------------
if __name__ == "__main__":
    pick_off = ("atr", "beta", "no_short_extreme")
    wp = build(off=pick_off)
    r, xp = stats("IS-chosen: buffer + no_short_rally + stop50 + top40", wp)
    yrp = xp.groupby(xp.index.year).apply(lambda s: round(100 * ((1 + s).prod() - 1), 1))
    rng = np.random.default_rng(1)
    realp = lab.sharpe(xp.loc[im.OOS], 365)
    plp = []
    for _ in range(100):
        v = wp.values.copy()
        for j in range(v.shape[1]):
            v[:, j] = np.roll(v[:, j], rng.integers(200, len(v) - 200))
        plp.append(lab.sharpe(lab.backtest(pd.DataFrame(v, index=wp.index, columns=wp.columns), im.P, im.COST)["net"].loc[im.OOS], 365))
    b = lab.backtest(wp, im.P, im.COST)
    extra = {"OOS price %/yr": round(100 * b["gross"].loc[im.OOS].mean() * 365, 1),
             "OOS funding %/yr": round(-100 * b["fund"].loc[im.OOS].mean() * 365, 1),
             "OOS cost %/yr": round(100 * b["cost"].loc[im.OOS].mean() * 365, 1),
             "placebo OOS median / best": (round(float(np.median(plp)), 2), round(float(max(plp)), 2)),
             "placebo share >= real": float(np.mean(np.array(plp) >= realp)),
             "worst day %": round(100 * xp.min(), 1), "worst month %": round(100 * xp.resample("ME").sum().min(), 1)}
    md = ("\n## The IS-chosen combination (combo_grid.py): buffer + no_short_rally + stop50 + top40\n\n"
          + pd.DataFrame([r]).to_markdown(index=False) + "\n\nBy year (%): " + ", ".join(f"{y}: {v}" for y, v in yrp.items())
          + "\n\n" + pd.Series(extra).to_frame("value").to_markdown() + "\n")
    open("results_combined.md", "a").write(md)
    print(md)
