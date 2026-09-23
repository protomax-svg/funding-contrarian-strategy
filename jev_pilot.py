"""Can the Jev model (TypeSafe System One) tell good days from bad days for #7b?

One request per day. The state is anonymised (no dates, no coin names, only percentiles and plain words),
so the model cannot recall what happened next. Jev is weak at arithmetic, so every number is pre-digested
into a 0-100 percentile plus a word. Target: the strategy's next-7-day net return.

Usage: python jev_pilot.py N        (hard cap N requests; results appended to jev_pilot.jsonl, resumable)
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

import regime as rg   # reuses the backtest, states and trailing percentiles (no look-ahead)

HERE = Path(__file__).resolve().parent
OUT = HERE / "jev_pilot.jsonl"
KEY = (HERE / ".env").read_text().split("=", 1)[1].strip().strip('"').strip("'")
URL = "https://api.typesafe.ai/v1/systemone"


def word(p):
    return "very low" if p < 0.15 else "low" if p < 0.35 else "normal" if p < 0.65 else "high" if p < 0.85 else "very high"


def state_for(t):
    """Anonymised description of the market at close t."""
    s = {}
    for name, p in rg.PCT.items():
        v = p.loc[t]
        s[name] = f"{word(v)} ({int(round(100 * v))}th percentile of the last year)"
    s["BTC above its 200-day average"] = "yes" if rg.STATES["BTC trend (close / SMA200)"].loc[t] > 1 else "no"
    w = rg.W0.loc[t]
    f = rg.F7.loc[t]
    s["long basket average funding"] = f"{1e4 * f[w > 0].mean():.2f} bps per day"
    s["short basket average funding"] = f"{1e4 * f[w < 0].mean():.2f} bps per day"
    return s


QUESTIONS = {
    "profitable_next_week": {
        "type": "noul",
        "instructions": ("A market-neutral crypto strategy buys the perpetual futures with the lowest recent funding rates "
                         "and shorts the ones with the highest, holding each position a few days. Given the market state, "
                         "will this strategy make money over the next 7 days?")},
    "exposure": {
        "type": "score",
        "instructions": "For the same strategy, how much capital should it use over the next 7 days given the market state?",
        "criteria": ["none", "small", "normal", "full"]},
}


USED = HERE / "jev_requests_used.txt"        # every HTTP attempt, failed ones too
BUDGET = int(__import__("os").environ.get("JEV_BUDGET", 200))


class OutOfBudget(Exception):
    pass


def ask(state):
    body = {"model": "jev-latest", "state": state, "questions": QUESTIONS}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    for i in range(4):
        used = int(USED.read_text()) if USED.exists() else 0
        if used >= BUDGET:
            raise OutOfBudget(f"{used} requests used, budget {BUDGET}")
        USED.write_text(str(used + 1))
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504, 529) and i < 3:   # busy/overloaded: back off and retry
                time.sleep(10 * (i + 1))
                continue
            raise
        except urllib.error.URLError:          # TLS/network blip
            if i == 3:
                raise
            time.sleep(5)


def sample_days(n, seed=7):
    fwd = rg.BASE.shift(-1).rolling(7).sum().shift(-6)           # sum of net returns t+1..t+7
    days = fwd.loc[rg.OOS].dropna().index
    days = days[rg.PCT["strategy own trailing 60d return"].loc[days].notna()]
    rng = np.random.default_rng(seed)
    return list(rng.choice(days, size=min(n, len(days)), replace=False)), fwd   # random order: any prefix spans 2024-26


def run(cap):
    done = {json.loads(l)["day"] for l in OUT.read_text().splitlines()} if OUT.exists() else set()
    days, _ = sample_days(1000)                 # fixed order: the first 200 are a subset of the first 1000
    todo = [d for d in days if str(d.date()) not in done][:cap]
    with OUT.open("a") as f:
        for i, d in enumerate(todo):
            try:
                r = ask(state_for(d))
            except OutOfBudget as e:
                print("stop:", e); break
            a = r["answers"]
            f.write(json.dumps({"day": str(d.date()), "p_profit": a["profitable_next_week"]["noul"],
                                "exposure": a["exposure"]["score"], "tokens": r.get("usage", {})}) + "\n")
            f.flush()
            if i % 25 == 0:
                print(f"{i + 1}/{len(todo)}", flush=True)
    print("answers now:", len(OUT.read_text().splitlines()), "| requests used:", USED.read_text())


def evaluate():
    rows = [json.loads(l) for l in OUT.read_text().splitlines()]
    df = pd.DataFrame(rows).set_index(pd.to_datetime([r["day"] for r in rows], utc=True))
    _, fwd = sample_days(1000)
    df["fwd7"] = fwd.loc[df.index].values
    df["fwd1"] = rg.BASE.shift(-1).loc[df.index].values
    # the rule-based filter from regime.py on the same days, for comparison
    atr_on = (rg.PCT["BTC ATR% (market ATR)"] >= 1 / 3).astype(float)
    trend_on = (rg.PCT["BTC trend (close / SMA200)"] < 2 / 3).astype(float)
    df["rule"] = (atr_on * trend_on).loc[df.index].values
    out = {"n_days": len(df)}
    rng = np.random.default_rng(0)
    for col in ("p_profit", "exposure", "rule"):
        ic = df[col].corr(df.fwd7, method="spearman")
        boot = [df.sample(len(df), replace=True, random_state=int(rng.integers(1e9)))[[col, "fwd7"]]
                .corr(method="spearman").iloc[0, 1] for _ in range(1000)]
        out[f"IC {col} vs next 7d"] = round(ic, 3)
        out[f"IC {col} 90% CI"] = (round(np.nanpercentile(boot, 5), 3), round(np.nanpercentile(boot, 95), 3))
    hi = df.p_profit >= df.p_profit.median()
    out["next-7d return when Jev above its median (bps)"] = round(1e4 * df.fwd7[hi].mean(), 1)
    out["next-7d return when Jev below its median (bps)"] = round(1e4 * df.fwd7[~hi].mean(), 1)
    out["next-7d return when rule ON (bps)"] = round(1e4 * df.fwd7[df.rule == 1].mean(), 1)
    out["next-7d return when rule OFF (bps)"] = round(1e4 * df.fwd7[df.rule == 0].mean(), 1)
    out["all days (bps)"] = round(1e4 * df.fwd7.mean(), 1)
    out["corr Jev p_profit vs rule"] = round(df.p_profit.corr(df.rule), 3)
    out["Jev p_profit spread (min / median / max)"] = (round(df.p_profit.min(), 3), round(df.p_profit.median(), 3),
                                                       round(df.p_profit.max(), 3))
    out["avg input tokens"] = round(float(np.mean([t.get("input_tokens", 0) for t in df.tokens])), 0)
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "eval":
        run(int(sys.argv[1]))
    for k, v in evaluate().items():
        print(f"{k}: {v}")
