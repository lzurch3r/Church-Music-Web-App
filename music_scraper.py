import os
import re
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class ChurchMusicUniversalScraper:
    def __init__(self):
        self.base_url = "https://www.churchofjesuschrist.org"
        # The core targets we want to harvest music assets from
        self.collections = [
            {
                "title": "Hymns (Hymns for Home and Church)", 
                "url": f"{self.base_url}/media/music/collections/hymns-for-home-and-church?lang=eng",
                "crumb_filter": "crumbs=hymns-for-home-and-church"
            },
            {
                "title": "Hymns of The Church of Jesus Christ of Latter-day Saints", 
                "url": f"{self.base_url}/media/music/collections/hymns?lang=eng",
                "crumb_filter": "crumbs=hymns"
            },
            {
                "title": "Children's Songbook", 
                "url": f"{self.base_url}/media/music/collections/childrens-songbook?lang=eng",
                "crumb_filter": "crumbs=childrens-songbook"
            },
            {
                "title": "Youth and Contemporary Music", 
                "url": f"{self.base_url}/media/music/collections/youth-and-contemporary?lang=eng",
                "crumb_filter": "crumbs=youth-and-contemporary"
            }
        ]

    def scrape_catalog(self, output_filename="Sacred_Music_Complete_Archive.md"):
        print("=================================================================")
        print("  LAUNCHING UNIVERSAL AUTOMATED PLAYWRIGHT HARVESTER PIPELINE    ")
        print("=================================================================")
        
        master_catalog = {}

        with sync_playwright() as p:
            # Initialize a robust background browser instance
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()

            # Process each individual book collection sequentially
            for collection in self.collections:
                print(f"\n🚀 STARTING COLLECTION: {collection['title']}")
                print(f"Targeting URL: {collection['url']}")
                
                try:
                    page.goto(collection['url'], wait_until="networkidle")
                    
                    # Wait for target hydration links to materialize inside the layout tree
                    page.wait_for_selector(f"a[href*='{collection['crumb_filter']}']", timeout=10000)
                    
                    # Pull down fully compiled HTML tree elements
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    
                    song_pages = []
                    for anchor in soup.find_all('a', href=True):
                        href = anchor['href']
                        if "/media/music/songs/" in href and collection['crumb_filter'] in href:
                            full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                            if full_url not in song_pages:
                                song_pages.append(full_url)
                                
                    print(f"-> Tier 1 Complete: Discovered {len(song_pages)} tracks inside this book section.")
                    
                    # Tier 2: Dig down into each tracked item to capture its cloud .mp3 stream
                    collection_tracks = []
                    for idx, song_url in enumerate(song_pages, 1):
                        title_slug = song_url.split('/')[-1].split('?')[0].replace('-', ' ').title()
                        print(f"   [{idx}/{len(song_pages)}] Crawling Media Asset: {title_slug}")
                        
                        try:
                            page.goto(song_url, wait_until="load")
                            page.wait_for_timeout(800) # Fast load stabilization padding
                            
                            song_html = page.content()
                            mp3_match = re.search(r'https://assets\.churchofjesuschrist\.org/[^\s"\']+\.mp3', song_html)
                            
                            if mp3_match:
                                mp3_link = mp3_match.group(0)
                                collection_tracks.append({
                                    "title": title_slug,
                                    "mp3_url": mp3_link
                                })
                            else:
                                print(f"      ⚠️ Warning: No direct .mp3 file stream exposed on profile text nodes.")
                        except Exception as song_err:
                            print(f"      ❌ Error parsing song page: {song_err}")
                            
                        # Keep a polite pacing footprint to keep the host connection happy
                        time.sleep(0.05)
                        
                    # Save completed collection dataset mapping
                    master_catalog[collection['title']] = collection_tracks
                    
                except Exception as col_err:
                    print(f"❌ Failed to systematically process collection {collection['title']}: {col_err}")

            # Close the automated background interface cleanly
            browser.close()

        # Step 3: Compile all parsed data nodes into a clean Markdown table format file
        self.export_to_markdown(master_catalog, output_filename)

    def export_to_markdown(self, catalog, filename):
        print("\n=================================================================")
        print(f"  TIER 3: GENERATING MASTER MARKDOWN INDEX -> {filename}  ")
        print("=================================================================")
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write("# Consolidated Sacred Music Media Archive\n")
            f.write("### Restoring public .mp3 streaming asset entries missing from mobile application migrations.\n")
            f.write("----\n\n")
            
            for collection_title, tracks in catalog.items():
                f.write(f"## 📚 Collection: {collection_title}\n")
                f.write(f"Total Audio Files Indexed: `{len(tracks)}` \n\n")
                
                if not tracks:
                    f.write("*No valid binary audio links recovered for this directory cluster.*\n\n")
                    continue
                
                # Construct clean Markdown reading tables
                f.write("| # | Song Name | Direct CDN Audio Stream Link |\n")
                f.write("|---|-----------|------------------------------|\n")
                
                for index, track in enumerate(tracks, 1):
                    f.write(f"| {index} | **{track['title']}** | [Stream/Download Audio Asset]({track['mp3_url']}) |\n")
                    
                f.write("\n\n")
                
        print(f"\n[Operation Success] Your complete library manifest has been written to '{filename}'.")

if __name__ == "__main__":
    scraper = ChurchMusicUniversalScraper()
    scraper.scrape_catalog()