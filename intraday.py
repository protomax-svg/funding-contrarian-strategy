"""Intraday Reddit ideas: #2 BB+VWAP breakout (BTC 1h, exact posted rules), #13 hour-of-day,
#5 Kalman BTC/ETH pairs (4h), #6 rolling cointegration pairs across the universe (4h)."""
import itertools

import numpy as np
import pandas as pd

import lab

COST = 7.0
out = []


def table(title, rows, note=""):
    out.append(f"\n## {title}\n")
    if note:
        out.append(note + "\n")
    out.append(pd.DataFrame(rows).to_markdown(index=False))
    print(title, "done", flush=True)


# =====================================================================
# #2 Bollinger + VWAP breakout, BTC 1h. Posted: BB(42,2.5), VWAP, ADX(5), RSI(5), 3 slots,
# TP 3%, SL 1.5%, time exit 1075 min, mean-reversion exit. Post date 2025-06-25 -> after that is true OOS.
# =====================================================================
k = pd.read_parquet(lab.D / "klines_1h" / "BTCUSDT.parquet").set_index("ts")
fu = pd.read_parquet(lab.D / "funding" / "BTCUSDT.parquet").set_index("ts").funding_rate
fu.index = fu.index.floor("min") - pd.Timedelta("1min")
fund_h = fu.resample("1h").sum().reindex(k.index).fillna(0.0).values
O, Hh, Ll, Cc, V = (k[c].values for c in ("open", "high", "low", "close", "volume"))
tp_ = (k.high + k.low + k.close) / 3
day = k.index.floor("D")
vwap = ((tp_ * k.volume).groupby(day).cumsum() / k.volume.groupby(day).cumsum()).values


def bbvwap(n=42, kk=2.5, tp=0.03, sl=0.015, tmax=18, slots=3, cost=COST, filt=True):
    c = k.close
    mid, sd = c.rolling(n).mean(), c.rolling(n).std()
    up, lo = (mid + kk * sd).values, (mid - kk * sd).values
    r5 = lab.rsi(c, 5).values
    a5 = lab.adx(k.high, k.low, c, 5).values
    above6 = (c > vwap).rolling(6).sum().values == 6
    below6 = (c < vwap).rolling(6).sum().values == 6
    longsig = (Cc >= up) | (filt & above6 & (r5 > 55) & (a5 > 45))
    shortsig = (Cc <= lo) | (filt & below6 & (r5 < 45) & (a5 > 45))
    outside_u, outside_l = Cc >= up, Cc <= lo
    N = len(Cc)
    pnl = np.zeros(N)
    open_tr = []   # [dir, entry_px, entry_bar, entered_outside]
    trades = []
    w = 1.0 / slots
    for i in range(1, N):
        # 1) manage open trades on bar i (entered at open of an earlier bar)
        keep = []
        for d, px, eb, outs in open_tr:
            stop = px * (1 - d * sl)
            targ = px * (1 + d * tp)
            hit_sl = (Ll[i] <= stop) if d > 0 else (Hh[i] >= stop)
            hit_tp = (Hh[i] >= targ) if d > 0 else (Ll[i] <= targ)
            prev = Cc[i - 1] if eb < i else px
            if hit_sl:                      # pessimistic: stop first if both in range
                exit_px = min(stop, O[i]) if d > 0 else max(stop, O[i])
            elif hit_tp:
                exit_px = targ
            else:
                exit_px = None
            pnl[i] -= w * d * fund_h[i]
            if exit_px is not None:
                pnl[i] += w * (d * (exit_px / prev - 1) - cost / 1e4)
                trades.append(d * (exit_px / px - 1) - 2 * cost / 1e4)
                continue
            pnl[i] += w * d * (Cc[i] / prev - 1)
            back_in = outs and (lo[i] < Cc[i] < up[i])
            if i - eb + 1 >= tmax or back_in:   # exit at next open ~= this close
                pnl[i] -= w * cost / 1e4
                trades.append(d * (Cc[i] / px - 1) - 2 * cost / 1e4)
                continue
            keep.append([d, px, eb, outs])
        open_tr = keep
        # 2) new entries from signal on closed bar i-1, filled at open of bar i
        j = i - 1
        if len(open_tr) < slots and (longsig[j] or shortsig[j]) and np.isfinite(up[j]):
            d = 1 if longsig[j] else -1
            open_tr.append([d, O[i], i, bool(outside_u[j] if d > 0 else outside_l[j])])
            pnl[i] += w * (d * (Cc[i] / O[i] - 1) - cost / 1e4)
            # re-check stop/target inside the entry bar itself (pessimistic)
            px = O[i]
            stop, targ = px * (1 - d * sl), px * (1 + d * tp)
            if (d > 0 and Ll[i] <= stop) or (d < 0 and Hh[i] >= stop):
                pnl[i] += w * (d * (stop / Cc[i] - 1) - cost / 1e4)
                trades.append(-sl - 2 * cost / 1e4)
                open_tr.pop()
    s = pd.Series(pnl, index=k.index)
    return s, np.array(trades)


def rep_series(s, name, ntr, trades):
    bt = pd.DataFrame({"net": s, "gross": s, "cost": 0.0, "fund": 0.0, "turn": 0.0, "gross_exp": 1.0})
    r = lab.report(bt, "1h", name)
    r = {kk: r[kk] for kk in ("name", "all_sharpe", "all_annret", "IS_sharpe", "OOS_sharpe", "OOS_annret", "maxdd", "p_boot")}
    post = s.loc["2025-07-01":]
    r["after_post_sharpe"] = round(lab.sharpe(post, lab.PPY["1h"]), 2)
    r["after_post_ret"] = round(float(post.sum()), 3)
    r["trades"] = ntr
    r["win%"] = round(100 * float((trades > 0).mean()), 1) if ntr else 0
    r["avg_trade_bps"] = round(1e4 * float(trades.mean()), 1) if ntr else 0
    return r


rows = []
for filt, cost in ((False, 2.5), (True, 2.5), (False, COST), (True, COST)):
    s, tr = bbvwap(filt=filt, cost=cost)
    rows.append(rep_series(s, f"{'v2 BB+VWAP/ADX/RSI' if filt else 'v1 BB only'} @ {cost}bps", len(tr), tr))
grid = []
for n, kk, tp, sl in itertools.product([34, 42, 50], [2.0, 2.5, 3.0], [0.024, 0.03, 0.036], [0.012, 0.015, 0.018]):
    s, tr = bbvwap(n, kk, tp, sl)
    grid.append(rep_series(s, f"n={n} k={kk} tp={tp} sl={sl}", len(tr), tr))
g = pd.DataFrame(grid)
table("#2 Bollinger + VWAP breakout, BTC 1h (posted params; post dated 2025-06-25)", rows,
      "2.5 bps = the post's 0.025% commission. 7 bps = our realistic taker+slippage. `after_post` = 2025-07..2026-08, never seen by the author.")
out.append(f"\n±20% grid ({len(g)} variants, 7 bps): median OOS Sharpe {g.OOS_sharpe.median():.2f}, "
           f"share OOS>0 {(g.OOS_sharpe > 0).mean():.2f}, median after-post Sharpe {g.after_post_sharpe.median():.2f}, "
           f"median avg trade {g.avg_trade_bps.median():.1f} bps.")

# =====================================================================
# #13 hour-of-day seasonality (crypto has no close; test the 24 UTC hours directly)
# =====================================================================
P1 = lab.load("1h")
U1 = lab.universe(P1, top_n=30, min_age_bars=60 * 24, vol_window=30 * 24)
ew = (P1["ret"].where(U1)).mean(axis=1)
btc = P1["ret"]["BTCUSDT"]
rows = []
for nm, r in (("BTC", btc), ("EW top-30", ew)):
    is_, oos = r[r.index < lab.SPLIT], r[r.index >= lab.SPLIT]
    m_is, m_oos = is_.groupby(is_.index.hour).mean(), oos.groupby(oos.index.hour).mean()
    rho = m_is.corr(m_oos, method="spearman")
    for kk_ in (3, 6):
        best, worst = m_is.nlargest(kk_).index, m_is.nsmallest(kk_).index
        # long the IS-best hours, short the IS-worst hours; 1 round trip each per hour held
        hr = oos.index.hour
        sig = np.where(np.isin(hr, best), 1, np.where(np.isin(hr, worst), -1, 0))
        g_ = sig * oos.values
        net = g_ - (sig != 0) * 2 * COST / 1e4
        rows.append({"series": nm, "k_hours": kk_, "rank_corr_IS_vs_OOS": round(rho, 2),
                     "OOS_gross_bps_per_trade": round(1e4 * g_[sig != 0].mean(), 2),
                     "OOS_net_ann": round(float(net.mean() * lab.PPY["1h"]), 3),
                     "IS_best_hours_UTC": list(best), "IS_worst_hours_UTC": list(worst)})
table("#13 Hour-of-day / session effect", rows,
      "Hours ranked on 2020-2023 only, traded 2024+. Each held hour costs a round trip (the edge must beat ~14 bps).")

# =====================================================================
# #5 Kalman-filter BTC/ETH pairs (4h), Chan's method + the post's rolling-z variant
# =====================================================================
P4 = lab.load("4h")
y = np.log(P4["close"]["BTCUSDT"]).values
x = np.log(P4["close"]["ETHUSDT"]).values
idx4 = P4["close"].index


def kalman(y, x, delta=1e-4, ve=1e-3):
    n = len(y)
    th = np.zeros(2)
    Pm = np.zeros((2, 2))
    Vw = delta / (1 - delta) * np.eye(2)
    beta, e, Q = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    for t in range(n):
        if not (np.isfinite(y[t]) and np.isfinite(x[t])):
            continue
        F = np.array([x[t], 1.0])
        R = Pm + Vw
        yhat = F @ th
        Q[t] = F @ R @ F + ve
        e[t] = y[t] - yhat
        K = R @ F / Q[t]
        th = th + K * e[t]
        Pm = R - np.outer(K, F) @ R
        beta[t] = th[0]
    return beta, e, Q


def pair_bt(z, b, entry, exit_, stop, ret_y, ret_x, cost=COST):
    """Spread position from z (known at t): -1 when z>entry (short y), +1 when z<-entry, flat on cross of exit."""
    n = len(z)
    pos = np.zeros(n)
    p = 0
    for t in range(n):
        if not np.isfinite(z[t]):
            p = 0
        elif p == 0:
            p = -1 if z[t] > entry else (1 if z[t] < -entry else 0)
        elif (p > 0 and (z[t] >= -exit_ or z[t] < -stop)) or (p < 0 and (z[t] <= exit_ or z[t] > stop)):
            p = 0
        pos[t] = p
    bb = np.nan_to_num(b)
    wy = pos / (1 + np.abs(bb))
    wx = -pos * bb / (1 + np.abs(bb))
    wy_l, wx_l = np.roll(wy, 1), np.roll(wx, 1)
    wy_l[0] = wx_l[0] = 0
    gross = wy_l * np.nan_to_num(ret_y) + wx_l * np.nan_to_num(ret_x)
    turn = np.abs(np.diff(wy, prepend=0)) + np.abs(np.diff(wx, prepend=0))
    net = gross - np.roll(turn, 1) * cost / 1e4
    return net, pos


ry, rx = P4["ret"]["BTCUSDT"].values, P4["ret"]["ETHUSDT"].values
fy, fx = P4["funding"]["BTCUSDT"].values, P4["funding"]["ETHUSDT"].values
beta, e, Q = kalman(y, x)
rows = []


def rep4(net, pos, name, wy=None):
    s = pd.Series(net, index=idx4)
    bt = pd.DataFrame({"net": s, "gross": s, "cost": 0.0, "fund": 0.0, "turn": 0.0, "gross_exp": np.abs(pos)})
    r = lab.report(bt, "4h", name)
    r = {kk: r[kk] for kk in ("name", "all_sharpe", "all_annret", "IS_sharpe", "OOS_sharpe", "OOS_annret", "maxdd", "p_boot")}
    r["time_in_mkt"] = round(float((pos != 0).mean()), 2)
    return r


for ent in (0.5, 1.0, 1.5, 2.0):
    zc = e / np.sqrt(Q)
    net, pos = pair_bt(zc, beta, ent, 0.0, 99, ry, rx)
    rows.append(rep4(net, pos, f"Chan z=e/sqrt(Q) entry {ent} exit 0"))
spread = pd.Series(y - beta * x)
for lb, ent in itertools.product((10, 30, 90), (1.5, 2.0, 2.5)):
    zr = ((spread - spread.rolling(lb).mean()) / spread.rolling(lb).std()).values
    net, pos = pair_bt(zr, beta, ent, 0.0, 99, ry, rx)
    rows.append(rep4(net, pos, f"post: rolling z lb={lb} entry {ent} exit 0"))
table("#5 Kalman-filter BTC/ETH pairs (4h)", rows,
      "Kalman delta=1e-4, Ve=1e-3 (Chan defaults, not tuned). Funding on the two legs nearly cancels and is ignored here.")

# =====================================================================
# #6 rolling cointegration pairs across the top-20 (4h). Re-select every 30 days (the "fell apart after 60 days" comment).
# =====================================================================
U4 = lab.universe(P4, top_n=20, min_age_bars=120 * 6, vol_window=30 * 6)
LP = np.log(P4["close"])
R4 = P4["ret"]
FORM, TRADE = 90 * 6, 30 * 6


def eg_tstat(yv, xv):
    X = np.column_stack([xv, np.ones_like(xv)])
    coef, *_ = np.linalg.lstsq(X, yv, rcond=None)
    res = yv - X @ coef
    de, lag, dlag = np.diff(res)[1:], res[1:-1], np.diff(res)[:-1]
    A = np.column_stack([lag, dlag])
    c2, *_ = np.linalg.lstsq(A, de, rcond=None)
    r2 = de - A @ c2
    s2 = r2 @ r2 / (len(de) - 2)
    se = np.sqrt(s2 * np.linalg.inv(A.T @ A)[0, 0])
    hl = -np.log(2) / np.log(1 + c2[0]) if -1 < c2[0] < 0 else np.inf
    return c2[0] / se, coef[0], coef[1], res.mean(), res.std(), hl


def coint_book(crit=-3.90, max_pairs=5, entry=2.0, stop=4.0, cost=COST):
    n = len(LP)
    total = np.zeros(n)
    n_sel = []
    for s0 in range(FORM, n - 1, TRADE):
        syms = [c for c in LP.columns if U4.iloc[s0 - 1][c] and LP.iloc[s0 - FORM:s0][c].notna().all()]
        cand = []
        for a, b in itertools.combinations(syms, 2):
            ya, xb = LP[a].values[s0 - FORM:s0], LP[b].values[s0 - FORM:s0]
            t, be, al, mu, sd, hl = eg_tstat(ya, xb)
            if t < crit and 6 <= hl <= 60 and be > 0:
                cand.append((t, a, b, be, al, mu, sd))
        cand.sort()
        pick = cand[:max_pairs]
        n_sel.append(len(pick))
        e_ = min(s0 + TRADE, n)
        for t, a, b, be, al, mu, sd in pick:
            sp = LP[a].values[s0 - 1:e_] - be * LP[b].values[s0 - 1:e_] - al
            z = (sp - mu) / sd
            net, _ = pair_bt(z, np.full(len(z), be), entry, 0.0, stop,
                             R4[a].values[s0 - 1:e_], R4[b].values[s0 - 1:e_], cost)
            net[-1] -= 0  # positions are force-flat at window end via next window's fresh state
            total[s0 - 1:e_] += net / max_pairs
    return pd.Series(total, index=LP.index), np.array(n_sel)


rows = []
for crit, ent, stop in ((-3.90, 2.0, 4.0), (-3.34, 2.0, 4.0), (-3.90, 1.5, 3.0), (-3.90, 2.0, 99)):
    s, ns = coint_book(crit, 5, ent, stop)
    bt = pd.DataFrame({"net": s, "gross": s, "cost": 0.0, "fund": 0.0, "turn": 0.0, "gross_exp": 1.0})
    r = lab.report(bt, "4h", f"EG t<{crit} entry {ent} stop {stop}")
    r = {kk: r[kk] for kk in ("name", "all_sharpe", "all_annret", "IS_sharpe", "OOS_sharpe", "OOS_annret", "maxdd", "p_boot")}
    r["avg_pairs_found"] = round(float(ns.mean()), 1)
    rows.append(r)
table("#6 Rolling cointegration pairs, top-20, 4h (90d formation, 30d trading)", rows,
      "Pairs picked only from data before each 30-day window. Up to 5 pairs, 1/5 capital each. 7 bps/side, 2 legs.")

open("results_intraday.md", "w").write("# Intraday / pairs results\n" + "\n".join(out) + "\n")
print("wrote results_intraday.md")
