import requests
import time
from datetime import datetime, timezone

URL = "https://api.dexscreener.com/latest/dex/search?q=raydium"

# =========================
# V7 — EARLY ENTRY FILTERS
# =========================

MIN_MARKET_CAP = 5_000
MAX_MARKET_CAP = 50_000

MIN_LIQUIDITY = 2_000
MIN_VOLUME_5M = 300

MAX_PAIR_AGE_MINUTES = 30

MIN_SCORE = 55

seen_tokens = set()


def get_pair_age_minutes(pair):
    created = pair.get("pairCreatedAt")

    if not created:
        return 999999

    try:
        created_seconds = float(created) / 1000
        now = datetime.now(timezone.utc).timestamp()
        return (now - created_seconds) / 60
    except:
        return 999999


def alpha_score(market_cap, liquidity, volume5m, age_minutes):
    score = 0

    # =========================
    # MARKET CAP — MOST IMPORTANT
    # =========================

    if market_cap <= 15_000:
        score += 35
    elif market_cap <= 30_000:
        score += 30
    elif market_cap <= 50_000:
        score += 20

    # =========================
    # PAIR AGE — VERY IMPORTANT
    # =========================

    if age_minutes <= 5:
        score += 30
    elif age_minutes <= 10:
        score += 25
    elif age_minutes <= 20:
        score += 20
    elif age_minutes <= 30:
        score += 10

    # =========================
    # LIQUIDITY
    # =========================

    if liquidity >= 20_000:
        score += 20
    elif liquidity >= 10_000:
        score += 17
    elif liquidity >= 5_000:
        score += 14
    elif liquidity >= 2_000:
        score += 10

    # =========================
    # 5M VOLUME
    # =========================

    if volume5m >= 10_000:
        score += 15
    elif volume5m >= 5_000:
        score += 13
    elif volume5m >= 1_000:
        score += 10
    elif volume5m >= 500:
        score += 7
    elif volume5m >= 300:
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

            symbol = base_token.get("symbol", "Unknown")

            # =========================
            # GET DATA
            # =========================

            market_cap = float(pair.get("marketCap") or 0)

            liquidity = float(
                pair.get("liquidity", {}).get("usd") or 0
            )

            volume5m = float(
                pair.get("volume", {}).get("m5") or 0
            )

            age_minutes = get_pair_age_minutes(pair)

            # =========================
            # EARLY ENTRY FILTER
            # =========================

            if market_cap < MIN_MARKET_CAP:
                continue

            if market_cap > MAX_MARKET_CAP:
                continue

            if liquidity < MIN_LIQUIDITY:
                continue

            if volume5m < MIN_VOLUME_5M:
                continue

            if age_minutes > MAX_PAIR_AGE_MINUTES:
                continue

            # =========================
            # SCORE
            # =========================

            score = alpha_score(
                market_cap,
                liquidity,
                volume5m,
                age_minutes
            )

            print(
                f"{symbol} | "
                f"MC=${market_cap:.0f} | "
                f"LQ=${liquidity:.0f} | "
                f"V5=${volume5m:.0f} | "
                f"AGE={age_minutes:.1f}m | "
                f"SCORE={score}"
            )

            if score < MIN_SCORE:
                continue

            chart = pair.get("url", "")

            message = f"""🚀 WEB3RAY V7 — EARLY ALPHA

⭐ Alpha Score: {score}/100

🪙 {symbol}

📊 Market Cap: ${market_cap:,.0f}
💧 Liquidity: ${liquidity:,.0f}
📈 Volume 5m: ${volume5m:,.0f}
⏱️ Pair Age: {age_minutes:.1f} min

🔥 EARLY ENTRY CANDIDATE

🔗 {chart}
"""

            result = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": message
                },
                timeout=10
            )

            result.raise_for_status()

            print("SENT", symbol)

            seen_tokens.add(address)

            alerts_sent += 1

            time.sleep(1)

        print(f"V7 FINISHED — {alerts_sent} ALERT(S) SENT")

    except Exception as e:
        print("ERROR:", e)
