import requests
import time

seen_tokens = set()

URL = "https://api.dexscreener.com/latest/dex/search?q=raydium"

MAX_AGE_MINUTES = 180
MIN_LIQUIDITY = 1000
MAX_FDV = 300000


def get_new_tokens(token, chat_id):
    print("🔍 WEB3RAY V2 SCANNING")

    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        pairs = data.get("pairs", [])
        print("TOTAL PAIRS FOUND:", len(pairs))

        sent = 0

        for pair in pairs:

            base = pair.get("baseToken", {})

            symbol = base.get("symbol")
            address = base.get("address")

            if not symbol or not address:
                continue

            if address in seen_tokens:
                continue

            liquidity = float(pair.get("liquidity", {}).get("usd") or 0)

            volume = pair.get("volume", {})
            volume_5m = float(volume.get("m5") or 0)
            volume_1h = float(volume.get("h1") or 0)
            volume_24h = float(volume.get("h24") or 0)

            fdv = float(pair.get("fdv") or 0)

            chart = pair.get("url", "N/A")

            pair_created = pair.get("pairCreatedAt")

            age_minutes = None

            if pair_created:
                age_minutes = (time.time() * 1000 - pair_created) / 60000

            if age_minutes is not None and age_minutes > MAX_AGE_MINUTES:
                continue

            if liquidity < MIN_LIQUIDITY:
                continue

            if fdv and fdv > MAX_FDV:
                continue

            seen_tokens.add(address)

            age_text = (
                f"{age_minutes:.1f} min"
                if age_minutes is not None
                else "Unknown"
            )

            message = f"""🚀 WEB3RAY ALPHA V2

🪙 Token: {symbol}

⏱ Age: {age_text}

📄 CA:
{address}

💰 FDV:
${fdv:,.0f}

💧 Liquidity:
${liquidity:,.0f}

📈 Volume
5m : ${volume_5m:,.0f}
1h : ${volume_1h:,.0f}
24h: ${volume_24h:,.0f}

🔗 Chart:
{chart}
"""

            telegram_url = f"https://api.telegram.org/bot{token}/sendMessage"

            requests.post(
                telegram_url,
                data={
                    "chat_id": chat_id,
                    "text": message
                },
                timeout=10
            )

            print(message)

            sent += 1

            if sent >= 3:
                break

        print("✅ SCAN COMPLETE")

    except Exception as e:
        print("ERROR:", e)
