import requests
import time
from datetime import datetime, timezone

# ============================================================
# WEB3RAY V10 — EARLY RUNNER SCANNER
# ============================================================

PROFILES_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
TOKENS_URL = "https://api.dexscreener.com/tokens/v1/solana/{}"

# ============================================================
# TARGET
# ============================================================

MIN_MARKET_CAP = 5_000
MAX_MARKET_CAP = 200_000

MIN_LIQUIDITY = 500
MAX_PAIR_AGE_MINUTES = 90

# Alert thresholds
MIN_FIRST_SIGHT_SCORE = 55
MIN_MOMENTUM_SCORE = 55

# Scan repeatedly during one GitHub Actions job
RUN_SECONDS = 240
SCAN_INTERVAL_SECONDS = 45

# ============================================================
# STATE
# ============================================================

watchlist = {}
alerted_tokens = set()


# ============================================================
# AGE
# ============================================================

def get_age_minutes(pair):
    created_at = pair.get("pairCreatedAt")

    if not created_at:
        return 999999

    try:
        created_seconds = float(created_at) / 1000
        now = datetime.now(timezone.utc).timestamp()

        return max(
            0,
            (now - created_seconds) / 60
        )

    except Exception:
        return 999999


# ============================================================
# DISCOVERY
# ============================================================

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


# ============================================================
# GET TOKEN PAIRS
# ============================================================

def get_pairs(addresses):

    if not addresses:
        return []

    results = []

    for start in range(0, len(addresses), 30):

        batch = addresses[start:start + 30]

        url = TOKENS_URL.format(
            ",".join(batch)
        )

        try:

            response = requests.get(
                url,
                timeout=20
            )

            response.raise_for_status()

            data = response.json()

            if isinstance(data, list):
                results.extend(data)

        except Exception as e:

            print(
                f"PAIR REQUEST ERROR: {type(e).__name__}: {e}"
            )

        time.sleep(0.3)

    return results


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
    # VERY LOW MARKET CAP
    # --------------------------------------------------------

    if market_cap <= 10_000:
        score += 25

    elif market_cap <= 25_000:
        score += 22

    elif market_cap <= 50_000:
        score += 18

    elif market_cap <= 100_000:
        score += 14

    elif market_cap <= 200_000:
        score += 8

    # --------------------------------------------------------
    # AGE
    # --------------------------------------------------------

    if age_minutes <= 5:
        score += 20

    elif age_minutes <= 10:
        score += 18

    elif age_minutes <= 20:
        score += 15

    elif age_minutes <= 30:
        score += 12

    elif age_minutes <= 60:
        score += 8

    elif age_minutes <= 90:
        score += 4

    # --------------------------------------------------------
    # LIQUIDITY
    # --------------------------------------------------------

    if liquidity >= 20_000:
        score += 15

    elif liquidity >= 10_000:
        score += 13

    elif liquidity >= 5_000:
        score += 11

    elif liquidity >= 2_000:
        score += 9

    elif liquidity >= 500:
        score += 5

    # --------------------------------------------------------
    # 5M VOLUME
    # --------------------------------------------------------

    if volume5m >= 20_000:
        score += 20

    elif volume5m >= 10_000:
        score += 17

    elif volume5m >= 5_000:
        score += 14

    elif volume5m >= 1_000:
        score += 10

    elif volume5m >= 300:
        score += 6

    elif volume5m >= 100:
        score += 3

    # --------------------------------------------------------
    # BUY PRESSURE
    # --------------------------------------------------------

    total_trades = buys5m + sells5m

    if total_trades > 0:

        buy_ratio = buys5m / total_trades

        if buy_ratio >= 0.75:
            score += 15

        elif buy_ratio >= 0.65:
            score += 11

        elif buy_ratio >= 0.55:
            score += 6

    # --------------------------------------------------------
    # PRICE MOMENTUM
    # --------------------------------------------------------

    if price_change5m >= 50:
        score += 15

    elif price_change5m >= 25:
        score += 12

    elif price_change5m >= 10:
        score += 8

    elif price_change5m >= 5:
        score += 4

    # --------------------------------------------------------
    # 1H VOLUME CONFIRMATION
    # --------------------------------------------------------

    if volume1h >= 50_000:
        score += 8

    elif volume1h >= 20_000:
        score += 6

    elif volume1h >= 10_000:
        score += 4

    # --------------------------------------------------------
    # MARKET CAP MOMENTUM
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # VOLUME MOMENTUM
    # --------------------------------------------------------

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
    chart
):

    total_trades = buys5m + sells5m

    if total_trades > 0:

        buy_ratio = (
            buys5m / total_trades
        ) * 100

    else:

        buy_ratio = 0

    message = f"""🚨 WEB3RAY V10 — {alert_type}

⭐ Score: {score}/100

🪙 ${symbol}

📊 MC: ${market_cap:,.0f}
💧 Liquidity: ${liquidity:,.0f}

📈 Volume 5m: ${volume5m:,.0f}

🟢 Buys: {buys5m}
🔴 Sells: {sells5m}
📊 Buy pressure: {buy_ratio:.0f}%

🔥 Price 5m: {price_change5m:+.1f}%

⏱️ Age: {age_minutes:.1f} min

⚡ EARLY RUNNER SIGNAL

🔗 {chart}
"""

    response = requests.post(
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

def scan_once(token, chat_id):

    print("")
    print("================================")
    print("WEB3RAY V10 — SCAN")
    print("================================")

    try:

        profiles = get_latest_profiles()

    except Exception as e:

        print(
            f"PROFILE ERROR: {type(e).__name__}: {e}"
        )

        return 0

    addresses = []

    for profile in profiles:

        if profile.get("chainId") != "solana":
            continue

        address = profile.get("tokenAddress")

        if not address:
            continue

        if address in addresses:
            continue

        addresses.append(address)

    print(
        f"SOLANA PROFILES: {len(addresses)}"
    )

    pairs = get_pairs(addresses)

    print(
        f"PAIRS RECEIVED: {len(pairs)}"
    )

    alerts_sent = 0

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

        symbol = base.get(
            "symbol",
            "UNKNOWN"
        )

        market_cap = float(
            pair.get("marketCap") or 0
        )

        liquidity = float(
            pair.get(
                "liquidity",
                {}
            ).get("usd") or 0
        )

        volume = pair.get(
            "volume",
            {}
        )

        volume5m = float(
            volume.get("m5") or 0
        )

        volume1h = float(
            volume.get("h1") or 0
        )

        txns = pair.get(
            "txns",
            {}
        )

        txns5m = txns.get(
            "m5",
            {}
        )

        buys5m = int(
            txns5m.get("buys") or 0
        )

        sells5m = int(
            txns5m.get("sells") or 0
        )

        price_change = pair.get(
            "priceChange",
            {}
        )

        price_change5m = float(
            price_change.get("m5") or 0
        )

        age_minutes = get_age_minutes(
            pair
        )

        print(
            f"CHECK ${symbol} | "
            f"MC=${market_cap:.0f} | "
            f"LQ=${liquidity:.0f} | "
            f"V5=${volume5m:.0f} | "
            f"AGE={age_minutes:.1f}m | "
            f"BUYS={buys5m} | "
            f"SELLS={sells5m} | "
            f"P5={price_change5m:+.1f}%"
        )

        # ----------------------------------------------------
        # BASIC FILTERS
        # ----------------------------------------------------

        if market_cap < MIN_MARKET_CAP:
            continue

        if market_cap > MAX_MARKET_CAP:
            continue

        if liquidity < MIN_LIQUIDITY:
            continue

        if age_minutes > MAX_PAIR_AGE_MINUTES:
            continue

        # ----------------------------------------------------
        # PREVIOUS SNAPSHOT
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # SAVE SNAPSHOT
        # ----------------------------------------------------

        watchlist[address] = {
            "market_cap": market_cap,
            "volume5m": volume5m,
            "liquidity": liquidity,
            "timestamp": time.time()
        }

        # ----------------------------------------------------
        # PRINT SCORE
        # ----------------------------------------------------

        print(
            f"SCORE ${symbol}: {score}/100"
        )

        # ----------------------------------------------------
        # FIRST-SIGHT ALERT
        # ----------------------------------------------------

        if previous_mc == 0:

            if score >= MIN_FIRST_SIGHT_SCORE:

                if address not in alerted_tokens:

                    print(
                        f"🚨 FIRST SIGHT ALERT: ${symbol}"
                    )

                    try:

                        send_alert(
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
                            "FIRST SIGHT",
                            pair.get("url", "")
                        )

                        alerted_tokens.add(address)
                        alerts_sent += 1

                    except Exception as e:

                        print(
                            f"TELEGRAM ERROR: {e}"
                        )

            else:

                print(
                    f"TRACKING ${symbol}"
                )

            continue

        # ----------------------------------------------------
        # MOMENTUM
        # ----------------------------------------------------

        mc_change = 0

        if previous_mc > 0:

            mc_change = (
                (market_cap - previous_mc)
                / previous_mc
            ) * 100

        volume_change = 0

        if previous_volume > 0:

            volume_change = (
                (volume5m - previous_volume)
                / previous_volume
            ) * 100

        print(
            f"MOMENTUM ${symbol} | "
            f"MC={mc_change:+.1f}% | "
            f"VOL={volume_change:+.1f}% | "
            f"SCORE={score}"
        )

        # ----------------------------------------------------
        # MOMENTUM ALERT
        # ----------------------------------------------------

        if score >= MIN_MOMENTUM_SCORE:

            if (
                mc_change >= 10
                or volume_change >= 25
                or price_change5m >= 10
            ):

                if address not in alerted_tokens:

                    print(
                        f"🚨 MOMENTUM ALERT: ${symbol}"
                    )

                    try:

                        send_alert(
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
                            "MOMENTUM",
                            pair.get("url", "")
                        )

                        alerted_tokens.add(address)
                        alerts_sent += 1

                    except Exception as e:

                        print(
                            f"TELEGRAM ERROR: {e}"
                        )

        time.sleep(0.2)

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
    print("WEB3RAY V10 STARTED")
    print("================================")
    print(
        f"RUN TIME: {RUN_SECONDS} seconds"
    )
    print(
        f"SCAN EVERY: {SCAN_INTERVAL_SECONDS} seconds"
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

        elapsed = time.time() - started

        if elapsed >= RUN_SECONDS:
            break

        print(
            f"WAITING {SCAN_INTERVAL_SECONDS}s..."
        )

        time.sleep(
            SCAN_INTERVAL_SECONDS
        )

    print("")
    print("================================")
    print(
        f"WEB3RAY V10 FINISHED — "
        f"{total_alerts} TOTAL ALERT(S)"
    )
    print("================================")
