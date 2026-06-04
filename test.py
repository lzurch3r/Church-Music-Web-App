import re
import requests
from bs4 import BeautifulSoup

def scrape_come_thou_fount():
    base_url = "https://www.churchofjesuschrist.org"
    collection_url = f"{base_url}/media/music/collections/hymns-for-home-and-church?lang=eng"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }

    print("=================================================================")
    print("STEP 1: FETCHING COLLECTION INDEX AND SEARCHING FOR ROUTE PATH")
    print("=================================================================")
    
    response = requests.get(collection_url, headers=headers, timeout=15)
    if response.status_code != 200:
        print(f"Failed to access collection page. Status code: {response.status_code}")
        return

    # Use regular expressions to scan the server payload for the precise path trace match
    # This checks the text before BeautifulSoup handles unrendered JavaScript elements
    target_pattern = r'\"(/media/music/songs/come-thou-fount-of-every-blessing\?[^\"]*crumbs=hymns-for-home-and-church[^\"]*)\"'
    match = re.search(target_pattern, response.text)

    if not match:
        print("Could not isolate the target song path containing the 'crumbs' query parameter.")
        return

    # Clean HTML entity encodings if present (e.g., &amp; -> &)
    song_relative_path = match.group(1).replace('&amp;', '&')
    song_profile_url = f"{base_url}{song_relative_path}"
    print(f"🎯 SUCCESS! Isolated Song Page URL:\n   {song_profile_url}\n")

    print("=================================================================")
    print("STEP 2: FETCHING INDIVIDUAL SONG PAGE AND ISOLATING .MP3 CDN LINK")
    print("=================================================================")
    
    song_response = requests.get(song_profile_url, headers=headers, timeout=15)
    if song_response.status_code != 200:
        print(f"Failed to access song profile page. Status code: {song_response.status_code}")
        return

    # Scan the song profile page text data for the specific assets CDN media endpoint link
    mp3_pattern = r'https://assets\.churchofjesuschrist\.org/[^\s"\']+\.mp3'
    mp3_match = re.search(mp3_pattern, song_response.text)

    if not mp3_match:
        print("Could not find the direct assets.churchofjesuschrist.org .mp3 file target in the page code.")
        return

    mp3_cdn_url = mp3_match.group(0)
    print(f"🎉 SUCCESS! Found Streaming Asset URL:\n   {mp3_cdn_url}\n")

    print("=================================================================")
    print("STEP 3: COMPILING EXPORT FILE")
    print("=================================================================")
    
    output_filename = "come_thou_fount_link.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"{mp3_cdn_url}\n")
        
    print(f"Saved link directly to: '{output_filename}'")

if __name__ == "__main__":
    scrape_come_thou_fount()