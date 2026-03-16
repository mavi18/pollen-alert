import os
import json
import requests
import socket
from datetime import datetime, timezone

# Force IPv4 for GitHub Actions compatibility
import requests.packages.urllib3.util.connection as urllib3_cn
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

# Configuration
# Use the hidden JSON API endpoint
API_URL_TEMPLATE = "https://www.pelovespravodajstvo.sk/verejnost/xml/getallcities/?kraj={kraj_id}"
DATA_FILE = "pollen_data_sk.json"
NTFY_TOPIC = os.getenv('NTFY_TOPIC')
KRAJ_ID = os.getenv('KRAJ_ID', '1') # Default: 1 (Bratislava)

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

def get_level(value):
    val = float(value) if value else 0
    if val == 0: return 0
    if val <= 5: return 1
    if val <= 30: return 2
    if val <= 50: return 3
    if val <= 150: return 4
    return 5

def scrape_data(kraj_id):
    url = API_URL_TEMPLATE.format(kraj_id=kraj_id)
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    raw_data = response.json()
    results = {}
    
    for item in raw_data:
        name = item.get('alergen')
        if not name: continue
        
        # Mapping to match existing dashboard structure
        results[name] = {
            "level": get_level(item.get('value', 0)),
            "value": item.get('value', 0),
            "trend": TREND_MAP.get(item.get('prognose', '').split('/')[-1], "➡️ Ustálená")
        }
    
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

def compare_and_notify(new_data, old_history):
    if not old_history:
        return True # First run
    
    last_entry = old_history[-1]['allergens']
    
    # Compare levels only (ignore small value fluctuations)
    current_levels = {k: v['level'] for k, v in new_data.items()}
    last_levels = {k: v['level'] for k, v in last_entry.items()}
    
    if current_levels == last_levels:
        print("Pollen levels are identical to the last record. No update needed.")
        return False

    # Check for significant changes
    changes = []
    # Use union of keys to catch new allergens appearing
    all_allergens = set(current_levels.keys()) | set(last_levels.keys())
    
    for allergen in all_allergens:
        new_lvl = current_levels.get(allergen, 0)
        old_lvl = last_levels.get(allergen, 0)
        
        if new_lvl != old_lvl:
            action = "stúpla" if new_lvl > old_lvl else "klesla"
            changes.append(f"{allergen}: {LEVEL_NAMES[old_lvl]} -> {LEVEL_NAMES[new_lvl]} ({new_data.get(allergen, {}).get('trend', '')})")
    
    if changes:
        title = "📊 Zmena peľovej situácie (Štátny monitoring)"
        message = "Boli zaznamenané zmeny:\n" + "\n".join(changes)
        send_notification(title, message, priority="high")
    
    return True

def main():
    try:
        current_pollen = scrape_data(KRAJ_ID)
        if not current_pollen:
            print("No data received from API.")
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
            
            # Keep only last 12 records (approx 3 months of weekly updates)
            history = history[-12:]
            
            with open(DATA_FILE, 'w') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            print(f"New data saved to {DATA_FILE}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
