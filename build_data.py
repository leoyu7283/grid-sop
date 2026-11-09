"""抓取 CoinGecko 前 100 大與派網 K 線，計算指標，輸出 data.json。

用法：python build_data.py [輸出路徑]
可選環境變數：COINGECKO_API_KEY（CoinGecko 免費 Demo 金鑰，降低被限流機率）
"""
import json, os, sys, time, datetime, requests

ATR_N = 30   # ATR 期數
ER_N = 30    # ER 期數
ADX_N = 14   # ADX 期數
MIN_BARS = ER_N + 1          # 至少要有幾根 K 線才計算
SHOW_BARS = 120              # 網頁線圖顯示幾根
OUT = sys.argv[1] if len(sys.argv) > 1 else "data.json"

S = requests.Session()
S.headers["User-Agent"] = "grid-dashboard/1.1"
CG_KEY = os.environ.get("COINGECKO_API_KEY", "").strip()


def get(url, params=None, headers=None, tries=5):
    last = None
    for i in range(tries):
        try:
            r = S.get(url, params=params, headers=headers, timeout=25)
            if r.status_code == 200:
                return r.json()
            last = r.status_code
        except requests.RequestException as e:
            last = e
        time.sleep(2 + i * 4)
    raise RuntimeError(f"{url} {params} -> {last}")


# ---------- 1. CoinGecko 前 100 大 ----------
cg = get("https://api.coingecko.com/api/v3/coins/markets",
         {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": 1},
         headers={"x-cg-demo-api-key": CG_KEY} if CG_KEY else None)

STABLE_SYMS = {"usdt", "usdc", "dai", "usde", "usds", "fdusd", "tusd", "pyusd", "usd1", "rlusd", "usdd", "usdtb",
               "susde", "gho", "frax", "usdx", "bfusd", "usdf", "usdg", "eurc", "xaut", "paxg", "buidl", "usyc", "ousg"}
WRAPPED_SYMS = {"wbtc", "weth", "steth", "wsteth", "weeth", "cbbtc", "reth", "wbeth", "lbtc", "meth", "ezeth",
                "solvbtc", "jitosol", "bnsol", "msol", "rseth", "tbtc", "cbeth", "clbtc", "bbtc", "jupsol", "wbnb", "oseth"}
WRAPPED_WORDS = ["wrapped", "staked", "bridged", "liquid staking", "restaked"]


def classify(c):
    s, n = c["symbol"].lower(), c["name"].lower()
    if s in STABLE_SYMS or (("usd" in s or "usd" in n) and abs((c["current_price"] or 0) - 1) < 0.05):
        return "stable"
    if s in WRAPPED_SYMS or any(w in n for w in WRAPPED_WORDS):
        return "wrapped"
    return None


# ---------- 2. 派網交易對 ----------
spot = get("https://api.pionex.com/api/v1/common/symbols", {"type": "SPOT"})["data"]["symbols"]
perp = get("https://api.pionex.com/api/v1/common/symbols", {"type": "PERP"})["data"]["symbols"]
spot_map = {s["baseCurrency"].upper(): s for s in spot if s["quoteCurrency"] == "USDT" and s.get("enable", True)}
perp_map = {s["symbol"].split("_")[0].upper(): s for s in perp if s["symbol"].endswith("_USDT_PERP")}
SPOT_ALIAS = {"GRAM": "TON"}

tick = get("https://api.pionex.com/api/v1/market/tickers", {"type": "SPOT"})["data"]["tickers"]
spot_amt = {t["symbol"]: float(t.get("amount") or 0) for t in tick}


# ---------- 3. 指標 ----------
def wilder(vals, n):
    out = [None] * len(vals)
    if len(vals) < n:
        return out
    a = sum(vals[:n]) / n
    out[n - 1] = a
    for i in range(n, len(vals)):
        a = (a * (n - 1) + vals[i]) / n
        out[i] = a
    return out


def indicators(k):
    n = len(k)
    c = [x["c"] for x in k]
    tr = [k[0]["h"] - k[0]["l"]] + [max(k[i]["h"] - k[i]["l"], abs(k[i]["h"] - c[i - 1]), abs(k[i]["l"] - c[i - 1]))
                                    for i in range(1, n)]
    atr = wilder(tr, ATR_N)
    er = None
    if n > ER_N:
        path = sum(abs(c[i] - c[i - 1]) for i in range(n - ER_N, n))
        er = abs(c[-1] - c[-1 - ER_N]) / path if path else 0
    adx = None
    A = ADX_N
    if n > 3 * A:
        pdm, mdm = [0], [0]
        for i in range(1, n):
            up = k[i]["h"] - k[i - 1]["h"]; dn = k[i - 1]["l"] - k[i]["l"]
            pdm.append(up if up > dn and up > 0 else 0)
            mdm.append(dn if dn > up and dn > 0 else 0)
        trs, ps, ms = sum(tr[1:A + 1]), sum(pdm[1:A + 1]), sum(mdm[1:A + 1])
        dxs = []
        for i in range(A + 1, n):
            trs = trs - trs / A + tr[i]; ps = ps - ps / A + pdm[i]; ms = ms - ms / A + mdm[i]
            pdi = 100 * ps / trs if trs else 0; mdi = 100 * ms / trs if trs else 0
            dxs.append(100 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) else 0)
        a = sum(dxs[:A]) / A
        for d in dxs[A:]:
            a = (a * (A - 1) + d) / A
        adx = a
    ma50 = sum(c[-50:]) / 50 if n >= 50 else None
    return atr, er, adx, ma50


def parse(ks):
    ks = sorted(ks, key=lambda x: x["time"])
    return [{"t": x["time"], "o": float(x["open"]), "h": float(x["high"]), "l": float(x["low"]),
             "c": float(x["close"])} for x in ks]


def fetch(sym, interval, limit=260):
    return parse(get("https://api.pionex.com/api/v1/market/klines",
                     {"symbol": sym, "interval": interval, "limit": limit})["data"]["klines"])


def fetch_daily_long(sym, pages=3):
    """分頁往回抓日線（每頁 500 根），用來合成週線。"""
    out, end = [], None
    for _ in range(pages):
        p = {"symbol": sym, "interval": "1D", "limit": 500}
        if end:
            p["endTime"] = end
        ks = get("https://api.pionex.com/api/v1/market/klines", p)["data"]["klines"]
        time.sleep(0.12)
        if not ks:
            break
        ks = parse(ks)
        out = ks + out
        if len(ks) < 500:
            break
        end = ks[0]["t"] - 1
    seen, uniq = set(), []
    for x in out:
        if x["t"] not in seen:
            seen.add(x["t"]); uniq.append(x)
    return sorted(uniq, key=lambda x: x["t"])


def to_weekly(daily):
    """日線合成週線，每週從週一 00:00 UTC 開始（台灣時間週一 08:00）。"""
    weeks = {}
    for x in daily:
        d = datetime.datetime.fromtimestamp(x["t"] / 1000, datetime.timezone.utc)
        wk = int((d - datetime.timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        w = weeks.get(wk)
        if w is None:
            weeks[wk] = {"t": wk, "o": x["o"], "h": x["h"], "l": x["l"], "c": x["c"]}
        else:
            w["h"] = max(w["h"], x["h"]); w["l"] = min(w["l"], x["l"]); w["c"] = x["c"]
    return [weeks[k] for k in sorted(weeks)]


def sig(x, p=6):
    if x is None:
        return None
    if x == 0:
        return 0
    return float(f"{x:.{p}g}")


def pack(ks):
    atr, er, adx, ma50 = indicators(ks)
    last = ks[-1]["c"]
    tail, atr_tail = ks[-SHOW_BARS:], atr[-SHOW_BARS:]
    return {
        "price": sig(last), "atr": sig(atr[-1]), "atrPct": sig(atr[-1] / last * 100, 4),
        "er": sig(er, 3), "adx": sig(adx, 3), "ma50": sig(ma50), "bars": len(ks),
        "k": [[x["t"] // 1000, sig(x["o"]), sig(x["h"]), sig(x["l"]), sig(x["c"])] for x in tail],
        "atrSeries": [sig(a / x["c"] * 100, 4) if a else None for a, x in zip(atr_tail, tail)],
    }


coins, excluded = [], []
for c in cg:
    sym = c["symbol"].upper()
    cls = classify(c)
    base = {"rank": c["market_cap_rank"], "sym": sym, "name": c["name"],
            "mcap": c["market_cap"], "vol24": c["total_volume"], "chg24": c.get("price_change_percentage_24h")}
    if cls:
        excluded.append({**base, "reason": "穩定幣" if cls == "stable" else "包裝／質押幣"}); continue
    ssym = SPOT_ALIAS.get(sym, sym)
    has_spot, has_perp = ssym in spot_map, sym in perp_map
    if not (has_spot or has_perp):
        excluded.append({**base, "reason": "派網未上架"}); continue
    srcs = ([f"{ssym}_USDT"] if has_spot else []) + ([f"{sym}_USDT_PERP"] if has_perp else [])
    entry = {**base, "spot": has_spot, "perp": has_perp,
             "pionexVol": spot_amt.get(f"{ssym}_USDT"),
             "minAmt": float(spot_map[ssym]["minAmount"]) if has_spot else None,
             "lot": {
                 "spot": {"step": 10 ** -int(spot_map[ssym]["basePrecision"]), "minQty": float(spot_map[ssym]["minTradeSize"]),
                          "minNotional": float(spot_map[ssym]["minAmount"])} if has_spot else None,
                 "perp": {"step": float(perp_map[sym]["baseStep"]), "minQty": float(perp_map[sym]["minSizeLimit"]),
                          "minNotional": float(perp_map[sym].get("minNotional") or 1)} if has_perp else None,
             },
             "tf": {}}
    # 日線（長歷史，同時用來合成週線）
    daily, src_used = [], None
    for src in srcs:
        try:
            daily = fetch_daily_long(src)
        except Exception as e:
            print("fail", src, "1D", e); daily = []
        if len(daily) >= MIN_BARS:
            src_used = src; break
    if len(daily) < MIN_BARS:
        excluded.append({**base, "reason": f"上市不足 {MIN_BARS} 天"}); continue
    entry["tf"]["1D"] = pack(daily[-400:])
    weekly = to_weekly(daily)
    if len(weekly) >= MIN_BARS:
        entry["tf"]["1W"] = pack(weekly)
    try:
        h4 = fetch(src_used, "4H")
        time.sleep(0.12)
        if len(h4) >= MIN_BARS:
            entry["tf"]["4H"] = pack(h4)
    except Exception as e:
        print("fail", src_used, "4H", e)
    coins.append(entry)
    print(f"{sym:8} ok  {','.join(entry['tf'])}  D ATR% {entry['tf']['1D']['atrPct']:.2f}  ER {entry['tf']['1D']['er']}")

if len(coins) < 20:
    raise SystemExit(f"只抓到 {len(coins)} 個幣，資料可能異常，停止輸出")

out = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
       "params": {"atr": ATR_N, "er": ER_N, "adx": ADX_N},
       "coins": coins, "excluded": excluded}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print(len(coins), "coins,", len(excluded), "excluded")
