import os
import json
import re
from curl_cffi import requests

# Idealo product URL containing unified Iberian market offers
URL_IDEALO = "https://www.idealo.es/precios/201968116/logitech-mx-master-3s.html"
TARGET_PRICE = 90.0

def send_telegram_alert(price, link):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID").strip()
    
    if not bot_token or not chat_id:
        print("Error: Telegram configuration secrets missing.")
        return

    message = (
        f"🚨 **Price Drop Alert via Idealo!** 🚨\n\n"
        f"Logitech MX Master 3S has reached a new low of **{price} €**!\n"
        f"🎯 Your target limit: {TARGET_PRICE} €\n\n"
        f"🔗 Deal details page: {link}"
    )
    
    telegram_url = f"https://telegram.org{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    response = requests.post(telegram_url, json=payload, impersonate="chrome")
    if response.status_code == 200:
        print("Success! Notification sent out to Telegram.")
    else:
        print(f"Failed sending alert: {response.text}")

def check_price():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
    }
    
    print("Connecting to Idealo's open metadata endpoint...")
    try:
        response = requests.get(URL_IDEALO, headers=headers, impersonate="chrome", timeout=15)
        
        if response.status_code != 200:
            print(f"Connection aborted by host. Response status: {response.status_code}")
            return
            
        html_data = response.text
        
        # Scrape via the hidden standard Google Schema metadata block embedded on the page
        json_ld_matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html_data, re.DOTALL)
        
        price_found = None
        for match in json_ld_matches:
            try:
                parsed_json = json.loads(match.strip())
                # Navigate through the structural schema layer (Product -> offers -> lowPrice)
                if isinstance(parsed_json, dict) and parsed_json.get("@type") == "Product":
                    offers = parsed_json.get("offers", {})
                    if isinstance(offers, dict) and "lowPrice" in offers:
                        price_found = float(offers["lowPrice"])
                        break
            except Exception:
                continue

        if price_found:
            print(f"🏆 Unified minimum market price captured: {price_found} €")
            
            if price_found < TARGET_PRICE:
                print("Market threshold triggered! Dispatching message...")
                send_telegram_alert(price_found, URL_IDEALO)
            else:
                print(f"No discount active. Market minimum ({price_found} €) remains at or above {TARGET_PRICE} €.")
        else:
            print("Warning: Metadata blocks structural format changed. Capturing simple baseline fallback:")
            # Alternative direct text match structure fallback if structural JSON elements shift
            text_match = re.search(r'"lowPrice"\s*:\s*([\d\.]+)', html_data)
            if text_match:
                fallback_price = float(text_match.group(1))
                print(f"🏆 Backup matched minimum market price: {fallback_price} €")
                if fallback_price < TARGET_PRICE:
                    send_telegram_alert(fallback_price, URL_IDEALO)
            else:
                print("Could not isolate structural monetary tags from target layout.")
                
    except Exception as e:
        print(f"An unexpected engine error occurred: {e}")

if __name__ == "__main__":
    check_price()
