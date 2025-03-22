import time
import requests
import os

# 監視対象のトークン（環境変数から取得）
TOKENS = os.getenv("TOKENS", "BTCUSDT,ETHUSDT,XRPUSDT,DOGEUSDT,SOLUSDT,ADAUSDT,MATICUSDT").split(",")

# 初期価格を記録する辞書
initial_prices = {}

# MEXC APIのURL
MEXC_API_URL = "https://api.mexc.com/api/v3/ticker/price"

# NTFYの設定
NTFY_TOPIC = "crypto12923"  # 固定
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

def get_price(symbol):
    """MEXCからトークンの現在価格を取得"""
    response = requests.get(f"{MEXC_API_URL}?symbol={symbol}")
    if response.status_code == 200:
        return float(response.json()["price"])
    return None

def send_ntfy_notification(message):
    """NTFYで通知を送信"""
    requests.post(NTFY_URL, data=message.encode("utf-8"))

def monitor_prices():
    """価格を監視し、±10%変動時にアラートを鳴らす"""
    global initial_prices

    # 初回起動時に基準価格を設定
    for token in TOKENS:
        initial_prices[token] = get_price(token)
        if initial_prices[token] is None:
            print(f"⚠ {token} の初期価格取得に失敗しました")

    while True:
        for token in TOKENS:
            current_price = get_price(token)
            if current_price is None or token not in initial_prices:
                continue

            initial_price = initial_prices[token]
            price_change = ((current_price - initial_price) / initial_price) * 100

            if abs(price_change) >= 0.01:  # ±10%以上変動
                send_ntfy_notification(f"{token} が {initial_price:.2f} USDT から {current_price:.2f} USDT に変動 ({price_change:.2f}%)")

        time.sleep(10)  # 10秒ごとにチェック

if __name__ == "__main__":
    monitor_prices()

