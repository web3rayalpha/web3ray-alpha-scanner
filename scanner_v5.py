import requests
import time
from datetime import datetime, timezone

seen_tokens = set()

URL = "https://api.dexscreener.com/latest/dex/search?q=raydium"

# V6 SETTINGS
MIN_LIQUIDITY = 1000
MAX_MARKET_CAP = 500000
MAX_FDV = 1000000
MIN_VOLUME_5M = 100

# Only consider very new pairs
MAX_AGE_MINUTES = 30

# Don't let one GitHub Actions run spam your Telegram
MAX_ALERTS_PER_RUN = 3


def alpha_score(liquidity, market_cap, volume5m, age_minutes):

    score = 0

    # LIQUIDITY
    if liquidity >= 50000:
        score += 30
    elif liquidity >= 20000:
        score += 25
    elif liquidity >= 5000:
        score += 20
    elif liquidity >= 1000:
        score += 10

    # MARKET CAP
    if market_cap <= 50000:
        score += 30
    elif market_cap <= 100000:
        score += 25
    elif market_cap <= 250000:
        score += 15
    elif market_cap <= 500000:
        score += 10

    # VOLUME 5M
    if volume5m >= 10000:
        score += 30
    elif volume5m >= 5000:
        score += 20
    elif volume5m >= 1000:
        score += 10
    elif volume5m >= 100:
        score += 5

    # EXTRA POINTS FOR BEING VERY NEW
    if age_minutes <= 5:
        score += 10
    elif age_minutes <= 15:
        score += 5

    return min(score, 100)


def get_new_tokens(token, chat_id):

    try:

        response = requests.get(URL, timeout=15)
        response.raise_for_status()

        pairs = response.json().get("pairs", [])

        print(f"FOUND {len(pairs)} PAIRS")

        # Sort newest pairs first
        pairs.sort(
            key=lambda p: p.get("pairCreatedAt") or 0,
            reverse=True
        )

        alerts_sent = 0

        for pair in pairs:

            if alerts_sent >= MAX_ALERTS_PER_RUN:
                print("MAX ALERTS REACHED")
                break

            # SOLANA ONLY
            if pair.get("chainId") != "solana":
                continue

            address = pair.get("baseToken", {}).get("address")

            if not address or address in seen_tokens:
                continue

            symbol = pair.get("baseToken", {}).get(
                "symbol",
                "Unknown"
            )

            liquidity = float(
                pair.get("liquidity", {}).get("usd") or 0
            )

            fdv = float(pair.get("fdv") or 0)

            # Use real Market Cap when available
            market_cap = float(
                pair.get("marketCap")
                or fdv
                or 0
            )

            volume5m = float(
                pair.get("volume", {}).get("m5") or 0
            )

            # PAIR AGE
            created_at = pair.get("pairCreatedAt")

            if not created_at:
                continue

            now_ms = time.time() * 1000

            age_minutes = (
                now_ms - created_at
            ) / 1000 / 60

            # Ignore invalid/future timestamps
            if age_minutes < 0:
                continue

            # Ignore old pairs
            if age_minutes > MAX_AGE_MINUTES:
                continue

            # Basic filters
            if liquidity < MIN_LIQUIDITY:
                continue

            if market_cap > MAX_MARKET_CAP:
                continue

            if fdv > MAX_FDV:
                continue

            if volume5m < MIN_VOLUME_5M:
                continue

            score = alpha_score(
                liquidity,
                market_cap,
                volume5m,
                age_minutes
            )

            if score < 40:
                continue

            chart = pair.get("url", "")

            age_text = (
                f"{age_minutes:.0f}m"
                if age_minutes < 60
                else f"{age_minutes / 60:.1f}h"
            )

            message = f"""🚀 WEB3RAY V6

⭐ Alpha Score: {score}/100

🪙 {symbol}

💎 Market Cap: ${market_cap:,.0f}
💰 FDV: ${fdv:,.0f}
💧 Liquidity: ${liquidity:,.0f}
📈 Volume 5m: ${volume5m:,.0f}

⏱ Pair Age: {age_text}

🔥 EARLY ALPHA

🔗 {chart}
"""

            result = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": message,
                    "disable_web_page_preview": False
                },
                timeout=10
            )

            if result.ok:

                print(
                    f"SENT {symbol} | "
                    f"MC=${market_cap:.0f} | "
                    f"AGE={age_text} | "
                    f"SCORE={score}"
                )

                seen_tokens.add(address)
                alerts_sent += 1

                time.sleep(1)

            else:

                print(
                    "TELEGRAM ERROR:",
                    result.text
                )

        print(
            f"V6 FINISHED — "
            f"{alerts_sent} ALERT(S) SENT"
        )

    except Exception as e:

        print("ERROR:", e)
