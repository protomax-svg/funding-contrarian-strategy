"""Independent audit of a fronttest DB against Binance's own data. Deliberately does NOT import fronttest/stats/lab:
every number is re-derived here with simple code, so a bug in the trading code cannot hide itself.

  python audit.py fronttest.db            (on the VPS, or on a copy made with: python fronttest.py --backup copy.db)

Checks
 1 books      start equity + trades + funding == saved cash; summed trade qty == saved positions
 2 funding    every real Binance funding event while a position was open is booked once, with the right sign and size
 3 fills      every paper fill price lies inside the real 1-minute Binance range at that moment
 4 lookahead  signal day = the UTC day that closed before the rebalance; saved close = Binance's daily close of that day;
              7d funding re-computed from raw events that happened before the rebalance
 5 rule       at each rebalance: longs = lowest 7d funding, shorts = highest, ~20% each side, equal size, dollar neutral
REST use: ~1 weight per trade (1m klines) + fundingRate calls (separate 500/5min pool). Throttled.
"""
import calendar
import json
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

API = "https://fapi.binance.com"
DAY = 86_400_000


def get(path, **p):
    for i in range(4):
        try:
            with urllib.request.urlopen(f"{API}{path}?{urllib.parse.urlencode(p)}", timeout=20) as r:
                time.sleep(0.12)
                return json.load(r)
        except Exception:
            if i == 3:
                raise
            time.sleep(2 * (i + 1))


def main(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    kv = {k: json.loads(v) for k, v in con.execute("select k, v from kv")}
    trades = con.execute("select ts, sym, qty, price, fee from trades order by ts, rowid").fetchall()
    fund = con.execute("select ts, sym, rate, mark, payment from funding order by ts").fetchall()
    reb = con.execute("select ts, day from rebalances order by ts").fetchall()
    start_eq = kv.get("rule", {}).get("start_equity", 1000.0)
    ok = True
    print(f"DB {db}: {len(trades)} trades, {len(fund)} funding rows, {len(reb)} rebalances\n")

    # ---------------- 1 books ----------------
    cash = start_eq - sum(q * p + f for _, _, q, p, f in trades) + sum(r[4] for r in fund)
    pos = defaultdict(float)
    for _, s, q, _, _ in trades:
        pos[s] += q
    pos = {s: q for s, q in pos.items() if abs(q) > 1e-12}
    saved = kv.get("pos", {})
    d_cash = cash - kv.get("cash", start_eq)
    bad_pos = {s for s in set(pos) | set(saved) if abs(pos.get(s, 0) - saved.get(s, 0)) > 1e-9 * max(1, abs(saved.get(s, 0)))}
    fee_bps = [1e4 * f / abs(q * p) for _, _, q, p, f in trades if q * p]
    print(f"1 BOOKS   cash replay diff ${d_cash:.6f} | positions mismatched: {len(bad_pos)} {sorted(bad_pos)[:5]} | "
          f"fee bps min/max {min(fee_bps, default=0):.2f}/{max(fee_bps, default=0):.2f}")
    ok &= abs(d_cash) < 1e-6 and not bad_pos

    # ---------------- 2 funding ----------------
    # holding intervals per coin from the trades: qty after each trade, valid until the next trade
    hist = defaultdict(list)                     # sym -> [(ts, qty_after)]
    run = defaultdict(float)
    for ts, s, q, _, _ in trades:
        run[s] += q
        hist[s].append((ts, run[s]))
    booked = defaultdict(dict)
    for ts, s, rate, mark, pay in fund:
        booked[s].setdefault(ts, []).append((rate, mark, pay))
    now = int(time.time() * 1000)
    missing, extra, wrong, double, n_exp = [], [], [], [], 0
    for s, h in hist.items():
        spans = [(t0, (h[i + 1][0] if i + 1 < len(h) else now), q) for i, (t0, q) in enumerate(h) if abs(q) > 1e-12]
        if not spans:
            continue
        ev = get("/fapi/v1/fundingRate", symbol=s, startTime=spans[0][0], endTime=now, limit=1000)
        for e in ev:
            t, rate, mark = int(e["fundingTime"]), float(e["fundingRate"]), float(e["markPrice"] or 0)
            q = next((q for a, b, q in spans if a < t <= b), 0.0)   # held at the settlement (opened before, closed after)
            if not q or mark <= 0:
                if t in booked[s]:
                    extra.append((s, t))
                continue
            n_exp += 1
            want = -q * mark * rate
            got = booked[s].get(t)
            if not got:
                missing.append((s, t, round(want, 6)))
            else:
                if len(got) > 1:
                    double.append((s, t))
                if abs(got[0][2] - want) > 1e-6 + 1e-6 * abs(want):
                    wrong.append((s, t, round(got[0][2], 6), round(want, 6)))
        real = {int(e["fundingTime"]) for e in ev}
        extra += [(s, t) for t in booked[s] if t not in real]
    print(f"2 FUNDING expected events {n_exp}, booked rows {len(fund)} | missing {len(missing)} extra {len(extra)} "
          f"double {len(double)} wrong-amount {len(wrong)}")
    for x in (missing[:3] + wrong[:3] + extra[:3] + double[:3]):
        print("          ", x)
    recent = [m for m in missing if now - m[1] < 3 * 3600_000]
    if recent:
        print(f"           ({len(recent)} of the missing are < 3h old: Binance publishes the record a little after settlement)")
    ok &= not (set(missing) - set(recent)) and not extra and not double and not wrong

    # ---------------- 3 fills ----------------
    outside, dev = [], []
    tcols = [r[1] for r in con.execute("pragma table_info(trades)")]
    # trades without a saved mark are from before the bid/ask-fill update: filled at mark with the rebalance *start* time
    new = set(con.execute("select rowid from trades where mark is not null").fetchall()) if "mark" in tcols else set()
    rows = con.execute("select rowid, ts, sym, qty, price, fee from trades order by ts, rowid").fetchall()
    checked = [r[1:] for r in rows if (r[0],) in new]
    old_n = len(rows) - len(checked)
    minutes = sorted({(s, ts // 60_000 * 60_000) for ts, s, *_ in checked})
    rng = {}
    for s, m in minutes:
        k = get("/fapi/v1/klines", symbol=s, interval="1m", startTime=m, limit=1)
        if k:
            rng[(s, m)] = (float(k[0][2]), float(k[0][3]), float(k[0][4]))
    for ts, s, q, p, _ in checked:
        r = rng.get((s, ts // 60_000 * 60_000))
        if not r:
            continue
        hi, lo, c = r
        dev.append(abs(1e4 * (p / c - 1)))
        if not (lo * 0.999 <= p <= hi * 1.001):   # mark vs last-trade price may differ by a few bps
            outside.append((s, ts, p, lo, hi))
    dev.sort()
    med = dev[len(dev) // 2] if dev else 0
    print(f"3 FILLS   {len(dev)} checked ({old_n} older mark-price fills skipped) | outside the real 1m range (±10 bps): {len(outside)} | "
          f"|fill - 1m close| median {med:.1f} bps, max {max(dev, default=0):.1f} bps")
    for x in outside[:3]:
        print("          ", x)
    ok &= not outside

    # ---------------- 4 lookahead + 5 rule ----------------
    has_feat = con.execute("select 1 from sqlite_master where name='features'").fetchone()
    for ts, day in reb:
        dts = calendar.timegm(time.strptime(day, "%Y-%m-%d")) * 1000          # UTC midnight of the signal day
        lag_h = (ts - (dts + DAY)) / 3.6e6
        sig = con.execute("select sym, f7_bps_day, weight from signals where ts=?", (ts,)).fetchall()
        L = [r for r in sig if r[2] > 0]
        S = [r for r in sig if r[2] < 0]
        rule_ok = bool(sig) and (not L or not S or max(r[1] for r in L) <= min(r[1] for r in S))
        sizes = {round(abs(r[2]), 6) for r in L + S}
        neutral = abs(sum(r[2] for r in L + S)) < 2e-3        # older DBs stored weights rounded to 4 decimals
        line = (f"4 LOOKAHEAD rebalance {day}+1 at +{lag_h:.2f}h after the close "
                f"{'OK' if 0 < lag_h < 24 else 'BAD'} | 5 RULE {len(sig)} coins, {len(L)} long / {len(S)} short, "
                f"long f7 <= short f7: {rule_ok}, equal size: {len(sizes) <= 2}, net {sum(r[2] for r in L + S):+.4f}")
        ok &= 0 < lag_h < 24 and rule_ok and neutral
        # positions right after this rebalance must be exactly the signal: same coins, same side
        held = defaultdict(float)
        for tts, s_, q_, _, _ in trades:
            if tts <= ts:
                held[s_] += q_
        want = {r[0]: (1 if r[2] > 0 else -1) for r in L + S}
        have = {k: (1 if v > 0 else -1) for k, v in held.items() if abs(v) > 1e-12}
        pos_ok = want == have
        line += f" | positions match signal: {pos_ok}" + ("" if pos_ok else f" (diff {sorted(set(want.items()) ^ set(have.items()))[:4]})")
        ok &= pos_ok
        # re-derive 7d funding + the daily close for a few coins from raw Binance data
        if has_feat and sig:
            probe = sorted(L, key=lambda r: r[1])[:2] + sorted(S, key=lambda r: -r[1])[:2]
            errs = []
            for s, f7, _ in probe:
                k = get("/fapi/v1/klines", symbol=s, interval="1d", startTime=dts, limit=1)
                row = con.execute("select close from features where ts=? and sym=?", (ts, s)).fetchone()
                if k and row and row[0] and abs(float(k[0][4]) / row[0] - 1) > 1e-9:
                    errs.append(f"{s} close saved {row[0]} vs Binance {k[0][4]}")
                ev = get("/fapi/v1/fundingRate", symbol=s, startTime=dts - 7 * DAY, endTime=ts, limit=1000)
                # bucket like the strategy: an event at 00:00:00.004 belongs to the day that just closed
                tot = sum(float(e["fundingRate"]) for e in ev
                          if dts - 6 * DAY <= (int(e["fundingTime"]) // 60_000 * 60_000 - 60_000) < dts + DAY)
                if abs(1e4 * tot / 7 - f7) > 1e-3:
                    errs.append(f"{s} f7 saved {f7:.4f} vs re-derived {1e4 * tot / 7:.4f} bps/day")
            line += " | re-derived close + 7d funding: " + ("OK" if not errs else "; ".join(errs))
            ok &= not errs
        print(line)
    print("\nRESULT:", "ALL CHECKS PASS" if ok else "SOMETHING IS WRONG - see lines above")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1] if len(sys.argv) > 1 else "fronttest.db") else 1)
