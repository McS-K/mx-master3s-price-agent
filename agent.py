import os
from curl_cffi import requests

# Возвращаем отслеживание всего рынка через KuantoKusta
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
        f"🚨 **Снижение цены в Португалии!** 🚨\n\n"
        f"Logitech MX Master 3S сейчас стоит всего **{price} €**!\n"
        f"Это ниже твоего лимита в {TARGET_PRICE} €.\n\n"
        f"🔗 Ссылка на KuantoKusta: {link}"
    )
    
    telegram_url = f"https://telegram.org{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    response = requests.post(telegram_url, json=payload, impersonate="chrome")
    if response.status_code == 200:
        print("Уведомление успешно отправлено в Telegram!")
    else:
        print(f"Не удалось отправить сообщение: {response.text}")

def check_price():
    scraperapi_key = os.environ.get("SCRAPERAPI_KEY")
    if not scraperapi_key:
        print("Ошибка: Ключ SCRAPERAPI_KEY не найден в секретах GitHub.")
        return

    print("Запрос к ценовому агрегатору Португалии через прокси-сервер ScraperAPI...")
    
    # Формируем специальную ссылку для ScraperAPI, которая обойдет Cloudflare
    proxied_url = f"http://scraperapi.com?api_key={scraperapi_key}&url={API_URL}"
    
    try:
        # Делаем запрос через прокси
        response = requests.get(proxied_url, timeout=30)
        
        if response.status_code != 200:
            print(f"Прокси вернул ошибку. Код ответа: {response.status_code}")
            return

        data = response.json()
        lowest_price = data.get("product", {}).get("prices", {}).get("cheapest", {}).get("value")
        
        if lowest_price is not None:
            current_price = float(lowest_price)
            print(f"Текущая минимальная цена на рынке Португалии: {current_price} €")
            
            if current_price < TARGET_PRICE:
                print("Цена ниже целевой! Запуск уведомления...")
                send_telegram_alert(current_price, URL_KK)
            else:
                print(f"Скидки пока нет. Цена ({current_price} €) выше или равна {TARGET_PRICE} €.")
        else:
            print("Не удалось распарсить цену из ответа API.")
            
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")

if __name__ == "__main__":
    check_price()
