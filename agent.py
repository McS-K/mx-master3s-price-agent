import os
import re
from curl_cffi import requests

# Страница поиска Google Shopping для Португалии (запрос цены на MX Master 3S)
URL_GOOGLE = "https://google.com"
TARGET_PRICE = 70.0

def send_telegram_alert(price):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Ошибка: Секреты Телеграма не найдены.")
        return

    message = (
        f"🚨 **Снижение цены на MX Master 3S!** 🚨\n\n"
        f"Google Поиск обнаружил цену **{price} €** на португальском рынке!\n"
        f"Это ниже твоего лимита в {TARGET_PRICE} €.\n\n"
        f"🔗 Проверь предложения в Google: {URL_GOOGLE}"
    )
    
    telegram_url = f"https://telegram.org{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    response = requests.post(telegram_url, json=payload, impersonate="chrome")
    if response.status_code == 200:
        print("Уведомление успешно отправлено в Telegram!")
    else:
        print(f"Ошибка отправки в Telegram: {response.text}")

def check_price():
    # Обычные заголовки браузера Chrome
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8"
    }
    
    print("Запрос к поисковой выдаче Google...")
    
    try:
        # Запрашиваем страницу поиска напрямую у Google (он лоялен к GitHub Actions)
        response = requests.get(URL_GOOGLE, headers=headers, impersonate="chrome", timeout=15)
        
        if response.status_code != 200:
            print(f"Google вернул код: {response.status_code}")
            return

        html_content = response.text
        
        # Ищем упоминания цен в формате "74,90 €", "74.99 €", "74.00EUR" или "74,00 €"
        # Регулярное выражение ищет цифры от 50 до 99, за которыми идет символ евро
        prices_found = re.findall(r'(?:[\s\xa0]|^)([56789]\d[\.,]\d{2})(?:[\s\xa0]*?€|[\s\xa0]*?EUR)', html_content)
        
        if prices_found:
            # Очищаем найденные строки и переводим во float
            float_prices = []
            for p in prices_found:
                clean_p = p.replace(",", ".")
                float_prices.append(float(clean_p))
            
            # Находим самую низкую цену из тех, что проиндексировал Google
            min_price = min(float_prices)
            print(f"Минимальная найденная цена в выдаче Google: {min_price} €")
            
            if min_price < TARGET_PRICE:
                print("Найдена цена ниже целевой! Отправка уведомления...")
                send_telegram_alert(min_price)
            else:
                print(f"Скидки пока нет. Минимальная цена ({min_price} €) выше или равна {TARGET_PRICE} €.")
        else:
            print("Не удалось извлечь блоки цен из поисковой выдачи. Возможно, стоит уточнить поисковый запрос.")
            
    except Exception as e:
        print(f"Произошла ошибка при анализе Google: {e}")

if __name__ == "__main__":
    check_price()
