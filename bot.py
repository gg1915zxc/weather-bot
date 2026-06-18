import os
import time
import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
WEATHER_TOKEN = os.environ["WEATHER_TOKEN"]
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass  # Просто игнорируем ошибку отправки

def get_weather(city):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": WEATHER_TOKEN,
        "units": "metric",
        "lang": "ru"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            data = resp.json()
            msg = data.get("message", "Неизвестная ошибка")
            if msg == "city not found":
                return f"Город «{city}» не найден. Проверь название."
            else:
                return f"Ошибка: {msg}"
        data = resp.json()
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        description = data["weather"][0]["description"]
        return (
            f"🌍 Погода в {city}:\n"
            f"Температура: {temp}°C\n"
            f"Ощущается как: {feels_like}°C\n"
            f"Влажность: {humidity}%\n"
            f"Описание: {description}"
        )
    except Exception:
        return "Не удалось получить данные о погоде. Попробуй позже."

def main():
    print("Бот запущен...")
    offset = 0
    while True:
        try:
            # Получаем новые сообщения
            url = f"{BASE_URL}/getUpdates"
            params = {"offset": offset, "timeout": 30}
            resp = requests.get(url, params=params, timeout=35)
            data = resp.json()
            if not data.get("ok"):
                time.sleep(1)
                continue

            for update in data["result"]:
                offset = update["update_id"] + 1
                message = update.get("message")
                if not message or "text" not in message:
                    continue
                chat_id = message["chat"]["id"]
                text = message["text"].strip()

                if text == "/start":
                    send_message(chat_id,
                        "Привет! Я бот погоды.\n"
                        "Просто напиши название города, и я пришлю погоду. Например: Москва"
                    )
                else:
                    # Любое другое сообщение считаем названием города
                    answer = get_weather(text)
                    send_message(chat_id, answer)
        except Exception:
            time.sleep(1)

if __name__ == "__main__":
    main()