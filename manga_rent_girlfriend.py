import cloudscraper
from bs4 import BeautifulSoup
import requests
import os
import time

# === CONFIGURATION ===
BASE_URL = "https://read.kanojookarishimasu.online"
MANGA_PAGE = f"{BASE_URL}/manga/rent-a-girlfriend/"
LATEST_CHAPTER_FILE = "latest_chapter.txt"

# Telegram Bot Config
BOT_TOKEN = "7514823299:AAFqcOxPaQhMUw1A7vs0IE2w-1SvQHEjuzo"
CHAT_ID_FILE = "chat_ids.txt"

# Initialize CloudScraper
scraper = cloudscraper.create_scraper()

# === FUNCTIONS ===

def get_latest_chapter():
    """Fetches the latest chapter URL from the manga site."""
    response = scraper.get(MANGA_PAGE)
    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    latest_chapter = soup.select_one(".wp-manga-chapter > a")
    if latest_chapter:
        return latest_chapter["href"]
    return None

def get_image_urls(chapter_url):
    """Extracts all manga page image URLs from the chapter page."""
    response = scraper.get(chapter_url)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    images = soup.select("div.reading-content img")
    return [img["src"] for img in images if img.get("src")]

def send_telegram_message(chat_id, text):
    """Sends a text message via Telegram Bot."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print(f"Failed to send message to {chat_id}: {response.text}")

def send_telegram_photo(chat_id, image_path):
    """Sends a locally downloaded image to Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(image_path, "rb") as img:
        response = requests.post(url, data={"chat_id": chat_id}, files={"photo": img})
    if response.status_code != 200:
        print(f"Failed to send photo to {chat_id}: {response.text}")

def get_registered_users():
    """Reads stored user chat IDs from a file."""
    if not os.path.exists(CHAT_ID_FILE):
        return []
    
    with open(CHAT_ID_FILE, "r") as f:
        return [line.strip() for line in f.readlines()]

def handle_new_chapter():
    """Checks for new chapters and sends updates to users."""
    latest_chapter_url = get_latest_chapter()
    users = get_registered_users()

    if not latest_chapter_url:
        for user in users:
            send_telegram_message(user, "⚠️ Failed to fetch the latest chapter.")
        return

    chapter_number = latest_chapter_url.split("-")[-1]

    if os.path.exists(LATEST_CHAPTER_FILE):
        with open(LATEST_CHAPTER_FILE, "r") as f:
            saved_chapter = f.read().strip()
    else:
        saved_chapter = ""

    if chapter_number != saved_chapter:
        if users:
            image_urls = get_image_urls(latest_chapter_url)

            for user in users:
                send_telegram_message(user, f"📖 New Manga Chapter Released!\n🔗 {latest_chapter_url}")

                for index, img_url in enumerate(image_urls, start=1):
                    # Download image to temp file
                    response = scraper.get(img_url)
                    if response.status_code == 200:
                        temp_image_path = f"temp_img_{user}_{index}.jpg"
                        with open(temp_image_path, "wb") as f:
                            f.write(response.content)
                        
                        # Send image file
                        send_telegram_photo(user, temp_image_path)

                        # Delete temp image after sending
                        os.remove(temp_image_path)
                        time.sleep(1)  # Avoid hitting Telegram rate limits
                    else:
                        print(f"Failed to download image: {img_url}")
        with open(LATEST_CHAPTER_FILE, "w") as f:
            f.write(chapter_number)
    else:
        for user in users:
            send_telegram_message(user, "✅ No new chapter available right now.")

# === RUN AUTOMATIC CHECK ===
if __name__ == "__main__":
    print("Bot is running...")
    handle_new_chapter()
