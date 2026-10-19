import os
from curl_cffi import requests

# Прямая ссылка на агрегатор Idealo Portugal для ручной проверки
URL_IDEALO = "https://idealo.pt"

# Открытый API Idealo для получения цен на MX Master 3S в Португалии
API_URL = "https://idealo.pt"
TARGET_PRICE = 75.0

def send_telegram_alert(price, store_name, link):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Ошибка: Секреты Телеграма не найдены в системе.")
        return

    message = (
        f"🚨 **Снижение цены в Португалии!** 🚨\n\n"
        f"Logitech MX Master 3S сейчас стоит всего **{price} €** в магазине **{store_name}**!\n"
        f"Это ниже твоего лимита в {TARGET_PRICE} €.\n\n"
        f"🔗 Ссылка на сравнение цен: {URL_IDEALO}"
    )
    
    telegram_url = f"https://telegram.org{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    response = requests.post(telegram_url, json=payload, impersonate="chrome")
    if response.status_code == 200:
        print("Уведомление успешно отправлено в Telegram!")
    else:
        print(f"Не удалось отправить сообщение: {response.text}")

def check_price():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    print("Запрос к открытому API агрегатора Idealo Portugal...")
    
    try:
        response = requests.get(API_URL, headers=headers, impersonate="chrome", timeout=15)
        
        if response.status_code != 200:
            # Если Idealo недоступен, используем резервный прямой запрос к открытому API PCDIGA
            print(f"Idealo временно недоступен (Код: {response.status_code}). Проверяем PCDIGA напрямую...")
            check_pcdiga_fallback()
            return

        data = response.json()
        offers = data.get("offers", [])
        
        if offers:
            # Сортируем полученные предложения по цене (от меньшей к большей)
            offers.sort(key=lambda x: float(x.get("price", {}).get("amount", 999)))
            best_offer = offers[0]
            
            current_price = float(best_offer.get("price", {}).get("amount", 0))
            store_name = best_offer.get("shop", {}).get("name", "Неизвестный магазин")
            
            print(f"Минимальная цена на рынке Португалии: {current_price} € (Магазин: {store_name})")
            
            if current_price < TARGET_PRICE:
                print("Цена ниже целевой! Запуск уведомления...")
                send_telegram_alert(current_price, store_name, URL_IDEALO)
            else:
                print(f"Скидки пока нет. Минимальная цена ({current_price} €) выше или равна {TARGET_PRICE} €.")
        else:
            print("API вернул пустой список предложений. Проверяем PCDIGA...")
            check_pcdiga_fallback()
            
    except Exception as e:
        print(f"Произошла ошибка при анализе данных: {e}. Запуск резервного режима...")
        check_pcdiga_fallback()

def check_pcdiga_fallback():
    # Наш проверенный резервный вариант, который точно отдавал данные
    try:
        api_pcdiga = "https://pcdiga.com"
        res = requests.get(api_pcdiga, impersonate="chrome", timeout=10)
        if res.status_code == 200 and isinstance(res.json(), list) and len(res.json()) > 0:
            price = float(res.json()[0]['items'][0]['sellers'][0]['commertialOffer']['Price'])
            print(f"Резервная проверка — цена на PCDIGA: {price} €")
            if price < TARGET_PRICE:
                send_telegram_alert(price, "PCDIGA", "https://www.pcdiga.com/")
        else:
            print("Резервный метод тоже не смог получить цену.")
    except Exception as e:
        print(f"Ошибка резервного метода: {e}")

if __name__ == "__main__":
    check_price()
