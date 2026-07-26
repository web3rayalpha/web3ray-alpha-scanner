import requests
import time
from datetime import datetime, timezone

seen_tokens = set()

URL = "https://public-api.birdeye.so/defi/v2/tokens/new_listing"

API_KEY = "PASTE_YOUR_BIRDEYE_API_KEY_HERE"

MIN_LIQUIDITY = 1000
MIN_SCORE = 80


def calculate_score(liquidity, age_minutes):
    score = 0

    if liquidity >= 10000:
        score += 40
    elif liquidity >= 5000:
        score += 30
    elif liquidity >= 2000:
        score += 20

    if age_minutes is not None:
        if age_minutes <= 5:
            score += 40
        elif age_minutes <= 15:
            score += 30
        elif age_minutes <= 60:
            score += 20

    return score


def get_new_tokens(token, chat_id):

    headers = {
        "X-API-KEY": API_KEY,
        "accept": "application/json",
        "x-chain": "solana"
    }

    params = {
        "limit": 20,
        "meme_platform_enabled": "true"
    }

    try:

        r = requests.get(URL, headers=headers, params=params, timeout=15)
        r.raise_for_status()

        items = r.json().get("data", {}).get("items", [])

        print(f"FOUND {len(items)} TOKENS")

        for t in items:

            address = t.get("address")

            if not address or address in seen_tokens:
                continue

            symbol = t.get("symbol", "Unknown")
            name = t.get("name", "Unknown")

            liquidity = float(t.get("liquidity") or 0)

            listed = t.get("liquidityAddedAt")

            age_minutes = None
            age_text = "Unknown"

            try:
                dt = datetime.fromisoformat(
                    listed.replace("Z", "+00:00")
                )
                age_minutes = int(
                    (datetime.now(timezone.utc) - dt).total_seconds() / 60
                )
                age_text = f"{age_minutes} min"
            except:
                pass

            score = calculate_score(liquidity, age_minutes)

            if liquidity < MIN_LIQUIDITY:
                continue

            if score < MIN_SCORE:
                print(f"SKIP {symbol} SCORE {score}")
                continue

            chart = f"https://birdeye.so/token/{address}?chain=solana"

            message = f"""🚀 WEB3RAY V4

🟢 Alpha Score: {score}/100

🪙 {symbol}

📛 {name}

⏱ Age: {age_text}

💧 Liquidity:
${liquidity:,.0f}

📄 Contract:
{address}

📈 Chart:
{chart}
"""

            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": message
                },
                timeout=10
            )

            print("SENT", symbol)

            seen_tokens.add(address)

            time.sleep(1)

    except Exception as e:
        print("ERROR:", e)
