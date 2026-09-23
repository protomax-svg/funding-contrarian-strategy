#!/usr/bin/env python3
"""Download Binance USDT-M perpetual futures klines + funding rate archives
from the public keyless archive (data.binance.vision) and write clean parquet.

Re-runnable: already-downloaded zip files are skipped. Parsing/parquet
writing always re-runs (cheap) so it reflects whatever zips are on disk.

Usage: .venv/bin/python fetch_data.py
"""
import calendar
import io
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data.binance.vision/data/futures/um"
HERE = Path(__file__).resolve().parent
TARGET = HERE / "data"
RAW = TARGET / "raw"

START = (2020, 1)
END = (2026, 8)
TODAY = date.today()
DAILY_FALLBACK_MONTHS = 3  # if monthly 404s within this many months of today, try daily zips
WORKERS = 16
RETRIES = 3

SYMBOLS = (
    "BTCUSDT ETHUSDT BNBUSDT XRPUSDT ADAUSDT SOLUSDT DOGEUSDT DOTUSDT LINKUSDT LTCUSDT "
    "BCHUSDT AVAXUSDT MATICUSDT POLUSDT TRXUSDT ETCUSDT XLMUSDT ATOMUSDT UNIUSDT FILUSDT "
    "AAVEUSDT NEARUSDT ALGOUSDT EOSUSDT XTZUSDT THETAUSDT VETUSDT SUSHIUSDT CRVUSDT COMPUSDT "
    "SNXUSDT 1INCHUSDT AXSUSDT SANDUSDT MANAUSDT FTMUSDT LUNAUSDT FTTUSDT SRMUSDT WAVESUSDT "
    "APTUSDT ARBUSDT OPUSDT SUIUSDT INJUSDT TIAUSDT SEIUSDT WLDUSDT PEPEUSDT 1000PEPEUSDT "
    "1000SHIBUSDT"
).split()

KLINE_COLS = [
    "ts", "open", "high", "low", "close", "volume",
    "quote_volume", "trades", "taker_buy_base", "taker_buy_quote",
]

session = requests.Session()


# ---------- download ----------

def months(start, end):
    y, m = start
    while (y, m) <= end:
        yield y, m
        m = m + 1 if m < 12 else 1
        y = y if m != 1 else y + 1


def is_recent(y, m):
    months_ago = (TODAY.year - y) * 12 + (TODAY.month - m)
    return 0 <= months_ago <= DAILY_FALLBACK_MONTHS


def fetch(url):
    """GET url with retries on network/5xx errors. Returns bytes, or None on 404/gone."""
    for attempt in range(RETRIES):
        try:
            r = session.get(url, timeout=30)
        except requests.RequestException:
            if attempt == RETRIES - 1:
                return None
            continue
        if r.status_code == 404:
            return None
        if r.ok:
            return r.content
        if attempt == RETRIES - 1:
            return None
    return None


def download_to(url, path: Path):
    if path.exists() and path.stat().st_size > 0:
        return True
    data = fetch(url)
    if data is None:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def download_klines_month(sym, y, m):
    fname = f"{sym}-1h-{y:04d}-{m:02d}.zip"
    url = f"{BASE}/monthly/klines/{sym}/1h/{fname}"
    if download_to(url, RAW / "klines" / sym / fname):
        return
    if not is_recent(y, m):
        return
    ndays = calendar.monthrange(y, m)[1]
    for d in range(1, ndays + 1):
        day = date(y, m, d)
        if day > TODAY:
            break
        dname = f"{sym}-1h-{day.isoformat()}.zip"
        durl = f"{BASE}/daily/klines/{sym}/1h/{dname}"
        download_to(durl, RAW / "klines_daily" / sym / dname)


def download_funding_month(sym, y, m):
    fname = f"{sym}-fundingRate-{y:04d}-{m:02d}.zip"
    url = f"{BASE}/monthly/fundingRate/{sym}/{fname}"
    download_to(url, RAW / "funding" / sym / fname)


def download_all():
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = []
        for sym in SYMBOLS:
            for y, m in months(START, END):
                futs.append(ex.submit(download_klines_month, sym, y, m))
                futs.append(ex.submit(download_funding_month, sym, y, m))
        done = 0
        for f in as_completed(futs):
            f.result()
            done += 1
            if done % 1000 == 0:
                print(f"  ...{done}/{len(futs)} download tasks done", file=sys.stderr)


# ---------- parse ----------

def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def _read_csv_positional(zpath: Path):
    """Read the single CSV inside a zip, detecting an optional header row."""
    with zipfile.ZipFile(zpath) as zf:
        text = zf.read(zf.namelist()[0]).decode()
    first_line = text[: text.find("\n")]
    has_header = not _is_number(first_line.split(",")[0])
    return pd.read_csv(io.StringIO(text), header=0 if has_header else None)


def _to_datetime(epoch_col):
    # ms epoch ~1.6e12-1.8e12 (13 digits); us epoch ~1.6e15-1.8e15 (16 digits)
    sample = epoch_col.dropna().iloc[0] if epoch_col.notna().any() else 0
    unit = "us" if sample > 1e14 else "ms"
    return pd.to_datetime(epoch_col, unit=unit, utc=True)


def parse_kline_zip(zpath: Path):
    df = _read_csv_positional(zpath)
    # binance order: open_time o h l c v close_time quote_vol trades tb_base tb_quote ignore
    df = df.iloc[:, [0, 1, 2, 3, 4, 5, 7, 8, 9, 10]]
    df.columns = KLINE_COLS
    for c in KLINE_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["ts"])
    df["ts"] = _to_datetime(df["ts"])
    return df


def parse_funding_zip(zpath: Path):
    df = _read_csv_positional(zpath)
    ts = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    rate = pd.to_numeric(df.iloc[:, -1], errors="coerce")
    out = pd.DataFrame({"ts": _to_datetime(ts), "funding_rate": rate})
    return out.dropna(subset=["ts"])


def analyze_klines(k: pd.DataFrame):
    if k.empty:
        return dict(first=None, last=None, count=0, missing=0, zero_streaks=0)
    first, last = k["ts"].iloc[0], k["ts"].iloc[-1]
    expected = int((last - first) / pd.Timedelta(hours=1)) + 1
    missing = expected - len(k)
    gap = k["ts"].diff().dt.total_seconds().fillna(3600) > 3600
    zero = k["volume"] == 0
    grp = (gap | (zero != zero.shift(fill_value=zero.iloc[0]))).cumsum()
    streaks = k.groupby(grp)["volume"].agg(n="size", zero=lambda s: (s == 0).all())
    long_zero_streaks = int((streaks["zero"] & (streaks["n"] > 24)).sum())
    return dict(first=first, last=last, count=len(k), missing=missing, zero_streaks=long_zero_streaks)


def build_symbol(sym):
    kdir, ddir, fdir = RAW / "klines" / sym, RAW / "klines_daily" / sym, RAW / "funding" / sym
    kzips = sorted(kdir.glob("*.zip")) if kdir.exists() else []
    kzips += sorted(ddir.glob("*.zip")) if ddir.exists() else []

    stats = dict(sym=sym, first=None, last=None, count=0, missing=0,
                 dup=0, zero_streaks=0, funding_count=0)

    if kzips:
        frames = [parse_kline_zip(p) for p in kzips]
        raw = pd.concat(frames, ignore_index=True)
        before = len(raw)
        k = raw.sort_values("ts").drop_duplicates(subset="ts", keep="last").reset_index(drop=True)
        stats["dup"] = before - len(k)
        num_cols = [c for c in KLINE_COLS if c != "ts"]
        k[num_cols] = k[num_cols].astype("float64")
        (TARGET / "klines_1h").mkdir(parents=True, exist_ok=True)
        k.to_parquet(TARGET / "klines_1h" / f"{sym}.parquet", index=False)
        stats.update(analyze_klines(k))

    fzips = sorted(fdir.glob("*.zip")) if fdir.exists() else []
    if fzips:
        frames = [parse_funding_zip(p) for p in fzips]
        fdf = pd.concat(frames, ignore_index=True)
        fdf = fdf.sort_values("ts").drop_duplicates(subset="ts", keep="last").reset_index(drop=True)
        (TARGET / "funding").mkdir(parents=True, exist_ok=True)
        fdf.to_parquet(TARGET / "funding" / f"{sym}.parquet", index=False)
        stats["funding_count"] = len(fdf)

    return stats


def write_inventory(rows):
    lines = [
        "# Data inventory",
        "",
        f"Generated {pd.Timestamp.utcnow().isoformat()}",
        "",
        "| Symbol | First bar | Last bar | Bars | Missing bars | Dup rows removed | Zero-vol streaks >24h | Funding rows |",
        "|---|---|---|---|---|---|---|---|",
    ]
    missing_syms = []
    for r in rows:
        if r["count"] == 0 and r["funding_count"] == 0:
            missing_syms.append(r["sym"])
            continue
        first = r["first"].strftime("%Y-%m-%d %H:%M") if r["first"] is not None else "-"
        last = r["last"].strftime("%Y-%m-%d %H:%M") if r["last"] is not None else "-"
        lines.append(
            f"| {r['sym']} | {first} | {last} | {r['count']} | {r['missing']} | "
            f"{r['dup']} | {r['zero_streaks']} | {r['funding_count']} |"
        )
    lines.append("")
    if missing_syms:
        lines.append(f"No data at all (404 on every request): {', '.join(missing_syms)}")
        lines.append("")
    (TARGET / "INVENTORY.md").write_text("\n".join(lines))
    return missing_syms


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    print("Downloading...", file=sys.stderr)
    download_all()
    print("Parsing + writing parquet...", file=sys.stderr)
    rows = [build_symbol(sym) for sym in SYMBOLS]
    missing = write_inventory(rows)
    got = len(SYMBOLS) - len(missing)
    print(f"Done. {got}/{len(SYMBOLS)} symbols have data.", file=sys.stderr)
    if missing:
        print("No data at all for: " + ", ".join(missing), file=sys.stderr)


if __name__ == "__main__":
    main()
