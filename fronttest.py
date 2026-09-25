"""Paper-trading fronttest of the funding-contrarian strategy (#7b), exactly as backtested.

Rule (alltest.py "top-100 base"): daily at the UTC close, among ALL Binance USDT-M crypto perps
(underlyingType COIN, status TRADING), take the top-100 by 30d average quote volume (>= 60 days listed);
long the 20% with the lowest 7-day funding, short the 20% with the highest; half the equity long, half short,
equal weight. A coin that leaves the top-100 is closed at the next rebalance. 7 bps/side on every change;
real funding paid/received at every settlement. BTC ATR and trend filters are logged in shadow mode only.

Signal logic is lab.universe + lab.xs_rank_weights on a live-built panel, so it cannot drift
from the backtest. Run:  python fronttest.py   -> http://127.0.0.1:8770   (env: FRONTTEST_DB, FRONTTEST_HOST, FRONTTEST_PORT)
"""
import json
import os
import sqlite3
import threading
import time
import traceback
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pandas as pd
from websockets.sync.client import connect as ws_connect

import lab
import stats

HERE = Path(__file__).resolve().parent
DB = Path(os.environ.get("FRONTTEST_DB", HERE / "fronttest.db"))
HOST = os.environ.get("FRONTTEST_HOST", "127.0.0.1")    # 0.0.0.0 on a server behind a firewall/proxy
PORT = int(os.environ.get("FRONTTEST_PORT", 8770))
START_EQUITY = 1_000.0
COST_BPS = 7.0
SNAP_S = 60                  # equity row in the DB every minute (prices themselves are live, every 3 s)
MARK_S = 900                 # mark of every held coin every 15 min -> worst/best move per trade (stats page)
LOOKBACK, TOP_N, Q = 7, 100, 0.2
ATR_OFF_BELOW = 1 / 3        # SHADOW: BTC ATR% in the low third of its last year (hurt on the full universe, alltest.py)
TREND_OFF_ABOVE = 2 / 3      # SHADOW: logged only; BTC close/SMA200 in the top third of its last year
API = "https://fapi.binance.com"
WS_URL = "wss://fstream.binance.com/market/ws/!markPrice@arr"   # all perps, mark + next funding time, every 3 s
# (the old /ws/ path still accepts the connection but sends nothing; hence the recv timeout below)
lock = threading.RLock()
# live cache fed by the websocket (plain dict writes are atomic under the GIL)
PX, NEXT_T, DUE = {}, {}, {}            # mark price; next funding time; symbol -> settlement time just passed
IDX, RATE = {}, {}                      # spot index price; predicted funding rate of the running interval
WS = {"ts": 0.0, "reconnects": 0, "sweep": True}
REST = {"calls": [], "ip_weight_1m": None}   # our REST call times + last IP-wide weight Binance reported


# ---------------- binance (keyless public REST) ----------------
def get(path, **params):
    q = urllib.parse.urlencode(params)          # some symbols are non-ASCII (e.g. Chinese names)
    for i in range(4):
        try:
            with urllib.request.urlopen(f"{API}{path}?{q}", timeout=20) as r:
                REST["calls"] = [t for t in REST["calls"] if t > time.time() - 3600] + [time.time()]
                REST["ip_weight_1m"] = r.headers.get("X-MBX-USED-WEIGHT-1M", REST["ip_weight_1m"])
                return json.load(r)
        except Exception:
            if i == 3:
                raise
            time.sleep(2 * (i + 1))


def tradable_symbols():
    """Every live USDT-M crypto perp (stocks, commodities, pre-market and index perps excluded)."""
    info = get("/fapi/v1/exchangeInfo")
    return sorted(s["symbol"] for s in info["symbols"]
                  if s["status"] == "TRADING" and s["contractType"] == "PERPETUAL"
                  and s["quoteAsset"] == "USDT" and s.get("underlyingType") == "COIN")


def mark_prices():
    """Websocket cache; REST (weight 10) only while the stream is down."""
    if time.time() - WS["ts"] < 60 and PX:
        return dict(PX)
    return {d["symbol"]: float(d["markPrice"]) for d in get("/fapi/v1/premiumIndex")}


def on_mark(items):
    """One !markPrice@arr frame. When a symbol's next funding time moves forward, a settlement just happened."""
    for d in items:
        sym, t_next = d["s"], int(d["T"])
        PX[sym] = float(d["p"])
        if d.get("i"):
            IDX[sym] = float(d["i"])
        if d.get("r") not in (None, ""):
            RATE[sym] = float(d["r"])
        prev = NEXT_T.get(sym)
        if prev and t_next > prev:
            DUE[sym] = prev
        NEXT_T[sym] = t_next
    WS["ts"] = time.time()


def ws_loop():
    while True:
        try:
            with ws_connect(WS_URL, open_timeout=20, max_size=2 ** 22) as ws:
                WS["sweep"] = True            # book anything settled while we were disconnected
                while True:
                    on_mark(json.loads(ws.recv(timeout=30)))   # silent stream -> TimeoutError -> reconnect
        except Exception as e:
            print(f"websocket dropped: {e!r}; reconnecting", flush=True)
        WS["reconnects"] += 1
        time.sleep(5)


def build_panel(syms, now_ms):
    """Daily closes + volume for every candidate (limit 99 -> weight 1 each, ~650 weight once a day),
    then funding only for the coins that made the top-N (fundingRate has its own 500/5min limit)."""
    close, qv, fund, high, low = {}, {}, {}, {}, {}
    start = now_ms - 12 * 86_400_000
    for s in syms:
        k = get("/fapi/v1/klines", symbol=s, interval="1d", limit=99, endTime=now_ms - 1)
        k = [r for r in k if r[6] < now_ms]                        # closed bars only
        if not k:
            continue
        idx = pd.to_datetime([r[0] for r in k], unit="ms", utc=True)
        close[s] = pd.Series([float(r[4]) for r in k], index=idx)
        qv[s] = pd.Series([float(r[7]) for r in k], index=idx)
        high[s] = pd.Series([float(r[2]) for r in k], index=idx)
        low[s] = pd.Series([float(r[3]) for r in k], index=idx)
        time.sleep(0.05)                                           # spread the weight: ~2-3 min per day
    P = {"close": pd.DataFrame(close).sort_index(), "qv": pd.DataFrame(qv).sort_index(),
         "high": pd.DataFrame(high).sort_index(), "low": pd.DataFrame(low).sort_index()}
    U = lab.universe(P, top_n=TOP_N)
    for s in [c for c in P["close"].columns if U[c].iloc[-1]]:
        f = get("/fapi/v1/fundingRate", symbol=s, startTime=start, endTime=now_ms - 1, limit=1000)
        fs = pd.Series([float(r["fundingRate"]) for r in f],
                       index=pd.to_datetime([r["fundingTime"] for r in f], unit="ms", utc=True))
        fs = fs[fs.index < pd.Timestamp(now_ms, unit="ms", tz="UTC")]
        # same bucketing as lab.load: an event at 00:00:00.004 belongs to the day that just closed
        fs.index = fs.index.floor("min") - pd.Timedelta("1min")
        fund[s] = fs.resample("1D").sum() if len(fs) else pd.Series(dtype=float)
    P["funding"] = pd.DataFrame(fund).reindex(index=P["close"].index, columns=P["close"].columns).fillna(0.0)
    return P


def market_filter(now_ms):
    """BTC regime at the last closed day, same math as regime.py (lab.atr_pct / lab.pct_rank)."""
    k = [r for r in get("/fapi/v1/klines", symbol="BTCUSDT", interval="1d", limit=1000) if r[6] < now_ms]
    idx = pd.to_datetime([r[0] for r in k], unit="ms", utc=True)
    h, l, c = (pd.Series([float(r[i]) for r in k], index=idx) for i in (2, 3, 4))
    atr_p = lab.pct_rank(lab.atr_pct(h, l, c)).iloc[-1]
    trend_p = lab.pct_rank(c / c.rolling(200).mean()).iloc[-1]
    return {"day": str(idx[-1].date()), "btc_atr_pct": round(float(atr_p), 4), "btc_trend_pct": round(float(trend_p), 4),
            "atr_on": bool(not atr_p < ATR_OFF_BELOW), "trend_on_shadow": bool(not trend_p >= TREND_OFF_ABOVE)}


def compute_signal(now_ms):
    P = build_panel(tradable_symbols(), now_ms)
    U = lab.universe(P, top_n=TOP_N)
    f7 = P["funding"].rolling(LOOKBACK).mean()
    w = lab.xs_rank_weights(-f7, U, q=Q).iloc[-1]
    day = P["close"].index[-1]
    # market state of every top-N coin at this close, for the stats page (all from the klines already fetched)
    C = P["close"]
    atr = lab.atr_pct(P["high"], P["low"], C).iloc[-1]
    vol30 = C.pct_change(fill_method=None).rolling(30, min_periods=15).std().iloc[-1] * np.sqrt(365)
    adv = P["qv"].rolling(30, min_periods=15).mean().iloc[-1]
    rank = adv.where(U.iloc[-1]).rank(ascending=False)
    r1, r7 = C.iloc[-1] / C.iloc[-2] - 1, C.iloc[-1] / C.iloc[-8] - 1
    fin = lambda v, k=1.0, n=4: None if not np.isfinite(v) else round(float(v) * k, n)
    rows = []
    for s in P["close"].columns:
        if U[s].iloc[-1]:
            rows.append({"sym": s, "f7_bps_day": round(1e4 * f7[s].iloc[-1], 3), "weight": round(float(w[s]), 4),
                         "rank_vol": fin(rank[s], 1, 0), "adv30_musd": fin(adv[s], 1e-6, 2), "close": fin(C[s].iloc[-1], 1, 10),
                         "atr14_pct": fin(atr[s], 100, 3), "vol30_pct": fin(vol30[s], 100, 2),
                         "ret1d_pct": fin(r1[s], 100, 3), "ret7d_pct": fin(r7[s], 100, 3)})
    rows.sort(key=lambda r: r["f7_bps_day"])
    filt = market_filter(now_ms)                                    # shadow only: logged, never gates trades
    return day, w[w != 0].to_dict(), rows, filt


# ---------------- storage ----------------
def db():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.executescript("""
    create table if not exists kv(k text primary key, v text);
    create table if not exists trades(ts int, sym text, qty real, price real, fee real);
    create table if not exists funding(ts int, sym text, rate real, mark real, payment real);
    create table if not exists equity(ts int, equity real, long_n real, short_n real);
    create table if not exists rebalances(ts int, day text, equity real, fees real, signal text);
    create table if not exists errors(ts int, msg text);
    create table if not exists signals(day text, ts int, sym text, f7_bps_day real, weight real);
    create table if not exists filters(day text, ts int, btc_atr_pct real, btc_trend_pct real,
                                       atr_on int, trend_on_shadow int);
    create table if not exists features(day text, ts int, sym text, rank_vol real, adv30_musd real, close real,
                                        atr14_pct real, vol30_pct real, ret1d_pct real, ret7d_pct real, f7_bps real,
                                        weight real, mark real, pred_funding_bps real, basis_bps real);
    create table if not exists marks(ts int, sym text, mark real);
    create index if not exists marks_sym_ts on marks(sym, ts);""")
    return c


CON = db()


def kv(k, default=None):
    r = CON.execute("select v from kv where k=?", (k,)).fetchone()
    return json.loads(r[0]) if r else default


def set_kv(k, v):
    CON.execute("insert or replace into kv values(?,?)", (k, json.dumps(v)))


def state():
    return {"cash": kv("cash", START_EQUITY), "pos": kv("pos", {}), "entry": kv("entry", {}),
            "fund_from": kv("fund_from", {}), "opened": kv("opened", {})}


def save(st):
    for k in ("cash", "pos", "entry", "fund_from", "opened"):
        set_kv(k, st[k])


def now_ms():
    return int(time.time() * 1000)


def px_of(st, px, s):
    return px.get(s) or PX.get(s) or st["entry"].get(s, 0.0)     # delisted coin: last known price


def equity_of(st, px):
    return st["cash"] + sum(q * px_of(st, px, s) for s, q in st["pos"].items())


# ---------------- engine ----------------
def settle_funding(st, syms=None):
    """Apply every funding event since each position was opened (long pays positive funding).
    Uses /fapi/v1/fundingRate, which has its own 500/5min limit, not the 2400/min weight pool."""
    for s, q in st["pos"].items():
        if syms is not None and s not in syms:
            continue
        since = st["fund_from"].get(s, now_ms())
        ev = get("/fapi/v1/fundingRate", symbol=s, startTime=since + 1, limit=1000)
        for e in ev:
            t, rate, mark = int(e["fundingTime"]), float(e["fundingRate"]), float(e["markPrice"] or 0)
            if t > now_ms() or mark <= 0:
                continue
            pay = -q * mark * rate
            st["cash"] += pay
            CON.execute("insert into funding values(?,?,?,?,?)", (t, s, rate, mark, pay))
            st["fund_from"][s] = t


def rebalance():
    t = now_ms()
    day, target_w, rows, filt = compute_signal(t)
    with lock:
        st = state()
        settle_funding(st)                       # old positions collect the 00:00 settlement first
        px = mark_prices()
        eq = equity_of(st, px)
        fees = 0.0
        for s in sorted(set(st["pos"]) | set(target_w)):
            q_old = st["pos"].get(s, 0.0)
            if s not in px:                        # delisted/removed while held: close at the last known price
                px[s] = PX.get(s, st["entry"].get(s, 1.0))
            q_new = target_w.get(s, 0.0) * eq / px[s]
            d = q_new - q_old
            if abs(d * px[s]) < 1e-6:
                continue
            fee = abs(d) * px[s] * COST_BPS / 1e4
            st["cash"] -= d * px[s] + fee
            fees += fee
            CON.execute("insert into trades values(?,?,?,?,?)", (t, s, d, px[s], fee))
            if abs(q_new) * px[s] < 1e-6:
                for m in ("pos", "entry", "fund_from", "opened"):
                    st[m].pop(s, None)
                continue
            if q_old == 0 or np.sign(q_old) != np.sign(q_new):
                st["entry"][s] = px[s]; st["fund_from"][s] = t; st["opened"][s] = t
            elif abs(q_new) > abs(q_old):        # added on the same side: average in
                st["entry"][s] = (st["entry"][s] * abs(q_old) + px[s] * abs(d)) / abs(q_new)
            st["pos"][s] = q_new
        save(st)
        set_kv("last_day", str(day.date()))
        set_kv("signal", rows)
        set_kv("filter", filt)
        CON.execute("insert into filters values(?,?,?,?,?,?)", (filt["day"], t, filt["btc_atr_pct"], filt["btc_trend_pct"],
                                                                 int(filt["atr_on"]), int(filt["trend_on_shadow"])))
        CON.executemany("insert into signals values(?,?,?,?,?)",
                        [(str(day.date()), t, r["sym"], r["f7_bps_day"], r["weight"]) for r in rows])
        CON.execute("insert into rebalances values(?,?,?,?,?)", (t, str(day.date()), eq, fees, json.dumps(target_w)))
        # market state at the moment of the trades: mark, predicted funding, basis vs spot index (websocket, 0 weight)
        basis = lambda s: (1e4 * (PX[s] / IDX[s] - 1)) if s in PX and IDX.get(s) else None
        CON.executemany("insert into features values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        [(str(day.date()), t, r["sym"], r["rank_vol"], r["adv30_musd"], r["close"], r["atr14_pct"],
                          r["vol30_pct"], r["ret1d_pct"], r["ret7d_pct"], r["f7_bps_day"], r["weight"], PX.get(r["sym"]),
                          1e4 * RATE[r["sym"]] if r["sym"] in RATE else None, basis(r["sym"])) for r in rows])
        CON.commit()
        snapshot(px)
    print(f"[{datetime.now(timezone.utc):%F %T}] rebalanced for {day.date()}: equity {eq:.2f}, fees {fees:.2f}", flush=True)


def snapshot(px=None):
    with lock:
        st = state()
        px = px or mark_prices()
        ln = sum(q * px_of(st, px, s) for s, q in st["pos"].items() if q > 0)
        sn = sum(q * px_of(st, px, s) for s, q in st["pos"].items() if q < 0)
        CON.execute("insert into equity values(?,?,?,?)", (now_ms(), equity_of(st, px), ln, sn))
        CON.commit()


def last_closed_day():
    return str((datetime.now(timezone.utc) - timedelta(days=1)).date())


def loop():
    with lock:
        if kv("started") is None:
            set_kv("started", now_ms())
            # fresh DB: never trade mid-day on a stale signal; the first rebalance is the next 00:05 UTC
            set_kv("last_day", last_closed_day())
        # everything needed to audit or move the run lives in the DB itself
        set_kv("rule", {"lookback_days": LOOKBACK, "top_n": TOP_N, "quantile": Q, "cost_bps": COST_BPS,
                        "start_equity": START_EQUITY, "candidates": "all USDT-M perps with underlyingType COIN",
                        "atr_filter_shadow": {"off_below_pct": ATR_OFF_BELOW, "window_days": 365, "atr_n": 14},
                        "trend_filter_shadow": {"off_above_pct": TREND_OFF_ABOVE, "sma": 200, "window_days": 365}})
        if not CON.execute("select 1 from signals limit 1").fetchone() and kv("signal"):
            CON.executemany("insert into signals values(?,?,?,?,?)",      # backfill the pre-table rebalance
                            [(kv("last_day"), r[0], x["sym"], x["f7_bps_day"], x["weight"])
                             for r in CON.execute("select ts from rebalances order by ts desc limit 1") for x in kv("signal")])
        CON.commit()
    last_snap = last_mark = 0
    while True:
        try:
            utc = datetime.now(timezone.utc)
            # daily bar closes 00:00 UTC; wait 5 min so klines + the 00:00 funding print are final
            with lock:
                due = kv("last_day") != last_closed_day()
            if due and (utc.hour > 0 or utc.minute >= 5):
                rebalance()
            # funding: one REST call per held symbol, only right after the websocket saw it settle
            ready = {s for s, t in list(DUE.items()) if now_ms() - t > 60_000}
            if ready or WS["sweep"]:
                with lock:
                    st = state()
                    settle_funding(st, None if WS["sweep"] else ready)
                    save(st); CON.commit()
                WS["sweep"] = False
                for s in ready:           # keep retrying each loop until Binance has published the record
                    if s not in st["pos"] or st["fund_from"].get(s, 0) >= DUE[s] - 1000 or now_ms() - DUE[s] > 3_600_000:
                        DUE.pop(s, None)
            if time.time() - last_snap >= SNAP_S:
                snapshot()
                last_snap = time.time()
            if time.time() - last_mark >= MARK_S and WS["ts"]:
                with lock:
                    held = list(state()["pos"])
                    CON.executemany("insert into marks values(?,?,?)", [(now_ms(), s, PX[s]) for s in held if s in PX])
                    CON.commit()
                last_mark = time.time()
        except Exception as e:
            with lock:
                CON.execute("insert into errors values(?,?)", (now_ms(), f"{e!r}"[:500])); CON.commit()
            traceback.print_exc()
        time.sleep(5)


# ---------------- API + UI ----------------
STATS_CACHE = {"t": 0.0, "out": None}


def api_stats():
    """Read-only connection and no trading lock during the heavy part; cached 60 s for many tabs."""
    if STATS_CACHE["out"] is not None and time.time() - STATS_CACHE["t"] < 60:
        return STATS_CACHE["out"]
    with lock:
        st = state()
        px = dict(PX) if PX else {}
        eq = equity_of(st, px) if px else None
        started = kv("started")
    ro = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        out = stats.compute(ro, px, START_EQUITY, eq)
    finally:
        ro.close()
    out.update({"now": now_ms(), "started": started, "start_equity": START_EQUITY, "equity": eq})
    STATS_CACHE.update(t=time.time(), out=out)
    return out


def api_state():
    with lock:
        st = state()
        try:
            px = mark_prices()
        except Exception:
            px = {}
        pos = []
        for s, q in sorted(st["pos"].items(), key=lambda x: -x[1]):
            p = px.get(s, st["entry"][s])
            f = CON.execute("select coalesce(sum(payment),0) from funding where sym=? and ts>=?",
                            (s, st["opened"].get(s, 0))).fetchone()[0]
            pos.append({"sym": s, "side": "LONG" if q > 0 else "SHORT", "qty": q, "entry": st["entry"][s], "mark": p,
                        "notional": q * p, "upnl": q * (p - st["entry"][s]), "funding": f})
        eq = equity_of(st, px) if px else None
        ser = CON.execute("select ts, equity from equity order by ts").fetchall()
        q = lambda sql: [dict(zip([d[0] for d in c.description], r)) for c in [CON.execute(sql)] for r in c.fetchall()]
        tot = CON.execute("select coalesce(sum(fee),0) from trades").fetchone()[0]
        fnd = CON.execute("select coalesce(sum(payment),0) from funding").fetchone()[0]
        nxt = datetime.now(timezone.utc).replace(hour=0, minute=5, second=0, microsecond=0) + timedelta(days=1)
        return {"now": now_ms(), "started": kv("started"), "start_equity": START_EQUITY, "equity": eq,
                "cash": st["cash"], "fees_total": tot, "funding_total": fnd, "last_day": kv("last_day"),
                "next_rebalance": int(nxt.timestamp() * 1000), "positions": pos, "signal": kv("signal", []), "filter": kv("filter"),
                "curve": ser, "trades": q("select * from trades order by ts desc limit 200"),
                "funding": q("select * from funding order by ts desc limit 200"),
                "rebalances": q("select ts, day, equity, fees from rebalances order by ts desc limit 60"),
                "errors": q("select * from errors order by ts desc limit 20"),
                "feed": {"ws_age_s": round(time.time() - WS["ts"], 1) if WS["ts"] else None,
                         "ws_reconnects": WS["reconnects"], "rest_calls_1h": len(REST["calls"]),
                         "ip_weight_1m": REST["ip_weight_1m"]},
                "rule": {"lookback_days": LOOKBACK, "top_n": TOP_N, "quantile": Q, "cost_bps": COST_BPS},
                "filter_history": q("select day, btc_atr_pct, btc_trend_pct, atr_on, trend_on_shadow from filters order by ts desc limit 60")}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/state"):
            body, ctype = json.dumps(api_state()).encode(), "application/json"
        elif self.path.startswith("/api/stats"):
            body, ctype = json.dumps(api_stats(), default=float).encode(), "application/json"
        elif self.path in ("/stats", "/stats.html"):
            body, ctype = (HERE / "stats.html").read_bytes(), "text/html; charset=utf-8"
        elif self.path in ("/", "/index.html"):
            body, ctype = (HERE / "fronttest.html").read_bytes(), "text/html; charset=utf-8"
        else:
            self.send_error(404); return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def selfcheck():
    """Fake prices + fake signal: a rebalance must move equity by exactly -fees; funding sign must be right."""
    global CON, DB, compute_signal, mark_prices, get
    import tempfile
    DB = Path(tempfile.mkdtemp()) / "t.db"
    CON = db()
    px = {"A": 10.0, "B": 20.0, "C": 5.0}
    FAKE_F = {"day": "x", "btc_atr_pct": 0.5, "btc_trend_pct": 0.5, "atr_on": True, "trend_on_shadow": True}
    mark_prices = lambda: dict(px)
    compute_signal = lambda t: (pd.Timestamp("2026-01-01", tz="UTC"), {"A": 0.5, "B": -0.5}, [], FAKE_F)
    get = lambda path, **k: []                        # no funding events
    rebalance()
    st = state()
    fee1 = CON.execute("select sum(fee) from trades").fetchone()[0]
    assert abs(equity_of(st, px) - (START_EQUITY - fee1)) < 1e-9
    assert abs(fee1 - START_EQUITY * 1.0 * COST_BPS / 1e4) < 1e-9          # gross 1.0 traded once
    assert abs(st["pos"]["A"] * px["A"] - 0.5 * (START_EQUITY - 0)) < 1e-6
    px["A"], px["B"] = 11.0, 22.0                                            # both +10%: long/short cancel
    assert abs(equity_of(st, px) - equity_of(st, {"A": 10.0, "B": 20.0})) < 1e-6
    compute_signal = lambda t: (pd.Timestamp("2026-01-02", tz="UTC"), {"C": 0.5, "B": -0.5}, [], FAKE_F)
    before = equity_of(state(), px)
    rebalance()
    st = state()
    fee2 = CON.execute("select sum(fee) from trades").fetchone()[0] - fee1
    assert abs(equity_of(st, px) - (before - fee2)) < 1e-9 and "A" not in st["pos"]
    # ATR filter off -> empty target -> everything closed, equity moves only by fees
    compute_signal = lambda t: (pd.Timestamp("2026-01-03", tz="UTC"), {}, [], dict(FAKE_F, atr_on=False))
    before = equity_of(state(), px); f0 = CON.execute("select sum(fee) from trades").fetchone()[0]
    rebalance(); st = state()
    assert not st["pos"] and abs(st["cash"] - (before - (CON.execute("select sum(fee) from trades").fetchone()[0] - f0))) < 1e-9
    compute_signal = lambda t: (pd.Timestamp("2026-01-04", tz="UTC"), {"C": 0.5, "B": -0.5}, [], FAKE_F)
    rebalance(); st = state()
    # a short receives positive funding
    get = lambda path, **k: [{"fundingTime": now_ms() - 1, "fundingRate": "0.001", "markPrice": "22"}] if k["symbol"] == "B" else []
    st = state(); st["fund_from"]["B"] = 0; c0 = st["cash"]; settle_funding(st)
    got, want = st["cash"] - c0, -st["pos"]["B"] * 22 * 0.001
    assert want > 0 and abs(got - want) < 1e-9
    on_mark([{"s": "B", "p": "22", "T": 1000}]); assert "B" not in DUE
    on_mark([{"s": "B", "p": "23", "T": 1000}]); assert "B" not in DUE and PX["B"] == 23.0
    on_mark([{"s": "B", "p": "23", "T": 2000}]); assert DUE["B"] == 1000          # rolled -> settlement at 1000
    print("fronttest selfcheck ok")


if __name__ == "__main__":
    import sys
    if "--selfcheck" in sys.argv:
        selfcheck(); raise SystemExit
    if "--backup" in sys.argv:                         # consistent copy even while the fronttest is running
        dst = sys.argv[sys.argv.index("--backup") + 1]
        with sqlite3.connect(dst) as out:
            CON.backup(out)
        print("backed up to", dst); raise SystemExit
    threading.Thread(target=ws_loop, daemon=True).start()
    threading.Thread(target=loop, daemon=True).start()
    print(f"fronttest UI on http://{HOST}:{PORT}  db={DB}", flush=True)
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
