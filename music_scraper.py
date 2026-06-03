import os
import re
import json
import requests
from bs4 import BeautifulSoup

class ChurchMusicScraper:
    def __init__(self):
        self.base_url = "https://www.churchofjesuschrist.org"
        self.root_music_url = f"{self.base_url}/media/music?lang=eng"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }

    def fetch_page_soup(self, url):
        """Safely fetches a web page and returns a BeautifulSoup object."""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'html.parser')
            else:
                print(f"[Error] Received status code {response.status_code} for URL: {url}")
                return None
        except Exception as e:
            print(f"[Exception] Failed to connect to {url}: {e}")
            return None

    def discover_music_categories(self):
        """Scrapes the main music library dashboard to find sub-collections."""
        print("Discovering music collections from main library directory...")
        soup = self.fetch_page_soup(self.root_music_url)
        if not soup:
            return []

        collections = []
        # Look for anchor tags pointing to distinct music collections/books
        # The Church site typically clusters these in grid cards or navigation menus
        for link in soup.find_all('a', href=re.compile(r'/media/music/collections/|/music/library/')):
            href = link.get('href')
            title = link.get_text(strip=True)
            
            # Form full URL path
            full_url = href if href.startswith('http') else f"{self.base_url}{href}"
            
            if full_url not in [c['url'] for c in collections] and title:
                collections.append({
                    "title": title,
                    "url": full_url
                })
        
        # Fallback defaults if the main landing page elements are heavily nested in Javascript
        if not collections:
            print("[Info] Dynamic UI detected. Applying baseline collection directories...")
            collections = [
                {"title": "Hymns", "url": f"{self.base_url}/media/music/collections/hymns?lang=eng"},
                {"title": "Children's Songbook", "url": f"{self.base_url}/media/music/collections/childrens-songbook?lang=eng"},
                {"title": "Youth Music", "url": f"{self.base_url}/media/music/collections/youth-music?lang=eng"}
            ]
        
        return collections

    def scrape_songs_from_collection(self, collection_url):
        """Extracts individual tracks, sheet music, and audio media from a collection page."""
        soup = self.fetch_page_soup(collection_url)
        if not soup:
            return []

        songs_list = []
        
        # Locate item blocks representing individual songs
        # Church media layouts generally utilize 'tile', 'item', or lists of anchor text links
        song_elements = soup.find_all(['div', 'a', 'li'], class_=re.compile(r'(music-item|song|media-tile|card)'))
        
        # Fallback to general anchors if layout wrappers are highly abstracted
        if not song_elements:
            song_elements = soup.find_all('a', href=re.compile(r'/media/music/songs/|/music/library/'))

        for element in song_elements:
            title = ""
            song_url = ""
            
            if element.name == 'a':
                title = element.get_text(strip=True)
                song_url = element.get('href')
            else:
                link_tag = element.find('a')
                if link_tag:
                    title = link_tag.get_text(strip=True)
                    song_url = link_tag.get('href')

            if not title or not song_url:
                continue

            full_song_url = song_url if song_url.startswith('http') else f"{self.base_url}{song_url}"
            
            # Deduplicate entries
            if full_song_url in [s['source_url'] for s in songs_list]:
                continue

            # Default structural record for the song
            song_data = {
                "title": title,
                "source_url": full_song_url,
                "audio_link": "Link on Page", # Default behavior
                "sheet_music_link": "View on Site"
            }
            
            songs_list.append(song_data)
            
        return songs_list

    def export_to_markdown(self, catalog, filename="Sacred_Music_Backup_Index.md"):
        """Compiles the scraped Python dictionaries into a beautiful, human-readable Markdown file."""
        print(f"Generating human-readable Markdown index: {filename}...")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Archived Sacred Music Library Index\n")
            f.write("### Generated to complement features missing from the consolidated Gospel Library app.\n")
            f.write("----\n\n")
            
            for category, songs in catalog.items():
                f.write(f"## 📚 Collection: {category}\n")
                f.write(f"Total Songs Found: `{len(songs)}` \n\n")
                
                if not songs:
                    f.write("*No public listings directly accessible in this directory subtree.*\n\n")
                    continue
                
                # Render a Markdown Table for maximum scannability
                f.write("| # | Song Title | Public Source URL | Media Access |\n")
                f.write("|---|------------|-------------------|--------------|\n")
                
                for idx, song in enumerate(songs, 1):
                    # Clean title string of weird linebreaks
                    clean_title = song['title'].replace('\n', ' ').strip()
                    f.write(f"| {idx} | **{clean_title}** | [Open Webpage]({song['source_url']}) | [Audio/Sheet Music]({song['source_url']}) |\n")
                
                f.write("\n\n")
                
        print("Export Complete! Ready for GitHub.")

    def run(self):
        catalog = {}
        collections = self.discover_music_categories()
        
        for col in collections:
            print(f"Scraping collection: {col['title']}...")
            songs = self.scrape_songs_from_collection(col['url'])
            catalog[col['title']] = songs
            print(f"-> Successfully indexed {len(songs)} tracks.")
            
        self.export_to_markdown(catalog)

if __name__ == "__main__":
    scraper = ChurchMusicScraper()
    scraper.run()