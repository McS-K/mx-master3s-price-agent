import os
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Ссылка на страницу категории/поиска MX Master 3S Graphite на KuantoKusta
URL_KK = "https://www.kuantokusta.pt/c/70/ratos-para-pc/m/515/logitech"
TARGET_PRICE = 75.0

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
        f"🔗 Ссылка на агрегатор: {link}"
    )
    
    # Для отправки в Телеграм используем встроенный в Playwright контекст или обычный запрос
    # Но так как у нас теперь нет библиотеки requests, отправим через curl прямо в системе
    cmd = f'curl -s -X POST "https://telegram.org{bot_token}/sendMessage" -d "chat_id={chat_id}&text={message}&parse_mode=Markdown"'
    os.system(cmd)
    print("Уведомление отправлено в Telegram!")

def check_price():
    print("🤖 Запуск реального браузера через Playwright...")
    
    with sync_playwright() as p:
        # Запускаем Chromium
        browser = p.chromium.launch(headless=True)
        # Создаем контекст с эмуляцией обычного компьютера
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        try:
            print(f"Переход на сайт KuantoKusta: {URL_KK}")
            # Переходим на сайт и ждем, пока прогрузится сеть
            page.goto(URL_KK, wait_until="networkidle", timeout=45000)
            
            # Берем весь сгенерированный HTML-код страницы
            html_content = page.content()
            browser.close()
            
            # Анализируем код с помощью BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Ищем текстовые упоминания цен конкретной модели MX Master 3S Graphite (910-006559)
            # KuantoKusta выводит цену в формате "desde75,91€" или "75,91 €"
            page_text = soup.get_text()
            
            # Регулярное выражение ищет цены, привязанные к MX Master 3S
            matches = re.findall(r'3s.*?desde\s*?(\d+[\.,]\d{2})', page_text.lower())
            
            if not matches:
                # Запасной поиск: ищем любые упоминания цен рядом с кодом модели 910-006559
                matches = re.findall(r'910-006559.*?(\d+[\.,]\d{2})', page_text.lower())
            
            if matches:
                # Конвертируем все найденные цены в формат float и берем минимальную
                prices = [float(m.replace(",", ".")) for m in matches]
                current_min_price = min(prices)
                
                print(f"🏆 Успех! Минимальная цена агрегатора на рынке Португалии: {current_min_price} €")
                
                if current_min_price < TARGET_PRICE:
                    print("Цена ниже твоего лимита! Запуск оповещения...")
                    send_telegram_alert(current_min_price, URL_KK)
                else:
                    print(f"Скидки пока нет. Текущая цена ({current_min_price} €) выше или равна {TARGET_PRICE} €.")
            else:
                print("⚠️ Не удалось вытащить точную цену. Попробуем найти любой блок цены на странице...")
                # Поиск любой цены на случай изменения верстки
                any_price = re.search(r'(\d{2}[\.,]\d{2})\s*?€', page_text)
                if any_price:
                    print(f"Обнаружена базовая цена на странице: {any_price.group(1)} €")
                else:
                    print("Робот застрял на проверке или верстка сайта полностью изменилась.")
                    
        except Exception as e:
            print(f"❌ Произошла ошибка во время работы браузера: {e}")
            browser.close()

if __name__ == "__main__":
    check_price()
