import os
import re
from curl_cffi import requests

# Целевая страница товара (для обычных пользователей)
URL_KK = "https://kuantokusta.pt"
TARGET_PRICE = 75.0

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
        f"🔗 Ссылка на покупку: {link}"
    )
    
    telegram_url = f"https://telegram.org{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    response = requests.post(telegram_url, json=payload, impersonate="chrome")
    if response.status_code == 200:
        print("Уведомление успешно отправлено в Telegram!")
    else:
        print(f"Не удалось отправить сообщение в Телеграм: {response.text}")

def check_price():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    print("Запрос к веб-странице товара с имитацией браузера...")
    
    try:
        # Загружаем основную HTML-страницу вместо API
        response = requests.get(URL_KK, headers=headers, impersonate="chrome", timeout=15)
        
        if response.status_code != 200:
            print(f"Не удалось открыть страницу. Код ответа: {response.status_code}")
            return

        html_content = response.text

        # Ищем цену в мета-тегах Schema.org или Open Graph с помощью регулярного выражения
        # Ищем конструкции вида: itemprop="price" content="79.90" или "price":"79.90"
        price_match = re.search(r'itemprop="price"\s+content="([\d\.]+)"', html_content)
        
        if not price_match:
            # Запасной вариант поиска в JSON-LD структуре внутри HTML
            price_match = re.search(r'"price"\s*:\s*"([\d\.]+)"', html_content)

        if price_match:
            current_price = float(price_match.group(1))
            print(f"Текущая минимальная цена в Португалии: {current_price} €")
            
            if current_price < TARGET_PRICE:
                print("Цена ниже целевой! Запуск уведомления...")
                send_telegram_alert(current_price, URL_KK)
            else:
                print(f"Скидки пока нет. Цена ({current_price} €) выше или равна {TARGET_PRICE} €.")
        else:
            print("Предупреждение: Не удалось найти мета-тег цены в HTML-коде страницы.")
            # Выведем кусочек кода для отладки, если сайт вернул заглушку защиты
            if "cloudflare" in html_content.lower() or "captcha" in html_content.lower():
                print("Обнаружена блокировка Cloudflare (требуется прохождение капчи).")
            else:
                print("Возможно, структура страницы изменилась.")
            
    except Exception as e:
        print(f"Произошла ошибка при выполнении запроса: {e}")

if __name__ == "__main__":
    check_price()
