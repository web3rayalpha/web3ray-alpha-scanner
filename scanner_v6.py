import time
from datetime import datetime, timezone

import requests


# ============================================================
# WEB3RAY V13
# RAYDIUM EARLY POOL HUNTER
# ============================================================

VERSION = "V13"

NEW_POOLS_URL = (
    "https://api.geckoterminal.com/api/v2/"
    "networks/solana/new_pools"
)

# ============================================================
# TARGET SETTINGS
# ============================================================

MIN_MC = 5_000
MAX_FIRST_SIGHT_MC = 15_000
MAX_TRACKING_MC = 100_000

MIN_LIQUIDITY = 1_000
MAX_AGE_MINUTES = 30

MIN_VOLUME_5M = 100
MIN_BUY_PRESSURE = 55

# Reject hard dumps.
MAX_5M_DROP = -15

# Alert thresholds.
MIN_FIRST_SIGHT_SCORE = 60
MIN_MOMENTUM_SCORE = 70

# ============================================================
# RUNTIME
# ============================================================

RUN_SECONDS = 240
SCAN_INTERVAL_SECONDS = 45

# Page 1 = newest pools.
NEW_POOL_PAGES = 1


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "Accept": "application/json",
    "User-Agent": "Web3Ray-Alpha-Scanner/13.0"
})


# ============================================================
# STATE
# ============================================================

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
# RAYDIUM DETECTION
# ============================================================

def is_raydium_pool(pool, included):
    """
    Detect Raydium using several possible GeckoTerminal
    representations.

    Accepts:
      - raydium
      - raydium-clmm
      - raydium-cpmm
      - any DEX id/name containing "raydium"
    """

    relationships = pool.get(
        "relationships",
        {}
    )

    dex_relationship = (
        relationships
        .get("dex", {})
        .get("data", {})
    )

    relationship_id = str(
        dex_relationship.get(
            "id",
            ""
        )
    ).lower().strip()

    # Direct relationship match.
    if "raydium" in relationship_id:
        return True, relationship_id, relationship_id

    # Search included DEX records.
    for item in included:

        if item.get("type") != "dex":
            continue

        item_id = str(
            item.get(
                "id",
                ""
            )
        ).lower().strip()

        if (
            relationship_id
            and item_id != relationship_id
        ):
            continue

        attributes = item.get(
            "attributes",
            {}
        )

        dex_name = str(
            attributes.get(
                "name",
                ""
            )
        ).lower().strip()

        if "raydium" in dex_name:
            return True, item_id, dex_name

    return False, relationship_id, ""


# ============================================================
# DISCOVERY
# ============================================================

def get_new_pools(page=1):
    try:

        response = session.get(
            NEW_POOLS_URL,
            params={
                "include": (
                    "base_token,"
                    "quote_token,"
                    "dex"
                ),
                "page": page
            },
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(
            data,
            dict
        ):
            return [], []

        pools = data.get(
            "data",
            []
        )

        included = data.get(
            "included",
            []
        )

        if not isinstance(
            pools,
            list
        ):
            pools = []

        if not isinstance(
            included,
            list
        ):
            included = []

        return pools, included

    except Exception as e:

        print(
            f"NEW POOLS ERROR: "
            f"{type(e).__name__}: {e}"
        )

        return [], []


def discover_new_raydium_pools():

    all_pools = []
    all_included = []

    for page in range(
        1,
        NEW_POOL_PAGES + 1
    ):

        pools, included = (
            get_new_pools(page)
        )

        print(
            f"NEW POOLS PAGE {page}: "
            f"{len(pools)}"
        )

        all_pools.extend(
            pools
        )

        all_included.extend(
            included
        )

        time.sleep(0.2)

    # ========================================================
    # DEBUG DEX IDs
    # ========================================================

    dex_ids = []
    dex_names = []

    for pool in all_pools:

        relationships = pool.get(
            "relationships",
            {}
        )

        dex_data = (
            relationships
            .get("dex", {})
            .get("data", {})
        )

        dex_id = str(
            dex_data.get(
                "id",
                ""
            )
        ).strip()

        if dex_id:
            dex_ids.append(
                dex_id
            )

    for item in all_included:

        if item.get("type") != "dex":
            continue

        attributes = item.get(
            "attributes",
            {}
        )

        name = str(
            attributes.get(
                "name",
                ""
            )
        ).strip()

        if name:
            dex_names.append(
                name
            )

    unique_dex_ids = sorted(
        set(dex_ids)
    )

    unique_dex_names = sorted(
        set(dex_names)
    )

    print(
        "DEX IDS FOUND: "
        + (
            ", ".join(
                unique_dex_ids
            )
            if unique_dex_ids
            else "NONE"
        )
    )

    print(
        "DEX NAMES FOUND: "
        + (
            ", ".join(
                unique_dex_names
            )
            if unique_dex_names
            else "NONE"
        )
    )

    # ========================================================
    # RAYDIUM FILTER
    # ========================================================

    raydium = []
    seen = set()

    for pool in all_pools:

        pool_id = str(
            pool.get(
                "id",
                ""
            )
        )

        if pool_id in seen:
            continue

        seen.add(
            pool_id
        )

        is_ray, dex_id, dex_name = (
            is_raydium_pool(
                pool,
                all_included
            )
        )

        if not is_ray:
            continue

        raydium.append(
            pool
        )

        print(
            f"RAYDIUM MATCH | "
            f"DEX_ID={dex_id} | "
            f"DEX_NAME="
            f"{dex_name or 'relationship match'}"
        )

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

    # --------------------------------------------------------
    # POOL
    # --------------------------------------------------------

    pool_address = attributes.get(
        "address"
    )

    pool_name = attributes.get(
        "name",
        "UNKNOWN"
    )

    # --------------------------------------------------------
    # BASE TOKEN
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

    symbol = str(
        pool_name
    ).split(
        " / "
    )[0].strip()

    if not symbol:
        symbol = "UNKNOWN"

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

    # New microcaps sometimes have no
    # verified market cap yet.
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
        volume_data.get(
            "m5"
        )
    )

    volume1h = safe_float(
        volume_data.get(
            "h1"
        )
    )

    # --------------------------------------------------------
    # PRICE CHANGE
    # --------------------------------------------------------

    price_data = attributes.get(
        "price_change_percentage",
        {}
    )

    price_change5m = safe_float(
        price_data.get(
            "m5"
        )
    )

    price_change1h = safe_float(
        price_data.get(
            "h1"
        )
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
        tx5m.get(
            "buys"
        )
    )

    sells5m = safe_int(
        tx5m.get(
            "sells"
        )
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
    # MARKET CAP
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
        min(
            score,
            100
        )
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
    market_cap = data["market_cap"]
    liquidity = data["liquidity"]
    volume5m = data["volume5m"]

    buys5m = data["buys5m"]
    sells5m = data["sells5m"]

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
        "https://dexscreener.com/"
        f"solana/{pool_address}"
    )

    if alert_type == "FIRST SIGHT":

        headline = (
            "🚨 WEB3RAY V13 — "
            "EARLY DISCOVERY"
        )

    else:

        headline = (
            "🚀 WEB3RAY V13 — "
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
        (
            "https://api.telegram.org/"
            f"bot{token}/sendMessage"
        ),
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

def scan_once(
    token,
    chat_id
):

    print("")
    print(
        "================================"
    )
    print(
        "WEB3RAY V13 — NEW POOL SCAN"
    )
    print(
        "================================"
    )

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

        
