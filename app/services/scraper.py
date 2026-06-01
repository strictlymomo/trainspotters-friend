import logging
import re
import asyncio
from typing import List, Dict, Optional, Callable
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class AsyncMixesDBScraper:
    """Async scraper for extracting tracklists from MixesDB artist pages"""

    def __init__(self, progress_callback: Optional[Callable] = None):
        self.base_url = "https://www.mixesdb.com"
        self.progress_callback = progress_callback
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    async def _send_progress(self, message_type: str, data: dict):
        """Send progress update via callback if provided"""
        if self.progress_callback:
            await self.progress_callback(message_type, data)

    def get_artist_page_url(self, artist_name: str) -> str:
        """Convert artist name to MixesDB category URL"""
        formatted_name = artist_name.replace(' ', '_')
        return f"{self.base_url}/w/Category:{formatted_name}"

    async def get_mix_urls_from_artist_page(self, artist_url: str) -> List[Dict[str, str]]:
        """Extract all mix URLs and titles from an artist's category page"""
        logger.info(f"Fetching artist page: {artist_url}")

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
                response = await client.get(artist_url)
                response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the catMixesList element
            mixes_list = soup.find('ul', id='catMixesList')

            if not mixes_list:
                logger.error("Could not find catMixesList element on page")
                return []

            # Extract all mix links from the list
            mix_links = []
            all_lis = mixes_list.find_all('li')
            logger.info(f"Found {len(all_lis)} list items in mixes list")

            for li in all_lis:
                link = li.find('a')
                if link:
                    href = link.get('href')
                    title = link.get_text(strip=True)

                    if href and title:
                        # Only process links that point to wiki pages (/w/)
                        if not href.startswith('/w/'):
                            logger.info(f"Skipping non-mix link: {href}")
                            continue

                        # Convert relative URL to absolute
                        if href.startswith('/'):
                            full_url = f"{self.base_url}{href}"
                        else:
                            full_url = href

                        mix_links.append({
                            'url': full_url,
                            'title': title
                        })

            logger.info(f"Found {len(mix_links)} valid mixes")
            return mix_links

        except httpx.HTTPError as e:
            logger.error(f"Error fetching artist page: {e}")
            return []

    async def get_tracklist_from_mix_page(self, mix_url: str, mix_title: str) -> str:
        """Extract tracklist from a mix page"""
        logger.info(f"Fetching tracklist from: {mix_title}")

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
                response = await client.get(mix_url)
                response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try to find the content div (main wiki content area)
            content_div = soup.find('div', id='mw-content-text')

            if not content_div:
                logger.warning(f"Could not find content div for: {mix_title}")
                return ""

            # Remove sections we don't want - be more aggressive
            # Remove category links
            for elem in content_div.find_all(class_='catlinks'):
                elem.decompose()

            # Remove related mixes sections by finding headings and removing following content
            for heading in content_div.find_all(['h2', 'h3', 'h4']):
                heading_text = heading.get_text(strip=True).lower()
                if 'related' in heading_text or 'see also' in heading_text:
                    # Remove the heading and all siblings until next heading
                    current = heading
                    while current:
                        next_sibling = current.next_sibling
                        current.decompose()
                        current = next_sibling
                        # Stop if we hit another heading
                        if current and hasattr(current, 'name') and current.name in ['h2', 'h3', 'h4']:
                            break

            # Remove any remaining elements with related/catMixes IDs
            for elem in content_div.find_all(id=lambda x: x and ('Related' in x or 'catMixes' in x)):
                elem.decompose()

            tracklist_lines = []

            # Helper function to detect if text is a related mix (not a track)
            def is_related_mix_format(text: str) -> bool:
                """Detect if text matches 'YYYY-MM-DD - Artist @ Venue' pattern"""
                # Pattern: starts with date and has @ symbol (venue indicator)
                related_mix_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}\s+-\s+.+\s+@')
                return bool(related_mix_pattern.match(text))

            # Helper function to detect if text is a track
            def is_track_format(text: str) -> bool:
                """Detect if text looks like a track (Artist - Title or [time] Artist - Title [Label])"""
                if ' - ' not in text or len(text) < 5:
                    return False

                # Exclude related mix format
                if is_related_mix_format(text):
                    return False

                # Look for track indicators: timestamps [00], [12:34], labels [Label], or just Artist - Title
                track_indicators = [
                    re.compile(r'^\[\d+\]'),  # [00]
                    re.compile(r'^\d{1,2}:\d{2}'),  # 12:34
                    re.compile(r'\[[\w\s]+\]$'),  # [Label Name] at end
                    re.compile(r'^\d{1,3}\.\s+'),  # 1. track number
                ]

                for pattern in track_indicators:
                    if pattern.search(text):
                        return True

                # If it has artist - title format but no date prefix, likely a track
                parts = text.split(' - ')
                if len(parts) >= 2 and not text.startswith(('19', '20')):  # Not starting with year
                    return True

                return False

            # Try to find ordered lists with track entries (most reliable)
            for ol_elem in content_div.find_all('ol'):
                list_items = ol_elem.find_all('li', recursive=False)
                track_items = []

                for li in list_items:
                    text = li.get_text(strip=True)
                    if is_track_format(text):
                        track_items.append(text)

                # If we found a list with multiple track items, use it
                if len(track_items) >= 3:
                    tracklist_lines = [f"{i+1}. {track}" for i, track in enumerate(track_items)]
                    break

            # If no ordered list found, try unordered lists (but be more careful)
            if not tracklist_lines:
                for ul_elem in content_div.find_all('ul'):
                    list_items = ul_elem.find_all('li', recursive=False)
                    track_items = []
                    related_count = 0

                    for li in list_items:
                        text = li.get_text(strip=True)
                        if is_related_mix_format(text):
                            related_count += 1
                        elif is_track_format(text):
                            track_items.append(text)

                    # Only use this list if it has tracks and NO related mixes
                    if len(track_items) >= 3 and related_count == 0:
                        tracklist_lines = [f"{i+1}. {track}" for i, track in enumerate(track_items)]
                        break

            # If no list found, fall back to text parsing
            if not tracklist_lines:
                tracklist_text = content_div.get_text(separator='\n', strip=True)
                lines = tracklist_text.split('\n')

                # Pattern for tracklist entries
                tracklist_pattern = re.compile(r'^(\[\d+\]|\d{1,2}:\d{2}(:\d{2})?|\d{1,3}\.)\s+.+\s+-\s+.+')

                for line in lines:
                    line = line.strip()
                    if line and tracklist_pattern.match(line) and not is_related_mix_format(line):
                        tracklist_lines.append(line)

            if not tracklist_lines:
                logger.warning(f"No tracklist found for: {mix_title}")
                return ""

            return '\n'.join(tracklist_lines)

        except httpx.HTTPError as e:
            logger.error(f"Error fetching mix page: {e}")
            return ""

    async def scrape_artist_tracklists(self, artist_name: str) -> List[Dict[str, str]]:
        """Scrape all tracklists for a given artist"""
        artist_url = self.get_artist_page_url(artist_name)

        # Get all mix URLs
        mix_links = await self.get_mix_urls_from_artist_page(artist_url)

        if not mix_links:
            logger.error("No mixes found for this artist")
            return []

        await self._send_progress("mixes_found", {
            "total_mixes": len(mix_links)
        })

        # Fetch tracklists
        all_tracklists = []
        for i, mix_info in enumerate(mix_links, 1):
            logger.info(f"Processing mix {i}/{len(mix_links)}")

            tracklist = await self.get_tracklist_from_mix_page(
                mix_info['url'],
                mix_info['title']
            )

            if tracklist:
                all_tracklists.append({
                    'title': mix_info['title'],
                    'url': mix_info['url'],
                    'tracklist': tracklist
                })

            await self._send_progress("mix_scraped", {
                "mix_number": i,
                "total_mixes": len(mix_links),
                "mix_title": mix_info['title']
            })

            # Rate limiting
            await asyncio.sleep(2)

        return all_tracklists

    def combine_tracklists(self, tracklists: List[Dict[str, str]]) -> str:
        """Combine all tracklists into a single text format"""
        return "\n\n".join([
            f"# {mix_data['title']}\n{mix_data['tracklist']}"
            for mix_data in tracklists
        ])
