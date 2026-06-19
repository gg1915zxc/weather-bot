import os
import requests
from flask import Flask, request, Response

# ---------- Ключи ----------
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
WEATHER_TOKEN = os.environ["WEATHER_TOKEN"]
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ---------- Состояния пользователей ----------
user_mode = {}

PHRASES = {
    "привет": "Привет! Я бот погоды. Нажми кнопку «Погода» и введи город.",
    "здравствуй": "Здравствуй! Чем могу помочь?",
    "как дела": "У меня всё отлично! А у тебя?",
    "что ты умеешь": "Я показываю погоду в любом городе мира.\nНажми кнопку «Погода» и введи название.",
    "спасибо": "Пожалуйста! Обращайся.",
    "пока": "До встречи!"
}

# ---------- Клавиатура ----------
def get_main_keyboard():
    return {
        "keyboard": [["🌤 Погода"]],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

# ---------- Погода ----------
def get_weather(city):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": WEATHER_TOKEN, "units": "metric", "lang": "ru"}
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

# ---------- Telegram helpers ----------
def send_message(chat_id, text, reply_markup=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

# ---------- Обработка входящего сообщения ----------
def process_message(chat_id, text):
    text = text.strip().lower()

    if text == "/start":
        send_message(chat_id,
            "Привет! Я бот погоды.\nНажми кнопку «🌤 Погода» и введи город.",
            reply_markup=get_main_keyboard())
        return

    if text == "🌤 погода":
        user_mode[chat_id] = "weather"
        send_message(chat_id, "Введи название города:")
        return

    if text in PHRASES:
        send_message(chat_id, PHRASES[text])
        return

    # Определяем режим
    current_mode = user_mode.get(chat_id)

    if current_mode == "weather":
        weather_result = get_weather(text)
        if weather_result is None:
            send_message(chat_id, f"Город «{text}» не найден. Проверь название.")
        else:
            send_message(chat_id, weather_result)
            user_mode.pop(chat_id, None)  # сброс режима
    else:
        send_message(chat_id,
            "Нажми кнопку «🌤 Погода», чтобы узнать погоду.",
            reply_markup=get_main_keyboard())

# ---------- Flask приложение ----------
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        if text:
            process_message(chat_id, text)
    return Response(status=200)

# ---------- Точка входа для настройки вебхука ----------
def set_webhook():
    url = f"{BASE_URL}/setWebhook"
    # PythonAnywhere даст нам публичный URL. Замени <твой_домен> ниже.
    webhook_url = "https://<твой_логин>.pythonanywhere.com/webhook"
    payload = {"url": webhook_url}
    resp = requests.post(url, json=payload)
    print("Webhook set:", resp.json())

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=5000)        "keyboard": [["🌤 Погода"]],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

# -------------------- Погода --------------------
def get_weather(city):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": WEATHER_TOKEN, "units": "metric", "lang": "ru"}
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

# -------------------- Self-ping (чтобы Render не усыплял) --------------------
def self_ping(port):
    """Каждые 10 минут стучимся к своему же веб-серверу."""
    while True:
        time.sleep(600)  # 10 минут
        try:
            requests.get(f"http://localhost:{port}/", timeout=5)
        except Exception:
            pass

# -------------------- Веб-сервер --------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    # Запускаем self-ping в отдельном потоке
    threading.Thread(target=self_ping, args=(port,), daemon=True).start()
    serve(app, host="0.0.0.0", port=port)

# -------------------- Главный цикл --------------------
def main_bot():
    print("Бот погоды (без ИИ, с self-ping) запущен...")
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

                if text == "/start":
                    send_message(chat_id,
                        "Привет! Я бот погоды.\nНажми кнопку «🌤 Погода» и введи город.",
                        reply_markup=get_main_keyboard())
                    continue

                if text == "🌤 погода":
                    user_mode[chat_id] = "weather"
                    send_message(chat_id, "Введи название города:")
                    continue

                if text in PHRASES:
                    send_message(chat_id, PHRASES[text])
                    continue

                current_mode = user_mode.get(chat_id)

                if current_mode == "weather":
                    weather_result = get_weather(text)
                    if weather_result is None:
                        send_message(chat_id, f"Город «{text}» не найден. Проверь название.")
                    else:
                        send_message(chat_id, weather_result)
                        user_mode.pop(chat_id, None)
                    continue

                else:
                    send_message(chat_id,
                        "Нажми кнопку «🌤 Погода», чтобы узнать погоду.",
                        reply_markup=get_main_keyboard())

        except Exception as e:
            print(f"Ошибка цикла: {e}")
            time.sleep(1)

if __name__ == "__main__":
    # Flask + self-ping стартуют в run_web_server
    threading.Thread(target=run_web_server, daemon=True).start()
    main_bot()
