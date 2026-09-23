"""Paper-trading fronttest of the funding-contrarian strategy (#7b), exactly as backtested.

Rule (unchanged from robust.py): daily at the UTC close, among the top-30 perps by 30d volume
(same candidate list as the backtest), long the 20% with the lowest 7-day funding, short the
20% with the highest; half the equity long, half short, equal weight. 7 bps/side on every
change; real funding paid/received at every settlement.

Signal logic is lab.universe + lab.xs_rank_weights on a live-built panel, so it cannot drift
from the backtest. Run:  python fronttest.py   -> http://127.0.0.1:8770   (env: FRONTTEST_DB, FRONTTEST_HOST, FRONTTEST_PORT)
"""
import json
import os
import sqlite3
import threading
import time
import traceback
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pandas as pd

import lab
from fetch_data import SYMBOLS

HERE = Path(__file__).resolve().parent
DB = Path(os.environ.get("FRONTTEST_DB", HERE / "fronttest.db"))
HOST = os.environ.get("FRONTTEST_HOST", "127.0.0.1")    # 0.0.0.0 on a server behind a firewall/proxy
PORT = int(os.environ.get("FRONTTEST_PORT", 8770))
START_EQUITY = 10_000.0
COST_BPS = 7.0
LOOKBACK, TOP_N, Q = 7, 30, 0.2
API = "https://fapi.binance.com"
lock = threading.RLock()


# ---------------- binance (keyless public REST) ----------------
def get(path, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    for i in range(4):
        try:
            with urllib.request.urlopen(f"{API}{path}?{q}", timeout=20) as r:
                return json.load(r)
        except Exception:
            if i == 3:
                raise
            time.sleep(2 * (i + 1))


def tradable_symbols():
    info = get("/fapi/v1/exchangeInfo")
    live = {s["symbol"] for s in info["symbols"] if s["status"] == "TRADING" and s["contractType"] == "PERPETUAL"}
    return [s for s in SYMBOLS if s in live]


def mark_prices():
    return {d["symbol"]: float(d["markPrice"]) for d in get("/fapi/v1/premiumIndex")}


def build_panel(syms, now_ms):
    close, qv, fund = {}, {}, {}
    start = now_ms - 12 * 86_400_000
    for s in syms:
        k = get("/fapi/v1/klines", symbol=s, interval="1d", limit=130)
        k = [r for r in k if r[6] < now_ms]                        # closed bars only
        idx = pd.to_datetime([r[0] for r in k], unit="ms", utc=True)
        close[s] = pd.Series([float(r[4]) for r in k], index=idx)
        qv[s] = pd.Series([float(r[7]) for r in k], index=idx)
        f = get("/fapi/v1/fundingRate", symbol=s, startTime=start, limit=1000)
        fs = pd.Series([float(r["fundingRate"]) for r in f],
                       index=pd.to_datetime([r["fundingTime"] for r in f], unit="ms", utc=True))
        fs = fs[fs.index < pd.Timestamp(now_ms, unit="ms", tz="UTC")]
        # same bucketing as lab.load: an event at 00:00:00.004 belongs to the day that just closed
        fs.index = fs.index.floor("min") - pd.Timedelta("1min")
        fund[s] = fs.resample("1D").sum() if len(fs) else pd.Series(dtype=float)
    P = {"close": pd.DataFrame(close).sort_index(), "qv": pd.DataFrame(qv).sort_index()}
    P["funding"] = pd.DataFrame(fund).reindex(index=P["close"].index, columns=P["close"].columns).fillna(0.0)
    return P


def compute_signal(now_ms):
    P = build_panel(tradable_symbols(), now_ms)
    U = lab.universe(P, top_n=TOP_N)
    f7 = P["funding"].rolling(LOOKBACK).mean()
    w = lab.xs_rank_weights(-f7, U, q=Q).iloc[-1]
    day = P["close"].index[-1]
    rows = []
    for s in P["close"].columns:
        if U[s].iloc[-1]:
            rows.append({"sym": s, "f7_bps_day": round(1e4 * f7[s].iloc[-1], 3), "weight": round(float(w[s]), 4)})
    rows.sort(key=lambda r: r["f7_bps_day"])
    return day, w[w != 0].to_dict(), rows


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
    create table if not exists signals(day text, ts int, sym text, f7_bps_day real, weight real);""")
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


def equity_of(st, px):
    return st["cash"] + sum(q * px[s] for s, q in st["pos"].items())


# ---------------- engine ----------------
def settle_funding(st):
    """Apply every funding event since each position was opened (long pays positive funding)."""
    for s, q in st["pos"].items():
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
    day, target_w, rows = compute_signal(t)
    with lock:
        st = state()
        settle_funding(st)                       # old positions collect the 00:00 settlement first
        px = mark_prices()
        eq = equity_of(st, px)
        fees = 0.0
        for s in sorted(set(st["pos"]) | set(target_w)):
            q_old = st["pos"].get(s, 0.0)
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
        CON.executemany("insert into signals values(?,?,?,?,?)",
                        [(str(day.date()), t, r["sym"], r["f7_bps_day"], r["weight"]) for r in rows])
        CON.execute("insert into rebalances values(?,?,?,?,?)", (t, str(day.date()), eq, fees, json.dumps(target_w)))
        CON.commit()
        snapshot(px)
    print(f"[{datetime.now(timezone.utc):%F %T}] rebalanced for {day.date()}: equity {eq:.2f}, fees {fees:.2f}", flush=True)


def snapshot(px=None):
    with lock:
        st = state()
        px = px or mark_prices()
        ln = sum(q * px[s] for s, q in st["pos"].items() if q > 0)
        sn = sum(q * px[s] for s, q in st["pos"].items() if q < 0)
        CON.execute("insert into equity values(?,?,?,?)", (now_ms(), equity_of(st, px), ln, sn))
        CON.commit()


def last_closed_day():
    return str((datetime.now(timezone.utc) - timedelta(days=1)).date())


def loop():
    with lock:
        if kv("started") is None:
            set_kv("started", now_ms())
        # everything needed to audit or move the run lives in the DB itself
        set_kv("rule", {"lookback_days": LOOKBACK, "top_n": TOP_N, "quantile": Q, "cost_bps": COST_BPS,
                        "start_equity": START_EQUITY, "candidates": SYMBOLS})
        if not CON.execute("select 1 from signals limit 1").fetchone() and kv("signal"):
            CON.executemany("insert into signals values(?,?,?,?,?)",      # backfill the pre-table rebalance
                            [(kv("last_day"), r[0], x["sym"], x["f7_bps_day"], x["weight"])
                             for r in CON.execute("select ts from rebalances order by ts desc limit 1") for x in kv("signal")])
        CON.commit()
    last_tick = 0
    while True:
        try:
            utc = datetime.now(timezone.utc)
            # daily bar closes 00:00 UTC; wait 5 min so klines + the 00:00 funding print are final
            with lock:
                due = kv("last_day") != last_closed_day()
            if due and (utc.hour > 0 or utc.minute >= 5):
                rebalance()
            if time.time() - last_tick >= 300:
                with lock:
                    st = state(); settle_funding(st); save(st); CON.commit()
                snapshot()
                last_tick = time.time()
        except Exception as e:
            with lock:
                CON.execute("insert into errors values(?,?)", (now_ms(), f"{e!r}"[:500])); CON.commit()
            traceback.print_exc()
        time.sleep(30)


# ---------------- API + UI ----------------
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
                "next_rebalance": int(nxt.timestamp() * 1000), "positions": pos, "signal": kv("signal", []),
                "curve": ser, "trades": q("select * from trades order by ts desc limit 200"),
                "funding": q("select * from funding order by ts desc limit 200"),
                "rebalances": q("select ts, day, equity, fees from rebalances order by ts desc limit 60"),
                "errors": q("select * from errors order by ts desc limit 20"),
                "rule": {"lookback_days": LOOKBACK, "top_n": TOP_N, "quantile": Q, "cost_bps": COST_BPS}}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/state"):
            body, ctype = json.dumps(api_state()).encode(), "application/json"
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
    mark_prices = lambda: dict(px)
    compute_signal = lambda t: (pd.Timestamp("2026-01-01", tz="UTC"), {"A": 0.5, "B": -0.5}, [])
    get = lambda path, **k: []                        # no funding events
    rebalance()
    st = state()
    fee1 = CON.execute("select sum(fee) from trades").fetchone()[0]
    assert abs(equity_of(st, px) - (START_EQUITY - fee1)) < 1e-9
    assert abs(fee1 - START_EQUITY * 1.0 * COST_BPS / 1e4) < 1e-9          # gross 1.0 traded once
    assert abs(st["pos"]["A"] * px["A"] - 0.5 * (START_EQUITY - 0)) < 1e-6
    px["A"], px["B"] = 11.0, 22.0                                            # both +10%: long/short cancel
    assert abs(equity_of(st, px) - equity_of(st, {"A": 10.0, "B": 20.0})) < 1e-6
    compute_signal = lambda t: (pd.Timestamp("2026-01-02", tz="UTC"), {"C": 0.5, "B": -0.5}, [])
    before = equity_of(state(), px)
    rebalance()
    st = state()
    fee2 = CON.execute("select sum(fee) from trades").fetchone()[0] - fee1
    assert abs(equity_of(st, px) - (before - fee2)) < 1e-9 and "A" not in st["pos"]
    # a short receives positive funding
    get = lambda path, **k: [{"fundingTime": now_ms() - 1, "fundingRate": "0.001", "markPrice": "22"}] if k["symbol"] == "B" else []
    st = state(); st["fund_from"]["B"] = 0; c0 = st["cash"]; settle_funding(st)
    got, want = st["cash"] - c0, -st["pos"]["B"] * 22 * 0.001
    assert want > 0 and abs(got - want) < 1e-9
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
    threading.Thread(target=loop, daemon=True).start()
    print(f"fronttest UI on http://{HOST}:{PORT}  db={DB}", flush=True)
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
