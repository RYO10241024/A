import time
import os
import ccxt
import requests

# 環境変数からトークンを取得（カンマ区切り）
TOKENS_8 = os.getenv("TOKENS_8", "BTC/USDT,ETH/USDT").split(",")
TOKENS_20 = os.getenv("TOKENS_20", "XRP/USDT,DOGE/USDT").split(",")
TOKENS_50 = os.getenv("TOKENS_50", "XRP/USDT,DOGE/USDT").split(",")

THRESHOLD_8 = 8
THRESHOLD_20 = 20
THRESHOLD_50 = 50

# 監視対象トークンをグループ化
TOKEN_GROUPS = [
    {"tokens": TOKENS_8, "threshold": THRESHOLD_8},
    {"tokens": TOKENS_20, "threshold": THRESHOLD_20},
    {"tokens": TOKENS_50, "threshold": THRESHOLD_50},
]

# 価格取得する取引所の優先順位
# Binanceは除外
EXCHANGES = [
    ("MEXC", ccxt.mexc()),
    ("Gate", ccxt.gate()),
    ("Phemex", ccxt.phemex()),
]

initial_prices = {}

# NTFY通知設定
NTFY_TOPIC = "crypto12923"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

def get_price(symbol):
    """
    MEXC → Gate → Phemex の順で現在価格を取得。
    どこかで取得できたら即 return。
    全部失敗したときだけエラーを出す。
    """
    last_error = None

    for exchange_name, exchange in EXCHANGES:
        try:
            ticker = exchange.fetch_ticker(symbol)
            price = ticker.get("last")

            if price is not None:
                return price

        except Exception as e:
            last_error = e
            continue

    print(f"❌ {symbol}: 全取引所で価格取得に失敗: {last_error}")
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

    # 初期価格を取得
    for group in TOKEN_GROUPS:
        for token in group["tokens"]:
            initial_prices[token] = get_price(token)

    while True:
        try:
            for group in TOKEN_GROUPS:
                threshold = group["threshold"]

                for token in group["tokens"]:
                    current_price = get_price(token)

                    if current_price is None or token not in initial_prices:
                        continue

                    initial_price = initial_prices[token]

                    if initial_price is None:
                        continue

                    price_change = ((current_price - initial_price) / initial_price) * 100

                    if abs(price_change) >= threshold:
                        send_ntfy_notification(
                            f"{token} が {initial_price:.4f} USDT から "
                            f"{current_price:.4f} USDT に変動 ({price_change:.2f}%)"
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
