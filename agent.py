import os
import requests
# Используем curl_cffi вместо стандартного requests для обхода Cloudflare 403
from curl_cffi import requests as requests_impersonate

# Конфигурация агента
URL_KK = "https://kuantokusta.pt"
API_URL = "https://kuantokusta.pt"
TARGET_PRICE = 70.0

def send_telegram_alert(price, link):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Ошибка: Секреты Телеграма не найдены в системе.")
        return

    message = (
        f"🚨 **Снижение цены!** 🚨\n\n"
        f"Logitech MX Master 3S сейчас стоит всего **{price} €**!\n"
        f"Это ниже твоего лимита в {TARGET_PRICE} €.\n\n"
        f"🔗 Ссылка на KuantoKusta: {link}"
    )
    
    telegram_url = f"https://telegram.org{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    # Для отправки сообщения в Telegram обычный requests подходит отлично
    response = requests.post(telegram_url, json=payload)
    if response.status_code == 200:
        print("Уведомление успешно отправлено в Telegram!")
    else:
        print(f"Не удалось отправить сообщение: {response.text}")

def check_price():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    print("Запрос к ценовому агрегатору Португалии с имитацией браузера Chrome...")
    
    try:
        # Параматер impersonate принудительно копирует TLS-отпечаток настоящего браузера
        response = requests_impersonate.get(API_URL, headers=headers, impersonate="chrome")
        
        if response.status_code != 200:
            print(f"Не удалось получить данные. Код ответа: {response.status_code}")
            return

        data = response.json()
        lowest_price = data.get("product", {}).get("prices", {}).get("cheapest", {}).get("value")
        
        if lowest_price is not None:
            current_price = float(lowest_price)
            print(f"Текущая минимальная цена в Португалии: {current_price} €")
            
            if current_price < TARGET_PRICE:
                print("Цена ниже целевой! Запуск уведомления...")
                send_telegram_alert(current_price, URL_KK)
            else:
                print(f"Скидки пока нет. Цена ({current_price} €) выше или равна {TARGET_PRICE} €.")
        else:
            print("Не удалось распарсить цену из ответа API.")
            
    except Exception as e:
        print(f"Произошла ошибка при выполнении запроса: {e}")

if __name__ == "__main__":
    check_price()
