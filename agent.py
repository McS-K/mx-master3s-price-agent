import os
import json
import re
from curl_cffi import requests

# Конфигурация
URL_IDEALO = "https://idealo.es"
TARGET_PRICE = 90.0  # Оставляем 90.0 для теста! После теста верни 70.0

def send_telegram_alert(price, link):
    # Принудительная очистка токенов от скрытых пробелов
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    
    if not bot_token or not chat_id:
        print("Ошибка: Секреты Телеграма пустые.")
        return

    message = (
        f"🚨 **Price Drop Alert via Idealo!** 🚨\n\n"
        f"Logitech MX Master 3S has reached a new low of **{price} €**!\n"
        f"🎯 Your target limit: {TARGET_PRICE} €\n\n"
        f"🔗 Deal details page: {link}"
    )
    
    telegram_url = f"https://telegram.org{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    print("Отправка запроса в API Telegram (чистый программный запрос)...")
    try:
        # ВАЖНО: Отправляем БЕЗ impersonate="chrome", чтобы Телеграм не блокировал запрос
        response = requests.post(telegram_url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Успех! Тестовое уведомление отправлено в Telegram-чат.")
        else:
            print(f"Ошибка от API Telegram: {response.text}")
    except Exception as e:
        print(f"Критическая ошибка отправки в Телеграм: {e}")

def check_price():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9"
    }
    
    print("Подключение к зеркалу Idealo с имитацией браузера...")
    try:
        # Для Idealo имитация браузера остается обязательной
        response = requests.get(URL_IDEALO.strip(), headers=headers, impersonate="chrome", timeout=15)
        
        if response.status_code != 200:
            print(f"Сайт вернул ошибку. Код ответа: {response.status_code}")
            return
            
        html_data = response.text
        
        # Твой старый проверенный формат поиска цены через JSON-LD
        json_ld_matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html_data, re.DOTALL)
        
        price_found = None
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

        # Резервный текстовый поиск по тегу lowPrice
        if not price_found:
            text_match = re.search(r'"lowPrice"\s*:\s*([\d\.]+)', html_data)
            if text_match:
                price_found = float(text_match.group(1))

        if price_found:
            print(f"🏆 Backup matched minimum market price: {price_found} €")
            
            # Математическое сравнение цен
            if float(price_found) < float(TARGET_PRICE):
                print(f"Триггер сработал ({price_found} < {TARGET_PRICE})! Запуск отправки...")
                send_telegram_alert(price_found, URL_IDEALO)
            else:
                print(f"Скидки нет. Цена рынка ({price_found} €) выше лимита ({TARGET_PRICE} €).")
        else:
            print("Не удалось извлечь цену из разметки страницы.")
                
    except Exception as e:
        print(f"Произошла ошибка при анализе сайта: {e}")

if __name__ == "__main__":
    check_price()
