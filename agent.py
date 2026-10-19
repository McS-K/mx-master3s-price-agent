import os
import re
import json
import sys
from curl_cffi import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# URL of the PRODUCT page on idealo (not the home page!).
# Best practice: store it in a GitHub Actions variable/secret named IDEALO_PRODUCT_URL.
# Alternatively, paste the link directly into the default value below.
PRODUCT_URL = os.environ.get(
    "IDEALO_PRODUCT_URL",
    "PASTE_YOUR_IDEALO_PRODUCT_PAGE_URL_HERE",
).strip()

PRODUCT_NAME = "Logitech MX Master 3S"
TARGET_PRICE = 90.0  # Test value, replace with the real threshold later

# Anything below this is treated as a parsing error (accessory, ad block, etc.)
MIN_PLAUSIBLE_PRICE = 40.0


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
def send_telegram_alert(price, link):
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
        f"{PRODUCT_NAME} has reached a new low of {price:.2f} €!\n"
        f"🎯 Your target limit: {TARGET_PRICE:.2f} €\n\n"
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
# Main logic
# ---------------------------------------------------------------------------
def check_price():
    if not PRODUCT_URL or PRODUCT_URL.startswith("PASTE_YOUR"):
        print("Error: product page URL is not set. Define IDEALO_PRODUCT_URL "
              "or edit PRODUCT_URL in agent.py.")
        return 1

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    # Note: User-Agent is intentionally not set manually; impersonate="chrome"
    # sends a consistent browser fingerprint (UA + TLS) on its own.

    print(f"Fetching product page: {PRODUCT_URL}")
    try:
        response = requests.get(
            PRODUCT_URL, headers=headers, impersonate="chrome", timeout=15
        )
    except Exception as e:
        print(f"Request failed: {e}")
        return 1

    if response.status_code != 200:
        print(f"Connection aborted by host. Response status: {response.status_code}")
        return 1

    price = get_price(response.text)

    if price is None:
        print("Could not find the price on the page. The page structure may "
              "have changed, or the URL is not a product page.")
        return 1

    if price < MIN_PLAUSIBLE_PRICE:
        print(f"Found price {price:.2f} € looks implausible for {PRODUCT_NAME} "
              f"(below {MIN_PLAUSIBLE_PRICE:.2f} €). Probably a parsing error, "
              f"skipping alert.")
        return 1

    print(f"🏆 Current minimum market price: {price:.2f} €")

    if price < TARGET_PRICE:
        print(f"Threshold triggered ({price:.2f} < {TARGET_PRICE:.2f})! Sending alert...")
        if not send_telegram_alert(price, PRODUCT_URL):
            return 1
    else:
        print(f"No discount active. Price ({price:.2f} €) is at or above "
              f"{TARGET_PRICE:.2f} €.")

    return 0


if __name__ == "__main__":
    sys.exit(check_price())
