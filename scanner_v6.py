import os
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import requests

# ----------------------------- CONFIG ---------------------------------

NETWORK = "solana"

GECKO_NEW_POOLS_URL = (
    "https://api.geckoterminal.com/api/v2/networks/solana/new_pools"
)
DEXSCREENER_TOKEN_URL = (
    "https://api.dexscreener.com/latest/dex/tokens/{}"
)
TELEGRAM_URL = "https://api.telegram.org/bot{}/sendMessage"

MIN_MARKET_CAP_USD = float(os.getenv("MIN_MARKET_CAP_USD", "5000"))
MAX_MARKET_CAP_USD = float(os.getenv("MAX_MARKET_CAP_USD", "15000"))
MIN_LIQUIDITY_USD = float(os.getenv("MIN_LIQUIDITY_USD", "3000"))
MAX_POOL_AGE_MINUTES = int(os.getenv("MAX_POOL_AGE_MINUTES", "90"))
MIN_VOLUME_5M_USD = float(os.getenv("MIN_VOLUME_5M_USD", "100"))
MIN_TXNS_5M = int(os.getenv("MIN_TXNS_5M", "2"))
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "30"))
RUN_SECONDS = int(os.getenv("RUN_SECONDS", "240"))
GECKO_PAGES = int(os.getenv("GECKO_PAGES", "3"))
MAX_ALERTS_PER_RUN = int(os.getenv("MAX_ALERTS_PER_RUN", "8"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(message)s",
)

log = logging.getLogger("web3ray-scanner")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Web3Ray-Alpha-Scanner/1.0",
    "Accept": "application/json",
})

SEEN_POOL_IDS: Set[str] = set()
ALERTED_TOKEN_ADDRESSES: Set[str] = set()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_json(
    url: str,
    params: Optional[dict] = None,
    timeout: int = 15,
) -> Optional[dict]:
    try:
        response = SESSION.get(url, params=params, timeout=timeout)

        if response.status_code == 429:
            log.warning("Rate limited by %s", url.split("/")[2])
            return None

        response.raise_for_status()
        data = response.json()

        return data if isinstance(data, dict) else None

    except (requests.RequestException, ValueError) as exc:
        log.warning(
            "Request failed (%s): %s",
            url.split("/")[2],
            exc,
        )
        return None


def _fetch_new_pools() -> List[dict]:
    pools: List[dict] = []

    for page in range(1, max(1, GECKO_PAGES) + 1):
        payload = _get_json(
            GECKO_NEW_POOLS_URL,
            params={"page": page},
        )

        if not payload:
            continue

        data = payload.get("data", [])

        if isinstance(data, list):
            pools.extend(
                item for item in data if isinstance(item, dict)
            )

        time.sleep(0.25)

    return pools


def _relationship_address(pool: dict, key: str) -> str:
    try:
        value = str(
            pool.get("relationships", {})
            .get(key, {})
            .get("data", {})
            .get("id", "")
        )

        if value.startswith("solana_"):
            return value.split("_", 1)[1]

        return value

    except AttributeError:
        return ""


def _pool_record(item: dict) -> Optional[dict]:
    attrs = item.get("attributes") or {}
    pool_id = str(item.get("id") or "")

    if not pool_id:
        return None

    dex_id = str(attrs.get("dex_id") or "").lower()

    # Only Raydium pools.
    if "raydium" not in dex_id:
        return None

    created_at = (
        attrs.get("pool_created_at")
        or attrs.get("created_at")
    )

    age_minutes = None

    if created_at:
        try:
            created = datetime.fromisoformat(
                str(created_at).replace("Z", "+00:00")
            )

            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            age_minutes = max(
                0.0,
                (
                    datetime.now(timezone.utc)
                    - created.astimezone(timezone.utc)
                ).total_seconds() / 60,
            )

        except (TypeError, ValueError):
            age_minutes = None

    base_id = _relationship_address(item, "base_token")
    quote_id = _relationship_address(item, "quote_token")

    if not base_id:
        base_id = str(attrs.get("base_token_address") or "")

    if not quote_id:
        quote_id = str(attrs.get("quote_token_address") or "")

    volume_data = attrs.get("volume_usd") or {}
    txn_data = attrs.get("transactions") or {}

    return {
        "pool_id": pool_id,
        "pool_address": str(
            attrs.get("address") or pool_id.split("_")[-1]
        ),
        "name": str(attrs.get("name") or "Unknown pool"),
        "dex_id": dex_id,
        "created_at": created_at,
        "age_minutes": age_minutes,
        "base_token": base_id,
        "quote_token": quote_id,
        "reserve_usd": _number(attrs.get("reserve_in_usd")),
        "price_usd": _number(
            attrs.get("base_token_price_usd")
        ),
        "volume_5m": _number(volume_data.get("m5")),
        "txns_5m": txn_data.get("m5") or {},
    }


def _tx_count(txns: Any) -> int:
    if not isinstance(txns, dict):
        return 0

    buys = int(_number(txns.get("buys")))
    sells = int(_number(txns.get("sells")))

    return buys + sells


def _dexscreener_pair(
    token_address: str,
    pool_address: str,
) -> Optional[dict]:
    if not token_address:
        return None

    payload = _get_json(
        DEXSCREENER_TOKEN_URL.format(token_address)
    )

    if not payload:
        return None

    pairs = payload.get("pairs") or []

    if not isinstance(pairs, list):
        return None

    # Prefer the exact pool address.
    for pair in pairs:
        if not isinstance(pair, dict):
            continue

        if str(pair.get("chainId", "")).lower() != "solana":
            continue

        if (
            pool_address
            and str(pair.get("pairAddress", "")).lower()
            == pool_address.lower()
        ):
            return pair

    # Otherwise choose a Raydium pair on Solana.
    for pair in pairs:
        if not isinstance(pair, dict):
            continue

        if str(pair.get("chainId", "")).lower() != "solana":
            continue

        if "raydium" in str(pair.get("dexId", "")).lower():
            return pair

    return None


def _market_data(pool: dict) -> dict:
    token_address = pool.get("base_token", "")

    pair = _dexscreener_pair(
        token_address,
        pool.get("pool_address", ""),
    )

    if not pair:
        return {
            "token_address": token_address,
            "symbol": "UNKNOWN",
            "token_name": pool.get("name", "Unknown token"),
            "market_cap": 0.0,
            "fdv": 0.0,
            "valuation": 0.0,
            "valuation_label": "MC unavailable",
            "liquidity": pool.get("reserve_usd", 0.0),
            "volume_5m": pool.get("volume_5m", 0.0),
            "txns_5m": _tx_count(pool.get("txns_5m")),
            "price_usd": pool.get("price_usd", 0.0),
            "pair_url": (
                "https://dexscreener.com/solana/"
                + str(pool.get("pool_address", ""))
            ),
            "pair": None,
        }

    base = pair.get("baseToken") or {}

    liquidity_data = pair.get("liquidity") or {}
    volume_data = pair.get("volume") or {}
    txn_data = pair.get("txns") or {}

    liquidity = _number(
        liquidity_data.get("usd"),
        pool.get("reserve_usd", 0.0),
    )

    volume_5m = _number(
        volume_data.get("m5"),
        pool.get("volume_5m", 0.0),
    )

    txns_5m = _tx_count(txn_data.get("m5"))

    market_cap = _number(pair.get("marketCap"))
    fdv = _number(pair.get("fdv"))

    # FDV is a fallback estimate, not the same as market cap.
    if market_cap > 0:
        valuation = market_cap
        valuation_label = "MC"
    elif fdv > 0:
        valuation = fdv
        valuation_label = "FDV estimate"
    else:
        valuation = 0.0
        valuation_label = "MC unavailable"

    pair_address = str(
        pair.get("pairAddress")
        or pool.get("pool_address", "")
    )

    return {
        "token_address": str(
            base.get("address") or token_address
        ),
        "symbol": str(base.get("symbol") or "UNKNOWN"),
        "token_name": str(
            base.get("name") or pool.get("name", "Unknown token")
        ),
        "market_cap": market_cap,
        "fdv": fdv,
        "valuation": valuation,
        "valuation_label": valuation_label,
        "liquidity": liquidity,
        "volume_5m": volume_5m,
        "txns_5m": txns_5m,
        "price_usd": _number(
            pair.get("priceUsd"),
            pool.get("price_usd", 0.0),
        ),
        "pair_url": str(
            pair.get("url")
            or (
                "https://dexscreener.com/solana/"
                + pair_address
            )
        ),
        "pair": pair,
    }


def _score(pool: dict, market: dict) -> tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []

    age = pool.get("age_minutes")
    valuation = _number(market.get("valuation"))
    liquidity = _number(market.get("liquidity"))
    volume = _number(market.get("volume_5m"))
    txns = int(market.get("txns_5m") or 0)

    if age is not None and age <= 15:
        score += 25
        reasons.append("Pool age <= 15 minutes")

    elif age is not None and age <= 45:
        score += 15
        reasons.append("Pool age <= 45 minutes")

    elif age is not None:
        score += 5
        reasons.append("Pool age <= configured maximum")

    if MIN_MARKET_CAP_USD <= valuation <= MAX_MARKET_CAP_USD:
        score += 25
        reasons.append(f"Early valuation ${valuation:,.0f}")

    if liquidity >= MIN_LIQUIDITY_USD:
        score += 20
        reasons.append(f"Liquidity ${liquidity:,.0f}")

    if volume >= MIN_VOLUME_5M_USD:
        score += 15
        reasons.append(f"5m volume ${volume:,.0f}")

    if txns >= MIN_TXNS_5M:
        score += 15
        reasons.append(f"{txns} transactions in 5m")

    return min(score, 100), reasons


def _send_telegram(
    token: str,
    chat_id: str,
    message: str,
) -> bool:
    url = TELEGRAM_URL.format(token)

    try:
        response = SESSION.post(
            url,
            data={
                "chat_id": chat_id,
                "text": message,
                "disable_web_page_preview": True,
            },
            timeout=15,
        )

        if not response.ok:
            log.warning(
                "Telegram returned HTTP %s: %s",
                response.status_code,
                response.text[:250],
            )
            return False

        body = response.json()

        if not body.get("ok"):
            log.warning("Telegram API error: %s", body)
            return False

        return True

    except (requests.RequestException, ValueError) as exc:
        log.warning("Telegram send failed: %s", exc)
        return False


def _alert_text(
    pool: dict,
    market: dict,
    score: int,
    reasons: List[str],
) -> str:
    age = pool.get("age_minutes")

    if age is None:
        age_text = "Unknown"
    else:
        age_text = f"{age:.0f} minutes"

    valuation = _number(market.get("valuation"))
    valuation_label = market.get(
        "valuation_label",
        "Valuation",
    )

    address = market.get("token_address") or "Unavailable"

    if reasons:
        reason_text = "\n".join(
            f"• {reason}" for reason in reasons
        )
    else:
        reason_text = "• Candidate needs manual review"

    return (
        "🛰️ WEB3RAY ALPHA SCANNER\n\n"
        f"🪙 {market.get('token_name', 'Unknown')} "
        f"(${market.get('symbol', 'UNKNOWN')})\n"
        f"📊 {valuation_label}: ${valuation:,.0f}\n"
        f"💧 Liquidity: "
        f"${_number(market.get('liquidity')):,.0f}\n"
        f"📈 5m volume: "
        f"${_number(market.get('volume_5m')):,.0f}\n"
        f"🔁 5m transactions: "
        f"{int(market.get('txns_5m') or 0)}\n"
        f"⏱️ Pool age: {age_text}\n"
        f"⭐ Signal score: {score}/100\n\n"
        f"Why it triggered:\n{reason_text}\n\n"
        f"🔗 DexScreener: {market.get('pair_url', '')}\n"
        f"📋 Token CA: {address}\n\n"
        "⚠️ Signal only, not financial advice. Verify mint/freeze "
        "authority, holders, liquidity, sells, and contract risks "
        "yourself."
    )


def scan_once(token: str, chat_id: str) -> int:
    items = _fetch_new_pools()

    log.info("Fetched %d new-pool records", len(items))

    alerts_sent = 0

    for item in items:
        pool = _pool_record(item)

        if not pool:
            continue

        pool_id = pool["pool_id"]

        if pool_id in SEEN_POOL_IDS:
            continue

        SEEN_POOL_IDS.add(pool_id)

        age = pool.get("age_minutes")

        if age is not None and age > MAX_POOL_AGE_MINUTES:
            continue

        market = _market_data(pool)
        valuation = _number(market.get("valuation"))
        liquidity = _number(market.get("liquidity"))

        # Require a usable valuation in the target range.
        if not (
            MIN_MARKET_CAP_USD
            <= valuation
            <= MAX_MARKET_CAP_USD
        ):
            continue

        if liquidity < MIN_LIQUIDITY_USD:
            continue

        token_address = market.get("token_address")

        if not token_address:
            continue

        if token_address in ALERTED_TOKEN_ADDRESSES:
            continue

        score, reasons = _score(pool, market)

        if score < 45:
            continue

        message = _alert_text(
            pool,
            market,
            score,
            reasons,
        )

        if _send_telegram(token, chat_id, message):
            ALERTED_TOKEN_ADDRESSES.add(token_address)
            alerts_sent += 1

            log.info(
                "Alert sent for %s (score %d)",
                market.get("symbol"),
                score,
            )

            if alerts_sent >= MAX_ALERTS_PER_RUN:
                break

    log.info("Scan complete; alerts sent: %d", alerts_sent)

    return alerts_sent


def get_new_tokens(token: str, chat_id: str) -> None:
    """Entry point imported by main.py."""
    if not token:
        raise ValueError("Telegram BOT_TOKEN is missing")

    if not chat_id:
        raise ValueError("Telegram CHAT_ID is missing")

    log.info("WEB3RAY ALPHA SCANNER STARTED")

    log.info(
        "Filters: valuation $%s-$%s | liquidity >= $%s | "
        "max pool age %sm",
        f"{MIN_MARKET_CAP_USD:,.0f}",
        f"{MAX_MARKET_CAP_USD:,.0f}",
        f"{MIN_LIQUIDITY_USD:,.0f}",
        MAX_POOL_AGE_MINUTES,
    )

    start = time.monotonic()

    while time.monotonic() - start < RUN_SECONDS:
        try:
            scan_once(token, chat_id)
        except Exception:
            log.exception(
                "Unexpected scan error; continuing after a short pause"
            )

        remaining = RUN_SECONDS - (time.monotonic() - start)

        if remaining <= 0:
            break

        time.sleep(
            min(max(5, SCAN_INTERVAL_SECONDS), remaining)
        )

    log.info("WEB3RAY ALPHA SCANNER FINISHED")
