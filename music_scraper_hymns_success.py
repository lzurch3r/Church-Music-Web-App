import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class ChurchMusicPlaywrightScraper:
    def __init__(self):
        self.base_url = "https://www.churchofjesuschrist.org"
        self.collection_url = f"{self.base_url}/media/music/collections/hymns-for-home-and-church?lang=eng"

    def execute_pipeline(self, output_filename="hymns_mp3_manifest.txt"):
        print("=================================================================")
        # Playwright launches an automated headless browser instance 
        # to handle the client-side JavaScript execution layer natively
        print("  LAUNCHING PLAYWRIGHT AUTOMATION ENGINE (TIER 1 & TIER 2)      ")
        print("=================================================================")
        
        with sync_playwright() as p:
            # Boot Chromium headless (set headless=False if you want to watch it work visually!)
            browser = p.chromium.launch(headless=True)
            
            # Mimic a real consumer desktop browser configuration
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()

            print(f"[Tier 1] Navigating to Master Directory Hub:\n   {self.collection_url}")
            page.goto(self.collection_url, wait_until="networkidle")
            
            # Critical step: Tell Playwright to explicitly wait until the modern 
            # unordered list UI wrappers are generated and populated inside the DOM
            print("[Tier 1] Waiting for interactive list elements to hydrate...")
            page.wait_for_selector("a[href*='crumbs=hymns-for-home-and-church']", timeout=15000)
            
            # Grab the fully evaluated page HTML source code
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            song_pages = []
            all_anchors = soup.find_all('a', href=True)
            
            for anchor in all_anchors:
                href = anchor['href']
                # Lock onto your explicit link constraint
                if "/media/music/songs/" in href and "crumbs=hymns-for-home-and-church" in href:
                    full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                    if full_url not in song_pages:
                        song_pages.append(full_url)

            print(f"\n[Tier 1 Success] Found exactly {len(song_pages)} matching song profile routes.")
            
            if len(song_pages) == 0:
                print("[Aborting] No links resolved. The page structure might have mutated.")
                browser.close()
                return

            compiled_mp3_links = []

            print("\n=================================================================")
            print("  TIER 2: SEQUENTIAL PROFILE DEEP SCANNING")
            print("=================================================================")
            
            # Loop through all 72 discovered paths
            for idx, song_url in enumerate(song_pages, 1):
                # Isolate the trailing text slug for clean progress reporting
                title_slug = song_url.split('/')[-1].split('?')[0].replace('-', ' ').title()
                print(f"[{idx}/{len(song_pages)}] Scanning profile layout: {title_slug}")
                
                try:
                    # Navigate the same active browser context to the individual song screen
                    page.goto(song_url, wait_until="load")
                    
                    # Wait for either an audio layout component or a brief period for script setup
                    page.wait_for_timeout(1000) 
                    
                    song_html = page.content()
                    
                    # Search for the explicit asset bucket CDN path mapping to the .mp3 stream
                    import re
                    mp3_match = re.search(r'https://assets\.churchofjesuschrist\.org/[^\s"\']+\.mp3', song_html)
                    
                    if mp3_match:
                        mp3_cdn_url = mp3_match.group(0)
                        print(f"   🎉 Isolated CDN Audio Target: {mp3_cdn_url}")
                        compiled_mp3_links.append(mp3_cdn_url)
                    else:
                        print(f"   ⚠️ Warning: Audio element script tag hidden on page text node.")
                        
                except Exception as inner_e:
                    print(f"   ❌ Error crawling profile node: {inner_e}")
                
                # Polite short throttle delay to balance speed against server pressure
                time.sleep(0.1)

            # Close browser cleanly
            browser.close()

        # Compile data to a pristine text manifest
        print(f"\n=================================================================")
        print(f"[Writing File] Outputting data lines to: {output_filename}")
        print("=================================================================")
        with open(output_filename, "w", encoding="utf-8") as f:
            for link in compiled_mp3_links:
                f.write(f"{link}\n")
                
        print(f"Success! '{output_filename}' generated with {len(compiled_mp3_links)} verified lines.")

if __name__ == "__main__":
    scraper = ChurchMusicPlaywrightScraper()
    scraper.execute_pipeline()