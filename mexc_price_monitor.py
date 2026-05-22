import time
import os
import ccxt
import requests

def parse_tokens(env_name):
    """
    環境変数を配列化。
    未設定なら空配列。
    """
    value = os.getenv(env_name, "").strip()

    if not value:
        return []

    return [token.strip() for token in value.split(",") if token.strip()]

# 環境変数から取得
TOKENS_8 = parse_tokens("TOKENS_8")
TOKENS_20 = parse_tokens("TOKENS_20")
TOKENS_50 = parse_tokens("TOKENS_50")

THRESHOLD_8 = 8
THRESHOLD_20 = 20
THRESHOLD_50 = 50

# 空のグループは除外
TOKEN_GROUPS = [
    {"tokens": TOKENS_8, "threshold": THRESHOLD_8},
    {"tokens": TOKENS_20, "threshold": THRESHOLD_20},
    {"tokens": TOKENS_50, "threshold": THRESHOLD_50},
]

TOKEN_GROUPS = [g for g in TOKEN_GROUPS if g["tokens"]]

# 価格取得する取引所の優先順位
EXCHANGES = [
    ("Bybit", ccxt.bybit()),
    ("BingX", ccxt.bingx()),
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
    優先順位順に価格取得。
    """
    last_error = None

    for exchange_name, exchange in EXCHANGES:
        try:
            ticker = exchange.fetch_ticker(symbol)
            price = ticker.get("last")

            if price is not None:
                print(f"✅ {symbol}: {exchange_name} -> {price}")
                return price

        except Exception as e:
            last_error = e
            continue

    print(f"❌ {symbol}: 全取引所で価格取得失敗: {last_error}")
    return None

def send_ntfy_notification(message):
    """NTFY通知"""
    try:
        requests.post(
            NTFY_URL,
            data=message.encode("utf-8"),
            timeout=5
        )
    except requests.exceptions.RequestException as e:
        print(f"⚠ 通知送信失敗: {e}")

def monitor_prices():
    global initial_prices

    if not TOKEN_GROUPS:
        print("⚠ 監視対象トークンがありません")
        return

    # 初期価格取得
    for group in TOKEN_GROUPS:
        for token in group["tokens"]:
            if token not in initial_prices:
                initial_prices[token] = get_price(token)

    while True:
        try:
            for group in TOKEN_GROUPS:
                threshold = group["threshold"]

                for token in group["tokens"]:
                    current_price = get_price(token)

                    if current_price is None:
                        continue

                    initial_price = initial_prices.get(token)

                    if initial_price is None:
                        continue

                    price_change = (
                        (current_price - initial_price)
                        / initial_price
                    ) * 100

                    print(
                        f"{token}: "
                        f"{price_change:.2f}% "
                        f"(基準 {initial_price} → 現在 {current_price})"
                    )

                    if abs(price_change) >= threshold:
                        send_ntfy_notification(
                            f"{token} が "
                            f"{initial_price:.4f} USDT → "
                            f"{current_price:.4f} USDT "
                            f"({price_change:.2f}%)"
                        )

                        # 通知後に基準価格更新
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
            print(f"⚠ 重大エラー: {e}")
            time.sleep(10)
