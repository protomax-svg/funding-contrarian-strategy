#!/usr/bin/env python3
"""Download Binance USDT-M perpetual futures DAILY klines + funding + premium
index for ALL USDT perp symbols that ever existed (including delisted ones,
for survivorship-bias-free backtests), from the public keyless archive
data.binance.vision.

Re-runnable: already-downloaded zips are skipped. Parsing/parquet writing
always re-runs (cheap) so output reflects whatever zips are on disk.

Reuses patterns from fetch_data.py (retries, header/no-header CSV detection,
ms-vs-us timestamp detection, skipping close_time / column 6 in kline CSVs)
without modifying that file.

Usage: .venv/bin/python fetch_all_daily.py
"""
import io
import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data.binance.vision/data/futures/um/monthly"
S3_LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
HERE = Path(__file__).resolve().parent
TARGET = HERE / "data" / "all"
RAW = TARGET / "raw"

START = (2020, 1)
END = (2026, 8)
WORKERS = 16
RETRIES = 3

# Binance USDⓈ-M "index" pseudo-symbols (not real coin perpetuals) that would
# otherwise match ^[A-Z0-9]+USDT$. Source: fapi exchangeInfo underlyingType=INDEX
# for the ones still listed; there is no public source for delisted indices,
# so this list only covers what's currently known.
INDEX_SYMBOLS = {"BTCDOMUSDT", "DEFIUSDT", "ALLUSDT"}

SYMBOL_RE = re.compile(r"^[A-Z0-9]+USDT$")

session = requests.Session()


# ---------- S3 bucket listing (keyless) ----------

def s3_list(prefix, delimiter=None):
    """Return (common_prefixes, content_keys) for a prefix, paginating via marker."""
    prefixes, keys = [], []
    marker = ""
    while True:
        params = {"prefix": prefix}
        if delimiter:
            params["delimiter"] = delimiter
        if marker:
            params["marker"] = marker
        r = session.get(S3_LIST, params=params, timeout=30)
        r.raise_for_status()
        text = r.text
        prefixes += re.findall(r"<CommonPrefixes><Prefix>([^<]+)</Prefix></CommonPrefixes>", text)
        keys += re.findall(r"<Contents><Key>([^<]+)</Key>", text)
        if "<IsTruncated>true</IsTruncated>" not in text:
            break
        nm = re.search(r"<NextMarker>([^<]+)</NextMarker>", text)
        marker = nm.group(1) if nm else (keys[-1] if keys else None)
        if marker is None:
            break
    return prefixes, keys


def list_symbols():
    prefixes, _ = s3_list("data/futures/um/monthly/klines/", delimiter="/")
    syms = set()
    for p in prefixes:
        sym = p.rsplit("/", 2)[-2]  # ".../klines/SYM/" -> SYM
        if SYMBOL_RE.match(sym) and sym not in INDEX_SYMBOLS:
            syms.add(sym)
    return sorted(syms)


MONTH_RE = re.compile(r"-(\d{4})-(\d{2})\.zip$")


def available_months(prefix):
    """Months (y, m) within [START, END] that have a .zip under prefix."""
    _, keys = s3_list(prefix)
    months = []
    for k in keys:
        if k.endswith(".CHECKSUM") or not k.endswith(".zip"):
            continue
        m = MONTH_RE.search(k)
        if not m:
            continue
        y, mo = int(m.group(1)), int(m.group(2))
        if START <= (y, mo) <= END:
            months.append((y, mo))
    return sorted(months)


def discover(sym):
    return {
        "klines": available_months(f"data/futures/um/monthly/klines/{sym}/1d/"),
        "funding": available_months(f"data/futures/um/monthly/fundingRate/{sym}/"),
        "premium": available_months(f"data/futures/um/monthly/premiumIndexKlines/{sym}/1d/"),
    }


# ---------- download ----------

def fetch(url):
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


def dl_task(kind, sym, y, m):
    fname_base = f"{sym}-1d-{y:04d}-{m:02d}.zip" if kind != "funding" else f"{sym}-fundingRate-{y:04d}-{m:02d}.zip"
    if kind == "klines":
        url = f"{BASE}/klines/{sym}/1d/{fname_base}"
        dest = RAW / "klines" / sym / fname_base
    elif kind == "premium":
        url = f"{BASE}/premiumIndexKlines/{sym}/1d/{fname_base}"
        dest = RAW / "premium" / sym / fname_base
    else:
        url = f"{BASE}/fundingRate/{sym}/{fname_base}"
        dest = RAW / "funding" / sym / fname_base
    download_to(url, dest)


# ---------- parse (mirrors fetch_data.py's CSV handling) ----------

def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def _read_csv_positional(zpath: Path):
    with zipfile.ZipFile(zpath) as zf:
        text = zf.read(zf.namelist()[0]).decode()
    first_line = text[: text.find("\n")]
    has_header = not _is_number(first_line.split(",")[0])
    return pd.read_csv(io.StringIO(text), header=0 if has_header else None)


def _to_datetime(epoch_col):
    sample = epoch_col.dropna().iloc[0] if epoch_col.notna().any() else 0
    unit = "us" if sample > 1e14 else "ms"
    return pd.to_datetime(epoch_col, unit=unit, utc=True)


def parse_kline_zip(zpath: Path):
    df = _read_csv_positional(zpath)
    # binance order: open_time o h l c v close_time quote_vol trades tb_base tb_quote ignore
    # (close_time = column 6, deliberately skipped)
    df = df.iloc[:, [0, 1, 2, 3, 4, 7, 10]]
    df.columns = ["ts", "open", "high", "low", "close", "quote_volume", "taker_buy_quote"]
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ts"] = pd.to_numeric(df["ts"], errors="coerce")
    df = df.dropna(subset=["ts"])
    df["ts"] = _to_datetime(df["ts"]).dt.normalize()
    return df


def parse_premium_zip(zpath: Path):
    df = _read_csv_positional(zpath)
    ts = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    close = pd.to_numeric(df.iloc[:, 4], errors="coerce")
    out = pd.DataFrame({"ts": _to_datetime(ts).dt.normalize(), "premium_close": close})
    return out.dropna(subset=["ts"])


def parse_funding_zip(zpath: Path):
    df = _read_csv_positional(zpath)
    ts = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    rate = pd.to_numeric(df.iloc[:, -1], errors="coerce")
    out = pd.DataFrame({"ts": _to_datetime(ts), "rate": rate})
    return out.dropna(subset=["ts"])


def bucket_funding_daily(events: pd.DataFrame):
    """Sum funding per UTC day: ts floored to the minute, minus 1 minute, then
    resample 1D sum -> a 00:00:00.xxx event belongs to the PREVIOUS day."""
    if events.empty:
        return pd.Series(dtype="float64")
    bucket = events["ts"].dt.floor("min") - pd.Timedelta(minutes=1)
    s = pd.Series(events["rate"].values, index=bucket).sort_index()
    return s.resample("1D").sum()


def build_symbol(sym):
    kdir, pdir, fdir = RAW / "klines" / sym, RAW / "premium" / sym, RAW / "funding" / sym

    klines = pd.DataFrame()
    kzips = sorted(kdir.glob("*.zip")) if kdir.exists() else []
    if kzips:
        klines = pd.concat([parse_kline_zip(p) for p in kzips], ignore_index=True)
        klines = klines.sort_values("ts").drop_duplicates(subset="ts", keep="last").set_index("ts")

    premium = pd.DataFrame()
    pzips = sorted(pdir.glob("*.zip")) if pdir.exists() else []
    if pzips:
        premium = pd.concat([parse_premium_zip(p) for p in pzips], ignore_index=True)
        premium = premium.sort_values("ts").drop_duplicates(subset="ts", keep="last").set_index("ts")

    events = pd.DataFrame()
    funding_daily = pd.Series(dtype="float64")
    fzips = sorted(fdir.glob("*.zip")) if fdir.exists() else []
    if fzips:
        events = pd.concat([parse_funding_zip(p) for p in fzips], ignore_index=True)
        events = events.sort_values("ts").drop_duplicates(subset="ts", keep="last").reset_index(drop=True)
        funding_daily = bucket_funding_daily(events)

    return klines, premium, funding_daily, events


# ---------- main ----------

def main():
    RAW.mkdir(parents=True, exist_ok=True)

    print("Listing symbols...", file=sys.stderr)
    symbols = list_symbols()
    TARGET.mkdir(parents=True, exist_ok=True)
    (TARGET / "symbols.txt").write_text("\n".join(symbols) + "\n")
    print(f"  {len(symbols)} USDT perp symbols", file=sys.stderr)

    print("Discovering available months per symbol...", file=sys.stderr)
    avail = {}
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(discover, sym): sym for sym in symbols}
        done = 0
        for f in as_completed(futs):
            avail[futs[f]] = f.result()
            done += 1
            if done % 200 == 0:
                print(f"  ...{done}/{len(symbols)} discovered", file=sys.stderr)

    tasks = []
    for sym, d in avail.items():
        for kind in ("klines", "funding", "premium"):
            for y, m in d[kind]:
                tasks.append((kind, sym, y, m))
    print(f"Downloading {len(tasks)} zips...", file=sys.stderr)
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = [ex.submit(dl_task, *t) for t in tasks]
        done = 0
        for f in as_completed(futs):
            f.result()
            done += 1
            if done % 2000 == 0:
                print(f"  ...{done}/{len(tasks)} download tasks done", file=sys.stderr)

    print("Parsing + building wide parquet...", file=sys.stderr)
    fields = {"open": {}, "high": {}, "low": {}, "close": {}, "quote_volume": {}, "taker_buy_quote": {}}
    premium_close = {}
    funding_daily_by_sym = {}
    events_frames = []
    stats = []

    for sym in symbols:
        klines, premium, fdaily, events = build_symbol(sym)
        for field in fields:
            if not klines.empty:
                fields[field][sym] = klines[field]
        if not premium.empty:
            premium_close[sym] = premium["premium_close"]
        if not fdaily.empty:
            funding_daily_by_sym[sym] = fdaily
        if not events.empty:
            ev = events.copy()
            ev["symbol"] = sym
            events_frames.append(ev)

        first = klines.index.min() if not klines.empty else None
        last = klines.index.max() if not klines.empty else None
        stats.append(dict(sym=sym, first=first, last=last,
                           days=len(klines), funding_rows=len(events)))

    for field, d in fields.items():
        pd.DataFrame(d).sort_index().to_parquet(TARGET / f"{field}.parquet")
    pd.DataFrame(premium_close).sort_index().to_parquet(TARGET / "premium_close.parquet")
    pd.DataFrame(funding_daily_by_sym).sort_index().to_parquet(TARGET / "funding_daily.parquet")
    if events_frames:
        all_events = pd.concat(events_frames, ignore_index=True)[["ts", "symbol", "rate"]]
        all_events = all_events.sort_values(["ts", "symbol"]).reset_index(drop=True)
    else:
        all_events = pd.DataFrame(columns=["ts", "symbol", "rate"])
    all_events.to_parquet(TARGET / "funding_events.parquet", index=False)

    print("Writing inventory + verification...", file=sys.stderr)
    write_inventory(stats, fields["close"])


def write_inventory(stats, close_by_sym):
    cutoff = pd.Timestamp("2026-08-01", tz="UTC")
    with_data = [s for s in stats if s["days"] > 0]
    delisted = [s for s in with_data if s["last"] is not None and s["last"] < cutoff]

    lines = [
        "# Daily inventory (all USDT perps, including delisted)",
        "",
        f"Generated {pd.Timestamp.utcnow().isoformat()}",
        "",
        f"Symbols found under klines/ prefix: {len(stats)}",
        f"Symbols with any daily kline data: {len(with_data)}",
        f"Symbols with no data at all: {len(stats) - len(with_data)}",
        f"Delisted (last bar before 2026-08-01): {len(delisted)}",
        "",
        "## Per-year symbol counts (>=60 days of data that year)",
        "",
    ]
    for year in range(2020, 2027):
        y0, y1 = pd.Timestamp(f"{year}-01-01", tz="UTC"), pd.Timestamp(f"{year}-12-31", tz="UTC")
        n = 0
        for sym, s in close_by_sym.items():
            cnt = s.loc[(s.index >= y0) & (s.index <= y1)].notna().sum()
            if cnt >= 60:
                n += 1
        lines.append(f"- {year}: {n} symbols")

    lines += ["", "## First/last date distribution", ""]
    firsts = sorted(s["first"] for s in with_data if s["first"] is not None)
    lasts = sorted(s["last"] for s in with_data if s["last"] is not None)
    if firsts:
        lines.append(f"First bar range: {firsts[0].date()} .. {firsts[-1].date()}")
    if lasts:
        lines.append(f"Last bar range: {lasts[0].date()} .. {lasts[-1].date()}")

    lines += ["", "## Delisted symbols (last bar before 2026-08-01)", ""]
    for s in sorted(delisted, key=lambda s: s["last"]):
        lines.append(f"- {s['sym']}: last bar {s['last'].date()} ({s['days']} days total)")

    no_data = [s["sym"] for s in stats if s["days"] == 0]
    lines += ["", "## No data at all", "", ", ".join(no_data) if no_data else "(none)"]

    # ---- verification ----
    lines += ["", "## Verification", ""]
    try:
        close_all = pd.read_parquet(TARGET / "close.parquet")
        for sym in ("BTCUSDT", "ETHUSDT"):
            h1 = pd.read_parquet(HERE / "data" / "klines_1h" / f"{sym}.parquet")
            h1_daily = h1.set_index("ts")["close"].groupby(pd.Grouper(freq="1D")).last()
            common = close_all[sym].dropna().index.intersection(h1_daily.dropna().index)
            diff = (close_all.loc[common, sym] - h1_daily.loc[common]).abs()
            lines.append(f"- {sym} daily close vs last 1h close/day: max abs diff = {diff.max():.10g} "
                         f"over {len(common)} common days")
    except Exception as e:
        lines.append(f"- close.parquet vs klines_1h verification FAILED: {e}")

    try:
        fexist = pd.read_parquet(HERE / "data" / "funding" / "BTCUSDT.parquet")
        fexist_daily = bucket_funding_daily(fexist.rename(columns={"funding_rate": "rate"}))
        fnew = pd.read_parquet(TARGET / "funding_daily.parquet")["BTCUSDT"]
        common = fexist_daily.dropna().index.intersection(fnew.dropna().index)
        diff = (fexist_daily.loc[common] - fnew.loc[common]).abs()
        lines.append(f"- BTCUSDT funding_daily vs existing data/funding/BTCUSDT.parquet (same bucketing): "
                     f"max abs diff = {diff.max():.10g} over {len(common)} common days")
    except Exception as e:
        lines.append(f"- funding_daily verification FAILED: {e}")

    (TARGET / "INVENTORY.md").write_text("\n".join(lines) + "\n")
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
