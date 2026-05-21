import time
import os
import ccxt
import requests

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

# 価格取得する取引所の優先順位
EXCHANGES = [
    ("MEXC", ccxt.mexc()),
    ("Binance", ccxt.binance()),
    ("Gate", ccxt.gate()),
    ("Phemex", ccxt.phemex()),
]

initial_prices = {}

NTFY_TOPIC = "crypto12923"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

def get_price(symbol):
    """
    MEXC → Binance → Gate → Phemex の順で価格取得。
    最初に成功した価格を返す。
    """
    for exchange_name, exchange in EXCHANGES:
        try:
            ticker = exchange.fetch_ticker(symbol)
            price = ticker.get("last")

            if price is not None:
                print(f"✅ {symbol}: {exchange_name} から取得 {price}")
                return price, exchange_name

        except Exception as e:
            print(f"⚠ {symbol}: {exchange_name} で取得失敗: {e}")

    print(f"❌ {symbol}: 全取引所で価格取得に失敗")
    return None, None

def send_ntfy_notification(message):
    try:
        requests.post(NTFY_URL, data=message.encode("utf-8"), timeout=5)
    except requests.exceptions.RequestException as e:
        print(f"⚠ 通知の送信に失敗: {e}")

def monitor_prices():
    global initial_prices

    # 初期価格を取得
    for group in TOKEN_GROUPS:
        for token in group["tokens"]:
            price, exchange_name = get_price(token)

            if price is not None:
                initial_prices[token] = {
                    "price": price,
                    "exchange": exchange_name,
                }

    while True:
        try:
            for group in TOKEN_GROUPS:
                threshold = group["threshold"]

                for token in group["tokens"]:
                    current_price, current_exchange = get_price(token)

                    if current_price is None or token not in initial_prices:
                        continue

                    initial_price = initial_prices[token]["price"]
                    initial_exchange = initial_prices[token]["exchange"]

                    price_change = ((current_price - initial_price) / initial_price) * 100

                    if abs(price_change) >= threshold:
                        send_ntfy_notification(
                            f"{token} が {initial_exchange} の初期価格 {initial_price:.4f} USDT から "
                            f"{current_exchange} の現在価格 {current_price:.4f} USDT に変動 "
                            f"({price_change:.2f}%)"
                        )

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
