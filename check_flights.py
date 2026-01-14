import requests
import os
import json
from datetime import datetime
import pytz

# --- Telegram ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# --- Amadeus ---
AMADEUS_KEY = os.environ["AMADEUS_API_KEY"]
AMADEUS_SECRET = os.environ["AMADEUS_API_SECRET"]

# --- Параметры поиска ---
ROUTES = [
    {"origin": "WAW", "name": "Warsaw Chopin"},
    {"origin": "WMI", "name": "Warsaw Modlin"}
]
DESTINATION = "PFO"
DATES = ["2026-04-26", "2026-04-27", "2026-04-28"]
ADULTS = 1

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

# --- Польский часовой пояс ---
poland_tz = pytz.timezone("Europe/Warsaw")

# --- Загрузка истории ---
try:
    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)
except FileNotFoundError:
    history = []

# --- Проверка маршрутов и дат ---
for route in ROUTES:
    for date in DATES:
        flights_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": route["origin"],
            "destinationLocationCode": DESTINATION,
            "departureDate": date,
            "adults": ADULTS,
            "max": 1
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get(flights_url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        try:
            flight = data["data"][0]
            price = float(flight["price"]["total"])
            itinerary = flight["itineraries"][0]
            segments = itinerary["segments"]

            seg_info = []
            for seg in segments:
                departure = datetime.fromisoformat(seg["departure"]["at"]).astimezone(poland_tz).strftime("%H:%M")
                arrival = datetime.fromisoformat(seg["arrival"]["at"]).astimezone(poland_tz).strftime("%H:%M")
                seg_info.append(f"{seg['carrierCode']} {seg['number']}: {seg['departure']['iataCode']} {departure} -> {seg['arrival']['iataCode']} {arrival}, Duration {seg['duration']}, Stops {len(segments)-1}")

            now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(poland_tz).strftime("%Y-%m-%d %H:%M")
            history.append({
                "datetime": now,
                "route": f"{route['origin']} → {DESTINATION}",
                "route_name": route["name"],
                "departure_date": date,
                "price": price,
                "details": seg_info
            })
        except Exception as e:
            now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(poland_tz).strftime("%Y-%m-%d %H:%M")
            history.append({
                "datetime": now,
                "route": f"{route['origin']} → {DESTINATION}",
                "route_name": route["name"],
                "departure_date": date,
                "price": None,
                "details": [f"Ошибка: {str(e)}"]
            })

# --- Оставляем последние 12 записей (2 маршрута × 3 даты × 2 раза в день) ---
history = history[-12:]

# --- Сохраняем историю ---
with open(HISTORY_FILE, "w") as f:
    json.dump(history, f, indent=2)

# --- Формируем отчет для Telegram ---
report_lines = []
for h in history:
    lines = [f"{h['datetime']} | {h['route_name']} ({h['route']}) | {h['departure_date']} | Price: {h['price']} €"]
    lines.extend(h['details'])
    report_lines.append("\n".join(lines))

report = "✈️ Flight Prices Report\n\n" + "\n\n".join(report_lines)

# --- Отправка в Telegram ---
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {"chat_id": CHAT_ID, "text": report}
response = requests.post(url, json=payload)
print("STATUS:", response.status_code)
print("RESPONSE:", response.text)
