"""
Finance Agent — SHRRI AI OS v2 (Phase 5)

No finance tool existed inside the SHRRI repo itself — the only real
market-data logic was in the separate JARVIS HUD scripts at
~/.config/eww/scripts/market.py and gold.py. Those aren't importable
as a library (different location, HUD-specific), so this agent
reimplements the SAME proven, working, no-API-key approach directly:
Yahoo Finance's public chart endpoint for stocks/indices/commodities,
and CoinGecko's public simple-price endpoint for crypto.

No invented data — if a symbol lookup fails, it says so honestly
rather than fabricating a price.

Intent routing (checked in order):
  - "nifty"/"sensex"                     -> Indian index price
  - "bitcoin"/"btc"/"crypto" + coin name -> CoinGecko price
  - "gold"                                -> gold price via GC=F futures
  - a stock symbol/company name mentioned -> Yahoo Finance chart lookup
  - "market"/"markets" (general)          -> a quick multi-asset snapshot
"""

import re

import requests

_HEADERS = {"User-Agent": "Mozilla/5.0"}

_KNOWN_SYMBOLS = {
    "nifty": "^NSEI",
    "sensex": "^BSESN",
    "tcs": "TCS.NS",
    "infosys": "INFY.NS",
    "infy": "INFY.NS",
    "reliance": "RELIANCE.NS",
    "gold": "GC=F",
    "apple": "AAPL",
    "tesla": "TSLA",
    "google": "GOOGL",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "nvidia": "NVDA",
}


def _get_stock(symbol: str):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
        r = requests.get(url, timeout=8, headers=_HEADERS)
        d = r.json()["chart"]["result"][0]
        closes = [x for x in d["indicators"]["quote"][0]["close"] if x is not None]
        if len(closes) >= 2:
            prev, curr = closes[-2], closes[-1]
            change = round(((curr - prev) / prev) * 100, 2)
            return round(curr, 2), change
        return None, None
    except Exception:
        return None, None


def _get_crypto(coin_id: str):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=inr,usd&include_24hr_change=true"
        r = requests.get(url, timeout=8)
        d = r.json().get(coin_id)
        if not d:
            return None, None
        price = d.get("inr", d.get("usd"))
        change = d.get("inr_24h_change", d.get("usd_24h_change"))
        return price, (round(change, 2) if change is not None else None)
    except Exception:
        return None, None


class FinanceAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def _lookup_symbol(self, prompt_low: str) -> str:
        for name, sym in _KNOWN_SYMBOLS.items():
            if name in prompt_low:
                return sym
        m = re.search(r"\b([A-Z]{2,6}(?:\.[A-Z]{2})?)\b", prompt_low.upper())
        return m.group(1) if m else ""

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "").strip()
        low = prompt.lower()
        if self.verbose:
            print(f"[finance_agent] Handling: {prompt[:80]!r}")

        if re.search(r"\b(bitcoin|btc|ethereum|eth|crypto)\b", low):
            coin_id = "bitcoin"
            if "ethereum" in low or re.search(r"\beth\b", low):
                coin_id = "ethereum"
            price, change = _get_crypto(coin_id)
            if price is None:
                return f"Couldn't fetch {coin_id} price right now — CoinGecko lookup failed."
            return f"{coin_id.capitalize()}: ₹{price:,.0f} ({change:+.2f}% in 24h)" if change is not None else f"{coin_id.capitalize()}: ₹{price:,.0f}"

        if re.search(r"\b(market|markets)\b", low) and not any(k in low for k in _KNOWN_SYMBOLS):
            lines = []
            for label, sym in [("NIFTY", "^NSEI"), ("SENSEX", "^BSESN"), ("GOLD", "GC=F")]:
                price, change = _get_stock(sym)
                if price is None:
                    lines.append(f"{label}: unavailable")
                else:
                    lines.append(f"{label}: {price:,.2f} ({change:+.2f}%)")
            btc_price, btc_change = _get_crypto("bitcoin")
            if btc_price is not None:
                lines.append(f"BTC: ₹{btc_price:,.0f} ({btc_change:+.2f}%)" if btc_change is not None else f"BTC: ₹{btc_price:,.0f}")
            return "📈 Market snapshot:\n" + "\n".join(lines)

        symbol = self._lookup_symbol(low)
        if not symbol:
            return "GAP: tell me a specific stock, index, or crypto to check (e.g. 'NIFTY price', 'Bitcoin price', 'TCS stock')."

        price, change = _get_stock(symbol)
        if price is None:
            return f"Couldn't fetch a price for '{symbol}' right now — the lookup failed or the symbol may be wrong."
        return f"{symbol}: {price:,.2f} ({change:+.2f}% today)"
