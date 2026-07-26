import requests
import time

seen_tokens = set()

URL = "https://api.dexscreener.com/latest/dex/search?q=raydium"

MIN_LIQUIDITY = 5000
MAX_FDV = 1000000
MIN_VOLUME_5M = 1000


def alpha_score(liquidity, fdv, volume5m):
    score = 0

    if liquidity >= 50000:
        score += 40
    elif liquidity >= 20000:
        score += 30
    elif liquidity >= 5000:
        score += 20

    if fdv <= 500000:
        score += 30
    elif fdv <= 1000000:
        score += 20

    if volume5m >= 10000:
        score += 30
    elif volume5m >= 5000:
        score += 20
    elif volume5m >= 1000:
        score += 10

    return score


def get_new_tokens(token, chat_id):

    try:

        response = requests.get(URL, timeout=15)
        response.raise_for_status()

        pairs = response.json().get("pairs", [])

        print(f"FOUND {len(pairs)} PAIRS")

        for pair in pairs:

            address = pair.get("baseToken", {}).get("address")

            if not address or address in seen_tokens:
                continue

            symbol = pair.get("baseToken", {}).get("symbol", "Unknown")
            liquidity = float(pair.get("liquidity", {}).get("usd") or 0)
            fdv = float(pair.get("fdv") or 0)
            volume5m = float(pair.get("volume", {}).get("m5") or 0)

            if liquidity < MIN_LIQUIDITY:
                continue

            if fdv > MAX_FDV:
                continue

            if volume5m < MIN_VOLUME_5M:
                continue

            score = alpha_score(liquidity, fdv, volume5m)

            if score < 70:
                continue

            chart = pair.get("url", "")

            message = f"""🚀 WEB3RAY V5

⭐ Alpha Score: {score}/100

🪙 {symbol}

💧 Liquidity: ${liquidity:,.0f}
💰 FDV: ${fdv:,.0f}
📈 Volume 5m: ${volume5m:,.0f}

🔗 {chart}
"""

            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": message
                },
                timeout=10
            )

            seen_tokens.add(address)

            print("SENT", symbol)

            time.sleep(1)

    except Exception as e:
        print(e)
