# 🇸🇰 Personal Pollen Alert System (Slovakia)

A lightweight, automated system that monitors pollen levels in Slovakia, sends push notifications to your iPhone via **ntfy.sh**, and provides a simple web dashboard.

## 🚀 How it Works
1. **GitHub Action:** Runs every day at 7:00 AM CET.
2. **Backend (Python):** Fetches data from Open-Meteo Air Quality API for your city.
3. **Notifications:** Sends a "Warning" if pollen is high today, or "Good News" if it's low for the next 3 days (notifications are in Slovak).
4. **Dashboard:** Updates a `data.json` file used by the GitHub Pages dashboard.

---

## 🛠 Setup Instructions

### 1. Find Your Coordinates
Go to [Google Maps](https://www.google.com/maps) or [LatLong.net](https://www.latlong.net/) and search for your city/district in Slovakia.
*   **Bratislava:** `LAT=48.1486`, `LON=17.1077`
*   **Košice:** `LAT=48.7164`, `LON=21.2611`

### 2. Set Up ntfy on iPhone
1. Download the **ntfy** app from the iOS App Store.
2. Open the app and click **"+"** to subscribe to a new topic.
3. Choose a unique name (e.g., `pollen-alert-bratislava-123`).
4. Keep this name for the `NTFY_TOPIC` secret.

### 3. Configure GitHub Secrets
Go to your repository: **Settings > Secrets and variables > Actions > New repository secret**.
Add the following:
*   `LAT`: Your latitude (e.g., `48.1486`)
*   `LON`: Your longitude (e.g., `17.1077`)
*   `NTFY_TOPIC`: Your unique ntfy topic name.
*   `ALLERGENS`: Comma-separated list (e.g., `birch,grass,ragweed,alder,mugwort`).
*   `THRESHOLD`: The grain/m³ limit (default is `10`).
*   `LANG`: Notification language (`en` or `sk`). Defaults to `en`.

> **Dashboard Language:** The web dashboard has a toggle (EN/SK) in the top right corner. It will remember your last choice locally.

### 4. Enable GitHub Pages
1. Go to **Settings > Pages**.
2. Under **Build and deployment > Source**, select **Deploy from a branch**.
3. Select `main` branch and `/ (root)` folder. Click **Save**.
4. Your dashboard will be live at `https://<your-username>.github.io/<repo-name>/`.

---

## 📊 Dashboard Preview
The dashboard (in Slovak) includes:
*   **Traffic Lights:** Green (< Threshold), Orange (> Threshold), Red (> 5x Threshold).
*   **5-Day Trend:** A line chart showing forecasted pollen levels.

## 🛠 Development
To run the script locally:
```bash
pip install requests
export LAT=48.1486
export LON=17.1077
export NTFY_TOPIC=your_topic
export ALLERGENS=birch,grass
export THRESHOLD=10
python pollen_check.py
```
This will generate `data.json` in the current directory.
