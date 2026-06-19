import os
import time
import threading
import requests
from flask import Flask
from waitress import serve

# -------------------- Ключи из переменных окружения --------------------
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
WEATHER_TOKEN = os.environ["WEATHER_TOKEN"]
HF_TOKEN = os.environ["HF_TOKEN"]  # Hugging Face токен

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
user_mode = {}  # chat_id -> "weather" или "ai"

# Фразы для мгновенного ответа
PHRASES = {
    "привет": "Привет! Я бот погоды и искусственного интеллекта.\nВыбери режим на клавиатуре.",
    "здравствуй": "Здравствуй! Чем могу помочь?",
    "как дела": "У меня всё отлично! А у тебя?",
    "что ты умеешь": "Я могу показать погоду в любом городе и отвечать на вопросы с помощью нейросети Mistral.\nИспользуй кнопки ниже.",
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

# -------------------- ИИ (Hugging Face) --------------------
def ask_huggingface(prompt):
    try:
        API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {
            "inputs": f"<s>[INST] {prompt} [/INST]",
            "parameters": {"max_new_tokens": 250, "temperature": 0.7}
        }
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=40)
        # Первый запрос может вернуть пустой ответ, пока модель загружается
        if resp.status_code == 503:
            return "Модель загружается, подождите 10–20 секунд и попробуйте ещё раз."
        if resp.status_code != 200:
            return "Ошибка при обращении к нейросети."
        result = resp.json()
        if isinstance(result, list) and "generated_text" in result[0]:
            return result[0]["generated_text"].split("[/INST]")[-1].strip()
        return "Не удалось получить ответ."
    except Exception:
        return "Извини, не смог связаться с нейросетью."

# -------------------- Веб-сервер (чтобы не засыпать) --------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)

# -------------------- Главный цикл бота --------------------
def main_bot():
    print("Бот с погодой, Mistral AI и веб-сервером запущен...")
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
                    ai_answer = ask_huggingface(text)
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
    # Запускаем веб-сервер в фоновом потоке
    threading.Thread(target=run_web_server, daemon=True).start()
    # Запускаем бота
    main_bot()
