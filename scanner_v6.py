import time
from datetime import datetime, timezone

import requests


# ============================================================
# WEB3RAY V15
# RAYDIUM EARLY POOL HUNTER
# ============================================================

VERSION = "V15"

# ============================================================
# TARGET SETTINGS
# ============================================================

MIN_MC = 5_000
MAX_FIRST_SIGHT_MC = 15_000
MAX_TRACKING_MC = 100_000

MIN_LIQUIDITY = 1_000
MIN_VOLUME_5M = 100
MIN_BUY_PRESSURE = 55

MAX_5M_DROP = -15
MAX_AGE_MINUTES = 30

MIN_FIRST_SIGHT_SCORE = 55
MIN_MOMENTUM_SCORE = 70

# ============================================================
# RUNTIME
# ============================================================

RUN_SECONDS = 240
SCAN_INTERVAL_SECONDS = 30

# More pages = better chance of seeing new pools.
NEW_POOL_PAGES = 3

# ============================================================
# APIS
# ============================================================

GECKO_NEW_POOLS_URL = (
    "https://api.geckoterminal.com/api/v2/"
    "networks/solana/new_pools"
)

DEXSCREENER_TOKEN_PAIRS_URL = (
    "https://api.dexscreener.com/token-pairs/v1/solana/"
)

# ============================================================
# HTTP
# ============================================================

session = requests.Session()

session.headers.update({
    "Accept": "application/json",
    "User-Agent": "Web3Ray-Alpha-Scanner/15.0",
})

# ============================================================
# MEMORY
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

    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        if value is None:
            return default

        return int(float(value))

    except (TypeError, ValueError):
        return default


# ============================================================
# BUY PRESSURE
# ============================================================

def get_buy_pressure(buys, sells):

    total = buys + sells

    if total <= 0:
        return 0.0

    return (buys / total) * 100.0


# ============================================================
# TOKEN AGE
# ============================================================

def get_age_minutes(created_at):

    if not created_at:
        return 999999.0

    try:

        value = str(created_at).replace(
            "Z",
            "+00:00"
        )

        created = datetime.fromisoformat(value)

        if created.tzinfo is None:
            created = created.replace(
                tzinfo=timezone.utc
            )

        now = datetime.now(timezone.utc)

        age = (
            now - created
        ).total_seconds() / 60.0

        return max(0.0, age)

    except Exception:
        return 999999.0


# ============================================================
# GECKO NEW POOLS
# ============================================================

def get_new_pools(page=1):

    try:

        response = session.get(
            GECKO_NEW_POOLS_URL,
            params={
                "include": (
                    "base_token,"
                    "quote_token,"
                    "dex"
                ),
                "page": page,
            },
            timeout=20,
        )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            return [], []

        pools = payload.get(
            "data",
            []
        )

        included = payload.get(
            "included",
            []
        )

        if not isinstance(pools, list):
            pools = []

        if not isinstance(included, list):
            included = []

        return pools, included

    except Exception as exc:

        print(
            f"NEW POOLS ERROR | "
            f"{type(exc).__name__}: {exc}"
        )

        return [], []


# ============================================================
# RAYDIUM DETECTION
# ============================================================

def is_raydium_pool(pool, included):

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
    ).lower().strip()

    # Direct match.
    if "raydium" in dex_id:
        return True

    # Included DEX match.
    for item in included:

        if item.get("type") != "dex":
            continue

        item_id = str(
            item.get(
                "id",
                ""
            )
        ).lower().strip()

        if dex_id and item_id != dex_id:
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
            return True

    return False


# ============================================================
# DISCOVER RAYDIUM POOLS
# ============================================================

def discover_new_raydium_pools():

    raydium_pools = []
    seen = set()

    for page in range(
        1,
        NEW_POOL_PAGES + 1
    ):

        pools, included = get_new_pools(
            page
        )

        print(
            f"NEW POOLS PAGE {page}: "
            f"{len(pools)}"
        )

        for pool in pools:

            pool_id = str(
                pool.get(
                    "id",
                    ""
                )
            )

            if not pool_id:
                continue

            if pool_id in seen:
                continue

            seen.add(pool_id)

            if is_raydium_pool(
                pool,
                included
            ):
                raydium_pools.append(
                    pool
                )

        if page < NEW_POOL_PAGES:
            time.sleep(0.25)

    print(
        f"RAYDIUM NEW POOLS: "
        f"{len(raydium_pools)}"
    )

    return raydium_pools


# ============================================================
# PARSE GECKO POOL
# ============================================================

def parse_gecko_pool(pool):

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

    pool_address = str(
        attributes.get(
            "address",
            ""
        )
    ).strip()

    # --------------------------------------------------------
    # BASE TOKEN
    # --------------------------------------------------------

    base_token = (
        relationships
        .get("base_token", {})
        .get("data", {})
    )

    token_address = str(
        base_token.get(
            "id",
            ""
        )
    ).strip()

    if token_address.startswith(
        "solana_"
    ):
        token_address = token_address[7:]

    # --------------------------------------------------------
    # SYMBOL
    # --------------------------------------------------------

    pool_name = str(
        attributes.get(
            "name",
            "UNKNOWN"
        )
    ).strip()

    symbol = (
        pool_name
        .split(" / ")[0]
        .strip()
    )

    if not symbol:
        symbol = "UNKNOWN"

    # --------------------------------------------------------
    # MARKET CAP
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

    if not isinstance(
        volume_data,
        dict
    ):
        volume_data = {}

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

    if not isinstance(
        price_data,
        dict
    ):
        price_data = {}

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

    if not isinstance(
        transactions,
        dict
    ):
        transactions = {}

    tx5m = transactions.get(
        "m5",
        {}
    )

    if not isinstance(
        tx5m,
        dict
    ):
        tx5m = {}

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
    }


# ============================================================
# DEXSCREENER ENRICHMENT
# ============================================================

def enrich_from_dexscreener(data):

    token_address = data.get(
        "token_address",
        ""
    )

    if not token_address:
        return data

    original_pool = data.get(
        "pool_address",
        ""
    )

    try:

        response = session.get(
            f"{DEXSCREENER_TOKEN_PAIRS_URL}"
            f"{token_address}",
            timeout=10,
        )

        if response.status_code != 200:
            return data

        pairs = response.json()

        if not isinstance(
            pairs,
            list
        ):
            return data

        raydium_pairs = []

        for pair in pairs:

            dex_id = str(
                pair.get(
                    "dexId",
                    ""
                )
            ).lower()

            if dex_id == "raydium":
                raydium_pairs.append(
                    pair
                )

        if not raydium_pairs:
            return data

        # Prefer the exact discovered pool.
        selected = None

        for pair in raydium_pairs:

            if str(
                pair.get(
                    "pairAddress",
                    ""
                )
            ) == original_pool:

                selected = pair
                break

        # Otherwise use the most liquid Raydium pair.
        if selected is None:

            selected = max(
                raydium_pairs,
                key=lambda pair: safe_float(
                    (
                        pair.get(
                            "liquidity",
                            {}
                        )
                        or {}
                    ).get(
                        "usd"
                    )
                    if isinstance(
                        pair.get(
                            "liquidity",
                            {}
                        ),
                        dict
                    )
                    else 0
                )
            )

        # ----------------------------------------------------
        # LIQUIDITY
        # ----------------------------------------------------

        liquidity_data = selected.get(
            "liquidity",
            {}
        )

        if isinstance(
            liquidity_data,
            dict
        ):

            ds_liquidity = safe_float(
                liquidity_data.get(
                    "usd"
                )
            )

            if ds_liquidity > 0:
                data["liquidity"] = (
                    ds_liquidity
                )

        # ----------------------------------------------------
        # MARKET CAP
        # ----------------------------------------------------

        ds_mc = safe_float(
            selected.get(
                "marketCap"
            )
        )

        ds_fdv = safe_float(
            selected.get(
                "fdv"
            )
        )

        if ds_mc > 0:
            data["market_cap"] = ds_mc

        elif (
            ds_fdv > 0
            and data["market_cap"] <= 0
        ):
            data["market_cap"] = ds_fdv

        # ----------------------------------------------------
        # VOLUME
        # ----------------------------------------------------

        volume = selected.get(
            "volume",
            {}
        )

        if isinstance(
            volume,
            dict
        ):

            ds_v5 = safe_float(
                volume.get(
                    "m5"
                )
            )

            ds_v1h = safe_float(
                volume.get(
                    "h1"
                )
            )

            if ds_v5 > 0:
                data["volume5m"] = ds_v5

            if ds_v1h > 0:
                data["volume1h"] = ds_v1h

        # ----------------------------------------------------
        # PRICE CHANGE
        # ----------------------------------------------------

        changes = selected.get(
            "priceChange",
            {}
        )

        if isinstance(
            changes,
            dict
        ):

            data["price_change5m"] = (
                safe_float(
                    changes.get(
                        "m5"
                    )
                )
            )

            data["price_change1h"] = (
                safe_float(
                    changes.get(
                        "h1"
                    )
                )
            )

        # ----------------------------------------------------
        # TRANSACTIONS
        # ----------------------------------------------------

        txns = selected.get(
            "txns",
            {}
        )

        if isinstance(
            txns,
            dict
        ):

            tx5 = txns.get(
                "m5",
                {}
            )

            if isinstance(
                tx5,
                dict
            ):

                data["buys5m"] = (
                    safe_int(
                        tx5.get(
                            "buys"
                        )
                    )
                )

                data["sells5m"] = (
                    safe_int(
                        tx5.get(
                            "sells"
                        )
                    )
                )

                data["buy_pressure"] = (
                    get_buy_pressure(
                        data["buys5m"],
                        data["sells5m"]
                    )
                )

        # IMPORTANT:
        # Keep the original Gecko pool address
        # and original age. This prevents enrichment
        # from accidentally replacing the new pool
        # with an older pair.

    except Exception as exc:

        print(
            f"DEX ENRICH ERROR "
            f"${data.get('symbol', '?')} | "
            f"{type(exc).__name__}: {exc}"
        )

    return data


# ============================================================
# SCORE
# ============================================================

def calculate_score(
    data,
    mc_change,
    volume_change
):

    score = 0

    market_cap = data[
        "market_cap"
    ]

    liquidity = data[
        "liquidity"
    ]

    volume5m = data[
        "volume5m"
    ]

    volume1h = data[
        "volume1h"
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
    # VOLUME 5M
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

    elif pr
