import requests
import json
import time
import os
import hashlib
from datetime import datetime
import re

# ============================================================
# APKA NTFY CHANNEL NAME - Isko apna unique naam do
# ============================================================
NTFY_TOPIC = "somnath-hotel-alert-xyz123"  # Aap isko badal sakte ho

# ============================================================
# COMPETITORS LIST
# ============================================================
COMPETITORS = [
    {
        "name": "Clarks Collection Hotel Somnath",
        "search_query": "Clarks Collection Hotel Somnath reviews"
    },
    {
        "name": "Ekansh Hotels and Resorts Somnath",
        "search_query": "Ekansh Hotels and Resorts Somnath reviews"
    },
    {
        "name": "Aditya Inn Somnath",
        "search_query": "Aditya Inn Somnath reviews"
    },
    {
        "name": "Regenta Central Somnath",
        "search_query": "Regenta Central Somnath reviews"
    },
    {
        "name": "VITS Somnath Gateway",
        "search_query": "VITS Somnath Gateway reviews"
    },
    {
        "name": "Sarovar Portico Somnath",
        "search_query": "Sarovar Portico Somnath reviews"
    }
]

# ============================================================
# REVIEWS STORE FILE
# ============================================================
STORE_FILE = "reviews_store.json"

def load_store():
    """Purane reviews load karo"""
    if os.path.exists(STORE_FILE):
        with open(STORE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_store(store):
    """Reviews store karo"""
    with open(STORE_FILE, 'w', encoding='utf-8') as f:
        json.dump(store, f, indent=2, ensure_ascii=False)

def send_notification(title, message, priority="default"):
    """Phone pe notification bhejo via ntfy.sh"""
    try:
        response = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={
                "Title": title.encode('utf-8'),
                "Priority": priority,
                "Tags": "hotel,review,alert",
                "Icon": "https://fonts.gstatic.com/s/i/materialicons/hotel/v6/24px.svg"
            },
            timeout=10
        )
        if response.status_code == 200:
            print(f"✅ Notification bheja: {title}")
        else:
            print(f"❌ Notification fail: {response.status_code}")
    except Exception as e:
        print(f"❌ Notification error: {e}")

def get_reviews_via_serpapi(hotel_name, search_query):
    """
    Google Reviews fetch karo using SerpAPI (free tier: 100 searches/month)
    Ya phir direct scraping se
    """
    try:
        # SerpAPI use karo (free account banao serpapi.com pe)
        SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
        
        if SERPAPI_KEY:
            url = "https://serpapi.com/search"
            params = {
                "engine": "google_maps_reviews",
                "place_id": search_query,
                "api_key": SERPAPI_KEY,
                "hl": "en",
                "sort_by": "newestFirst"
            }
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            reviews = []
            if "reviews" in data:
                for r in data["reviews"][:5]:  # Last 5 reviews
                    reviews.append({
                        "author": r.get("user", {}).get("name", "Unknown"),
                        "rating": r.get("rating", 0),
                        "text": r.get("snippet", ""),
                        "date": r.get("date", ""),
                        "id": hashlib.md5(f"{r.get('user', {}).get('name', '')}{r.get('snippet', '')}".encode()).hexdigest()
                    })
            return reviews
        else:
            # SerpAPI key nahi hai toh basic scraping
            return scrape_reviews_basic(hotel_name)
            
    except Exception as e:
        print(f"❌ Error fetching reviews for {hotel_name}: {e}")
        return []

def scrape_reviews_basic(hotel_name):
    """
    Basic review scraping without API
    Place ID se Google Maps reviews fetch karta hai
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        # Google search se review count dhundho
        search_url = f"https://www.google.com/search?q={hotel_name.replace(' ', '+')}+reviews&hl=en"
        response = requests.get(search_url, headers=headers, timeout=15)
        
        # Review count extract karo
        text = response.text
        
        # Rating pattern dhundho
        rating_match = re.search(r'"(\d+\.\d+)".*?"(\d+,?\d*)\s*(?:Google\s*)?reviews?"', text)
        review_count_match = re.search(r'(\d[\d,]*)\s*(?:Google\s*)?reviews?', text)
        
        review_count = 0
        if review_count_match:
            review_count = int(review_count_match.group(1).replace(',', ''))
        
        # Ek synthetic entry banao count track karne ke liye
        return [{
            "id": f"count_{review_count}",
            "count": review_count,
            "author": "SYSTEM",
            "rating": 0,
            "text": f"Total reviews: {review_count}",
            "date": datetime.now().isoformat()
        }]
        
    except Exception as e:
        print(f"❌ Scraping error for {hotel_name}: {e}")
        return []

def check_new_reviews():
    """Har hotel ke liye naye reviews check karo"""
    print(f"\n🔍 Checking reviews at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    store = load_store()
    found_new = False
    
    for hotel in COMPETITORS:
        hotel_name = hotel["name"]
        print(f"\n📍 Checking: {hotel_name}")
        
        reviews = scrape_reviews_basic(hotel_name)
        
        if not reviews:
            print(f"   ⚠️ No data found")
            continue
        
        # Review count track karo
        current_data = reviews[0] if reviews else None
        
        if current_data:
            current_count = current_data.get("count", 0)
            old_count = store.get(hotel_name, {}).get("count", 0)
            
            print(f"   📊 Reviews: {old_count} → {current_count}")
            
            if hotel_name not in store:
                # Pehli baar check kar raha hai
                store[hotel_name] = {
                    "count": current_count,
                    "last_checked": datetime.now().isoformat()
                }
                print(f"   ✅ First time tracking: {current_count} reviews")
                
            elif current_count > old_count:
                # Naya review aaya!
                new_count = current_count - old_count
                found_new = True
                
                print(f"   🆕 NEW REVIEW DETECTED! (+{new_count})")
                
                # Notification bhejo
                title = f"🏨 New Review Alert!"
                message = (
                    f"Hotel: {hotel_name}\n"
                    f"Naye Reviews: +{new_count}\n"
                    f"Total Reviews: {current_count}\n"
                    f"Time: {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
                    f"Turant check karo Google Maps pe!"
                )
                
                send_notification(title, message, priority="high")
                
                # Store update karo
                store[hotel_name]["count"] = current_count
                store[hotel_name]["last_checked"] = datetime.now().isoformat()
                store[hotel_name]["last_new_review"] = datetime.now().isoformat()
                
            else:
                store[hotel_name]["last_checked"] = datetime.now().isoformat()
                print(f"   ✅ No new reviews")
    
    save_store(store)
    
    if not found_new:
        print("\n✅ Koi naya review nahi aaya abhi tak")
    
    return found_new

def run_monitor():
    """Main monitoring loop - har 1 ghante mein check karo"""
    print("🚀 Hotel Review Monitor Shuru Ho Gaya!")
    print(f"📱 Notifications jayenge: ntfy.sh/{NTFY_TOPIC}")
    print(f"⏰ Check interval: Har 1 ghante mein")
    print(f"🏨 Monitoring {len(COMPETITORS)} hotels")
    print("=" * 50)
    
    # Startup notification
    send_notification(
        "✅ Monitor Started!",
        f"Aapka Hotel Review Monitor shuru ho gaya!\n{len(COMPETITORS)} competitors monitor ho rahe hain.\nHar ghante notification milegi agar naya review aaya.",
        priority="low"
    )
    
    while True:
        try:
            check_new_reviews()
            
            print(f"\n⏳ Next check in 1 hour...")
            print(f"   (Press Ctrl+C to stop)")
            
            # 1 ghante wait karo (3600 seconds)
            time.sleep(3600)
            
        except KeyboardInterrupt:
            print("\n\n🛑 Monitor band kar diya. Bye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("⏳ 5 minute mein retry karunga...")
            time.sleep(300)

if __name__ == "__main__":
    run_monitor()
