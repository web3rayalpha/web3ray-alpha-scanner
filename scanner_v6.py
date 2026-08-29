import requests
import time
from datetime import datetime, timezone

# ============================================================
# WEB3RAY V8 — EARLY SOLANA/RAYDIUM SCANNER
# ============================================================

PROFILES_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
TOKENS_URL = "https://api.dexscreener.com/tokens/v1/solana/{}"

# ============================================================
# EARLY ENTRY SETTINGS
# ============================================================

MIN_MARKET_CAP = 5_000
MAX_MARKET_CAP = 25_000

MIN_LIQUIDITY = 500
MIN_VOLUME_5M = 100

MAX_PAIR_AGE_MINUTES = 60

MIN_SCORE = 30

# How many latest token profiles to inspect
MAX_PROFILES = 100

seen_tokens = set()


def get_pair_age_minutes(pair):

    created_at = pair.get("pairCreatedAt")

    if not created_at:
        return 999999

    try:

        created_seconds = float(created_at) / 1000

        now = datetime.now(
            timezone.utc
        ).timestamp()

        return max(
            (now - created_seconds) / 60,
            0
        )

    except Exception:

        return 999999


def alpha_score(
    market_cap,
    liquidity,
    volume5m,
    age_minutes
):

    score = 0

    # ========================================================
    # MARKET CAP
    # ========================================================

    if market_cap <= 10_000:
        score += 35

    elif market_cap <= 15_000:
        score += 30

    elif market_cap <= 20_000:
        score += 25

    elif market_cap <= 25_000:
        score += 20

    # ========================================================
    # LIQUIDITY
    # ========================================================

    if liquidity >= 10_000:
        score += 25

    elif liquidity >= 5_000:
        score += 20

    elif liquidity >= 2_000:
        score += 15

    elif liquidity >= 500:
        score += 10

    # ========================================================
    # 5 MINUTE VOLUME
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
        score += 10

    # ========================================================
    # PAIR AGE
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

    return min(score, 100)


def get_latest_profiles():

    response = requests.get(
        PROFILES_URL,
        timeout=15
    )

    response.raise_for_status()

    profiles = response.json()

    if not isinstance(profiles, list):
        return []

    return profiles[:MAX_PROFILES]


def get_token_pairs(addresses):

    if not addresses:
        return []

    address_string = ",".join(addresses)

    url = TOKENS_URL.format(
        address_string
    )

    response = requests.get(
        url,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        return []

    return data


def get_new_tokens(token, chat_id):

    try:

        print("WEB3RAY V8 STARTED")

        # ====================================================
        # DISCOVER LATEST TOKEN PROFILES
        # ====================================================

        profiles = get_latest_profiles()

        print(
            f"FOUND {len(profiles)} LATEST PROFILES"
        )

        # ====================================================
        # ONLY SOLANA TOKEN ADDRESSES
        # ====================================================

        addresses = []

        for profile in profiles:

            if profile.get("chainId") != "solana":
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
            f"SOLANA TOKENS TO CHECK: "
            f"{len(addresses)}"
        )

        alerts_sent = 0

        # ====================================================
        # DEXSCREENER ALLOWS UP TO 30 TOKEN ADDRESSES
        # PER REQUEST
        # ====================================================

        for start in range(
            0,
            len(addresses),
            30
        ):

            batch = addresses[
                start:start + 30
            ]

            print(
                f"CHECKING BATCH "
                f"{start // 30 + 1}"
            )

            try:

                pairs = get_token_pairs(
                    batch
                )

            except Exception as e:

                print(
                    f"BATCH ERROR: {e}"
                )

                continue

            print(
                f"FOUND {len(pairs)} PAIRS "
                f"IN BATCH"
            )

            # =================================================
            # INSPECT PAIRS
            # =================================================

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

                if address in seen_tokens:
                    continue

                symbol = base_token.get(
                    "symbol",
                    "Unknown"
                )

                # =============================================
                # DATA
                # =============================================

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

                age_minutes = (
                    get_pair_age_minutes(
                        pair
                    )
                )

                # =============================================
                # SHOW WHAT WE FOUND
                # =============================================

                print(
                    f"CHECK {symbol} | "
                    f"MC=${market_cap:.0f} | "
                    f"LQ=${liquidity:.0f} | "
                    f"V5=${volume5m:.0f} | "
                    f"AGE={age_minutes:.1f}m"
                )

                # =============================================
                # EARLY ENTRY FILTER
                # =============================================

                if market_cap < MIN_MARKET_CAP:

                    print(
                        f"REJECT {symbol} "
                        f"-> MC TOO LOW"
                    )

                    continue

                if market_cap > MAX_MARKET_CAP:

                    print(
                        f"REJECT {symbol} "
                        f"-> MC TOO HIGH"
                    )

                    continue

                if liquidity < MIN_LIQUIDITY:

                    print(
                        f"REJECT {symbol} "
                        f"-> LIQUIDITY TOO LOW"
                    )

                    continue

                if volume5m < MIN_VOLUME_5M:

                    print(
                        f"REJECT {symbol} "
                        f"-> VOLUME TOO LOW"
                    )

                    continue

                if age_minutes > MAX_PAIR_AGE_MINUTES:

                    print(
                        f"REJECT {symbol} "
                        f"-> TOO OLD"
                    )

                    continue

                # =============================================
                # SCORE
                # =============================================

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
                        f"REJECT {symbol} "
                        f"-> SCORE TOO LOW"
                    )

                    continue

                # =============================================
                # TELEGRAM ALERT
                # =============================================

                chart = pair.get(
                    "url",
                    ""
                )

                message = f"""🚀 WEB3RAY V8 — EARLY ALPHA

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
                    f"https://api.telegram.org/"
                    f"bot{token}/sendMessage",

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

                seen_tokens.add(
                    address
                )

                alerts_sent += 1

                time.sleep(1)

            time.sleep(0.5)

        print(
            f"V8 FINISHED — "
            f"{alerts_sent} ALERT(S) SENT"
        )

    except Exception as e:

        print(
            f"ERROR: "
            f"{type(e).__name__}: {e}"
            )
