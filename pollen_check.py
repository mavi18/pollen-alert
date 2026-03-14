import os
import json
import requests
from datetime import datetime, timedelta, timezone

def get_pollen_data(lat, lon):
    url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&hourly=alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,ragweed_pollen"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def process_data(data, target_allergens, threshold):
    hourly = data['hourly']
    times = hourly['time']
    daily_data = {}

    for i, t in enumerate(times):
        date = t.split('T')[0]
        if date not in daily_data:
            daily_data[date] = {a: 0 for a in target_allergens}
        
        for a in target_allergens:
            api_key = f"{a}_pollen"
            if api_key in hourly:
                val = hourly[api_key][i]
                if val is not None:
                    daily_data[date][a] = max(daily_data[date][a], val)

    sorted_dates = sorted(daily_data.keys())
    return [{"date": d, "allergens": daily_data[d]} for d in sorted_dates]

def send_notification(topic, title, message, priority="default"):
    url = f"https://ntfy.sh/{topic}"
    requests.post(url, 
        data=message.encode('utf-8'),
        headers={
            "Title": title.encode('utf-8'),
            "Priority": priority,
            "Tags": "herb,sunny"
        }
    )

def main():
    # Load environment variables
    lat = os.getenv('LAT', '48.1486')
    lon = os.getenv('LON', '17.1077')
    ntfy_topic = os.getenv('NTFY_TOPIC')
    allergens_str = os.getenv('ALLERGENS', 'birch,grass,ragweed,alder,mugwort')
    threshold = float(os.getenv('THRESHOLD', '10'))

    target_allergens = [a.strip().lower() for a in allergens_str.split(',')]
    
    # Filter only supported allergens (Open-Meteo)
    supported = ['alder', 'birch', 'grass', 'mugwort', 'ragweed']
    monitored = [a for a in target_allergens if a in supported]

    if not monitored:
        print("No supported allergens found in ALLERGENS list.")
        return

    # Fetch and process
    raw_data = get_pollen_data(lat, lon)
    processed_daily = process_data(raw_data, monitored, threshold)

    # Logic for notifications
    today_date = datetime.now().strftime('%Y-%m-%d')
    three_day_window = processed_daily[:3] # Today + next 2 days
    
    is_all_low = True
    high_today_info = []

    for day in three_day_window:
        for allergen, val in day['allergens'].items():
            if val >= threshold:
                is_all_low = False
                if day['date'] == today_date:
                    high_today_info.append(f"{allergen.capitalize()}: {val:.1f}")

    if ntfy_topic:
        if is_all_low:
            send_notification(
                ntfy_topic, 
                "☀️ Good News: Low Pollen!", 
                f"All monitored allergens are below {threshold} grains/m³ for the next 3 days.",
                priority="low"
            )
        elif high_today_info:
            send_notification(
                ntfy_topic, 
                "🌿 Warning: High Pollen!", 
                f"High levels today ({today_date}): {', '.join(high_today_info)}",
                priority="high"
            )

    # Save data for dashboard
    output = {
        "last_updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "city_coords": [float(lat), float(lon)],
        "threshold": threshold,
        "daily_data": processed_daily
    }

    with open('data.json', 'w') as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    main()
