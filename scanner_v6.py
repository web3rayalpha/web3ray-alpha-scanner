import time
from datetime import datetime, timezone

import requests


# ============================================================
# WEB3RAY V12
# NEW RAYDIUM POOL HUNTER
# ============================================================

NEW_POOLS_URL = (
    "https://api.geckoterminal.com/api/v2/"
    "networks/solana/new_pools"
)

MIN_MC = 5_000
MAX_FIRST_SIGHT_MC = 15_000
MAX_TRACKING_MC = 100_000

MIN_LIQUIDITY = 1_000
MAX_AGE_MINUTES = 30

MIN_VOLUME_5M = 100
MIN_BUY_PRESSURE = 55

MAX_5M_DROP = -15

MIN_FIRST_SIGHT_SCORE = 60
MIN_MOMENTUM_SCORE = 70

RUN_SECONDS = 240
SCAN_INTERVAL_SECONDS = 45

# Number of new-pool pages to inspect.
# Page 1 contains the newest pools.
NEW_POOL_PAGES = 1


session = requests.Session()

session.headers.update({
    "Accept": "application/json",
    "User-Agent": "Web3Ray-Alpha-Scanner/12.0"
})


watchlist = {}
alerted_tokens = set()


# ============================================================
# SAFE HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        return float(value)

    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value is None:
            return default

        return int(value)

    except Exception:
        return default


def get_buy_pressure(buys, sells):
    total = buys + sells

    if total <= 0:
        return 0.0

    return (buys / total) * 100


def get_age_minutes(created_at):
    if not created_at:
        return 999999

    try:
        created = datetime.fromisoformat(
            created_at.replace(
                "Z",
                "+00:00"
            )
        )

        now = datetime.now(
            timezone.utc
        )

        return max(
            0,
            (
                now - created
            ).total_seconds() / 60
        )

    except Exception:
        return 999999


# ============================================================
# DISCOVERY
# ============================================================

def get_new_pools(page=1):
    try:
        response = session.get(
            NEW_POOLS_URL,
            params={
                "include": "base_token,quote_token,dex",
                "page": page
            },
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            return []

        pools = data.get(
            "data",
            []
        )

        if not isinstance(pools, list):
            return []

        return pools

    except Exception as e:
        print(
            f"NEW POOLS ERROR: "
            f"{type(e).__name__}: {e}"
        )

        return []


def discover_new_raydium_pools():
    all_pools = []

    for page in range(
        1,
        NEW_POOL_PAGES + 1
    ):

        pools = get_new_pools(page)

        print(
            f"NEW POOLS PAGE {page}: "
            f"{len(pools)}"
        )

        all_pools.extend(pools)

        time.sleep(0.2)

    raydium = []

    seen = set()

    for pool in all_pools:

        pool_id = pool.get(
            "id",
            ""
        )

        if pool_id in seen:
            continue

        seen.add(pool_id)

        relationships = pool.get(
            "relationships",
            {}
        )

        dex_data = (
            relationships
            .get("dex", {})
            .get("data", {})
        )

        dex_id = dex_data.get(
            "id",
            ""
        )

        if dex_id != "raydium":
            continue

        raydium.append(pool)

    return raydium


# ============================================================
# POOL PARSING
# ============================================================

def parse_pool(pool):

    attributes = pool.get(
        "attributes",
        {}
    )

    relationships = pool.get(
        "relationships",
        {}
    )

    pool_address = attributes.get(
        "address"
    )

    pool_name = attributes.get(
        "name",
        "UNKNOWN"
    )

    # --------------------------------------------------------
    # TOKEN
    # --------------------------------------------------------

    base_token = (
        relationships
        .get("base_token", {})
        .get("data", {})
    )

    token_address = base_token.get(
        "id",
        ""
    )

    if token_address.startswith(
        "solana_"
    ):
        token_address = token_address[
            len("solana_"):
        ]

    symbol = pool_name.split(
        " / "
    )[0].strip()

    # --------------------------------------------------------
    # MARKET CAP / FDV
    # --------------------------------------------------------

    market_cap = safe_float(
        attributes.get(
            "market_cap_usd"
        )
    )

    fdv = safe_float(
        attributes.get(
            "fdv_usd"
        )
    )

    # Unverified microcaps can have
    # null market cap, so FDV is used
    # as a fallback for discovery.
    if market_cap <= 0:
        market_cap = fdv

    # --------------------------------------------------------
    # LIQUIDITY
    # --------------------------------------------------------

    liquidity = safe_float(
        attributes.get(
            "reserve_in_usd"
        )
    )

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    volume_data = attributes.get(
        "volume_usd",
        {}
    )

    volume5m = safe_float(
        volume_data.get("m5")
    )

    volume1h = safe_float(
        volume_data.get("h1")
    )

    # --------------------------------------------------------
    # PRICE CHANGE
    # --------------------------------------------------------

    price_data = attributes.get(
        "price_change_percentage",
        {}
    )

    price_change5m = safe_float(
        price_data.get("m5")
    )

    price_change1h = safe_float(
        price_data.get("h1")
    )

    # --------------------------------------------------------
    # TRANSACTIONS
    # --------------------------------------------------------

    transactions = attributes.get(
        "transactions",
        {}
    )

    tx5m = transactions.get(
        "m5",
        {}
    )

    buys5m = safe_int(
        tx5m.get("buys")
    )

    sells5m = safe_int(
        tx5m.get("sells")
    )

    buy_pressure = get_buy_pressure(
        buys5m,
        sells5m
    )

    # --------------------------------------------------------
    # AGE
    # --------------------------------------------------------

    created_at = attributes.get(
        "pool_created_at"
    )

    age_minutes = get_age_minutes(
        created_at
    )

    return {
        "pool_address": pool_address,
        "token_address": token_address,
        "symbol": symbol,
        "market_cap": market_cap,
        "fdv": fdv,
        "liquidity": liquidity,
        "volume5m": volume5m,
        "volume1h": volume1h,
        "price_change5m": price_change5m,
        "price_change1h": price_change1h,
        "buys5m": buys5m,
        "sells5m": sells5m,
        "buy_pressure": buy_pressure,
        "age_minutes": age_minutes,
        "created_at": created_at
    }


# ============================================================
# SCORING
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
    mc_change,
    volume_change
):

    score = 0

    # --------------------------------------------------------
    # EARLY MARKET CAP
    # --------------------------------------------------------

    if market_cap <= 7_500:
        score += 30

    elif market_cap <= 10_000:
        score += 28

    elif market_cap <= 15_000:
        score += 25

    elif market_cap <= 20_000:
        score += 20

    elif market_cap <= 35_000:
        score += 15

    elif market_cap <= 50_000:
        score += 10

    elif market_cap <= 75_000:
        score += 5

    # --------------------------------------------------------
    # AGE
    # --------------------------------------------------------

    if age_minutes <= 5:
        score += 25

    elif age_minutes <= 10:
        score += 23

    elif age_minutes <= 15:
        score += 20

    elif age_minutes <= 20:
        score += 17

    elif age_minutes <= 25:
        score += 12

    elif age_minutes <= 30:
        score += 7

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
        score += 8

    elif liquidity >= 1_000:
        score += 5

    # --------------------------------------------------------
    # 5M VOLUME
    # --------------------------------------------------------

    if volume5m >= 20_000:
        score += 20

    elif volume5m >= 10_000:
        score += 18

    elif volume5m >= 5_000:
        score += 15

    elif volume5m >= 2_000:
        score += 12

    elif volume5m >= 1_000:
        score += 9

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

    if buy_pressure >= 80:
        score += 15

    elif buy_pressure >= 70:
        score += 13

    elif buy_pressure >= 65:
        score += 10

    elif buy_pressure >= 60:
        score += 7

    elif buy_pressure >= 55:
        score += 4

    # --------------------------------------------------------
    # PRICE MOMENTUM
    # --------------------------------------------------------

    if price_change5m >= 50:
        score += 15

    elif price_change5m >= 25:
        score += 13

    elif price_change5m >= 15:
        score += 10

    elif price_change5m >= 10:
        score += 8

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
    # MC ACCELERATION
    # --------------------------------------------------------

    if mc_change >= 100:
        score += 20

    elif mc_change >= 50:
        score += 17

    elif mc_change >= 25:
        score += 13

    elif mc_change >= 15:
        score += 9

    elif mc_change >= 10:
        score += 5

    # --------------------------------------------------------
    # VOLUME ACCELERATION
    # --------------------------------------------------------

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
        score -= 35

    elif price_change5m <= -20:
        score -= 30

    elif price_change5m <= -15:
        score -= 25

    elif price_change5m <= -10:
        score -= 15

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
    data,
    score,
    alert_type,
    mc_change=0,
    volume_change=0
):

    symbol = data["symbol"]

    market_cap = data[
        "market_cap"
    ]

    liquidity = data[
        "liquidity"
    ]

    volume5m = data[
        "volume5m"
    ]

    buys5m = data[
        "buys5m"
    ]

    sells5m = data[
        "sells5m"
    ]

    buy_pressure = data[
        "buy_pressure"
    ]

    price_change5m = data[
        "price_change5m"
    ]

    age_minutes = data[
        "age_minutes"
    ]

    pool_address = data[
        "pool_address"
    ]

    chart = (
        f"https://dexscreener.com/"
        f"solana/{pool_address}"
    )

    if alert_type == "FIRST SIGHT":

        headline = (
            "🚨 WEB3RAY V12 — "
            "EARLY DISCOVERY"
        )

    else:

        headline = (
            "🚀 WEB3RAY V12 — "
            "MOMENTUM CONFIRMED"
        )

    message = f"""{headline}

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

⏱️ Pool age: {age_minutes:.1f} min

🎯 Target zone:
$5K–$15K

⚠️ Signal only — DYOR.

🔗 {chart}
"""

    response = session.post(
        f"https://api.telegram.org/"
        f"bot{token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": message
        },
        timeout=10
    )

    response.raise_for_status()


# ============================================================
# SINGLE SCAN
# ============================================================

def scan_once(token, chat_id):

    print("")
    print("================================")
    print("WEB3RAY V12 — NEW POOL SCAN")
    print("================================")

    pools = (
        discover_new_raydium_pools()
    )

    print(
        f"RAYDIUM NEW POOLS: "
        f"{len(pools)}"
    )

    alerts_sent = 0

    for pool in pools:

        try:

            data = parse_pool(
                pool
            )

        except Exception as e:

            print(
                f"PARSE ERROR: "
                f"{type(e).__name__}: {e}"
            )

            continue

        symbol = data[
            "symbol"
        ]

        market_cap = data[
            "market_cap"
        ]

        liquidity = data[
            "liquidity"
        ]

        volume5m = data[
            "volume5m"
        ]

        buys5m = data[
            "buys5m"
        ]

        sells5m = data[
            "sells5m"
        ]

        buy_pressure = data[
            "buy_pressure"
        ]

        price_change5m = data[
            "price_change5m"
        ]

        age_minutes = data[
            "age_minutes"
        ]

        pool_address = data[
            "pool_address"
        ]

        if not pool_address:
            continue

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
        # HARD FILTERS
        # ----------------------------------------------------

        if market_cap < MIN_MC:

            print(
                f"REJECT ${symbol}: "
                f"MC TOO LOW"
            )

            continue

        if market_cap > MAX_TRACKING_MC:

            print(
                f"REJECT ${symbol}: "
                f"MC TOO HIGH"
            )

            continue

        if liquidity < MIN_LIQUIDITY:

            print(
                f"REJECT ${symbol}: "
                f"LIQUIDITY TOO LOW"
            )

            continue

        if age_minutes > MAX_AGE_MINUTES:

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

        if price_change5m <= MAX_5M_DROP:

            print(
                f"🚫 REJECT ${symbol}: "
                f"5M DUMP "
                f"{price_change5m:+.1f}%"
            )

            continue

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

        key = (
            data["token_address"]
            or pool_address
        )

        previous = watchlist.get(
            key,
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
            market_cap=market_cap,
            liquidity=liquidity,
            volume5m=volume5m,
            volume1h=data[
                "volume1h"
            ],
            buys5m=buys5m,
            sells5m=sells5m,
            price_change5m=price_change5m,
            age_minutes=age_minutes,
            mc_change=mc_change,
            volume_change=volume_change
        )

        print(
            f"SCORE ${symbol}: "
            f"{score}/100"
        )

        # ----------------------------------------------------
        # SAVE STATE
        # ----------------------------------------------------

        watchlist[key] = {
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
                    f"FIRST SIGHT ABOVE "
                    f"$15K"
                )

                continue

            if score < MIN_FIRST_SIGHT_SCORE:

                print(
                    f"TRACKING ${symbol}: "
                    f"SCORE {score}"
                )

                continue

            if key in alerted_tokens:

                continue

            print(
                f"🚨 EARLY DISCOVERY: "
                f"${symbol}"
            )

            try:

                send_alert(
                    token=token,
                    chat_id=chat_id,
                    data=data,
                    score=score,
                    alert_type="FIRST SIGHT"
                )

                alerted_tokens.add(
                    key
                )

                alerts_sent += 1

            except Exception as e:

                print(
                    f"TELEGRAM ERROR: "
                    f"{type(e).__name__}: {e}"
                )

            continue

        # ----------------------------------------------------
        # MOMENTUM
        # ----------------------------------------------------

        print(
            f"MOMENTUM ${symbol} | "
            f"MC={mc_change:+.1f}% | "
            f"VOL={volume_change:+.1f}% | "
            f"SCORE={score}"
        )

        strong_mc_move = (
            mc_change >= 15
        )

        strong_volume_move = (
            volume_change >= 40
        )

        strong_price_move = (
            price_change5m >= 10
        )

        if score < MIN_MOMENTUM_SCORE:

            continue

        if not (
            strong_mc_move
            or strong_volume_move
            or strong_price_move
        ):

            continue

        if key in alerted_tokens:

            continue

        print(
            f"🚀 MOMENTUM CONFIRMED: "
            f"${symbol}"
        )

        try:

            send_alert(
                token=token,
                chat_id=chat_id,
                data=data,
                score=score,
                alert_type="MOMENTUM",
                mc_change=mc_change,
                volume_change=volume_change
            )

            alerted_tokens.add(
                key
            )

            alerts_sent += 1

        except Exception as e:

            print(
                f"TELEGRAM ERROR: "
                f"{type(e).__name__}: {e}"
            )

        time.sleep(0.1)

    print("")
    print(
        f"SCAN COMPLETE — "
        f"{alerts_sent} ALERT(S)"
    )

    return alerts_sent


# ============================================================
# MAIN LOOP
# ============================================================

def get_new_tokens(token, chat_id):

    print("")
    print("================================")
    print("WEB3RAY V12 STARTED")
    print("================================")

    print(
        "DISCOVERY: "
        "GECKOTERMINAL NEW SOLANA POOLS"
    )

    print(
        "DEX FILTER: RAYDIUM"
    )

    print(
        "TARGET MC: $5K–$15K"
    )

    print(
        f"RUN TIME: "
        f"{RUN_SECONDS} seconds"
    )

    print(
        f"SCAN EVERY: "
        f"{SCAN_INTERVAL_SECONDS} seconds"
    )

    started = time.time()

    total_alerts = 0

    while (
        time.time() - started
        < RUN_SECONDS
    ):

        try:

            total_alerts += scan_once(
                token,
                chat_id
            )

        except Exception as e:

            print(
                f"SCAN ERROR: "
                f"{type(e).__name__}: {e}"
            )

        elapsed = (
            time.time() - started
        )

        if elapsed >= RUN_SECONDS:
            break

        print(
            f"WAITING "
            f"{SCAN_INTERVAL_SECONDS}s..."
        )

        time.sleep(
            SCAN_INTERVAL_SECONDS
        )

    print("")
    print("================================")

    print(
        f"WEB3RAY V12 FINISHED — "
        f"{total_alerts} TOTAL ALERT(S)"
    )

    print("================================")
