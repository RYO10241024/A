import os
import time
import requests
import ccxt

# =========================================================
# CONFIG
# =========================================================

CHECK_INTERVAL = 10

THRESHOLD_8 = 8
THRESHOLD_20 = 20
THRESHOLD_50 = 50

NTFY_TOPIC = "crypto12923"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

# =========================================================
# TOKEN PARSE
# =========================================================

def parse_tokens(env_name):

    value = os.getenv(env_name, "").strip()

    if not value:
        return []

    return [
        x.strip()
        for x in value.split(",")
        if x.strip()
    ]

TOKEN_GROUPS = [
    {
        "tokens": parse_tokens("TOKENS_8"),
        "threshold": THRESHOLD_8
    },
    {
        "tokens": parse_tokens("TOKENS_20"),
        "threshold": THRESHOLD_20
    },
    {
        "tokens": parse_tokens("TOKENS_50"),
        "threshold": THRESHOLD_50
    }
]

TOKEN_GROUPS = [
    g for g in TOKEN_GROUPS
    if g["tokens"]
]

# =========================================================
# EXCHANGES
# =========================================================

RAW_EXCHANGES = [

    (
        "Bybit",
        ccxt.bybit({
            "enableRateLimit": True,
            "options": {
                "defaultType": "swap"
            }
        })
    ),

    (
        "BingX",
        ccxt.bingx({
            "enableRateLimit": True,
            "options": {
                "defaultType": "swap"
            }
        })
    ),

    (
        "MEXC",
        ccxt.mexc({
            "enableRateLimit": True
        })
    ),

    (
        "Gate",
        ccxt.gate({
            "enableRateLimit": True
        })
    ),

    (
        "Phemex",
        ccxt.phemex({
            "enableRateLimit": True,
            "options": {
                "defaultType": "swap"
            }
        })
    ),
]

EXCHANGES = []

# =========================================================
# CACHE
# =========================================================

MARKETS_CACHE = {}
SYMBOL_CACHE = {}
INITIAL_PRICES = {}
ERROR_CACHE = set()

# =========================================================
# LOG
# =========================================================

def once_error(msg):

    if msg in ERROR_CACHE:
        return

    ERROR_CACHE.add(msg)

    print(msg)

# =========================================================
# NTFY
# =========================================================

def send_ntfy(message):

    try:

        requests.post(
            NTFY_URL,
            data=message.encode("utf-8"),
            timeout=5
        )

    except Exception as e:

        once_error(f"⚠ ntfy error: {e}")

# =========================================================
# LOAD MARKETS
# =========================================================

def setup_exchanges():

    global EXCHANGES

    for exchange_name, exchange in RAW_EXCHANGES:

        try:

            print(f"🔄 loading {exchange_name}")

            markets = exchange.load_markets()

            MARKETS_CACHE[exchange_name] = markets

            EXCHANGES.append(
                (
                    exchange_name,
                    exchange
                )
            )

            print(
                f"✅ {exchange_name} loaded "
                f"({len(markets)} markets)"
            )

        except Exception as e:

            once_error(
                f"⚠ {exchange_name} disabled: {e}"
            )

# =========================================================
# SYMBOL FIND
# =========================================================

def normalize_symbol(exchange_name, symbol):

    cache_key = f"{exchange_name}:{symbol}"

    if cache_key in SYMBOL_CACHE:
        return SYMBOL_CACHE[cache_key]

    markets = MARKETS_CACHE.get(exchange_name, {})

    # exact
    if symbol in markets:

        SYMBOL_CACHE[cache_key] = symbol

        return symbol

    target = (
        symbol.upper()
        .replace("/", "")
        .replace(":USDT", "")
    )

    # partial match
    for market_symbol in markets.keys():

        normalized_market = (
            market_symbol.upper()
            .replace("/", "")
            .replace(":USDT", "")
        )

        if target in normalized_market:

            SYMBOL_CACHE[cache_key] = market_symbol

            print(
                f"🔄 {exchange_name}: "
                f"{symbol} -> {market_symbol}"
            )

            return market_symbol

    SYMBOL_CACHE[cache_key] = None

    return None

# =========================================================
# PRICE
# =========================================================

def get_price(symbol):

    for exchange_name, exchange in EXCHANGES:

        try:

            actual_symbol = normalize_symbol(
                exchange_name,
                symbol
            )

            if not actual_symbol:
                continue

            ticker = exchange.fetch_ticker(
                actual_symbol
            )

            price = ticker.get("last")

            if price is not None:

                return float(price)

        except Exception as e:

            once_error(
                f"⚠ {exchange_name} "
                f"{symbol}: "
                f"{type(e).__name__}"
            )

    return None

# =========================================================
# INITIAL PRICE
# =========================================================

def setup_initial_prices():

    for group in TOKEN_GROUPS:

        for token in group["tokens"]:

            if token in INITIAL_PRICES:
                continue

            price = get_price(token)

            if price is not None:

                INITIAL_PRICES[token] = price

                print(
                    f"📌 {token}: {price}"
                )

# =========================================================
# MONITOR
# =========================================================

def monitor():

    if not TOKEN_GROUPS:

        print("⚠ no tokens")

        return

    setup_exchanges()

    setup_initial_prices()

    while True:

        try:

            for group in TOKEN_GROUPS:

                threshold = group["threshold"]

                for token in group["tokens"]:

                    current_price = get_price(token)

                    if current_price is None:
                        continue

                    initial_price = INITIAL_PRICES.get(token)

                    if initial_price is None:
                        continue

                    change = (
                        (
                            current_price
                            - initial_price
                        ) / initial_price
                    ) * 100

                    print(
                        f"📈 {token} "
                        f"{change:.2f}%"
                    )

                    if abs(change) >= threshold:

                        msg = (
                            f"{token}\n"
                            f"{initial_price:.6f}"
                            f" -> "
                            f"{current_price:.6f}\n"
                            f"{change:.2f}%"
                        )

                        send_ntfy(msg)

                        print(
                            f"🚨 alert {token}"
                        )

            time.sleep(CHECK_INTERVAL)

        except Exception as e:

            once_error(
                f"⚠ monitor: {e}"
            )

            time.sleep(5)

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print("================================")
    print(" CRYPTO MONITOR STARTED")
    print("================================")

    monitor()
