"""Statistics for the fronttest DB: every position as a round trip (open -> close), per-coin and per-side
aggregates, daily P&L, and a check that all parts add up to the equity change.

Pure functions over a sqlite connection, so the page, the CLI and the self-check use the same numbers.
Accounting per coin uses average cost: adding to a position moves the average entry, reducing it realises
(price - avg entry) x reduced qty. Funding and fees are attributed to the round trip they happened in.
"""
import math

import numpy as np
import pandas as pd

# backtest reference for the live rule (alltest.py / leverage_test.py, top-100 plain, 2024-01..2026-08, 1x)
BACKTEST = {"sharpe": 1.10, "ann_return_pct": 35.0, "daily_mean_pct": 0.083, "daily_std_pct": 1.37,
            "worst_day_pct": -9.3, "max_dd_pct": -27.0, "price_pct_yr": -21.4, "funding_pct_yr": 63.0, "cost_pct_yr": 6.3}
EPS = 1e-12


def _df(con, sql):
    return pd.read_sql_query(sql, con)


def episodes(con, marks_now=None):
    """One row per round trip. Open ones are marked to `marks_now` (sym -> price)."""
    marks_now = marks_now or {}
    tr = _df(con, "select ts, sym, qty, price, fee from trades order by ts, rowid")
    fu = _df(con, "select ts, sym, rate, payment from funding")
    ft = _df(con, "select * from features") if _has(con, "features") else pd.DataFrame()
    mk = _df(con, "select ts, sym, mark from marks") if _has(con, "marks") else pd.DataFrame(columns=["ts", "sym", "mark"])
    now = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)
    out = []
    for sym, g in tr.groupby("sym", sort=False):
        pos = avg = 0.0
        ep = None

        def close(ts, px):
            ep.update(close_ts=ts, exit=px, status="closed")
            out.append(ep)

        for ts, _, d, px, fee in g.itertuples(index=False):
            if abs(pos) < EPS:
                ep = {"sym": sym, "side": "LONG" if d > 0 else "SHORT", "open_ts": ts, "entry": px, "resizes": 0,
                      "price_pnl": 0.0, "fees": 0.0, "max_notional": abs(d * px)}
                pos, avg = d, px
                ep["fees"] += fee
                continue
            ep["fees"] += fee
            if np.sign(d) == np.sign(pos):                       # add on the same side
                avg = (avg * abs(pos) + px * abs(d)) / abs(pos + d)
                pos += d
                ep["resizes"] += 1
            else:
                closed = min(abs(d), abs(pos))
                ep["price_pnl"] += closed * (px - avg) * np.sign(pos)
                rest = pos + d
                if abs(rest) < EPS or abs(rest * px) < 1e-6:
                    close(ts, px); pos = avg = 0.0; ep = None
                    continue
                if np.sign(rest) != np.sign(pos):                # flipped: close, then open the remainder
                    close(ts, px)
                    ep = {"sym": sym, "side": "LONG" if rest > 0 else "SHORT", "open_ts": ts, "entry": px, "resizes": 0,
                          "price_pnl": 0.0, "fees": 0.0, "max_notional": abs(rest * px)}
                    pos, avg = rest, px
                    continue
                pos = rest
                ep["resizes"] += 1
            ep["max_notional"] = max(ep["max_notional"], abs(pos * px))
        if ep is not None:                                        # still open
            m = marks_now.get(sym, avg)
            ep.update(close_ts=None, exit=m, status="open", qty=pos, avg_entry=avg,
                      unrealized=pos * (m - avg))
            out.append(ep)
    E = pd.DataFrame(out)
    if E.empty:
        return E
    E["unrealized"] = E.get("unrealized", 0.0)
    E["unrealized"] = E["unrealized"].fillna(0.0)
    end = E.close_ts.fillna(now)
    # funding inside [open, close): the close happens right after the 00:00 settlement it still collects
    # per coin: sorted arrays + binary search -> each round trip is O(log n), not a scan
    def arrays(df, cols):
        return {k: (g.ts.to_numpy(), *[g[c].to_numpy(dtype=float) for c in cols])
                for k, g in df.sort_values("ts").groupby("sym")}
    FU, MK = arrays(fu, ("payment", "rate")), arrays(mk, ("mark",))
    fsum, fcnt, frate, mae, mfe = [], [], [], [], []
    for sym, o, e, side, entry, ex in zip(E.sym, E.open_ts, end, E.side, E.entry, E.exit):
        if sym in FU:
            ts, pay, rate = FU[sym]
            i0, i1 = np.searchsorted(ts, o, "right"), np.searchsorted(ts, e, "right")   # funding in (open, close]
            fsum.append(float(pay[i0:i1].sum())); fcnt.append(int(i1 - i0))
            frate.append(float(rate[i0:i1].mean()) if i1 > i0 else np.nan)
        else:
            fsum.append(0.0); fcnt.append(0); frate.append(np.nan)
        m = np.array([ex], dtype=float)
        if sym in MK:
            ts, mark = MK[sym]
            m = np.append(mark[np.searchsorted(ts, o, "left"):np.searchsorted(ts, e, "right")], ex)
        sgn = 1.0 if side == "LONG" else -1.0
        exc = sgn * (m[m > 0] / entry - 1) if entry else np.zeros(1)
        mae.append(100 * min(exc.min(initial=0.0), 0.0)); mfe.append(100 * max(exc.max(initial=0.0), 0.0))
    E["funding"], E["funding_events"], E["avg_funding_rate_bps"] = fsum, fcnt, np.array(frate) * 1e4
    E["net"] = E.price_pnl + E.unrealized + E.funding - E.fees
    E["hold_h"] = (end - E.open_ts) / 3.6e6
    E["return_pct"] = 100 * E.net / E.max_notional.replace(0, np.nan)
    E["mae_pct"], E["mfe_pct"] = mae, mfe
    # market state at entry (features row written at the same rebalance timestamp)
    if not ft.empty:
        cols = [c for c in ("rank_vol", "adv30_musd", "atr14_pct", "vol30_pct", "ret1d_pct", "ret7d_pct",
                            "f7_bps", "pred_funding_bps", "basis_bps") if c in ft.columns]
        E = E.merge(ft[["ts", "sym"] + cols].rename(columns={"ts": "open_ts", **{c: f"entry_{c}" for c in cols}}),
                    on=["open_ts", "sym"], how="left")
    return E


def _has(con, table):
    return con.execute("select 1 from sqlite_master where type='table' and name=?", (table,)).fetchone() is not None


def _mean(s):
    s = pd.to_numeric(s, errors="coerce").dropna()
    return float(s.mean()) if len(s) else None


def per_coin(E):
    rows = []
    for sym, g in E.groupby("sym"):
        closed = g[g.status == "closed"]
        op = g[g.status == "open"]
        rows.append({
            "sym": sym, "trades": len(g), "longs": int((g.side == "LONG").sum()), "shorts": int((g.side == "SHORT").sum()),
            "open_now": op.side.iloc[0] if len(op) else "",
            "days_held": float(g.hold_h.sum() / 24),
            "price_pnl": float(g.price_pnl.sum() + g.unrealized.sum()), "funding": float(g.funding.sum()),
            "fees": float(g.fees.sum()), "net": float(g.net.sum()),
            "win_rate": float((closed.net > 0).mean()) if len(closed) else None,
            "avg_hold_h": float(g.hold_h.mean()), "best": float(g.net.max()), "worst": float(g.net.min()),
            "worst_mae_pct": float(g.mae_pct.min()), "best_mfe_pct": float(g.mfe_pct.max()),
            "funding_events": int(g.funding_events.sum()),
            "avg_funding_rate_bps": _mean(g.avg_funding_rate_bps),
            "avg_entry_f7_bps": _mean(g.get("entry_f7_bps", pd.Series(dtype=float))),
            "avg_entry_atr14_pct": _mean(g.get("entry_atr14_pct", pd.Series(dtype=float))),
            "avg_entry_vol30_pct": _mean(g.get("entry_vol30_pct", pd.Series(dtype=float))),
            "avg_entry_rank": _mean(g.get("entry_rank_vol", pd.Series(dtype=float))),
        })
    return pd.DataFrame(rows).sort_values("net", ascending=False) if rows else pd.DataFrame()


def per_side(E):
    rows = []
    for side, g in E.groupby("side"):
        closed = g[g.status == "closed"]
        rows.append({"side": side, "trades": len(g), "open": int((g.status == "open").sum()),
                     "price_pnl": float(g.price_pnl.sum() + g.unrealized.sum()), "funding": float(g.funding.sum()),
                     "fees": float(g.fees.sum()), "net": float(g.net.sum()),
                     "win_rate": float((closed.net > 0).mean()) if len(closed) else None,
                     "avg_hold_h": float(g.hold_h.mean()), "avg_mae_pct": float(g.mae_pct.mean()),
                     "worst_mae_pct": float(g.mae_pct.min())})
    return pd.DataFrame(rows)


def daily(con, start_equity):
    eq = _df(con, "select ts, equity from equity order by ts")
    if eq.empty:
        return pd.DataFrame(), {}
    eq["day"] = pd.to_datetime(eq.ts, unit="ms", utc=True).dt.floor("D")
    last = eq.groupby("day").equity.last()
    prev = last.shift(1).fillna(start_equity)
    d = pd.DataFrame({"equity": last, "pnl": last - prev, "ret_pct": 100 * (last / prev - 1)})
    fu = _df(con, "select ts, payment from funding")
    tr = _df(con, "select ts, fee from trades")
    for name, df, col in (("funding", fu, "payment"), ("fees", tr, "fee")):
        if len(df):
            s = df.groupby(pd.to_datetime(df.ts, unit="ms", utc=True).dt.floor("D"))[col].sum()
            d[name] = s.reindex(d.index).fillna(0.0)
        else:
            d[name] = 0.0
    d["price_pnl"] = d.pnl - d.funding + d.fees
    r = d.ret_pct / 100
    curve = (1 + r).cumprod()
    summary = {"days": len(d), "total_return_pct": float(100 * (curve.iloc[-1] - 1)),
               "daily_mean_pct": float(d.ret_pct.mean()), "daily_std_pct": float(d.ret_pct.std()) if len(d) > 1 else None,
               "sharpe": float(r.mean() / r.std() * math.sqrt(365)) if len(d) > 2 and r.std() > 0 else None,
               "max_dd_pct": float(100 * (curve / curve.cummax() - 1).min()),
               "best_day_pct": float(d.ret_pct.max()), "worst_day_pct": float(d.ret_pct.min()),
               "win_days_pct": float(100 * (d.pnl > 0).mean())}
    # intraday drawdown from the minute equity rows (deeper than the daily closes)
    e = eq.equity
    summary["max_dd_intraday_pct"] = float(100 * (e / e.cummax() - 1).min())
    d.index = d.index.strftime("%Y-%m-%d")
    return d.reset_index(names="day"), summary


def compute(con, marks_now, start_equity, equity_now):
    E = episodes(con, marks_now)
    D, dsum = daily(con, start_equity)
    parts = {"price_pnl": float(E.price_pnl.sum() + E.unrealized.sum()) if len(E) else 0.0,
             "funding": float(E.funding.sum()) if len(E) else 0.0, "fees": float(E.fees.sum()) if len(E) else 0.0}
    parts["net"] = parts["price_pnl"] + parts["funding"] - parts["fees"]
    total_fund = float(con.execute("select coalesce(sum(payment),0) from funding").fetchone()[0])
    parts["equity_change"] = (equity_now - start_equity) if equity_now is not None else None
    parts["unattributed"] = (parts["equity_change"] - parts["net"]) if equity_now is not None else None
    parts["funding_not_in_a_trade"] = total_fund - parts["funding"]
    clean = lambda df: [] if df is None or len(df) == 0 else \
        [{k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in r.items()} for r in df.to_dict("records")]
    return {"totals": parts, "daily_summary": dsum, "backtest": BACKTEST,
            "sides": clean(per_side(E)) if len(E) else [], "coins": clean(per_coin(E)) if len(E) else [],
            "episodes": clean(E.sort_values("open_ts", ascending=False)) if len(E) else [], "daily": clean(D)}


if __name__ == "__main__":
    # self-check on a synthetic DB: long A (resized), short B flipped to long, funding on both
    import sqlite3
    con = sqlite3.connect(":memory:")
    con.executescript("""create table trades(ts int, sym text, qty real, price real, fee real);
                         create table funding(ts int, sym text, rate real, mark real, payment real);
                         create table equity(ts int, equity real, long_n real, short_n real);""")
    T = [(1, "A", 10, 10.0, 0.07), (2, "A", 5, 12.0, 0.042), (3, "A", -15, 11.0, 0.1155),   # long A: avg 10.667, sold 11
         (1, "B", -4, 25.0, 0.07), (2, "B", 6, 20.0, 0.084), (3, "B", -2, 22.0, 0.0308)]      # short B, flip long 2, close
    con.executemany("insert into trades values(?,?,?,?,?)", T)
    con.executemany("insert into funding values(?,?,?,?,?)", [(2, "A", 0.001, 11, -0.11), (2, "B", 0.001, 21, 0.084)])
    E = episodes(con)
    a = E[E.sym == "A"].iloc[0]
    assert abs(a.price_pnl - 15 * (11 - (10 * 10 + 5 * 12) / 15)) < 1e-9 and a.resizes == 1 and a.status == "closed"
    b = E[E.sym == "B"]
    assert len(b) == 2 and list(b.side) == ["SHORT", "LONG"]
    assert abs(b.iloc[0].price_pnl - 4 * (25 - 20)) < 1e-9 and abs(b.iloc[1].price_pnl - 2 * (22 - 20)) < 1e-9
    # everything adds up: price + funding - fees == cash change of the same trades and payments
    cash = -sum(q * p + f for _, _, q, p, f in T) + (-0.11 + 0.084)
    assert abs(E.net.sum() - cash) < 1e-9, (E.net.sum(), cash)
    print("stats selfcheck ok")
