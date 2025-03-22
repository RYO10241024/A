import time
import requests
import os

# 監視対象のトークンと価格閾値（環境変数で設定可能）
TOKENS = {
    "BTCUSDT": {
        "upper": float(os.getenv("BTC_UPPER", 70000)),
        "lower": float(os.getenv("BTC_LOWER", 65000)),
    },
    "ETHUSDT": {
        "upper": float(os.getenv("ETH_UPPER", 4000)),
        "lower": float(os.getenv("ETH_LOWER", 3500)),
    },
}

MEXC_API_URL = "https://api.mexc.com/api/v3/ticker/price"
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "crypto12923")  # 環境変数から取得
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
    """価格を監視し、閾値を超えたら通知"""
    while True:
        for token, limits in TOKENS.items():
            price = get_price(token)
            if price is None:
                continue

            if price > limits["upper"]:
                send_ntfy_notification(f"{token} が {limits['upper']} USDT を超えました！現在価格: {price} USDT")
            elif price < limits["lower"]:
                send_ntfy_notification(f"{token} が {limits['lower']} USDT を下回りました！現在価格: {price} USDT")

        time.sleep(10)  # 10秒ごとにチェック

if __name__ == "__main__":
    monitor_prices()
