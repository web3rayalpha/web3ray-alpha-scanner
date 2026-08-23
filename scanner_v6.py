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
            # EARLY ENTRY FILTER
            # =========================

            if market_cap < MIN_MARKET_CAP:
                print(f"REJECT {symbol} → MC TOO LOW")
                continue

            if market_cap > MAX_MARKET_CAP:
                print(f"REJECT {symbol} → MC TOO HIGH")
                continue

            if liquidity < MIN_LIQUIDITY:
                print(f"REJECT {symbol} → LIQUIDITY TOO LOW")
                continue

            if volume5m < MIN_VOLUME_5M:
                print(f"REJECT {symbol} → VOLUME TOO LOW")
                continue

            if age_minutes > MAX_PAIR_AGE_MINUTES:
                print(f"REJECT {symbol} → TOO OLD")
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
                print(f"REJECT {symbol} → SCORE TOO LOW")
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

            print(f"SENT {symbol}")

            seen_tokens.add(address)

            alerts_sent += 1

            time.sleep(1)

        print(f"V7 FINISHED — {alerts_sent} ALERT(S) SENT")

    except Exception as e:
        print("ERROR:", e)
