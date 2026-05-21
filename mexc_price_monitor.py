import time
import os
import requests

# BTC/USDT 形式でOK
TOKENS_8 = os.getenv("TOKENS_8", "BTC/USDT,ETH/USDT").split(",")
TOKENS_20 = os.getenv("TOKENS_20", "XRP/USDT,DOGE/USDT").split(",")
TOKENS_50 = os.getenv("TOKENS_50", "XRP/USDT,DOGE/USDT").split(",")

THRESHOLD_8 = 8
THRESHOLD_20 = 20
THRESHOLD_50 = 50

TOKEN_GROUPS = [
    {"tokens": TOKENS_8, "threshold": THRESHOLD_8},
    {"tokens": TOKENS_20, "threshold": THRESHOLD_20},
    {"tokens": TOKENS_50, "threshold": THRESHOLD_50},
]

initial_prices = {}

# NTFY通知設定
NTFY_TOPIC = "crypto12923"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"


def to_plain_symbol(symbol):
    """
    BTC/USDT -> BTCUSDT
    """
    return symbol.strip().upper().replace("/", "")


def to_dash_symbol(symbol):
    """
    BTC/USDT -> BTC-USDT
    """
    return symbol.strip().upper().replace("/", "-")


def to_underscore_symbol(symbol):
    """
    BTC/USDT -> BTC_USDT
    """
    return symbol.strip().upper().replace("/", "_")


def get_price_binance(symbol):
    try:
        url = "https://api.binance.com/api/v3/ticker/price"
        params = {"symbol": to_plain_symbol(symbol)}

        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()

        data = r.json()
        return float(data["price"])

    except Exception as e:
        print(f"⚠ Binance失敗 {symbol}: {e}")
        return None


def get_price_bybit(symbol):
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        params = {
            "category": "spot",
            "symbol": to_plain_symbol(symbol),
        }

        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()

        data = r.json()
        result = data.get("result", {})
        ticker_list = result.get("list", [])

        if not ticker_list:
            return None

        return float(ticker_list[0]["lastPrice"])

    except Exception as e:
        print(f"⚠ Bybit失敗 {symbol}: {e}")
        return None


def get_price_bingx(symbol):
    try:
        # BingX Spot
        url = "https://open-api.bingx.com/openApi/spot/v1/ticker/24hr"
        params = {"symbol": to_dash_symbol(symbol)}

        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()

        data = r.json()

        # 返却形式が data: {...} または data: [{...}] の場合に対応
        ticker_data = data.get("data")

        if isinstance(ticker_data, list):
            if not ticker_data:
                return None
            ticker_data = ticker_data[0]

        if not isinstance(ticker_data, dict):
            return None

        price = (
            ticker_data.get("lastPrice")
            or ticker_data.get("last")
            or ticker_data.get("close")
        )

        if price is None:
            return None

        return float(price)

    except Exception as e:
        print(f"⚠ BingX失敗 {symbol}: {e}")
        return None


def get_price_mexc(symbol):
    try:
        url = "https://api.mexc.com/api/v3/ticker/price"
        params = {"symbol": to_plain_symbol(symbol)}

        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()

        data = r.json()
        return float(data["price"])

    except Exception as e:
        print(f"⚠ MEXC失敗 {symbol}: {e}")
        return None


def get_price_gate(symbol):
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {"currency_pair": to_underscore_symbol(symbol)}

        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()

        data = r.json()

        if not data:
            return None

        return float(data[0]["last"])

    except Exception as e:
        print(f"⚠ Gate失敗 {symbol}: {e}")
        return None


def get_price_phemex(symbol):
    try:
        # Phemex Spot
        url = "https://api.phemex.com/md/spot/ticker/24hr"
        params = {"symbol": to_plain_symbol(symbol)}

        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()

        data = r.json()
        result = data.get("result", {})

        price = (
            result.get("lastEp")
            or result.get("last")
            or result.get("lastPrice")
        )

        if price is None:
            return None

        # lastEp は 価格 * 1e8 の整数で返ることがある
        price = float(price)

        if price > 1_000_000:
            price = price / 100_000_000

        return price

    except Exception as e:
        print(f"⚠ Phemex失敗 {symbol}: {e}")
        return None


PRICE_SOURCES = [
    ("Binance", get_price_binance),
    ("Bybit", get_price_bybit),
    ("BingX", get_price_bingx),
    ("MEXC", get_price_mexc),
    ("Gate", get_price_gate),
    ("Phemex", get_price_phemex),
]


def get_price(symbol):
    """
    指定順で価格取得:
    Binance -> Bybit -> BingX -> MEXC -> Gate -> Phemex
    """
    symbol = symbol.strip().upper()

    for exchange_name, fetcher in PRICE_SOURCES:
        price = fetcher(symbol)

        if price is not None and price > 0:
            print(f"✅ {symbol}: {price} from {exchange_name}")
            return price

    print(f"⚠ {symbol} は全取引所で価格取得に失敗")
    return None


def send_ntfy_notification(message):
    """NTFYで通知を送信"""
    try:
        requests.post(NTFY_URL, data=message.encode("utf-8"), timeout=5)
    except requests.exceptions.RequestException as e:
        print(f"⚠ 通知の送信に失敗: {e}")


def monitor_prices():
    """価格を監視し、閾値を超えたら通知"""
    global initial_prices

    for group in TOKEN_GROUPS:
        for token in group["tokens"]:
            token = token.strip().upper()
            initial_prices[token] = get_price(token)

    print("✅ 初期価格:")
    for token, price in initial_prices.items():
        if price is not None:
            print(f"{token}: {price:.8f} USDT")

    while True:
        try:
            for group in TOKEN_GROUPS:
                threshold = group["threshold"]

                for token in group["tokens"]:
                    token = token.strip().upper()

                    current_price = get_price(token)

                    if current_price is None or token not in initial_prices:
                        continue

                    initial_price = initial_prices[token]

                    if initial_price is None or initial_price == 0:
                        continue

                    price_change = ((current_price - initial_price) / initial_price) * 100

                    if abs(price_change) >= threshold:
                        send_ntfy_notification(
                            f"{token} が {initial_price:.8f} USDT から "
                            f"{current_price:.8f} USDT に変動 ({price_change:.2f}%)"
                        )

                        print(
                            f"🚨 {token}: {price_change:.2f}% "
                            f"({initial_price:.8f} → {current_price:.8f})"
                        )

                        # 通知後に基準価格を更新
                        initial_prices[token] = current_price

            time.sleep(10)

        except Exception as e:
            print(f"⚠ エラー発生: {e}")
            time.sleep(5)


if __name__ == "__main__":
    while True:
        try:
            monitor_prices()
        except Exception as e:
            print(f"⚠ 重大なエラー: {e}")
            time.sleep(10)
