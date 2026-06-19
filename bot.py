import os
import time
import threading
import requests
from flask import Flask
from groq import Groq

# -------------------- Ключи из переменных окружения --------------------
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
WEATHER_TOKEN = os.environ["WEATHER_TOKEN"]
GROQ_TOKEN = os.environ["GROQ_TOKEN"]

# Клиент Groq
groq_client = Groq(api_key=GROQ_TOKEN)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
user_mode = {}  # chat_id -> "weather" или "ai"

# Фразы для быстрого ответа
PHRASES = {
    "привет": "Привет! Я бот погоды и искусственного интеллекта.\nВыбери режим на клавиатуре.",
    "здравствуй": "Здравствуй! Чем могу помочь?",
    "как дела": "У меня всё отлично! А у тебя?",
    "что ты умеешь": "Я могу показать погоду в любом городе и отвечать на вопросы с помощью нейросети Groq.\nИспользуй кнопки ниже.",
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
    return {
        "keyboard": [
            ["🌤 Погода"],
            ["🤖 ИИ"]
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
                return None
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

# -------------------- ИИ (Groq) --------------------
def ask_groq(prompt):
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model="llama3-8b-8192",  # бесплатная модель, быстрая
            max_tokens=500,
            temperature=0.7
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception:
        return "Извини, не смог получить ответ от нейросети. Попробуй ещё раз."

# -------------------- Веб-сервер (чтобы не засыпать) --------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    from waitress import serve
    serve(app, host="0.0.0.0", port=port)

# -------------------- Главный цикл бота --------------------
def main_bot():
    print("Бот с погодой, Groq и веб-сервером запущен...")
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
                        "Привет! Выбери режим:\n"
                        "🌤 Погода – узнать погоду\n"
                        "🤖 ИИ – задать вопрос нейросети",
                        reply_markup=get_main_keyboard())
                    continue

                # Нажатия на кнопки
                if text == "🌤 погода":
                    user_mode[chat_id] = "weather"
                    send_message(chat_id, "Введи название города:")
                    continue
                if text == "🤖 ии":
                    user_mode[chat_id] = "ai"
                    send_message(chat_id, "Задай любой вопрос:")
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
                        send_message(chat_id, f"Город «{text}» не найден. Попробуй ещё раз.")
                    else:
                        send_message(chat_id, weather_result)
                        user_mode.pop(chat_id, None)  # сброс режима
                    continue

                elif current_mode == "ai":
                    ai_answer = ask_groq(text)
                    send_message(chat_id, ai_answer)
                    # оставляем режим, чтобы задать ещё вопрос
                    continue

                else:
                    # Режим не выбран – напоминаем
                    send_message(chat_id, "Пожалуйста, выбери режим на клавиатуре.",
                                 reply_markup=get_main_keyboard())

        except Exception as e:
            print(f"Ошибка цикла: {e}")
            time.sleep(1)

if __name__ == "__main__":
    # Запускаем Flask в фоновом потоке
    threading.Thread(target=run_web_server, daemon=True).start()
    # Основной поток – бот
    main_bot()
