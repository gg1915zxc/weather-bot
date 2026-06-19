import os
import time
import threading
import requests
from flask import Flask
from waitress import serve

# -------------------- Ключи --------------------
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
WEATHER_TOKEN = os.environ["WEATHER_TOKEN"]

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
user_mode = {}  # chat_id -> "weather" или None

# Фразы для мгновенного ответа
PHRASES = {
    "привет": "Привет! Я бот погоды. Нажми кнопку «Погода» и введи город.",
    "здравствуй": "Здравствуй! Чем могу помочь?",
    "как дела": "У меня всё отлично! А у тебя?",
    "что ты умеешь": "Я показываю погоду в любом городе мира.\nНажми кнопку «Погода» и введи название.",
    "спасибо": "Пожалуйста! Обращайся.",
    "пока": "До встречи!"
}

# -------------------- Telegram helpers --------------------
def send_message(chat_id, text, reply_markup=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

def get_main_keyboard():
    """Клавиатура с одной кнопкой «Погода»."""
    return {
        "keyboard": [
            ["🌤 Погода"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

# -------------------- Погода --------------------
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
                return None  # Город не найден
            return f"Ошибка погоды: {msg}"
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
        return "Не удалось получить данные о погоде."

# -------------------- Веб-сервер (против сна) --------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)

# -------------------- Главный цикл --------------------
def main_bot():
    print("Бот погоды (без ИИ) запущен...")
    offset = 0
    while True:
        try:
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
                text = message["text"].strip().lower()

                # Команда /start – показываем клавиатуру
                if text == "/start":
                    send_message(chat_id,
                        "Привет! Я бот погоды.\n"
                        "Нажми кнопку «🌤 Погода» и введи название города.",
                        reply_markup=get_main_keyboard())
                    continue

                # Нажатие кнопки «Погода»
                if text == "🌤 погода":
                    user_mode[chat_id] = "weather"
                    send_message(chat_id, "Введи название города:")
                    continue

                # Известные фразы
                if text in PHRASES:
                    send_message(chat_id, PHRASES[text])
                    continue

                # Обработка по режиму
                current_mode = user_mode.get(chat_id)

                if current_mode == "weather":
                    weather_result = get_weather(text)
                    if weather_result is None:
                        send_message(chat_id, f"Город «{text}» не найден. Проверь название и попробуй ещё раз.")
                    else:
                        send_message(chat_id, weather_result)
                        user_mode.pop(chat_id, None)  # сброс режима после успеха
                    continue

                else:
                    # Режим не выбран – напоминаем о кнопке
                    send_message(chat_id, "Нажми кнопку «🌤 Погода», чтобы узнать погоду.",
                                 reply_markup=get_main_keyboard())

        except Exception as e:
            print(f"Ошибка цикла: {e}")
            time.sleep(1)

if __name__ == "__main__":
    # Flask в отдельном потоке
    threading.Thread(target=run_web_server, daemon=True).start()
    # Основной поток – бот
    main_bot()
