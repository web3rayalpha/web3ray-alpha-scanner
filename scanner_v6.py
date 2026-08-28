import requests
import time
from datetime import datetime, timezone

URL = "https://api.dexscreener.com/latest/dex/search?q=raydium"

# =========================
# V7 EARLY ENTRY SETTINGS
# =========================

MIN_MARKET_CAP = 5000
MAX_MARKET_CAP = 25000

MIN_LIQUIDITY = 500
MIN_VOLUME_5M = 100

MAX_PAIR_AGE_MINUTES = 60

MIN_SCORE = 30

seen_tokens = set()


def get_pair_age_minutes(pair):
    created_at = pair.get("pairCreatedAt")

    if not created_at:
        return 999999

    try:
        created_seconds = float(created_at) / 1000
        now = datetime.now(timezone.utc).timestamp()

        age = (now - created_seconds) / 60

        return max(age, 0)

    except Exception:
        return 999999


def alpha_score(
    market_cap,
    liquidity,
    volume5m,
    age_minutes
):
    score = 0

    # =========================
    # MARKET CAP
    # =========================

    if 5000 <= market_cap <= 25000:
        score += 30

    elif market_cap <= 50000:
        score += 25

    elif market_cap <= 100000:
        score += 20

    elif market_cap <= 150000:
        score += 10

    # =========================
    # LIQUIDITY
    # =========================

    if liquidity >= 10000:
        score += 25

    elif liquidity >= 5000:
        score += 20

    elif liquidity >= 2000:
        score += 15

    elif liquidity >= 500:
        score += 10

    # =========================
    # 5M VOLUME
    # =========================

    if volume5m >= 10000:
        score += 25

    elif volume5m >= 5000:
        score += 20

    elif volume5m >= 1000:
        score += 15

    elif volume5m >= 100:
        score += 10

    # =========================
    # AGE
    # =========================

    if age_minutes <= 10:
        score += 20

    elif age_minutes <= 20:
        score += 15

    elif age_minutes <= 30:
        score += 10

    elif age_minutes <= 60:
        score += 5

    return min(score, 100)


def get_new_tokens(token, chat_id):

    try:

        response = requests.get(
            URL,
            timeout=15
        )

        response.raise_for_status()

        pairs = response.json().get("pairs", [])

        print(f"FOUND {len(pairs)} PAIRS")

        alerts_sent = 0

        for pair in pairs:

            # =========================
            # ONLY SOLANA / RAYDIUM
            # =========================

            if pair.get("chainId") != "solana":
                continue

            if pair.get("dexId") != "raydium":
                continue

            base_token = pair.get("baseToken", {})

            address = base_token.get("address")

            if not address:
                continue

            if address in seen_tokens:
                continue

            symbol = base_token.get(
                "symbol",
                "Unknown"
            )

            # =========================
            # GET DATA
            # =========================

            market_cap = float(
                pair.get("marketCap") or 0
            )

            liquidity = float(
                pair.get("liquidity", {}).get("usd") or 0
            )

            volume5m = float(
                pair.get("volume", {}).get("m5") or 0
            )

            age_minutes = get_pair_age_minutes(pair)

            # =========================
            # SHOW EVERY TOKEN
            # =========================

            print(
                f"CHECK {symbol} | "
                f"MC=${market_cap:.0f} | "
                f"LQ=${liquidity:.0f} | "
                f"V5=${volume5m:.0f} | "
                f"AGE={age_minutes:.1f}m"
            )

            # =========================
            # EARLY ENTRY FILTERS
            # =========================

            if market_cap < MIN_MARKET_CAP:
                print(
                    f"REJECT {symbol} -> MC TOO LOW"
                )
                continue

            if market_cap > MAX_MARKET_CAP:
                print(
                    f"REJECT {symbol} -> MC TOO HIGH"
                )
                continue

            if liquidity < MIN_LIQUIDITY:
                print(
                    f"REJECT {symbol} -> LIQUIDITY TOO LOW"
                )
                continue

            if volume5m < MIN_VOLUME_5M:
                print(
                    f"REJECT {symbol} -> VOLUME TOO LOW"
                )
                continue

            if age_minutes > MAX_PAIR_AGE_MINUTES:
                print(
                    f"REJECT {symbol} -> TOO OLD"
                )
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
                f"PASS {symbol} | "
                f"MC=${market_cap:.0f} | "
                f"LQ=${liquidity:.0f} | "
                f"V5=${volume5m:.0f} | "
                f"AGE={age_minutes:.1f}m | "
                f"SCORE={score}"
            )

            if score < MIN_SCORE:
                print(
                    f"REJECT {symbol} -> SCORE TOO LOW"
                )
                continue

            # =========================
            # TELEGRAM ALERT
            # =========================

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

            print(
                f"SENT {symbol} | "
                f"MC=${market_cap:.0f}"
            )

            seen_tokens.add(address)

            alerts_sent += 1

            time.sleep(1)

        print(
            f"V7 FINISHED — "
            f"{alerts_sent} ALERT(S) SENT"
        )

    except Exception as e:

        print(
            f"ERROR: {type(e).__name__}: {e}"
                    )
