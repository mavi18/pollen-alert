import os
import json
import requests
import socket
from bs4 import BeautifulSoup
from datetime import datetime, timezone

# Force IPv4 for GitHub Actions compatibility
import requests.packages.urllib3.util.connection as urllib3_cn
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

# Configuration
URL = "https://www.pelovespravodajstvo.sk/verejnost/aktualne"
DATA_FILE = "pollen_data_sk.json"
NTFY_TOPIC = os.getenv('NTFY_TOPIC')
KRAJ_ID = os.getenv('KRAJ_ID', '1') # Default: 1 (Bratislava)

LEVEL_MAP = {
    "koncentracia_0.png": 0,
    "koncentracia_1.png": 1,
    "koncentracia_2.png": 2,
    "koncentracia_3.png": 3,
    "koncentracia_4.png": 4,
    "koncentracia_5.png": 5
}

LEVEL_NAMES = {
    0: "Nulová",
    1: "Veľmi nízka",
    2: "Nízka",
    3: "Stredná",
    4: "Vysoká",
    5: "Veľmi vysoká"
}

TREND_MAP = {
    "koncentracia_stav_znizenie.png": "⬇️ Klesá",
    "koncentracia_stav_ustalena_znizenie.png": "↘️ Ustálená/Klesá",
    "koncentracia_stav_ustalena.png": "➡️ Ustálená",
    "koncentracia_stav_ustalena_zvysenie.png": "↗️ Ustálená/Stúpa",
    "koncentracia_stav_zvysenie.png": "⬆️ Stúpa"
}

def scrape_data(kraj_id):
    headers = {'User-Agent': 'Mozilla/5.0'}
    data = {'kraj': kraj_id}
    response = requests.post(URL, headers=headers, data=data)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    results = {}
    
    # Target the "Top 5" or any available allergens in the select containers
    items = soup.select('.selectCnt label')
    for item in items:
        name = item.get_text(strip=True)
        if not name: continue
        
        imgs = item.find_all('img')
        level = 0
        trend = "➡️ Ustálená"
        
        for img in imgs:
            src = img.get('src', '')
            filename = src.split('/')[-1]
            if "koncentracia_" in filename and "stav" not in filename:
                level = LEVEL_MAP.get(filename, 0)
            elif "koncentracia_stav_" in filename:
                trend = TREND_MAP.get(filename, "➡️ Ustálená")
        
        results[name] = {"level": level, "trend": trend}
    
    return results

def send_notification(title, message, priority="default"):
    if not NTFY_TOPIC: return
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    requests.post(url, 
        data=message.encode('utf-8'),
        headers={
            "Title": title.encode('utf-8'),
            "Priority": priority,
            "Tags": "warning,herb"
        }
    )

def compare_and_notify(new_data, old_data):
    if not old_data:
        return True # First run, always save
    
    last_entry = old_data[-1]['allergens']
    if last_entry == new_data:
        print("Data is identical to the last record. No update needed.")
        return False

    # Check for significant changes
    changes = []
    for allergen, info in new_data.items():
        old_info = last_entry.get(allergen, {"level": 0, "trend": ""})
        diff = info['level'] - old_info['level']
        
        if abs(diff) >= 1: # Level changed
            action = "stúpla" if diff > 0 else "klesla"
            changes.append(f"{allergen} {action} na {LEVEL_NAMES[info['level']]} ({info['trend']})")
    
    if changes:
        title = "📊 Zmena hladiny peľu (Štátny monitoring)"
        message = "\n".join(changes)
        send_notification(title, message, priority="high")
    
    return True

def main():
    try:
        current_pollen = scrape_data(KRAJ_ID)
        if not current_pollen:
            print("No data scraped. Check site structure.")
            return

        # Load history
        history = []
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                history = json.load(f)

        if compare_and_notify(current_pollen, history):
            new_record = {
                "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                "date": datetime.now().strftime('%d.%m.%Y'),
                "allergens": current_pollen
            }
            history.append(new_record)
            
            # Keep only last 10 records to keep file small
            history = history[-10:]
            
            with open(DATA_FILE, 'w') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            print(f"New data saved to {DATA_FILE}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
