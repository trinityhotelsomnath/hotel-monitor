import requests
import json
import time
import os
import re
import threading
from datetime import datetime
from flask import Flask

# ============================================================
# FLASK APP - Gunicorn isko serve karega (bohot reliable)
# ============================================================
app = Flask(__name__)

@app.route("/")
def health():
    return "Hotel Monitor is running!"

# ============================================================
# NTFY TOPIC
# ============================================================
NTFY_TOPIC = "somnath-hotel-alert-xyz123"

# ============================================================
# COMPETITORS - Google + OTA Reviews
# ============================================================
COMPETITORS = [
    {
        "name": "Clarks Collection Hotel Somnath",
        "google": "Clarks Collection Hotel Somnath reviews",
        "tripadvisor": "https://www.tripadvisor.in/Hotel_Review-g2282347-d26851474-Reviews-Clarks_Collection_Somnath-Somnath_Gir_Somnath_District_Gujarat.html",
        "makemytrip": "Clarks Collection Somnath Pure Veg MakeMyTrip reviews",
        "booking": "Clarks Collection Somnath Booking.com reviews",
    },
    {
        "name": "Ekansh Hotels and Resorts Somnath",
        "google": "Ekansh Hotels and Resorts Somnath reviews",
        "tripadvisor": "Ekansh Hotels Somnath TripAdvisor reviews",
        "makemytrip": "Ekansh Hotels Somnath MakeMyTrip reviews",
        "booking": "Ekansh Hotels Somnath Booking.com reviews",
    },
    {
        "name": "Aditya Inn Somnath",
        "google": "Aditya Inn Somnath reviews",
        "tripadvisor": "Aditya Inn Somnath TripAdvisor reviews",
        "makemytrip": "Aditya Inn Somnath MakeMyTrip reviews",
        "booking": "Aditya Inn Somnath Booking.com reviews",
    },
    {
        "name": "Regenta Central Somnath",
        "google": "Regenta Central Somnath reviews",
        "tripadvisor": "Regenta Central Somnath TripAdvisor reviews",
        "makemytrip": "Regenta Central Somnath MakeMyTrip reviews",
        "booking": "Regenta Central Somnath Booking.com reviews",
    },
    {
        "name": "VITS Somnath Gateway",
        "google": "VITS Somnath Gateway reviews",
        "tripadvisor": "VITS Somnath Gateway TripAdvisor reviews",
        "makemytrip": "VITS Somnath Gateway MakeMyTrip reviews",
        "booking": "VITS Somnath Gateway Booking.com reviews",
    },
    {
        "name": "Sarovar Portico Somnath",
        "google": "Sarovar Portico Somnath reviews",
        "tripadvisor": "Sarovar Portico Somnath TripAdvisor reviews",
        "makemytrip": "Sarovar Portico Somnath MakeMyTrip reviews",
        "booking": "Sarovar Portico Somnath Booking.com reviews",
    },
]

STORE_FILE = "reviews_store.json"

def load_store():
    if os.path.exists(STORE_FILE):
        with open(STORE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_store(store):
    with open(STORE_FILE, 'w', encoding='utf-8') as f:
        json.dump(store, f, indent=2, ensure_ascii=False)

def send_notification(title, message, priority="default"):
    try:
        response = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={
                "Title": title.encode('utf-8'),
                "Priority": priority,
                "Tags": "hotel,review,alert",
            },
            timeout=10
        )
        if response.status_code == 200:
            print(f"✅ Notification sent: {title}")
        else:
            print(f"❌ Notification failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Notification error: {e}")

def get_review_count_from_google(hotel_name):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        search_url = f"https://www.google.com/search?q={hotel_name.replace(' ', '+')}+reviews&hl=en"
        response = requests.get(search_url, headers=headers, timeout=12)
        text = response.text
        match = re.search(r'(\d[\d,]*)\s*(?:Google\s*)?reviews?', text)
        if match:
            return int(match.group(1).replace(',', ''))
        return 0
    except Exception as e:
        print(f"  ❌ Google fetch error: {e}")
        return 0

def get_review_count_from_tripadvisor(url_or_query):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if url_or_query.startswith("http"):
            url = url_or_query
        else:
            search_url = f"https://www.google.com/search?q={url_or_query.replace(' ', '+')}&hl=en"
            r = requests.get(search_url, headers=headers, timeout=12)
            ta_match = re.search(r'https://www\.tripadvisor\.[a-z]+/Hotel_Review[^\s"\']+', r.text)
            if not ta_match:
                return 0
            url = ta_match.group(0)

        response = requests.get(url, headers=headers, timeout=12)
        text = response.text
        patterns = [
            r'"reviewCount"\s*:\s*(\d+)',
            r'(\d[\d,]*)\s*reviews?',
            r'(\d+)\s*traveler reviews',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1).replace(',', ''))
        return 0
    except Exception as e:
        print(f"  ❌ TripAdvisor fetch error: {e}")
        return 0

def get_review_count_from_mmt(hotel_name):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        search_url = f"https://www.google.com/search?q={hotel_name.replace(' ', '+')}+MakeMyTrip+reviews&hl=en"
        response = requests.get(search_url, headers=headers, timeout=12)
        text = response.text
        match = re.search(r'(\d[\d,]*)\s*(?:ratings?|reviews?)', text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(',', ''))
        return 0
    except Exception as e:
        print(f"  ❌ MMT fetch error: {e}")
        return 0

def get_review_count_from_booking(hotel_name):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        search_url = f"https://www.google.com/search?q={hotel_name.replace(' ', '+')}+Booking.com+reviews&hl=en"
        response = requests.get(search_url, headers=headers, timeout=12)
        text = response.text
        match = re.search(r'(\d[\d,]*)\s*(?:guest\s*)?reviews?', text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(',', ''))
        return 0
    except Exception as e:
        print(f"  ❌ Booking fetch error: {e}")
        return 0

def check_hotel_reviews(hotel, store):
    name = hotel["name"]
    print(f"\n📍 Checking: {name}")

    if name not in store:
        store[name] = {}

    platforms = {
        "Google": lambda: get_review_count_from_google(hotel["google"]),
        "TripAdvisor": lambda: get_review_count_from_tripadvisor(hotel["tripadvisor"]),
        "MakeMyTrip": lambda: get_review_count_from_mmt(hotel["name"]),
        "Booking.com": lambda: get_review_count_from_booking(hotel["name"]),
    }

    new_reviews_found = []

    for platform, fetch_fn in platforms.items():
        try:
            current_count = fetch_fn()
            old_count = store[name].get(platform, {}).get("count", 0)

            print(f"  {platform}: {old_count} → {current_count}")

            if current_count > 0 and old_count == 0:
                store[name][platform] = {
                    "count": current_count,
                    "last_checked": datetime.now().isoformat()
                }
            elif current_count > old_count and old_count > 0:
                new_count = current_count - old_count
                new_reviews_found.append({
                    "platform": platform,
                    "new": new_count,
                    "total": current_count
                })
                store[name][platform] = {
                    "count": current_count,
                    "last_checked": datetime.now().isoformat(),
                    "last_new": datetime.now().isoformat()
                }
            else:
                if platform in store[name]:
                    store[name][platform]["last_checked"] = datetime.now().isoformat()

            # Har request ke baad thoda rukho, taaki health check ko bhi mauka mile
            time.sleep(6)

        except Exception as e:
            print(f"  ❌ {platform} error: {e}")

    if new_reviews_found:
        platforms_text = "\n".join([
            f"• {r['platform']}: +{r['new']} naya review (Total: {r['total']})"
            for r in new_reviews_found
        ])
        title = f"🏨 New Review: {name}"
        message = (
            f"Hotel: {name}\n\n"
            f"{platforms_text}\n\n"
            f"Time: {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n"
            f"Turant check karo!"
        )
        send_notification(title, message, priority="high")

def check_all_reviews():
    print(f"\n🔍 Checking ALL hotels at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    store = load_store()

    for hotel in COMPETITORS:
        check_hotel_reviews(hotel, store)
        time.sleep(5)  # Hotels ke beech zyada gap - health check ko breathing room

    save_store(store)
    print(f"\n✅ Check complete! Next check in 1 hour.")

def background_monitor_loop():
    """Yeh function background thread mein chalega, LOW PRIORITY ke saath"""
    print("🚀 Hotel Review Monitor (Multi-OTA) Shuru Ho Gaya!")
    print(f"📱 Notifications: ntfy.sh/{NTFY_TOPIC}")
    print(f"⏰ Interval: Har 1 ghante mein")
    print(f"🏨 Hotels: {len(COMPETITORS)}")
    print("=" * 55)

    # Server ko pehle settle hone do
    time.sleep(15)

    send_notification(
        "✅ Multi-OTA Monitor Started!",
        f"Aapka Hotel Review Monitor shuru ho gaya!\n"
        f"{len(COMPETITORS)} competitors monitor ho rahe hain.\n"
        f"Platforms: Google, TripAdvisor, MakeMyTrip, Booking.com\n"
        f"Har ghante check hoga!",
        priority="low"
    )

    while True:
        try:
            check_all_reviews()
            print(f"\n⏳ Next check in 1 hour...")
            time.sleep(3600)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("⏳ 5 min mein retry...")
            time.sleep(300)

# Background thread ko module load hote hi shuru kar do
# (Gunicorn jab is file ko import karega, tab yeh automatically chalu ho jayega)
monitor_thread = threading.Thread(target=background_monitor_loop, daemon=True)
monitor_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
