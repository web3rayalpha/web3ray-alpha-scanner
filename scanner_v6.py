import requests
import time
from datetime import datetime, timezone

# ============================================================
# WEB3RAY V9 — EARLY MOMENTUM SCANNER
# ============================================================

PROFILES_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
TOKENS_URL = "https://api.dexscreener.com/tokens/v1/solana/{}"

# ============================================================
# TARGET
# ============================================================

MIN_MARKET_CAP = 5_000
MAX_MARKET_CAP = 100_000

MIN_LIQUIDITY = 500
MIN_VOLUME_5M = 100

MAX_PAIR_AGE_MINUTES = 60

MIN_SCORE = 45

# ============================================================
# WATCHLIST
# address -> previous token snapshot
# ============================================================

watchlist = {}

# Prevent repeated Telegram alerts
alerted_tokens = set()


def get_age_minutes(pair):

    created_at = pair.get("pairCreatedAt")

    if not created_at:
        return 999999

    try:

        created_seconds = float(created_at) / 1000

        now = datetime.now(
            timezone.utc
        ).timestamp()

        return max(
            0,
            (now - created_seconds) / 60
        )

    except Exception:

        return 999999


def get_latest_profiles():

    response = requests.get(
        PROFILES_URL,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        return []

    return data


def get_pairs(addresses):

    if not addresses:
        return []

    results = []

    for start in range(
        0,
        len(addresses),
        30
    ):

        batch = addresses[
            start:start + 30
        ]

        url = TOKENS_URL.format(
            ",".join(batch)
        )

        response = requests.get(
            url,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        if isinstance(data, list):
            results.extend(data)

        time.sleep(0.3)

    return results


def momentum_score(
    market_cap,
    liquidity,
    volume5m,
    age_minutes,
    previous_mc,
    previous_volume
):

    score = 0

    # ========================================================
    # EARLY MARKET CAP
    # ========================================================

    if market_cap <= 10_000:
        score += 25

    elif market_cap <= 25_000:
        score += 22

    elif market_cap <= 50_000:
        score += 18

    elif market_cap <= 100_000:
        score += 10

    # ========================================================
    # LIQUIDITY
    # ========================================================

    if liquidity >= 10_000:
        score += 20

    elif liquidity >= 5_000:
        score += 17

    elif liquidity >= 2_000:
        score += 13

    elif liquidity >= 500:
        score += 8

    # ========================================================
    # VOLUME
    # ========================================================

    if volume5m >= 10_000:
        score += 25

    elif volume5m >= 5_000:
        score += 20

    elif volume5m >= 1_000:
        score += 15

    elif volume5m >= 500:
        score += 12

    elif volume5m >= 100:
        score += 8

    # ========================================================
    # AGE
    # ========================================================

    if age_minutes <= 5:
        score += 20

    elif age_minutes <= 10:
        score += 17

    elif age_minutes <= 20:
        score += 14

    elif age_minutes <= 30:
        score += 10

    elif age_minutes <= 60:
        score += 5

    # ========================================================
    # MC MOMENTUM
    # ========================================================

    if previous_mc > 0:

        mc_change = (
            (market_cap - previous_mc)
            / previous_mc
        ) * 100

        if mc_change >= 100:
            score += 20

        elif mc_change >= 50:
            score += 15

        elif mc_change >= 25:
            score += 10

        elif mc_change >= 10:
            score += 5

    # ========================================================
    # VOLUME MOMENTUM
    # ========================================================

    if previous_volume > 0:

        volume_change = (
            (volume5m - previous_volume)
            / previous_volume
        ) * 100

        if volume_change >= 100:
            score += 15

        elif volume_change >= 50:
            score += 10

        elif volume_change >= 25:
            score += 5

    return min(score, 100)


def send_alert(
    token,
    chat_id,
    symbol,
    market_cap,
    liquidity,
    volume5m,
    age_minutes,
    score,
    chart
):

    message = f"""🚀 WEB3RAY V9 — MOMENTUM ALPHA

⭐ Momentum Score: {score}/100

🪙 {symbol}

📊 Market Cap: ${market_cap:,.0f}
💧 Liquidity: ${liquidity:,.0f}
📈 Volume 5m: ${volume5m:,.0f}
⏱️ Pair Age: {age_minutes:.1f} min

🔥 EARLY MOMENTUM DETECTED

🔗 {chart}
"""

    result = requests.post(
        f"https://api.telegram.org/"
        f"bot{token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": message
        },
        timeout=10
    )

    result.raise_for_status()


def get_new_tokens(token, chat_id):

    try:

        print("")
        print("================================")
        print("WEB3RAY V9 STARTED")
        print("================================")

        # ====================================================
        # DISCOVER LATEST TOKENS
        # ====================================================

        profiles = get_latest_profiles()

        addresses = []

        for profile in profiles:

            if profile.get(
                "chainId"
            ) != "solana":

                continue

            address = profile.get(
                "tokenAddress"
            )

            if not address:
                continue

            if address in addresses:
                continue

            addresses.append(address)

        print(
            f"LATEST SOLANA TOKENS: "
            f"{len(addresses)}"
        )

        # ====================================================
        # GET PAIR DATA
        # ====================================================

        pairs = get_pairs(addresses)

        print(
            f"PAIRS RECEIVED: "
            f"{len(pairs)}"
        )

        alerts_sent = 0

        # ====================================================
        # PROCESS PAIRS
        # ====================================================

        for pair in pairs:

            if pair.get(
                "chainId"
            ) != "solana":

                continue

            if pair.get(
                "dexId"
            ) != "raydium":

                continue

            base_token = pair.get(
                "baseToken",
                {}
            )

            address = base_token.get(
                "address"
            )

            if not address:
                continue

            symbol = base_token.get(
                "symbol",
                "Unknown"
            )

            market_cap = float(
                pair.get(
                    "marketCap"
                ) or 0
            )

            liquidity = float(
                pair.get(
                    "liquidity",
                    {}
                ).get(
                    "usd"
                ) or 0
            )

            volume5m = float(
                pair.get(
                    "volume",
                    {}
                ).get(
                    "m5"
                ) or 0
            )

            age_minutes = get_age_minutes(
                pair
            )

            print(
                f"CHECK {symbol} | "
                f"MC=${market_cap:.0f} | "
                f"LQ=${liquidity:.0f} | "
                f"V5=${volume5m:.0f} | "
                f"AGE={age_minutes:.1f}m"
            )

            # =================================================
            # BASIC SAFETY FILTERS
            # =================================================

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

            # =================================================
            # PREVIOUS SNAPSHOT
            # =================================================

            previous = watchlist.get(
                address,
                {}
            )

            previous_mc = float(
                previous.get(
                    "market_cap",
                    0
                )
            )

            previous_volume = float(
                previous.get(
                    "volume5m",
                    0
                )
            )

            # =================================================
            # SCORE
            # =================================================

            score = momentum_score(
                market_cap,
                liquidity,
                volume5m,
                age_minutes,
                previous_mc,
                previous_volume
            )

            # =================================================
            # SAVE CURRENT SNAPSHOT
            # =================================================

            watchlist[address] = {
                "market_cap": market_cap,
                "volume5m": volume5m,
                "liquidity": liquidity,
                "timestamp": time.time()
            }

            # =================================================
            # FIRST SIGHT
            # =================================================

            if previous_mc == 0:

                print(
                    f"TRACKING {symbol} | "
                    f"MC=${market_cap:.0f}"
                )

                continue

            # =================================================
            # MOMENTUM
            # =================================================

            mc_change = (
                (
                    market_cap - previous_mc
                )
                / previous_mc
            ) * 100

            volume_change = 0

            if previous_volume > 0:

                volume_change = (
                    (
                        volume5m
                        - previous_volume
                    )
                    / previous_volume
                ) * 100

            print(
                f"MOMENTUM {symbol} | "
                f"MC {mc_change:+.1f}% | "
                f"VOL {volume_change:+.1f}% | "
                f"SCORE {score}"
            )

            # =================================================
            # ALERT
            # =================================================

            if score < MIN_SCORE:

                print(
                    f"REJECT {symbol} "
                    f"-> SCORE TOO LOW"
                )

                continue

            if address in alerted_tokens:

                print(
                    f"SKIP {symbol} "
                    f"-> ALREADY ALERTED"
                )

                continue

            chart = pair.get(
                "url",
                ""
            )

            send_alert(
                token,
                chat_id,
                symbol,
                market_cap,
                liquidity,
                volume5m,
                age_minutes,
                score,
                chart
            )

            alerted_tokens.add(
                address
            )

            alerts_sent += 1

            print(
                f"🚨 ALERT SENT {symbol}"
            )

            time.sleep(1)

        print("")
        print(
            f"V9 FINISHED — "
            f"{alerts_sent} ALERT(S) SENT"
        )

    except Exception as e:

        print(
            f"ERROR: "
            f"{type(e).__name__}: {e}"
        )
