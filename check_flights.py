import requests
import os
import json
from datetime import datetime
import pytz  # для часового пояса Польши
import subprocess  # для git commit/push

# --- Telegram ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# --- Amadeus ---
AMADEUS_KEY = os.environ["AMADEUS_API_KEY"]
AMADEUS_SECRET = os.environ["AMADEUS_API_SECRET"]

# --- Параметры поиска ---
ORIGIN = "WAW"
DESTINATION = "PFO"
DATES = ["2026-04-26", "2026-04-27", "2026-04-28"]
ADULTS = 1

# --- Файл истории ---
HISTORY_FILE = "prices.json"

# --- Получаем токен Amadeus ---
auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
auth_data = {
    "grant_type": "client_credentials",
    "client_id": AMADEUS_KEY,
    "client_secret": AMADEUS_SECRET
}
auth_resp = requests.post(auth_url, data=auth_data)
auth_resp.raise_for_status()
access_token = auth_resp.json()["access_token"]

# --- Запрос цен по датам ---
flights_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
history_entries = []

# Польский часовой пояс
poland_tz = pytz.timezone("Europe/Warsaw")

for DEPARTURE_DATE in DATES:
    params = {
        "originLocationCode": ORIGIN,
        "destinationLocationCode": DESTINATION,
        "departureDate": DEPARTURE_DATE,
        "adults": ADULTS,
        "max": 1
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(flights_url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()

    try:
        price = float(data["data"][0]["price"]["total"])
    except Exception:
        price = None

    now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(poland_tz).strftime("%Y-%m-%d %H:%M")
    history_entries.append({"datetime": now, "departure": DEPARTURE_DATE, "price": price})

# --- Сохраняем историю ---
try:
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
except FileNotFoundError:
    history = []

history.extend(history_entries)
history = history[-6:]  # последние 6 проверок (3 дня × 2 раза в день)

with open(HISTORY_FILE, "w") as f:
    json.dump(history, f, indent=2)

# --- Формируем отчёт ---
prices_str = "\n".join([f"{h['datetime']} | {h['departure']}: {h['price']} €" for h in history])
report = f"✈️ WAW → PFO (Paphos)\nПоследние 6 цен:\n{prices_str}"

# --- Отправка в Telegram ---
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {"chat_id": CHAT_ID, "text": report}
response = requests.post(url, json=payload)
print("STATUS:", response.status_code)
print("RESPONSE:", response.text)

# --- Commit prices.json обратно в репо ---
try:
    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "github-actions@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", HISTORY_FILE], check=True)
    subprocess.run(["git", "commit", "-m", f"Update flight prices {datetime.now().strftime('%Y-%m-%d %H:%M')}"], check=True)
    subprocess.run(["git", "push"], check=True)
except subprocess.CalledProcessError:
    print("No changes to commit or git error")
