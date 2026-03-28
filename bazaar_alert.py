import requests
import time

apiKey  = "e71f4128-0eeb-4e7a-bec7-f00be861e1a8"
webhook  = "https://discord.com/api/webhooks/1487307771236978708/Aj7r4gSjrMEmwPJE6_oESoiVeYeuVgtgV5QKK7YRnKNI5VvvBu9hShwp8QCfnWmTiPmj"
secondsBetween = 5
minVolume = 1000
ALERTS = {
    "VERY_CRUDE_GABAGOOL": {
        "above": 50_000,
        # "below": 150_000,
    },
    "BOOSTER_COOKIE": {
        #"above": 50_000,
        "below": 9_500_000,
    },
}

alertState: dict[str, dict[str, bool]] = {
    item: {condition: False for condition in thresholds}
    for item, thresholds in ALERTS.items()
}

def fetch_bazaar() -> dict | None:
    url = f"https://api.hypixel.net/skyblock/bazaar?key={apiKey}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            print(f"API error: {data}")
            return None
        return data["products"]
    except Exception as e:
        print(f"Failed to fetch bazaar: {e}")
        return None

def get_buy_order_volume(product: dict) -> int:
    """Sum the total volume across all active buy orders."""
    return sum(order["amount"] for order in product.get("buySummary", []))

def send_discord_alert(itemID: str, condition: str, threshold: float, actual: float, volume: int, recovered: bool = False):
    itemName = itemID.replace("_", " ").title()
    if recovered:
        direction = "📉 dropped back below" if condition == "above" else "📈 risen back above"
        color = 0xFFAA00
        title = f"🔄 Price Recovered — {itemName}"
    else:
        direction = "📈 risen above" if condition == "above" else "📉 fallen below"
        color = 0x00FF00 if condition == "above" else 0xFF0000
        title = f"🔔 Bazaar Price Alert — {itemName}"
    embed = {
        "title": title,
        "description": (
            f"The price has **{direction}** your threshold!\n\n"
            f"**Current price:** `{actual:,.1f}` coins\n"
            f"**Your threshold:** `{threshold:,.1f}` coins\n"
            f"**Buy order volume:** `{volume:,}`"
        ),
        "color": color,
        "footer": {"text": "Hypixel Skyblock Bazaar Bot"},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        r = requests.post(webhook, json={"embeds": [embed]}, timeout=10)
        r.raise_for_status()
        label = "recovery" if recovered else "alert"
        print(f"Sent {label} for {itemID} ({condition} {threshold}) | volume: {volume:,}")
    except Exception as e:
        print(f"failed to send discord message: {e}")

def check_prices(products: dict):
    for itemID, thresholds in ALERTS.items():
        product = products.get(itemID)
        if not product:
            print(f"Item not found in bazaar: {itemID}")
            continue
        buySummary = product.get("buySummary", [])
        if not buySummary:
            continue
        currentPrice = buySummary[0]["pricePerUnit"]
        volume = get_buy_order_volume(product)
        for condition, threshold in thresholds.items():
            price_triggered = (
                currentPrice > threshold if condition == "above"
                else currentPrice < threshold
            )
            volumeLimit = volume >= minVolume
            wasTriggered = alertState[itemID].get(condition, False)
            if price_triggered and volumeLimit and not wasTriggered:
                # Price crossed threshold AND volume is sufficient — fire alert
                send_discord_alert(itemID, condition, threshold, currentPrice, volume)
                alertState[itemID][condition] = True
            elif wasTriggered and (not price_triggered or not volumeLimit):
                # Price has returned to normal OR volume dropped — send recovery alert
                send_discord_alert(itemID, condition, threshold, currentPrice, volume, recovered=True)
                alertState[itemID][condition] = False

def main():
    print(f"bot started, checking every {secondsBetween} seconds...")
    while True:
        products = fetch_bazaar()
        if products:
            check_prices(products)
        time.sleep(secondsBetween)

if __name__ == "__main__":
    main()
