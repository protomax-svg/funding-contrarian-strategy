"""Paper execution engine for WIDE-spread orders (normal-spread orders are market orders, done by the caller).

Per order (qty signed: + buy, - sell), at the start:
  spread < WIDE_BPS                  -> market order now (caller walks the real order book for the price impact)
  spread >= SKIP_BPS and entry       -> skipped if the expected funding over HOLD_DAYS < cost of crossing the spread
  spread >= WIDE_BPS                 -> post-only maker order at the touch (buy at best bid, sell at best ask)
Resting order:
  filled only when a real trade prints THROUGH its price (strict: no queue guessing)
  repriced to the touch when the market runs away by > REPRICE_PCT
  after MAKER_TIMEOUT_S unfilled     -> cancel, wait for the spread to drop below WIDE_BPS, then market order
Any order past DEADLINE_S            -> market order, whatever the spread

Engine is pure (feed it book/trade events, it returns fills), so it is unit-tested below.
Session wraps it with one Binance websocket (bookTicker + aggTrade of the order's coins).
"""
import json
import queue
import threading
import time
import urllib.parse
from dataclasses import dataclass, field

from websockets.sync.client import connect as ws_connect

WS_PUBLIC = "wss://fstream.binance.com/public/stream?streams="   # bookTicker lives here
WS_MARKET = "wss://fstream.binance.com/market/stream?streams="   # aggTrade lives here (the wrong path stays silent)
WIDE_BPS = 30.0            # 0.3 %: at or above this the order goes post-only instead of market
SKIP_BPS = 300.0           # 3 %: a new entry this wide is skipped when the expected funding does not pay for crossing
REPRICE_PCT = 0.3          # move the resting order when the touch runs away by more than this
MAKER_TIMEOUT_S = 20 * 60  # then market (if the spread allows)
DEADLINE_S = 6 * 3600      # hard stop: market order regardless of spread
HOLD_DAYS = 4.0            # backtest median hold, used for the expected-funding estimate
MAKER_BPS, TAKER_BPS = 2.0, 5.0


@dataclass
class Order:
    id: int
    sym: str
    qty: float
    kind: str                     # entry / exit / resize / flip
    created: float                # unix seconds
    f7_bps: float | None = None   # 7d avg daily funding at the signal (bps/day)
    status: str = "new"           # new, waiting_spread, resting, filled_maker, filled_taker, skipped
    limit: float | None = None
    moves: int = 0
    placed: float | None = None
    spread0_bps: float | None = None
    mid0: float | None = None
    est_funding_bps: float | None = None
    fill_px: float | None = None
    fill_ts: float | None = None
    fee: float = 0.0
    reason: str = ""
    events: list = field(default_factory=list)

    @property
    def buy(self):
        return self.qty > 0

    @property
    def done(self):
        return self.status in ("filled_maker", "filled_taker", "skipped")


def spread_bps(bid, ask):
    return 1e4 * (ask - bid) / ((ask + bid) / 2) if bid > 0 and ask > 0 else float("inf")


class Engine:
    def __init__(self, orders):
        self.orders = {o.id: o for o in orders}
        self.book = {}                    # sym -> (bid, ask)

    def _post(self, o, now):
        bid, ask = self.book[o.sym]
        o.limit = bid if o.buy else ask
        o.status, o.placed = "resting", now

    def _take(self, o, now, why):
        bid, ask = self.book[o.sym]
        o.fill_px = ask if o.buy else bid
        o.fee = abs(o.qty) * o.fill_px * TAKER_BPS / 1e4
        o.status, o.fill_ts, o.reason = "filled_taker", now, why
        return o

    def _fill_maker(self, o, now):
        o.fill_px = o.limit
        o.fee = abs(o.qty) * o.fill_px * MAKER_BPS / 1e4
        o.status, o.fill_ts = "filled_maker", now
        return o

    def on_book(self, sym, bid, ask, now):
        """Returns the orders that got filled by this update (taker fallbacks)."""
        if bid <= 0 or ask <= 0:
            return []
        self.book[sym] = (bid, ask)
        sp = spread_bps(bid, ask)
        fills = []
        for o in self.orders.values():
            if o.sym != sym or o.done:
                continue
            if o.status == "new":
                o.spread0_bps, o.mid0 = sp, (bid + ask) / 2
                if sp < WIDE_BPS:
                    fills.append(self._take(o, now, "normal spread"))
                    continue
                if sp >= SKIP_BPS and o.kind == "entry":
                    side = 1 if o.buy else -1
                    o.est_funding_bps = max(0.0, -side * (o.f7_bps or 0.0)) * HOLD_DAYS
                    cost = sp / 2 + TAKER_BPS
                    if o.est_funding_bps < cost:
                        o.status, o.reason = "skipped", f"spread {sp:.0f} bps, expected funding {o.est_funding_bps:.1f} < cost {cost:.1f} bps"
                        continue
                self._post(o, now)
                continue
            age = now - o.created
            if age >= DEADLINE_S:
                fills.append(self._take(o, now, "deadline"))
            elif o.status == "waiting_spread" and sp < WIDE_BPS:
                fills.append(self._take(o, now, "spread normalised after maker timeout"))
            elif o.status == "resting":
                away = (bid > o.limit * (1 + REPRICE_PCT / 100)) if o.buy else (ask < o.limit * (1 - REPRICE_PCT / 100))
                if away:
                    o.limit, o.moves = (bid if o.buy else ask), o.moves + 1
                if now - o.placed >= MAKER_TIMEOUT_S:
                    if sp < WIDE_BPS:
                        fills.append(self._take(o, now, "maker timeout"))
                    else:
                        o.status, o.limit = "waiting_spread", None      # cancel, wait for a normal spread
        return fills

    def on_trade(self, sym, price, now):
        """A real trade at `price`. Fills resting orders it traded through."""
        fills = []
        for o in self.orders.values():
            if o.sym == sym and o.status == "resting" and ((o.buy and price < o.limit) or (not o.buy and price > o.limit)):
                fills.append(self._fill_maker(o, now))
        return fills

    def tick(self, now):
        """Time-based checks when no message arrived for a coin (reuse the last book)."""
        fills = []
        for sym, (bid, ask) in list(self.book.items()):
            fills += self.on_book(sym, bid, ask, now)
        return fills

    @property
    def open(self):
        return [o for o in self.orders.values() if not o.done]


class Session(threading.Thread):
    """Runs an Engine on live Binance data until every order is done. on_fill(order) is called for each fill,
    on_update(order) after state changes (at most every UPDATE_S). Both run in this thread; the caller locks."""
    UPDATE_S = 5

    def __init__(self, orders, on_fill, on_update, first_book):
        super().__init__(daemon=True)
        self.engine = Engine(orders)
        self.on_fill, self.on_update = on_fill, on_update
        self.first_book = first_book            # sym -> (bid, ask) from REST, so orders start at once
        self.q = queue.Queue()
        self.stop = threading.Event()

    def _reader(self, base, suffix):
        """One websocket per stream family (Binance serves bookTicker on /public, aggTrade on /market)."""
        while not self.stop.is_set():
            syms = sorted({o.sym for o in self.engine.open})
            if not syms:
                return
            url = base + "/".join(urllib.parse.quote(f"{x.lower()}@{suffix}", safe="@") for x in syms)
            try:
                with ws_connect(url, open_timeout=20, max_size=2 ** 22) as ws:
                    t_open = time.time()
                    while not self.stop.is_set():
                        try:
                            self.q.put(json.loads(ws.recv(timeout=30)))
                        except TimeoutError:
                            break                       # silent stream: reconnect
                        if time.time() - t_open > 60 and {o.sym for o in self.engine.open} != set(syms):
                            break                       # fewer coins left: resubscribe to a smaller list
            except Exception as e:
                print(f"executor {suffix} websocket: {e!r}; reconnecting", flush=True)
                time.sleep(3)

    def run(self):
        now = time.time()
        fills = []
        for sym, (b, a) in self.first_book.items():
            if any(o.sym == sym for o in self.engine.orders.values()):
                fills += self.engine.on_book(sym, b, a, now)
        for o in fills:
            self.on_fill(o)
        for o in self.engine.orders.values():
            self.on_update(o)
        readers = [threading.Thread(target=self._reader, args=(WS_PUBLIC, "bookTicker"), daemon=True),
                   threading.Thread(target=self._reader, args=(WS_MARKET, "aggTrade"), daemon=True)]
        for r in readers:
            r.start()
        last_update = last_tick = time.time()
        while self.engine.open:
            try:
                msg = self.q.get(timeout=1)
            except queue.Empty:
                msg = None
            now = time.time()
            fills = []
            if msg:
                d, st = msg.get("data", {}), msg.get("stream", "").lower()
                if st.endswith("@bookticker"):
                    fills = self.engine.on_book(d["s"], float(d["b"]), float(d["a"]), now)
                elif st.endswith("@aggtrade"):
                    fills = self.engine.on_trade(d["s"], float(d["p"]), now)
            if now - last_tick >= 1:
                fills += self.engine.tick(now)
                last_tick = now
            for o in fills:
                self.on_fill(o)
            if fills or now - last_update >= self.UPDATE_S:
                for o in self.engine.orders.values():
                    self.on_update(o)
                last_update = now
        self.stop.set()
        for o in self.engine.orders.values():
            self.on_update(o)


if __name__ == "__main__":
    t0 = 1_000_000.0

    def mk(qty, kind="entry", f7=0.0, oid=1):
        return Order(id=oid, sym="X", qty=qty, kind=kind, created=t0, f7_bps=f7)

    # 1) normal spread (2 bps) -> market order at once, taker fee
    e = Engine([mk(+10)])
    f = e.on_book("X", 100.0, 100.02, t0)
    assert f and f[0].status == "filled_taker" and f[0].fill_px == 100.02 and f[0].reason == "normal spread"
    assert abs(f[0].fee - 10 * 100.02 * TAKER_BPS / 1e4) < 1e-12

    # 2) wide spread (50 bps) -> post-only at the bid; a trade AT the bid does not fill, one below does (maker fee)
    e = Engine([mk(+10)])
    assert not e.on_book("X", 100.0, 100.5, t0)
    o = e.orders[1]
    assert o.status == "resting" and o.limit == 100.0
    assert not e.on_trade("X", 100.0, t0 + 1)
    assert e.on_trade("X", 99.99, t0 + 2) and o.status == "filled_maker" and o.fill_px == 100.0
    assert abs(o.fee - 10 * 100.0 * MAKER_BPS / 1e4) < 1e-12

    # 3) wide spread, market runs away up by > 0.3 %: reprice to the new bid and count the move
    e = Engine([mk(+10)])
    e.on_book("X", 100.0, 100.5, t0)
    e.on_book("X", 100.2, 100.7, t0 + 10)
    assert e.orders[1].limit == 100.0 and e.orders[1].moves == 0
    e.on_book("X", 100.5, 101.0, t0 + 20)
    assert e.orders[1].limit == 100.5 and e.orders[1].moves == 1

    # 4) not filled after 20 min, spread still wide -> cancel and wait; spread normalises -> market order
    e = Engine([mk(-10, "exit")])
    e.on_book("X", 100.0, 100.5, t0)
    assert not e.on_book("X", 100.0, 100.5, t0 + MAKER_TIMEOUT_S + 1)
    assert e.orders[1].status == "waiting_spread"
    f = e.on_book("X", 100.0, 100.02, t0 + MAKER_TIMEOUT_S + 60)
    assert f and f[0].status == "filled_taker" and f[0].fill_px == 100.0

    # 5) huge spread (3 %+) entry: tiny funding -> skipped; big funding -> post-only; exits are never skipped
    e = Engine([mk(-10, "entry", f7=1.0, oid=1), mk(-10, "entry", f7=200.0, oid=2), mk(+10, "exit", oid=3)])
    e.on_book("X", 100.0, 104.0, t0)                  # ~392 bps
    assert e.orders[1].status == "skipped" and e.orders[2].status == "resting" and e.orders[3].status == "resting"

    # 6) past the 6 h deadline -> market order whatever the spread
    e = Engine([mk(+10, "exit")])
    e.on_book("X", 100.0, 101.0, t0)
    f = e.on_book("X", 100.0, 101.0, t0 + DEADLINE_S + 1)
    assert f and f[0].status == "filled_taker" and f[0].fill_px == 101.0 and f[0].reason == "deadline"

    # 7) a resting sell fills only when a trade prints ABOVE its price
    e = Engine([mk(-5, "exit")])
    e.on_book("X", 50.0, 50.3, t0)
    assert not e.on_trade("X", 50.3, t0 + 1)
    assert e.on_trade("X", 50.31, t0 + 2) and e.orders[1].fill_px == 50.3
    print("executor selfcheck ok")
