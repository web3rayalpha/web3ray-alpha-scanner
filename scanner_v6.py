import requests
import time

URL = "https://api.dexscreener.com/latest/dex/search?q=raydium"

# V6 filters
MIN_MARKET_CAP = 5000
MAX_MARKET_CAP = 150000
MIN_LIQUIDITY = 1000
MIN_VOLUME_5M = 100
MAX_FDV = 5000000
MIN_SCORE = 30

seen_tokens = set()


def alpha_score(market_cap, liquidity, fdv, volume5m):
    score = 0

    # Market cap
    if 5000 <= market_cap <= 25000:
        score += 30
    elif market_cap <= 50000:
        score += 25
    elif market_cap <= 100000:
        score += 20
    elif market_cap <= 150000:
        score += 10

    # Liquidity
    if liquidity >= 50000:
        score += 30
    elif liquidity >= 20000:
        score += 25
    elif liquidity >= 5000:
        score += 20
    elif liquidity >= 1000:
        score += 10

    # Volume 5m
    if volume5m >= 10000:
        score += 30
    elif volume5m >= 5000:
        score += 20
    elif volume5m >= 1000:
        score += 10
    elif volume5m >= 100:
        score += 5

    # FDV
    if fdv <= 500000:
        score += 10
    elif fdv <= 1000000:
        score += 5

    return min(score, 100)


def get_new_tokens(token, chat_id):

    try:
        response = requests.get(URL, timeout=15)
        response.raise_for_status()

        pairs = response.json().get("pairs", [])

        print(f"FOUND {len(pairs)} PAIRS")

        alerts_sent = 0

        for pair in pairs:

            base_token = pair.get("baseToken", {})

            address = base_token.get("address")

            if not address:
                continue

            if address in seen_tokens:
                continue

            symbol = base_token.get("symbol", "UNKNOWN")

            # IMPORTANT:
            # Use MARKET CAP, not FDV, for the MC shown in alerts.
            market_cap = float(pair.get("marketCap") or 0)

            liquidity = float(
                pair.get("liquidity", {}).get("usd") or 0
            )

            fdv = float(pair.get("fdv") or 0)

            volume5m = float(
                pair.get("volume", {}).get("m5") or 0
            )

            pair_url = pair.get("url", "")

            # Ignore pairs without real MC data
            if market_cap <= 0:
                continue

            # Filters
            if market_cap < MIN_MARKET_CAP:
                continue

            if market_cap > MAX_MARKET_CAP:
                continue

            if liquidity < MIN_LIQUIDITY:
                continue

            if volume5m < MIN_VOLUME_5M:
                continue

            if fdv > MAX_FDV:
                continue

            score = alpha_score(
                market_cap,
                liquidity,
                fdv,
                volume5m
            )

            print(
                f"{symbol} | "
                f"MC=${market_cap:.0f} | "
                f"LQ=${liquidity:.0f} | "
                f"FDV=${fdv:.0f} | "
                f"V5=${volume5m:.0f} | "
                f"SCORE={score}"
            )

            if score < MIN_SCORE:
                continue

            message = f"""🚀 WEB3RAY V6

⭐ Alpha Score: {score}/100

🪙 {symbol}

📊 Market Cap: ${market_cap:,.0f}
💧 Liquidity: ${liquidity:,.0f}
💰 FDV: ${fdv:,.0f}
📈 Volume 5m: ${volume5m:,.0f}

🔗 {pair_url}
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

            result.raise_for_status()

            print(f"SENT {symbol} | MC=${market_cap:.0f}")

            seen_tokens.add(address)
            alerts_sent += 1

            # Prevent Telegram spam
            if alerts_sent >= 10:
                break

            time.sleep(1)

        print(f"V6 FINISHED — {alerts_sent} ALERT(S) SENT")

    except Exception as e:
        print("ERROR:", e)
        raise
