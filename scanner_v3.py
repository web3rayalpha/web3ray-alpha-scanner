import requests
import time
from datetime import datetime, timezone

seen_tokens = set()

URL = "https://public-api.birdeye.so/defi/v2/tokens/new_listing"

MIN_LIQUIDITY = 1000


def get_new_tokens(token, chat_id, api_key):

    headers = {
        "X-API-KEY": api_key,
        "accept": "application/json",
        "x-chain": "solana"
    }

    params = {
        "limit": 20,
        "meme_platform_enabled": "true"
    }

    try:

        r = requests.get(
            URL,
            headers=headers,
            params=params,
            timeout=15
        )

        r.raise_for_status()

        data = r.json()

        items = data.get("data", {}).get("items", [])

        print(f"FOUND {len(items)} NEW TOKENS")

        for token_data in items:

            address = token_data.get("address")

            if not address:
                continue

            if address in seen_tokens:
                continue

            symbol = token_data.get("symbol", "Unknown")
            name = token_data.get("name", "Unknown")

            liquidity = float(token_data.get("liquidity") or 0)

            if liquidity < MIN_LIQUIDITY:
                continue

            listed = token_data.get("liquidityAddedAt")

            age = "Unknown"

            try:
                dt = datetime.fromisoformat(
                    listed.replace("Z", "+00:00")
                )

                mins = int(
                    (datetime.now(timezone.utc) - dt).total_seconds() / 60
                )

                age = f"{mins} min"

            except Exception:
                pass

            chart = f"https://birdeye.so/token/{address}?chain=solana"

            message = f"""🚀 WEB3RAY V3

🪙 {symbol}

📛 {name}

⏱ Age: {age}

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

            print(f"SENT {symbol}")

            seen_tokens.add(address)

            time.sleep(1)

    except Exception as e:
        print("ERROR:", e)
