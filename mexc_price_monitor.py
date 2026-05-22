import os
import time
import requests
import ccxt

# =========================================================
# 設定
# =========================================================

CHECK_INTERVAL = 10

THRESHOLD_8 = 8
THRESHOLD_20 = 20
THRESHOLD_50 = 50

NTFY_TOPIC = "crypto12923"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

# =========================================================
# 環境変数
# 未設定なら監視しない
# =========================================================

def parse_tokens(env_name):
    value = os.getenv(env_name, "").strip()

    if not value:
        return []

    return [
        token.strip()
        for token in value.split(",")
        if token.strip()
    ]

TOKENS_8 = parse_tokens("TOKENS_8")
TOKENS_20 = parse_tokens("TOKENS_20")
TOKENS_50 = parse_tokens("TOKENS_50")

TOKEN_GROUPS = [
    {
        "tokens": TOKENS_8,
        "threshold": THRESHOLD_8
    },
    {
        "tokens": TOKENS_20,
        "threshold": THRESHOLD_20
    },
    {
        "tokens": TOKENS_50,
        "threshold": THRESHOLD_50
    }
]

# 空除外
TOKEN_GROUPS = [
    g for g in TOKEN_GROUPS
    if g["tokens"]
]

# =========================================================
# 取引所
# =========================================================

EXCHANGES = [
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

# =========================================================
# キャッシュ
# =========================================================

MARKETS_CACHE = {}
INITIAL_PRICES = {}

# =========================================================
# util
# =========================================================

def send_ntfy(message):
    try:
        requests.post(
            NTFY_URL,
            data=message.encode("utf-8"),
            timeout=5
        )

    except Exception as e:
        print(f"⚠ 通知失敗: {e}")

def load_markets_once(exchange_name, exchange):
    if exchange_name in MARKETS_CACHE:
        return MARKETS_CACHE[exchange_name]

    try:
        markets = exchange.load_markets()
        MARKETS_CACHE[exchange_name] = markets
        return markets

    except Exception as e:
        print(f"⚠ {exchange_name} market load error: {e}")
        return {}

def normalize_symbol(exchange_name, markets, symbol):
    """
    シンボル自動補正
    """

    # 完全一致
    if symbol in markets:
        return symbol

    symbol_upper = symbol.upper()

    # 部分一致探索
    for market_symbol in markets.keys():
        if symbol_upper.replace("/", "") in market_symbol.upper().replace("/", ""):
            print(
                f"🔄 {exchange_name}: "
                f"{symbol} -> {market_symbol}"
            )
            return market_symbol

    return None

def get_price(symbol):

    for exchange_name, exchange in EXCHANGES:

        try:
            markets = load_markets_once(
                exchange_name,
                exchange
            )

            actual_symbol = normalize_symbol(
                exchange_name,
                markets,
                symbol
            )

            if not actual_symbol:
                continue

            ticker = exchange.fetch_ticker(actual_symbol)

            price = ticker.get("last")

            if price is not None:

                print(
                    f"✅ {exchange_name} "
                    f"{actual_symbol}: {price}"
                )

                return float(price)

        except Exception as e:

            print(
                f"⚠ {exchange_name} "
                f"{symbol}: {type(e).__name__}: {e}"
            )

    print(f"❌ {symbol}: 全取引所で取得失敗")

    return None

# =========================================================
# 監視
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
                    f"📌 初期価格 "
                    f"{token}: {price}"
                )

def monitor():

    if not TOKEN_GROUPS:
        print("⚠ 監視対象なし")
        return

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

                    change_percent = (
                        (
                            current_price - initial_price
                        ) / initial_price
                    ) * 100

                    print(
                        f"📈 {token} | "
                        f"{change_percent:.2f}% | "
                        f"{initial_price} -> {current_price}"
                    )

                    if abs(change_percent) >= threshold:

                        message = (
                            f"{token}\n"
                            f"{initial_price:.6f} -> "
                            f"{current_price:.6f}\n"
                            f"変動率: {change_percent:.2f}%"
                        )

                        send_ntfy(message)

                        print(f"🚨 通知送信: {token}")

                        # 基準更新
                        INITIAL_PRICES[token] = current_price

            time.sleep(CHECK_INTERVAL)

        except Exception as e:

            print(f"⚠ monitor error: {e}")

            time.sleep(5)

# =========================================================
# main
# =========================================================

if __name__ == "__main__":

    print("===================================")
    print(" Crypto Price Monitor Started")
    print("===================================")

    print()

    for group in TOKEN_GROUPS:

        print(
            f"Threshold {group['threshold']}%"
        )

        for token in group["tokens"]:
            print(f" - {token}")

    print()

    while True:

        try:

            monitor()

        except Exception as e:

            print(f"⚠ fatal error: {e}")

            time.sleep(10)
