import requests
import os
from datetime import date

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# 🚧 ВРЕМЕННО: тестовое сообщение
message = f"✈️ Тест! GitHub Actions работает.\nДата: {date.today()}"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": message
}

requests.post(url, json=payload)
