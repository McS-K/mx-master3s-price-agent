import os
import json
import re
import urllib.request
import urllib.parse
from curl_cffi import requests

# Core configuration setup
URL_IDEALO = "https://idealo.es"
TARGET_PRICE = 90.0  # Kept at 90.0 to guarantee a successful Telegram pipeline test!

def send_telegram_alert(price, link):
    # Fetch environment variables safely
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    
    if not bot_token or not chat_id:
        print("Error: Missing configured repository keys inside GitHub Settings.")
        return

    message = (
        f"🚨 **Price Drop Alert via Idealo!** 🚨\n\n"
        f"Logitech MX Master 3S has reached a new low of **{price} €**!\n"
        f"🎯 Your target limit: {TARGET_PRICE} €\n\n"
        f"🔗 Deal details page: {link}"
    )
    
    # Construct endpoint using explicit variable sanitization
    telegram_url = f"https://telegram.org{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    print("Dispatching explicit data payloads to the Telegram API using standard engine...")
    try:
        # Convert dictionary payload to clean byte strings to prevent string-formatting errors
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            telegram_url, 
            data=data, 
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            print("Success! Notification triggered out to Telegram chat.")
            
    except urllib.error.HTTPError as e:
        print(f"Telegram API rejected request (HTTPError): Status {e.code} - {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Failed running native network alert dispatch: {e}")

def check_price():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    print("Connecting to Idealo target mirrors using client impersonation layers...")
    try:
        response = requests.get(URL_IDEALO.strip(), headers=headers, impersonate="chrome", timeout=15)
        
        if response.status_code != 200:
            print(f"Connection aborted by host. Response status: {response.status_code}")
            return
            
        html_data = response.text
        price_found = None

        # LAYER 1: Attempt standard structural JSON extraction
        json_ld_matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html_data, re.DOTALL)
        for match in json_ld_matches:
            try:
                parsed_json = json.loads(match.strip())
                if isinstance(parsed_json, dict) and parsed_json.get("@type") == "Product":
                    offers = parsed_json.get("offers", {})
                    if isinstance(offers, dict) and "lowPrice" in offers:
                        price_found = float(offers["lowPrice"])
                        break
            except Exception:
                continue

        # LAYER 2: Text Engine Fallback (If layout is stripped)
        if not price_found:
            print("Structural tags omitted by host defense. Initiating visible layout parsing fallback...")
            text_match = re.search(r'"lowPrice"\s*:\s*"?([\d\.]+)"?', html_data)
            if text_match:
                price_found = float(text_match.group(1))
            
            # Sub-Layer 3: Global pricing format match (e.g. 79,90 €)
            if not price_found:
                clean_text = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html_data, flags=re.DOTALL)
                clean_text = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', clean_text, flags=re.DOTALL)
                clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
                
                price_strings = re.findall(r'(?:desde\s*|^|\s)(\d{2}[\.,]\d{2})\s*€', clean_text.lower())
                valid_prices = []
                for p in price_strings:
                    try:
                        num = float(p.replace(",", "."))
                        if num > 40.0:
                            valid_prices.append(num)
                    except ValueError:
                        continue
                if valid_prices:
                    price_found = min(valid_prices)

        if price_found:
            print(f"🏆 Verified current minimum market price: {price_found} €")
            
            if float(price_found) < float(TARGET_PRICE):
                print(f"Market threshold triggered ({price_found} < {TARGET_PRICE})! Dispatching alert notification...")
                send_telegram_alert(price_found, URL_IDEALO)
            else:
                print(f"No discount active. Market minimum ({price_found} €) remains at or above {TARGET_PRICE} €.")
        else:
            print("Could not isolate structural monetary tags from target layout or raw page streams.")
                
    except Exception as e:
        print(f"An unexpected engine error occurred: {e}")

if __name__ == "__main__":
    check_price()
