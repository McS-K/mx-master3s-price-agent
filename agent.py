import os
import re
import json
import sys
import time
from curl_cffi import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# One entry per monitored product. URLs are read from environment variables
# (GitHub Actions variables/secrets), so they are not hardcoded here.
# Remember to pass each variable in the `env:` section of your workflow file.
PRODUCTS = [
    {
        "name": "Logitech MX Master 3S",
        "url": "https://www.idealo.es/precios/201968116/logitech-mx-master-3s.html",
        "target": 70.0,         # Test value, replace with the real threshold later
        "min_plausible": 40.0,  # Anything below is treated as a parsing error
    },
    {
        "name": "Logitech MX Keys S Combo",
        "url": "https://www.idealo.es/precios/202841996/logitech-mx-keys-s-combo-us.html",
        "target": 150.0,
        "min_plausible": 60.0,
    },
]

PAUSE_BETWEEN_REQUESTS = 3  # seconds, to be gentle with idealo


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
def send_telegram_alert(name, price, target, link):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not bot_token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing "
              "(check GitHub Settings -> Secrets).")
        return False

    # Plain text (no parse_mode): avoids Markdown parsing errors caused by
    # special characters in URLs or text.
    message = (
        f"🚨 Price Drop Alert via Idealo! 🚨\n\n"
        f"{name} has reached a new low of {price:.2f} €!\n"
        f"🎯 Your target limit: {target:.2f} €\n\n"
        f"🔗 Deal details page: {link}"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": False,
    }

    print("Sending notification to the Telegram API...")
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            print("Success! Notification sent to Telegram.")
            return True
        print(f"Telegram error {r.status_code}: {r.text}")
        return False
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")
        return False


# ---------------------------------------------------------------------------
# Price extraction
# ---------------------------------------------------------------------------
def _to_float(value):
    """Convert '79.90' / '79,90' / 79.9 to float, or return None."""
    try:
        return float(str(value).strip().replace(",", "."))
    except (ValueError, TypeError):
        return None


def _iter_nodes(data):
    """Recursively yield all dict nodes from a JSON-LD structure
    (handles lists and '@graph')."""
    if isinstance(data, dict):
        yield data
        for value in data.values():
            if isinstance(value, (dict, list)):
                yield from _iter_nodes(value)
    elif isinstance(data, list):
        for item in data:
            yield from _iter_nodes(item)


def _is_product(node):
    node_type = node.get("@type")
    if isinstance(node_type, list):
        return "Product" in node_type
    return node_type == "Product"


def _price_from_offers(offers):
    """Extract the lowest price from an 'offers' object (dict or list)."""
    if isinstance(offers, list):
        prices = [p for p in (_price_from_offers(o) for o in offers) if p is not None]
        return min(prices) if prices else None
    if isinstance(offers, dict):
        for key in ("lowPrice", "price"):
            if key in offers:
                price = _to_float(offers[key])
                if price is not None:
                    return price
    return None


def extract_price_from_jsonld(html):
    """LAYER 1: structured data (JSON-LD) of the product."""
    blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    for block in blocks:
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        for node in _iter_nodes(data):
            if _is_product(node) and "offers" in node:
                price = _price_from_offers(node["offers"])
                if price is not None:
                    return price
    return None


def extract_price_from_raw(html):
    """LAYER 2: look for a lowPrice field anywhere in the raw HTML/JSON."""
    match = re.search(r'"lowPrice"\s*:\s*"?(\d+(?:[.,]\d+)?)"?', html)
    if match:
        return _to_float(match.group(1))
    return None


def get_price(html):
    price = extract_price_from_jsonld(html)
    if price is not None:
        print("Price found via JSON-LD structured data.")
        return price

    print("JSON-LD not found, trying raw lowPrice fallback...")
    price = extract_price_from_raw(html)
    if price is not None:
        print("Price found via raw lowPrice field.")
        return price

    return None


# ---------------------------------------------------------------------------
# Per-product check
# ---------------------------------------------------------------------------
def check_product(product):
    """Check one product. Returns True if everything went fine
    (including 'no discount'), False on any error."""
    name = product["name"]
    url = product["url"]
    target = product["target"]
    min_plausible = product["min_plausible"]

    print(f"\n=== {name} ===")

    if not url:
        print("Error: product URL is not set (check the environment variable "
              "and the `env:` section of your workflow).")
        return False

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    # Note: User-Agent is intentionally not set manually; impersonate="chrome"
    # sends a consistent browser fingerprint (UA + TLS) on its own.

    print(f"Fetching product page: {url}")
    try:
        response = requests.get(url, headers=headers, impersonate="chrome", timeout=15)
    except Exception as e:
        print(f"Request failed: {e}")
        return False

    if response.status_code != 200:
        print(f"Connection aborted by host. Response status: {response.status_code}")
        return False

    price = get_price(response.text)

    if price is None:
        print("Could not find the price on the page. The page structure may "
              "have changed, or the URL is not a product page.")
        return False

    if price < min_plausible:
        print(f"Found price {price:.2f} € looks implausible for {name} "
              f"(below {min_plausible:.2f} €). Probably a parsing error, "
              f"skipping alert.")
        return False

    print(f"🏆 Current minimum market price: {price:.2f} €")

    if price < target:
        print(f"Threshold triggered ({price:.2f} < {target:.2f})! Sending alert...")
        return send_telegram_alert(name, price, target, url)

    print(f"No discount active. Price ({price:.2f} €) is at or above {target:.2f} €.")
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    results = []
    for i, product in enumerate(PRODUCTS):
        if i > 0:
            time.sleep(PAUSE_BETWEEN_REQUESTS)
        try:
            results.append(check_product(product))
        except Exception as e:
            # One failing product must never block the others
            print(f"Unexpected error while checking {product['name']}: {e}")
            results.append(False)

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
