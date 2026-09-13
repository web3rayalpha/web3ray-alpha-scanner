  import requests
import time
from datetime import datetime, timezone


# ============================================================
# WEB3RAY V11 — EARLY RUNNER SCANNER
# ============================================================
#
# Purpose:
# Find very early Solana/Raydium tokens showing real momentum.
#
# V11:
# - Rejects heavy dumps
# - Rejects weak buy pressure
# - Focuses first-sight alerts below $100K MC
# - Tracks tokens between scans
# - Detects MC acceleration
# - Detects volume acceleration
# - Sends Telegram alerts
# - Compatible with existing main.py
#
# ============================================================


PROFILES_URL = (
    "https://api.dexscreener.com/token-profiles/latest/v1"
)

TOKENS_URL = (
    "https://api.dexscreener.com/tokens/v1/solana/{}"
)


# ============================================================
# SETTINGS
# ============================================================

MIN_MARKET_CAP = 5_000

MAX_FIRST_SIGHT_MC = 100_000

MAX_TRACKING_MC = 250_000

MIN_LIQUIDITY = 1_000

MAX_PAIR_AGE_MINUTES = 60

MIN_VOLUME_5M = 100

MIN_BUY_PRESSURE = 55

MAX_5M_DROP = -15

MIN_FIRST_SIGHT_SCORE = 60

MIN_MOMENTUM_SCORE = 65


# ============================================================
# GITHUB ACTIONS RUNTIME
# ============================================================

RUN_SECONDS = 240

SCAN_INTERVAL_SECONDS = 45


# ============================================================
# MEMORY DURING ONE RUN
# ============================================================

watchlist = {}

alerted_tokens = set()


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "Web3Ray-Alpha-Scanner/11.0"
})


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        return float(value)

    except Exception:

        return default


# ============================================================
# SAFE INT
# ============================================================

def safe_int(value, default=0):

    try:

        if value is None:
            return default

        return int(value)

    except Exception:

        return default


# ============================================================
# AGE
# ============================================================

def get_age_minutes(pair):

    created_at = pair.get("pairCreatedAt")

    if not created_at:
        return 999999

    try:

        created_seconds = (
            float(created_at) / 1000
        )

        now = datetime.now(
            timezone.utc
        ).timestamp()

        return max(
            0,
            (
                now - created_seconds
            ) / 60
        )

    except Exception:

        return 999999


# ============================================================
# BUY PRESSURE
# ============================================================

def get_buy_pressure(
    buys,
    sells
):

    total = buys + sells

    if total <= 0:
        return 0.0

    return (
        buys / total
    ) * 100


# ============================================================
# DISCOVER LATEST PROFILES
# ============================================================

def get_latest_profiles():

    try:

        response = session.get(
            PROFILES_URL,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):
            return []

        return data

    except Exception as e:

        print(
            "PROFILE ERROR: "
            f"{type(e).__name__}: {e}"
        )

        return []


# ============================================================
# GET PAIRS FOR TOKEN ADDRESSES
# ============================================================

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

        if not batch:
            continue

        url = TOKENS_URL.format(
            ",".join(batch)
        )

        try:

            response = session.get(
                url,
                timeout=20
            )

            response.raise_for_status()

            data = response.json()

            if isinstance(data, list):

                results.extend(data)

        except Exception as e:

            print(
                "PAIR REQUEST ERROR: "
                f"{type(e).__name__}: {e}"
            )

        time.sleep(0.25)

    return results


# ============================================================
# FIND BEST RAYDIUM PAIR PER TOKEN
# ============================================================

def select_raydium_pairs(pairs):

    selected = {}

    for pair in pairs:

        if pair.get("chainId") != "solana":
            continue

        if pair.get("dexId") != "raydium":
            continue

        base = pair.get(
            "baseToken",
            {}
        )

        address = base.get("address")

        if not address:
            continue

        liquidity = safe_float(
            pair.get(
                "liquidity",
                {}
            ).get("usd")
        )

        existing = selected.get(address)

        if existing is None:

            selected[address] = pair

            continue

        existing_liquidity = safe_float(
            existing.get(
                "liquidity",
                {}
            ).get("usd")
        )

        if liquidity > existing_liquidity:

            selected[address] = pair

    return list(
        selected.values()
    )


# ============================================================
# SCORE
# ============================================================

def calculate_score(
    market_cap,
    liquidity,
    volume5m,
    volume1h,
    buys5m,
    sells5m,
    price_change5m,
    age_minutes,
    previous_mc,
    previous_volume
):

    score = 0


    # --------------------------------------------------------
    # MARKET CAP
    # --------------------------------------------------------

    if market_cap <= 10_000:

        score += 25

    elif market_cap <= 20_000:

        score += 23

    elif market_cap <= 35_000:

        score += 20

    elif market_cap <= 50_000:

        score += 17

    elif market_cap <= 75_000:

        score += 12

    elif market_cap <= 100_000:

        score += 7


    # --------------------------------------------------------
    # AGE
    # --------------------------------------------------------

    if age_minutes <= 5:

        score += 20

    elif age_minutes <= 10:

        score += 18

    elif age_minutes <= 15:

        score += 16

    elif age_minutes <= 20:

        score += 14

    elif age_minutes <= 30:

        score += 10

    elif age_minutes <= 45:

        score += 6

    elif age_minutes <= 60:

        score += 3


    # --------------------------------------------------------
    # LIQUIDITY
    # --------------------------------------------------------

    if liquidity >= 20_000:

        score += 15

    elif liquidity >= 10_000:

        score += 13

    elif liquidity >= 5_000:

        score += 11

    elif liquidity >= 2_500:

        score += 9

    elif liquidity >= 1_000:

        score += 6


    # --------------------------------------------------------
    # VOLUME 5M
    # --------------------------------------------------------

    if volume5m >= 20_000:

        score += 20

    elif volume5m >= 10_000:

        score += 17

    elif volume5m >= 5_000:

        score += 14

    elif volume5m >= 2_000:

        score += 11

    elif volume5m >= 1_000:

        score += 8

    elif volume5m >= 500:

        score += 6

    elif volume5m >= 100:

        score += 3


    # --------------------------------------------------------
    # BUY PRESSURE
    # --------------------------------------------------------

    buy_pressure = get_buy_pressure(
        buys5m,
        sells5m
    )

    if buy_pressure >= 75:

        score += 15

    elif buy_pressure >= 65:

        score += 12

    elif buy_pressure >= 60:

        score += 9

    elif buy_pressure >= 55:

        score += 5


    # --------------------------------------------------------
    # PRICE MOMENTUM
    # --------------------------------------------------------

    if price_change5m >= 50:

        score += 15

    elif price_change5m >= 25:

        score += 12

    elif price_change5m >= 15:

        score += 10

    elif price_change5m >= 10:

        score += 7

    elif price_change5m >= 5:

        score += 4


    # --------------------------------------------------------
    # 1H VOLUME
    # --------------------------------------------------------

    if volume1h >= 50_000:

        score += 8

    elif volume1h >= 20_000:

        score += 6

    elif volume1h >= 10_000:

        score += 4


    # --------------------------------------------------------
    # MARKET CAP ACCELERATION
    # --------------------------------------------------------

    if previous_mc > 0:

        mc_change = (
            (
                market_cap
                - previous_mc
            )
            / previous_mc
        ) * 100

        if mc_change >= 100:

            score += 20

        elif mc_change >= 50:

            score += 16

        elif mc_change >= 25:

            score += 12

        elif mc_change >= 15:

            score += 8

        elif mc_change >= 10:

            score += 5


    # --------------------------------------------------------
    # VOLUME ACCELERATION
    # --------------------------------------------------------

    if previous_volume > 0:

        volume_change = (
            (
                volume5m
                - previous_volume
            )
            / previous_volume
        ) * 100

        if volume_change >= 100:

            score += 15

        elif volume_change >= 50:

            score += 12

        elif volume_change >= 25:

            score += 8

        elif volume_change >= 10:

            score += 4


    # --------------------------------------------------------
    # DUMP PENALTY
    # --------------------------------------------------------

    if price_change5m <= -30:

        score -= 30

    elif price_change5m <= -20:

        score -= 25

    elif price_change5m <= -15:

        score -= 20

    elif price_change5m <= -10:

        score -= 10

    elif price_change5m < 0:

        score -= 5


    return max(
        0,
        min(score, 100)
    )


# ============================================================
# TELEGRAM
# ============================================================

def send_alert(
    token,
    chat_id,
    symbol,
    market_cap,
    liquidity,
    volume5m,
    buys5m,
    sells5m,
    price_change5m,
    age_minutes,
    score,
    alert_type,
    chart,
    mc_change=0,
    volume_change=0
):

    buy_pressure = get_buy_pressure(
        buys5m,
        sells5m
    )

    message = f"""🚨 WEB3RAY V11 — {alert_type}

⭐ Score: {score}/100

🪙 ${symbol}

📊 MC: ${market_cap:,.0f}
💧 Liquidity: ${liquidity:,.0f}

📈 Volume 5m: ${volume5m:,.0f}

🟢 Buys: {buys5m}
🔴 Sells: {sells5m}
📊 Buy pressure: {buy_pressure:.0f}%

🔥 Price 5m: {price_change5m:+.1f}%

📈 MC change: {mc_change:+.1f}%
⚡ Volume change: {volume_change:+.1f}%

⏱️ Age: {age_minutes:.1f} min

⚡ EARLY RUNNER SIGNAL

⚠️ DYOR — signal is not a guarantee.

🔗 {chart}
"""

    response = session.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": message
        },
        timeout=10
    )

    response.raise_for_status()


# ============================================================
# ONE SCAN
# ============================================================

def scan_once(
    token,
    chat_id
):

    print("")
    print("================================")
    print("WEB3RAY V11 — SCAN")
    print("================================")


    # --------------------------------------------------------
    # DISCOVERY
    # --------------------------------------------------------

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

        addresses.append(
            address
        )


    print(
        f"SOLANA PROFILES: "
        f"{len(addresses)}"
    )


    # --------------------------------------------------------
    # PAIRS
    # --------------------------------------------------------

    pairs = get_pairs(
        addresses
    )


    print(
        f"PAIRS RECEIVED: "
        f"{len(pairs)}"
    )


    raydium_pairs = select_raydium_pairs(
        pairs
    )


    print(
        f"RAYDIUM PAIRS: "
        f"{len(raydium_pairs)}"
    )


    alerts_sent = 0


    # --------------------------------------------------------
    # PROCESS
    # --------------------------------------------------------

    for pair in raydium_pairs:

        base = pair.get(
            "baseToken",
            {}
        )


        address = base.get(
            "address"
        )

        if not address:
            continue


        symbol = base.get(
            "symbol",
            "UNKNOWN"
        )


        market_cap = safe_float(
            pair.get(
                "marketCap"
            )
        )


        liquidity = safe_float(
            pair.get(
                "liquidity",
                {}
            ).get(
                "usd"
            )
        )


        volume_data = pair.get(
            "volume",
            {}
        )


        volume5m = safe_float(
            volume_data.get(
                "m5"
            )
        )


        volume1h = safe_float(
            volume_data.get(
                "h1"
            )
        )


        txns = pair.get(
            "txns",
            {}
        )


        txns5m = txns.get(
            "m5",
            {}
        )


        buys5m = safe_int(
            txns5m.get(
                "buys"
            )
        )


        sells5m = safe_int(
            txns5m.get(
                "sells"
            )
        )


        price_data = pair.get(
            "priceChange",
            {}
        )


        price_change5m = safe_float(
            price_data.get(
                "m5"
            )
        )


        age_minutes = get_age_minutes(
            pair
        )


        buy_pressure = get_buy_pressure(
            buys5m,
            sells5m
        )


        # ----------------------------------------------------
        # LOG EVERYTHING IMPORTANT
        # ----------------------------------------------------

        print(
            f"CHECK ${symbol} | "
            f"MC=${market_cap:.0f} | "
            f"LQ=${liquidity:.0f} | "
            f"V5=${volume5m:.0f} | "
            f"AGE={age_minutes:.1f}m | "
            f"BUY={buy_pressure:.0f}% | "
            f"P5={price_change5m:+.1f}%"
        )


        # ----------------------------------------------------
        # BASIC FILTERS
        # ----------------------------------------------------

        if market_cap < MIN_MARKET_CAP:

            print(
                f"REJECT ${symbol}: MC TOO LOW"
            )

            continue


        if market_cap > MAX_TRACKING_MC:

            print(
                f"REJECT ${symbol}: MC TOO HIGH"
            )

            continue


        if liquidity < MIN_LIQUIDITY:

            print(
                f"REJECT ${symbol}: "
                f"LIQUIDITY TOO LOW"
            )

            continue


        if age_minutes > MAX_PAIR_AGE_MINUTES:

            print(
                f"REJECT ${symbol}: "
                f"TOO OLD"
            )

            continue


        if volume5m < MIN_VOLUME_5M:

            print(
                f"REJECT ${symbol}: "
                f"LOW 5M VOLUME"
            )

            continue


        # ----------------------------------------------------
        # HARD DUMP FILTER
        # ----------------------------------------------------

        if price_change5m <= MAX_5M_DROP:

            print(
                f"🚫 REJECT ${symbol}: "
                f"5M DUMP "
                f"{price_change5m:+.1f}%"
            )

            continue


        # ----------------------------------------------------
        # BUY PRESSURE FILTER
        # ----------------------------------------------------

        if buy_pressure < MIN_BUY_PRESSURE:

            print(
                f"🚫 REJECT ${symbol}: "
                f"WEAK BUY PRESSURE "
                f"{buy_pressure:.0f}%"
            )

            continue


        # ----------------------------------------------------
        # PREVIOUS STATE
        # ----------------------------------------------------

        previous = watchlist.get(
            address,
            {}
        )


        previous_mc = safe_float(
            previous.get(
                "market_cap"
            )
        )


        previous_volume = safe_float(
            previous.get(
                "volume5m"
            )
        )


        # ----------------------------------------------------
        # CHANGES
        # ----------------------------------------------------

        mc_change = 0

        if previous_mc > 0:

            mc_change = (
                (
                    market_cap
                    - previous_mc
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


        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        score = calculate_score(
            market_cap,
            liquidity,
            volume5m,
            volume1h,
            buys5m,
            sells5m,
            price_change5m,
            age_minutes,
            previous_mc,
            previous_volume
        )


        print(
            f"SCORE ${symbol}: "
            f"{score}/100"
        )


        # ----------------------------------------------------
        # SAVE STATE
        # ----------------------------------------------------

        watchlist[address] = {

            "market_cap": market_cap,

            "volume5m": volume5m,

            "liquidity": liquidity,

            "timestamp": time.time()
        }


        # ----------------------------------------------------
        # FIRST SIGHT
        # ----------------------------------------------------

        if previous_mc == 0:

            if market_cap > MAX_FIRST_SIGHT_MC:

                print(
                    f"SKIP ${symbol}: "
                    f"FIRST SIGHT MC TOO HIGH"
                )

                continue


            if score >= MIN_FIRST_SIGHT_SCORE:

                if address not in alerted_tokens:

                    print(
                        f"🚨 FIRST SIGHT ALERT: "
                        f"${symbol}"
                    )


                    try:

                        send_alert(
                            token=token,
                                       
