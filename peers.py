"""Price-only stat-arb inside peer groups (no funding in the signal; funding is still paid/received).

Peers: for every coin, its K most correlated coins over the trailing 90 days (refit every 7 days, top-100 universe).
Residual e = coin return - mean return of its peers. Rules fixed before the first run:
  REV L  : long the 20% with the lowest L-day residual, short the 20% highest (L = 1, 3, 7, 14)  - peers lag -> catch up
  MOM L  : the opposite on the L-day residual, skipping the last 7 days (L = 30, 60, 90)          - leaders keep leading
  hedged : same pick, but every coin is traded against its own peer basket (coin +w, each peer -w/K)
  plain  : same signals on raw returns, no peers (to see what the peers add)
All perps, point-in-time top-100, 7 bps/side, IS 2020-2023, OOS 2024-01..2026-08. -> results_peers.md
"""
import numpy as np
import pandas as pd

import lab

D = lab.D / "all"
SYMS = [l.strip() for l in open(D / "crypto_symbols.txt") if l.strip()]
IS, OOS = slice(None, lab.SPLIT - pd.Timedelta("1ns")), slice(lab.SPLIT, None)


def panel():
    """Same panel as alltest.panel (copied: importing alltest re-runs improve.py's whole study)."""
    P = {}
    for k, f in (("close", "close.parquet"), ("qv", "quote_volume.parquet"), ("funding", "funding_daily.parquet")):
        x = pd.read_parquet(D / f)
        P[k] = x.reindex(columns=[s for s in SYMS if s in x.columns])
    idx = P["close"].index
    idx = idx[(idx >= "2020-01-01") & (idx <= "2026-08-31")]
    for k in P:
        P[k] = P[k].reindex(index=idx, columns=P["close"].columns)
        if P[k].index.tz is None:
            P[k].index = P[k].index.tz_localize("UTC")
    P["funding"] = P["funding"].fillna(0.0)
    P["ret"] = P["close"].pct_change(fill_method=None)
    return P


def peer_matrices(R, U, k=5, window=90, every=7):
    """Per refit block: A[i, j] = 1 if j is one of i's k peers. Uses returns up to the refit day only."""
    blocks, A = [], None
    Rv, Uv = R.values, U.values
    for i in range(len(R)):
        if i >= window and (i - window) % every == 0:
            win = R.iloc[i - window + 1:i + 1]
            ok = [j for j in range(R.shape[1]) if Uv[i, j] and win.iloc[:, j].notna().sum() >= window * 0.8]
            A = np.zeros((R.shape[1], R.shape[1]))
            if len(ok) > k + 5:
                c = win.iloc[:, ok].corr().values
                np.fill_diagonal(c, -np.inf)
                c = np.nan_to_num(c, nan=-np.inf)
                for a, j in enumerate(ok):
                    A[j, [ok[b] for b in np.argsort(c[a])[-k:]]] = 1.0
        blocks.append(A)
    return blocks                                    # blocks[t] = peers known at close t


def peer_mean(R, blocks):
    """M[t, i] = mean return on day t of the peers chosen at close t-1 (no look-ahead into day t)."""
    R0, N = R.fillna(0.0).values, R.notna().values.astype(float)
    M = np.full(R.shape, np.nan)
    for t in range(1, len(R)):
        A = blocks[t - 1]
        if A is None or not A.any():
            continue
        cnt = N[t] @ A.T
        with np.errstate(invalid="ignore", divide="ignore"):
            M[t] = np.where(cnt > 0, (R0[t] @ A.T) / cnt, np.nan)
    return pd.DataFrame(M, index=R.index, columns=R.columns)


def hedge(v, blocks):
    """Trade every pick against its own peers: coin +v, each peer -v/k; then scale to gross 1."""
    W = v.values.copy()
    for t in range(len(v)):
        A = blocks[t]
        if A is not None and A.any() and np.abs(v.values[t]).sum() > 0:
            k = np.maximum(A.sum(axis=1), 1)
            W[t] = v.values[t] - (v.values[t] / k) @ A
    g = np.abs(W).sum(axis=1, keepdims=True)
    return pd.DataFrame(np.where(g > 0, W / np.where(g > 0, g, 1), 0.0), index=v.index, columns=v.columns)


def row(name, w, P):
    b = lab.backtest(w, P, 7.0)
    o = b.loc[OOS]
    sh = lambda x: round(lab.sharpe(x, 365), 2)
    return {"variant": name, "IS": sh(b.net.loc[IS]), "OOS": sh(o.net),
            "OOS@15bps": sh(lab.backtest(w, P, 15.0).net.loc[OOS]), "OOS +1d": sh(lab.backtest(w.shift(1).fillna(0), P, 7.0).net.loc[OOS]),
            "OOS %/yr": round(o.net.mean() * 36500, 1), "OOS price": round(o.gross.mean() * 36500, 1),
            "OOS funding": round(-o.fund.mean() * 36500, 1), "OOS cost": round(-o.cost.mean() * 36500, 1),
            "maxDD": round(lab.maxdd(b.net), 3), "net beta": round(float(w.sum(axis=1).mean()), 3)}


if __name__ == "__main__":
    P = panel()
    R = P["ret"]
    U = lab.universe(P, 100)
    blocks = peer_matrices(R, U)
    E = R - peer_mean(R, blocks)                                  # residual vs own peers, known at close t
    cs = lambda x, L: x.rolling(L, min_periods=L).sum()
    rows = []
    for L in (1, 3, 7, 14):
        rows.append(row(f"REV {L}d residual", lab.xs_rank_weights(-cs(E, L), U), P))
        rows.append(row(f"REV {L}d residual, hedged vs peers", hedge(lab.xs_rank_weights(-cs(E, L), U), blocks), P))
        rows.append(row(f"REV {L}d plain return (no peers)", lab.xs_rank_weights(-cs(R, L), U), P))
        print("REV", L, flush=True)
    for L in (30, 60, 90):
        rows.append(row(f"MOM {L}d residual skip 7", lab.xs_rank_weights(cs(E, L - 7).shift(7), U), P))
        rows.append(row(f"MOM {L}d residual skip 7, hedged", hedge(lab.xs_rank_weights(cs(E, L - 7).shift(7), U), blocks), P))
        rows.append(row(f"MOM {L}d plain skip 7 (no peers)", lab.xs_rank_weights(cs(R, L - 7).shift(7), U), P))
        print("MOM", L, flush=True)
    F7 = P["funding"].rolling(7).mean()
    rows.append(row("reference: live funding rule (top-100 base)", lab.xs_rank_weights(-F7, U), P))
    T = pd.DataFrame(rows)
    open(lab.D.parent / "results_peers.md", "w").write(
        "# Price-only stat-arb inside peer groups\n\nPeers = 5 most correlated coins (90d, refit weekly). "
        "Top-100, all perps, 7 bps/side, real funding paid/received. IS 2020-23, OOS 2024-01..2026-08. "
        "Columns in %/yr are OOS.\n\n" + T.to_markdown(index=False) + "\n")
    print(T.to_string(index=False))
