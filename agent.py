import os
from curl_cffi import requests

TARGET_PRICE = 70.0

# Ссылки на товары для отправки в уведомлении
LINKS = {
    "PCDIGA": "https://www.pcdiga.com/perifericos/ratos-teclados/ratos/rato-optico-logitech-mx-master-3s-bluetooth-edition-8000dpi-graphite-910-007501-5099206129382",
    "Worten": "https://www.worten.pt/produtos/rato-logitech-mx-master-3s-bluetooth-8000-dpi-preto-7612235",
    "FNAC": "https://fnac.pt"
}

def send_telegram_alert(price, store, link):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Ошибка: Секреты Телеграма не настроены.")
        return

    message = (
        f"🚨 **Снижение цены в Португалии!** 🚨\n\n"
        f"Logitech MX Master 3S упал до **{price} €**!\n"
        f"🏪 Магазин: **{store}**\n"
        f"🎯 Твой лимит: {TARGET_PRICE} €\n\n"
        f"🔗 Ссылка на покупку: {link}"
    )
    
    url = f"https://telegram.org{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload, impersonate="chrome")
    print(f"Уведомление о скидке в {store} отправлено в Telegram!")

def get_pcdiga_price():
    try:
        api_url = "https://pcdiga.com"
        res = requests.get(api_url, impersonate="chrome", timeout=10)
        if res.status_code == 200 and isinstance(res.json(), list) and len(res.json()) > 0:
            price = float(res.json()[0]['items'][0]['sellers'][0]['commertialOffer']['Price'])
            return price
    except Exception as e:
        print(f"[-] Не удалось проверить PCDIGA: {e}")
    return None

def get_worten_price():
    try:
        # Официальный открытый API каталога Worten
        api_url = "https://worten.pt"
        res = requests.get(api_url, impersonate="chrome", timeout=10)
        if res.status_code == 200:
            # Получаем цену со скидкой
            price = float(res.json().get("price", {}).get("sale_price", 999))
            return price
    except Exception as e:
        print(f"[-] Не удалось проверить Worten: {e}")
    return None

def get_fnac_price():
    try:
        # Эмуляция поискового API FNAC Portugal
        api_url = "https://fnac.pt"
        res = requests.get(api_url, impersonate="chrome", timeout=10)
        if res.status_code == 200:
            price = float(res.json().get("bestOffer", {}).get("price", 999))
            return price
    except Exception as e:
        print(f"[-] Не удалось проверить FNAC: {e}")
    return None

def main():
    print("🤖 Запуск мульти-магазинного мониторинга цен в Португалии...")
    
    prices = {}
    
    # Опрашиваем каждый магазин по цепочке
    pcdiga = get_pcdiga_price()
    if pcdiga: prices["PCDIGA"] = pcdiga
        
    worten = get_worten_price()
    if worten: prices["Worten"] = worten
        
    fnac = get_fnac_price()
    if fnac: prices["FNAC"] = fnac

    if not prices:
        print("❌ Критическая ошибка: Ни один магазин не вернул данные. Проверь структуру API.")
        return

    # Находим самый выгодный вариант среди всех ответивших магазинов
    best_store = min(prices, key=prices.get)
    best_price = prices[best_store]
    
    print("\n--- Результаты анализа рынка ---")
    for store, price in prices.items():
        print(f"• {store}: {price} €")
    print(f"🏆 Лучшее предложение: {best_price} € на {best_store}\n")

    # Проверяем условие уведомления
    if best_price < TARGET_PRICE:
        print(f" Найдена цена ниже лимита! Запуск оповещения...")
        send_telegram_alert(best_price, best_store, LINKS[best_store])
    else:
        print(f" Скидки пока нет. Минимальная цена рынка ({best_price} €) выше лимита в {TARGET_PRICE} €.")

if __name__ == "__main__":
    main()
