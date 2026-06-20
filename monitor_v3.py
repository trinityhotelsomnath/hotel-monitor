import requests
import json
import time
import os
import re
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============================================================
# FAKE WEB SERVER - Render ko khush karne ke liye (port binding)
# ============================================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Hotel Monitor is running!")
    def log_message(self, format, *args):
        pass  # Logs ko chup rakho

def start_fake_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

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
        "goibibo": "https://www.goibibo.com/hotels/review-of-clarks-collection-somnath-pure-veg-hotel-in-somnath-865236681647575828/",
    },
    {
        "name": "Ekansh Hotels and Resorts Somnath",
        "google": "Ekansh Hotels and Resorts Somnath reviews",
        "tripadvisor": "Ekansh Hotels Somnath TripAdvisor reviews",
        "makemytrip": "Ekansh Hotels Somnath MakeMyTrip reviews",
        "booking": "Ekansh Hotels Somnath Booking.com reviews",
        "goibibo": "Ekansh Hotels Somnath Goibibo reviews",
    },
    {
        "name": "Aditya Inn Somnath",
        "google": "Aditya Inn Somnath reviews",
        "tripadvisor": "Aditya Inn Somnath TripAdvisor reviews",
        "makemytrip": "Aditya Inn Somnath MakeMyTrip reviews",
        "booking": "Aditya Inn Somnath Booking.com reviews",
        "goibibo": "Aditya Inn Somnath Goibibo reviews",
    },
    {
        "name": "Regenta Central Somnath",
        "google": "Regenta Central Somnath reviews",
        "tripadvisor": "Regenta Central Somnath TripAdvisor reviews",
        "makemytrip": "Regenta Central Somnath MakeMyTrip reviews",
        "booking": "Regenta Central Somnath Booking.com reviews",
        "goibibo": "Regenta Central Somnath Goibibo reviews",
    },
    {
        "name": "VITS Somnath Gateway",
        "google": "VITS Somnath Gateway reviews",
        "tripadvisor": "VITS Somnath Gateway TripAdvisor reviews",
        "makemytrip": "VITS Somnath Gateway MakeMyTrip reviews",
        "booking": "VITS Somnath Gateway Booking.com reviews",
        "goibibo": "VITS Somnath Gateway Goibibo reviews",
    },
    {
        "name": "Sarovar Portico Somnath",
        "google": "Sarovar Portico Somnath reviews",
        "tripadvisor": "Sarovar Portico Somnath TripAdvisor reviews",
        "makemytrip": "Sarovar Portico Somnath MakeMyTrip reviews",
        "booking": "Sarovar Portico Somnath Booking.com reviews",
        "goibibo": "Sarovar Portico Somnath Goibibo reviews",
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
    """Google search se review count fetch karo"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        search_url = f"https://www.google.com/search?q={hotel_name.replace(' ', '+')}+reviews&hl=en"
        response = requests.get(search_url, headers=headers, timeout=15)
        text = response.text
        match = re.search(r'(\d[\d,]*)\s*(?:Google\s*)?reviews?', text)
        if match:
            return int(match.group(1).replace(',', ''))
        return 0
    except Exception as e:
        print(f"  ❌ Google fetch error: {e}")
        return 0

def get_review_count_from_tripadvisor(url_or_query):
    """TripAdvisor se review count fetch karo"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if url_or_query.startswith("http"):
            url = url_or_query
        else:
            # Google pe search karke URL dhundho
            search_url = f"https://www.google.com/search?q={url_or_query.replace(' ', '+')}&hl=en"
            r = requests.get(search_url, headers=headers, timeout=15)
            ta_match = re.search(r'https://www\.tripadvisor\.[a-z]+/Hotel_Review[^\s"\']+', r.text)
            if not ta_match:
                return 0
            url = ta_match.group(0)

        response = requests.get(url, headers=headers, timeout=15)
        text = response.text
        # Review count patterns
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
    """MakeMyTrip/Goibibo se review count fetch karo"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        search_url = f"https://www.google.com/search?q={hotel_name.replace(' ', '+')}+MakeMyTrip+reviews&hl=en"
        response = requests.get(search_url, headers=headers, timeout=15)
        text = response.text
        match = re.search(r'(\d[\d,]*)\s*(?:ratings?|reviews?)', text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(',', ''))
        return 0
    except Exception as e:
        print(f"  ❌ MMT fetch error: {e}")
        return 0

def get_review_count_from_booking(hotel_name):
    """Booking.com se review count fetch karo"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        search_url = f"https://www.google.com/search?q={hotel_name.replace(' ', '+')}+Booking.com+reviews&hl=en"
        response = requests.get(search_url, headers=headers, timeout=15)
        text = response.text
        match = re.search(r'(\d[\d,]*)\s*(?:guest\s*)?reviews?', text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(',', ''))
        return 0
    except Exception as e:
        print(f"  ❌ Booking fetch error: {e}")
        return 0

def check_hotel_reviews(hotel, store):
    """Ek hotel ke sabhi OTA reviews check karo"""
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
                # Pehli baar tracking
                store[name][platform] = {
                    "count": current_count,
                    "last_checked": datetime.now().isoformat()
                }
            elif current_count > old_count and old_count > 0:
                # Naya review aaya!
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

            time.sleep(2)  # Rate limiting

        except Exception as e:
            print(f"  ❌ {platform} error: {e}")

    # Agar koi naya review mila toh notification bhejo
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
    """Sabhi hotels check karo"""
    print(f"\n🔍 Checking ALL hotels at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    store = load_store()

    for hotel in COMPETITORS:
        check_hotel_reviews(hotel, store)
        time.sleep(3)  # Hotels ke beech wait

    save_store(store)
    print(f"\n✅ Check complete! Next check in 1 hour.")

def run_monitor():
    """Main loop"""
    print("🚀 Hotel Review Monitor (Multi-OTA) Shuru Ho Gaya!")
    print(f"📱 Notifications: ntfy.sh/{NTFY_TOPIC}")
    print(f"⏰ Interval: Har 1 ghante mein")
    print(f"🏨 Hotels: {len(COMPETITORS)}")
    print(f"🌐 Platforms: Google, TripAdvisor, MakeMyTrip, Booking.com")
    print("=" * 55)

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
            print(f"\n⏳ Next check in 1 hour... (Ctrl+C to stop)")
            time.sleep(3600)
        except KeyboardInterrupt:
            print("\n\n🛑 Monitor band. Bye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("⏳ 5 min mein retry...")
            time.sleep(300)

if __name__ == "__main__":
    # Pehle fake web server background mein chalao (Render ke liye)
    server_thread = threading.Thread(target=start_fake_server, daemon=True)
    server_thread.start()
    print("🌐 Health check server started on port", os.environ.get("PORT", 10000))

    # Phir asli monitoring shuru karo
    run_monitor()
