"""
ChurchMusicUniversalScraper — Full-catalog Playwright harvester
===============================================================
Crawls every public music collection on churchofjesuschrist.org,
auto-discovers subcategories, and extracts direct .mp3 CDN links.

ROOT CAUSE FIX (v2)
--------------------
The site is a Next.js / React SPA.  `page.content()` called at
`domcontentloaded` returns ~172 bytes of shell HTML with zero links.
We must wait for the JS to hydrate the DOM before reading content.

The fix is a three-stage wait strategy:
  1. goto(..., wait_until="networkidle")  — waits for XHR/fetch to settle
  2. wait_for_selector on a known rendered element (media tile or link)
  3. Read __NEXT_DATA__ JSON from the DOM (pre-populated by SSR/ISR)
     which contains the full item list even before React re-renders it.

Other improvements over v1
---------------------------
* __NEXT_DATA__ JSON mining: extracts song slugs AND mp3 URLs directly
  from the server-rendered payload, making HTML parsing a fallback
* Correct selector wait: waits for actual rendered anchor tags
* Network response interception for audio XHR as additional fallback
* Recursive subcollection walk with cycle protection
* Per-song retry with exponential back-off
* Global URL deduplication
* Pipe-escaped Markdown output
"""

import re
import json
import time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://www.churchofjesuschrist.org"

# All known top-level collection slugs.
# Auto-discovery supplements these at runtime.
TOP_LEVEL_SLUGS = [
    "hymns-for-home-and-church",
    "hymns",
    "childrens-songbook",
    "youth-and-contemporary",
    "music-for-everyday-listening",
    "music-from-general-conference",
    "tabernacle-choir-playlists",
    "featured-simplified-hymns-and-songs",
    "featured-music-for-children",
    "music-for-choir-and-voice",
    "music-for-instruments",
    "submitted-hymns",
    "music-from-church-events",
    "music-from-church-productions",
    "music-from-church-magazines",
    "christmas",
    "easter",
    "archived-content",
]

POLITE_DELAY   = 0.15   # seconds between song-page requests
MAX_RETRIES    = 3      # attempts per song page before giving up
NAV_TIMEOUT       = 45_000 # ms — generous for slow CDN pages
SONG_NAV_TIMEOUT  = 20_000 # ms — song pages: use 'load', not 'networkidle'
HYDRATE_WAIT      = 6_000  # ms — wait for React hydration after networkidle
SONG_SETTLE_WAIT  = 1_500  # ms — fixed settle time after song page 'load'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def collection_url(slug: str) -> str:
    return f"{BASE_URL}/media/music/collections/{slug}?lang=eng"

def song_url(slug: str, crumb: str) -> str:
    return f"{BASE_URL}/media/music/songs/{slug}?crumbs={crumb}&lang=eng"

def normalize_url(href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return href

def slug_to_title(slug: str) -> str:
    return slug.replace("-", " ").title()

def extract_mp3_urls(text: str) -> list:
    """Return all distinct .mp3 URLs from any text blob (HTML or JSON)."""
    raw = re.findall(r'https://[^\s"\'<>\\]+\.mp3', text)
    seen, out = set(), []
    for u in raw:
        u = u.rstrip(".,;)")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def extract_next_data(html: str) -> dict:
    """Parse the __NEXT_DATA__ JSON blob embedded by Next.js SSR."""
    m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}

def collect_from_next_data(data: dict) -> tuple:
    """
    Walk any Next.js page payload and collect:
      - song_slugs: list of song slug strings found under any key
      - mp3_urls:   list of direct .mp3 URLs found under any key
    Returns (song_slugs, mp3_urls).
    """
    raw = json.dumps(data)

    # Song page URIs embedded in the payload
    song_slugs = re.findall(r'"/media/music/songs/([^"?]+)', raw)

    # Direct mp3 URLs
    mp3_urls = extract_mp3_urls(raw)

    # Also try common key names for stream/audio URIs
    stream_uris = re.findall(r'"(?:streamUri|mediaUrl|audioUrl|mp3Url|src)"\s*:\s*"(https://[^"]+\.mp3)"', raw)
    for u in stream_uris:
        if u not in mp3_urls:
            mp3_urls.append(u)

    return list(dict.fromkeys(song_slugs)), list(dict.fromkeys(mp3_urls))

def wait_for_hydration(page, timeout: int = HYDRATE_WAIT):
    """
    Wait until React has rendered at least one music-related anchor.
    Falls back to a timed wait so we never hang indefinitely.
    """
    selectors = [
        "a[href*='/media/music/songs/']",
        "a[href*='/media/music/collections/']",
        "[class*='MediaTile']",
        "[class*='media-tile']",
        "[data-testid*='media']",
        "main a[href]",
    ]
    for sel in selectors:
        try:
            page.wait_for_selector(sel, timeout=timeout)
            return
        except PWTimeout:
            continue
    # Nothing matched — just let the timed wait elapse
    page.wait_for_timeout(timeout)


# ---------------------------------------------------------------------------
# Core scraper
# ---------------------------------------------------------------------------

class ChurchMusicUniversalScraper:

    def __init__(self, polite_delay: float = POLITE_DELAY):
        self.polite_delay = polite_delay
        self._seen_song_slugs: set  = set()
        self._seen_mp3_urls:   set  = set()
        self._seen_coll_slugs: set  = set()
        self._intercepted_mp3s: list = []

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def scrape_catalog(self, output_filename: str = "Sacred_Music_Complete_Archive.md"):
        print("=" * 65)
        print("  LAUNCHING FULL-CATALOG PLAYWRIGHT HARVESTER PIPELINE")
        print("=" * 65)

        # { top_title: { sub_title: [track, …] } }
        master_catalog: dict = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
            )
            page = context.new_page()

            # Intercept audio responses from the network (catches XHR-loaded mp3s)
            def _on_response(response):
                url = response.url
                if ".mp3" in url and url not in self._intercepted_mp3s:
                    self._intercepted_mp3s.append(url)
            page.on("response", _on_response)

            for slug in TOP_LEVEL_SLUGS:
                top_title = slug_to_title(slug)
                url       = collection_url(slug)

                print(f"\n{'='*65}")
                print(f"  TOP-LEVEL: {top_title}")
                print(f"  {url}")
                print(f"{'='*65}")

                if slug in self._seen_coll_slugs:
                    print("  (already processed — skipping)")
                    continue
                self._seen_coll_slugs.add(slug)

                top_data = self._process_collection(page, slug, top_title, url, depth=0)
                if top_data:
                    master_catalog[top_title] = top_data

            browser.close()

        self._export_markdown(master_catalog, output_filename)

    # ------------------------------------------------------------------
    # Recursive collection processor
    # ------------------------------------------------------------------

    def _process_collection(
        self, page, slug: str, title: str, url: str, depth: int
    ) -> dict:
        """
        Load a collection page. Returns { sub_title: [tracks] }.
        At depth 0 this is the top-level map; sub-collections recurse to depth 1+.
        """
        indent = "  " * (depth + 1)

        # ---- Load page with proper hydration wait ----
        try:
            self._navigate(page, url)
        except Exception as e:
            print(f"{indent}❌ Failed to load {url}: {e}")
            return {}

        html = page.content()
        next_data = extract_next_data(html)
        song_slugs_nd, mp3_urls_nd = collect_from_next_data(next_data)

        # ---- Find sub-collection links in the rendered DOM ----
        sub_slugs = self._find_subcollection_slugs(page, html, slug)

        # ---- Find direct song links ----
        song_slugs_html = self._find_song_slugs(page, html, slug)

        # Merge sources; prefer Next.js data (most complete) then DOM scan
        all_song_slugs = list(dict.fromkeys(song_slugs_nd + song_slugs_html))
        # Also handle "load more" before final HTML scrape
        self._exhaust_load_more(page)
        html2 = page.content()
        song_slugs_html2 = self._find_song_slugs(page, html2, slug)
        all_song_slugs = list(dict.fromkeys(all_song_slugs + song_slugs_html2))

        result = {}

        # ---- Recurse into sub-collections ----
        if sub_slugs:
            print(f"{indent}📂 {len(sub_slugs)} sub-collection(s) discovered under '{title}'")
            for sub_slug in sub_slugs:
                if sub_slug in self._seen_coll_slugs:
                    continue
                self._seen_coll_slugs.add(sub_slug)
                sub_title = slug_to_title(sub_slug)
                sub_url   = collection_url(sub_slug)
                print(f"{indent}  ↳ {sub_title}")
                sub_data = self._process_collection(page, sub_slug, sub_title, sub_url, depth + 1)
                result.update(sub_data)

        # ---- Scrape songs at this level ----
        if all_song_slugs:
            print(f"{indent}🎵 {len(all_song_slugs)} song(s) at '{title}' level")
            tracks = self._scrape_songs(page, all_song_slugs, slug, mp3_urls_nd, indent)
            if tracks:
                result[title] = tracks

        if not result:
            print(f"{indent}⚠  Nothing recoverable at '{title}'")

        return result

    # ------------------------------------------------------------------
    # Song slug discovery from page
    # ------------------------------------------------------------------

    def _find_song_slugs(self, page, html: str, parent_slug: str) -> list:
        """Extract song slugs from rendered HTML anchors."""
        slugs = []
        seen  = set()

        # From href attributes
        for m in re.finditer(r'href="(/media/music/songs/([^"?#]+))', html):
            s = m.group(2)
            if s not in seen:
                seen.add(s)
                slugs.append(s)

        # From data-* attributes or JSON islands
        for m in re.finditer(r'"contentUri"\s*:\s*"/media/music/songs/([^"?]+)"', html):
            s = m.group(1)
            if s not in seen:
                seen.add(s)
                slugs.append(s)

        return slugs

    # ------------------------------------------------------------------
    # Sub-collection slug discovery
    # ------------------------------------------------------------------

    def _find_subcollection_slugs(self, page, html: str, parent_slug: str) -> list:
        """Find child collection slugs linked from this page."""
        slugs = []
        seen  = set()

        for m in re.finditer(
            r'href="(?:https://www\.churchofjesuschrist\.org)?/media/music/collections/([^"?#/]+)',
            html
        ):
            s = m.group(1)
            if s != parent_slug and s not in seen and s not in self._seen_coll_slugs:
                seen.add(s)
                slugs.append(s)

        return slugs

    # ------------------------------------------------------------------
    # Song batch scraper
    # ------------------------------------------------------------------

    def _scrape_songs(
        self, page, song_slugs: list, crumb_slug: str,
        prefetched_mp3s: list, indent: str
    ) -> list:
        """Visit each song page and extract the mp3 URL."""
        tracks = []

        for idx, slug in enumerate(song_slugs, 1):
            if slug in self._seen_song_slugs:
                continue
            self._seen_song_slugs.add(slug)

            url = song_url(slug, crumb_slug)
            fallback_title = slug_to_title(slug)
            print(f"{indent}  [{idx}/{len(song_slugs)}] {fallback_title}", end="", flush=True)

            track = self._extract_track(page, url, fallback_title)
            if track:
                print(f"  ✓")
                tracks.append(track)
            else:
                print(f"  ✗ (no mp3)")

            time.sleep(self.polite_delay)

        return tracks

    # ------------------------------------------------------------------
    # Single song page → track dict
    # ------------------------------------------------------------------

    def _extract_track(self, page, url: str, fallback_title: str) -> dict | None:
        """
        Navigate to a song page and extract { title, mp3_url, song_page_url }.
        Three-pass extraction:
          1. __NEXT_DATA__ JSON (most reliable — SSR populated)
          2. Raw HTML regex scan
          3. JS DOM evaluation (audio elements, script tags)
          4. Network-intercepted responses
        """
        self._intercepted_mp3s.clear()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._navigate(page, url, is_song=True)

                html = page.content()

                # Pass 1: __NEXT_DATA__
                nd = extract_next_data(html)
                _, mp3s = collect_from_next_data(nd)

                # Pass 2: raw HTML
                if not mp3s:
                    mp3s = extract_mp3_urls(html)

                # Pass 3: live DOM
                if not mp3s:
                    mp3s = self._dom_mp3_scan(page)

                # Pass 4: network interception
                if not mp3s and self._intercepted_mp3s:
                    mp3s = list(self._intercepted_mp3s)

                if mp3s:
                    preferred = [u for u in mp3s if "assets.churchofjesuschrist" in u]
                    mp3_url = (preferred or mp3s)[0]
                    self._seen_mp3_urls.add(mp3_url)
                    title = self._page_title(page) or fallback_title
                    return {"title": title, "mp3_url": mp3_url, "song_page_url": url}

                if attempt < MAX_RETRIES:
                    page.wait_for_timeout(1000 * attempt)

            except PWTimeout:
                if attempt < MAX_RETRIES:
                    print(f" [timeout, retry {attempt}]", end="", flush=True)
                    time.sleep(1.5 * attempt)
                else:
                    print(f" [timeout, giving up]", end="", flush=True)
            except Exception as e:
                if attempt < MAX_RETRIES:
                    print(f" [err retry {attempt}]", end="", flush=True)
                    time.sleep(1.0 * attempt)
                else:
                    print(f" [err: {str(e)[:40]}]", end="", flush=True)

        return None

    # ------------------------------------------------------------------
    # JS DOM scan for audio elements
    # ------------------------------------------------------------------

    def _dom_mp3_scan(self, page) -> list:
        try:
            results = page.evaluate("""() => {
                const urls = new Set();
                // Audio/source/video elements
                document.querySelectorAll('audio, source, video').forEach(el => {
                    if (el.src  && el.src.includes('.mp3'))  urls.add(el.src);
                    if (el.currentSrc && el.currentSrc.includes('.mp3')) urls.add(el.currentSrc);
                });
                document.querySelectorAll('audio source').forEach(el => {
                    if (el.src) urls.add(el.src);
                });
                // __NEXT_DATA__ script
                const nd = document.getElementById('__NEXT_DATA__');
                if (nd) {
                    const m = nd.textContent.match(/https:\\/\\/[^"'\\s]+\\.mp3/g);
                    if (m) m.forEach(u => urls.add(u));
                }
                // All other inline scripts
                document.querySelectorAll('script:not([src])').forEach(s => {
                    const m = s.textContent.match(/https:\\/\\/[^"'\\s]+\\.mp3/g);
                    if (m) m.forEach(u => urls.add(u));
                });
                return [...urls];
            }""")
            return results or []
        except Exception:
            return []

    # ------------------------------------------------------------------
    # "Load more" exhaustion
    # ------------------------------------------------------------------

    def _exhaust_load_more(self, page, max_clicks: int = 40):
        selectors = [
            "button:has-text('Show More')",
            "button:has-text('Load More')",
            "button:has-text('See More')",
            "[data-testid='load-more']",
            "a[aria-label='Next page']",
            "a[rel='next']",
        ]
        for _ in range(max_clicks):
            clicked = False
            for sel in selectors:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(1500)
                        clicked = True
                        break
                except Exception:
                    pass
            if not clicked:
                break

    # ------------------------------------------------------------------
    # Navigation with proper hydration wait
    # ------------------------------------------------------------------

    def _navigate(self, page, url: str, is_song: bool = False):
        """
        Navigate and wait appropriately based on page type.

        Collection pages  -> networkidle + hydration selector wait.
          networkidle is essential here: the song/subcollection links are
          injected by client-side JS after several XHR calls finish.

        Song pages        -> load + fixed settle wait.
          Song pages embed an audio player that fires continuous keep-alive
          XHR/WebSocket requests, so networkidle NEVER fires on them.
          'load' fires once the initial document and its static resources
          are done; the __NEXT_DATA__ JSON (which carries the mp3 URL) is
          present in the SSR HTML before any JS runs, so a short fixed
          wait is all we need after that.
        """
        if is_song:
            for attempt in range(1, 3):
                try:
                    page.goto(url, wait_until="load", timeout=SONG_NAV_TIMEOUT)
                    page.wait_for_timeout(SONG_SETTLE_WAIT)
                    return
                except PWTimeout:
                    if attempt == 1:
                        time.sleep(2)
                    else:
                        raise
        else:
            for attempt in range(1, 3):
                try:
                    page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT)
                    wait_for_hydration(page, timeout=HYDRATE_WAIT)
                    return
                except PWTimeout:
                    if attempt == 1:
                        page.wait_for_timeout(3000)
                    else:
                        raise

    # ------------------------------------------------------------------
    # Title extraction
    # ------------------------------------------------------------------

    def _page_title(self, page) -> str:
        try:
            h1 = page.query_selector("h1")
            if h1:
                t = h1.inner_text().strip()
                if t:
                    return t
        except Exception:
            pass
        try:
            t = page.title()
            return re.split(r"\s*[|\-–—]\s*", t)[0].strip()
        except Exception:
            pass
        return ""

    # ------------------------------------------------------------------
    # Markdown export
    # ------------------------------------------------------------------

    def _export_markdown(self, catalog: dict, filename: str):
        print("\n" + "=" * 65)
        print(f"  GENERATING MASTER MARKDOWN INDEX → {filename}")
        print("=" * 65)

        total = sum(
            len(tracks)
            for sub_map in catalog.values()
            for tracks in sub_map.values()
        )

        with open(filename, "w", encoding="utf-8") as f:
            f.write("# Consolidated Sacred Music Media Archive\n\n")
            f.write(f"> **Total tracks indexed: {total}**\n\n")
            f.write("---\n\n")

            for top_title, sub_map in catalog.items():
                top_total = sum(len(t) for t in sub_map.values())
                f.write(f"## 📚 {top_title}  *({top_total} tracks)*\n\n")

                for sub_title, tracks in sub_map.items():
                    f.write(f"### 🎵 {sub_title}\n\n")
                    f.write(f"*{len(tracks)} audio file(s)*\n\n")

                    if not tracks:
                        f.write("*No audio links recovered.*\n\n")
                        continue

                    f.write("| # | Title | MP3 |\n")
                    f.write("|---|-------|-----|\n")
                    for i, track in enumerate(tracks, 1):
                        t = track["title"].replace("|", "\\|")
                        f.write(f"| {i} | **{t}** | [▶ Stream]({track['mp3_url']}) |\n")
                    f.write("\n")

        print(f"\n✅ Manifest written to '{filename}'")
        print(f"   {total} tracks across {len(catalog)} top-level collection(s).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    scraper = ChurchMusicUniversalScraper(polite_delay=POLITE_DELAY)
    scraper.scrape_catalog()
