import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Указываем точную страницу конкретной мышки MX Master 3S Graphite на KuantoKusta
URL_PRODUCT = "https://www.kuantokusta.pt/p/8468673/logitech-mx-master-3s-wirelessbluetooth-grafite-910-006559"
TARGET_PRICE = 70.0

def send_telegram_alert(price, link):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Ошибка: Секреты Телеграма не настроены.")
        return

    message = (
        f"🚨 **Снижение цены в Португалии!** 🚨\n\n"
        f"Logitech MX Master 3S упал до **{price} €**!\n"
        f"🎯 Твой лимит: {TARGET_PRICE} €\n\n"
        f"🔗 Ссылка на KuantoKusta: {link}"
    )
    
    # Отправка уведомления системной командой curl
    cmd = f'curl -s -X POST "https://telegram.org{bot_token}/sendMessage" -d "chat_id={chat_id}&text={message}&parse_mode=Markdown"'
    os.system(cmd)
    print("Уведомление отправлено в Telegram!")

def check_price():
    print("🤖 Запуск браузера Chromium через Playwright...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        try:
            print(f"Переход на точную страницу товара: {URL_PRODUCT}")
            page.goto(URL_PRODUCT, wait_until="networkidle", timeout=60000)
            
            # Ждем дополнительные 5 секунд, чтобы JS гарантированно отрисовал цены магазинов
            print("Ожидание загрузки ценовых блоков...")
            page.wait_for_timeout(5000)
            
            html_content = page.content()
            browser.close()
            
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Находим блок с главной минимальной ценой на KuantoKusta
            # Обычно он находится в мета-тегах или в главном блоке стоимости (класс "price" или атрибуты цены)
            price_element = soup.select_one('meta[property="product:price:amount"]')
            
            if not price_element:
                # Резервный вариант: ищем блок основной цены на карточке товара
                price_element = soup.select_one(".price, .main-price, [data-testid='product-price']")
            
            if price_element:
                # Извлекаем текст или контент цены
                if price_element.has_attr('content'):
                    price_text = price_element['content']
                else:
                    price_text = price_element.text
                
                # Очищаем строку от знаков евро, пробелов и меняем запятую на точку
                price_text = price_text.lower().replace("€", "").replace("desde", "").replace(",", ".").strip()
                
                # На всякий случай убираем любые оставшиеся нецифровые символы
                price_text = "".join([c for c in price_text if c.isdigit() or c == '.'])
                
                current_min_price = float(price_text)
                print(f"🏆 Успех! Минимальная цена со всего рынка Португалии: {current_min_price} €")
                
                if current_min_price < TARGET_PRICE:
                    print("Цена ниже твоего лимита! Запуск оповещения...")
                    send_telegram_alert(current_min_price, URL_PRODUCT)
                else:
                    print(f"Скидки пока нет. Текущая цена ({current_min_price} €) выше или равна {TARGET_PRICE} €.")
            else:
                print("⚠️ Не удалось найти HTML-элемент цены. Запишем кусок текста для отладки:")
                print(soup.get_text()[:500])
                    
        except Exception as e:
            print(f"❌ Произошла ошибка во время работы браузера: {e}")
            browser.close()

if __name__ == "__main__":
    check_price()
