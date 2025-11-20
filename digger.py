#!/usr/bin/env python3
"""
MixesDB Artist Scraper
Scrapes all mix tracklists for a given artist from MixesDB and optionally searches for tracks on digital stores
"""

import logging
import time
from typing import List, Dict
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from music_store_search import (
    Track, MusicStoreSearcher, parse_tracklist,
    save_results_to_csv, generate_stats, ensure_data_directory
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class MixesDBScraper:
    """Scraper for extracting tracklists from MixesDB artist pages"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.base_url = "https://www.mixesdb.com"

    def get_artist_page_url(self, artist_name: str) -> str:
        """Convert artist name to MixesDB category URL"""
        # Replace spaces with underscores for the category URL format
        formatted_name = artist_name.replace(' ', '_')
        return f"{self.base_url}/w/Category:{formatted_name}"

    def get_mix_urls_from_artist_page(self, artist_url: str) -> List[Dict[str, str]]:
        """Extract all mix URLs and titles from an artist's category page"""
        logger.info(f"Fetching artist page: {artist_url}")

        try:
            response = self.session.get(artist_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the catMixesList element (this is the correct one with all the mixes)
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
                    logger.debug(f"Processing link: {href} - {title}")

                    if href and title:
                        # Skip invalid links (like list-artist-content)
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

        except requests.RequestException as e:
            logger.error(f"Error fetching artist page: {e}")
            return []

    def get_tracklist_from_mix_page(self, mix_url: str, mix_title: str) -> str:
        """Extract tracklist from a mix page"""
        logger.info(f"Fetching tracklist from: {mix_title}")

        try:
            response = self.session.get(mix_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try to find the content div (main wiki content area)
            content_div = soup.find('div', id='mw-content-text')

            if not content_div:
                logger.warning(f"Could not find content div for: {mix_title}")
                return ""

            # Remove sections we don't want (related mixes, categories, etc.)
            # Remove all elements with class 'catlinks' (categories)
            for elem in content_div.find_all(class_='catlinks'):
                elem.decompose()

            # Remove all elements with id containing 'Related' or 'catMixes'
            for elem in content_div.find_all(id=lambda x: x and ('Related' in x or 'catMixes' in x)):
                elem.decompose()

            # First, try to find an <ol> or <ul> list containing tracks
            # Look for lists that appear after "Tracklist" heading
            import re
            tracklist_lines = []

            # Try to find ordered or unordered lists with track entries
            for ol_elem in content_div.find_all(['ol', 'ul']):
                list_items = ol_elem.find_all('li')
                # Check if list items look like tracks (contain " - ")
                track_items = []
                for li in list_items:
                    text = li.get_text(strip=True)
                    if ' - ' in text and len(text) > 5:  # Basic track format check
                        track_items.append(text)

                # If we found a list with multiple track-like items, use it
                if len(track_items) >= 3:
                    # Add numbers to match the expected format
                    tracklist_lines = [f"{i+1}. {track}" for i, track in enumerate(track_items)]
                    break

            # If no list found, fall back to text parsing
            if not tracklist_lines:
                # Get all text from the cleaned content area
                tracklist_text = content_div.get_text(separator='\n', strip=True)

                # Filter to only keep lines that look like tracklist entries
                # Tracklist lines have specific patterns:
                # - [000] Artist - Title
                # - 00:00:00 Artist - Title
                # - 00:00 Artist - Title
                # - 1. Artist - Title (numbered list)
                lines = tracklist_text.split('\n')

                # Pattern for tracklist entries (with timestamps or numbered)
                # Matches: [000], 00:00, 00:00:00, or just numbers like "1." or "01."
                tracklist_pattern = re.compile(r'^(\[\d+\]|\d{1,2}:\d{2}(:\d{2})?|\d{1,3}\.)\s+.+\s+-\s+.+')

                for line in lines:
                    line = line.strip()
                    if line and tracklist_pattern.match(line):
                        tracklist_lines.append(line)

            if not tracklist_lines:
                logger.warning(f"No tracklist found for: {mix_title}")
                return ""

            return '\n'.join(tracklist_lines)

        except requests.RequestException as e:
            logger.error(f"Error fetching mix page: {e}")
            return ""

    def scrape_artist_tracklists(self, artist_name: str) -> List[Dict[str, str]]:
        """Scrape all tracklists for a given artist"""
        artist_url = self.get_artist_page_url(artist_name)

        # Get all mix URLs
        mix_links = self.get_mix_urls_from_artist_page(artist_url)

        if not mix_links:
            logger.error("No mixes found for this artist")
            return []

        # Fetch tracklists
        all_tracklists = []
        for i, mix_info in enumerate(mix_links, 1):
            logger.info(f"Processing mix {i}/{len(mix_links)}")

            tracklist = self.get_tracklist_from_mix_page(
                mix_info['url'],
                mix_info['title']
            )

            if tracklist:
                all_tracklists.append({
                    'title': mix_info['title'],
                    'url': mix_info['url'],
                    'tracklist': tracklist
                })

            # Be respectful with rate limiting
            time.sleep(2)

        return all_tracklists


def print_tracklists(tracklists: List[Dict[str, str]]):
    """Print all tracklists in a readable format"""
    print("\n" + "="*80)
    print(f"Found {len(tracklists)} mixes with tracklists")
    print("="*80 + "\n")

    for i, mix_data in enumerate(tracklists, 1):
        print(f"\n{'='*80}")
        print(f"Mix {i}: {mix_data['title']}")
        print(f"URL: {mix_data['url']}")
        print(f"{'='*80}")
        print(mix_data['tracklist'])
        print()


def search_all_tracklists(tracklists: List[Dict[str, str]]):
    """Search for all tracks from all tracklists on digital music stores"""
    # Combine all tracklists
    combined_tracklist = "\n\n".join([
        f"# {mix_data['title']}\n{mix_data['tracklist']}"
        for mix_data in tracklists
    ])

    # Parse all tracks
    logger.info("Parsing all tracks...")
    tracks = parse_tracklist(combined_tracklist)
    logger.info(f"Parsed {len(tracks)} tracks from {len(tracklists)} mixes")

    if not tracks:
        logger.error("No valid tracks found")
        return

    # Create output directory
    run_dir = ensure_data_directory()
    logger.info(f"Results will be saved to: {run_dir}")

    # Save combined tracklist
    tracklist_file = run_dir / "combined_tracklist.txt"
    with open(tracklist_file, 'w', encoding='utf-8') as f:
        f.write(combined_tracklist)
    logger.info(f"Saved combined tracklist to: {tracklist_file}")

    # Initialize searcher
    searcher = MusicStoreSearcher()

    # Search for all tracks
    all_results = {}
    print("\n" + "="*80)
    print("Searching for tracks on digital music stores...")
    print("="*80 + "\n")

    for i, track in enumerate(tracks):
        results = searcher.search_all_platforms(track)
        if results:
            all_results[i] = results

        # Progress indicator
        print(f"Processed {i+1}/{len(tracks)} tracks", end='\r')

        # Be respectful with rate limiting
        time.sleep(2)

    print(f"\nProcessed {len(tracks)}/{len(tracks)} tracks\n")

    # Save results and generate stats
    results_file = save_results_to_csv(tracks, all_results, run_dir)
    stats_file = run_dir / "stats.txt"
    platform_rates = generate_stats(tracks, all_results, stats_file)

    # Print summary
    print(f"\n{'='*80}")
    print("Search Complete!")
    print(f"{'='*80}")
    print(f"Total tracks: {len(tracks)}")
    print(f"Tracks with results: {len([k for k, v in all_results.items() if v])}")
    print(f"Results saved to: {run_dir}/")
    print("\nSuccess rates by platform:")
    for platform, rate in sorted(platform_rates.items(), key=lambda x: x[1], reverse=True):
        print(f"  {platform}: {rate:.1f}%")
    print()


def main():
    """Main entry point"""
    import sys

    # Check for artist name argument
    if len(sys.argv) < 2:
        print("Usage: python digger.py <artist_name>")
        print("Example: python digger.py 'Carlos Souffront'")
        sys.exit(1)

    artist_name = ' '.join(sys.argv[1:])

    print(f"\n{'='*80}")
    print(f"MixesDB Artist Scraper")
    print(f"{'='*80}")
    print(f"Artist: {artist_name}")
    print(f"{'='*80}\n")

    # Initialize scraper
    scraper = MixesDBScraper()

    # Scrape all tracklists
    tracklists = scraper.scrape_artist_tracklists(artist_name)

    if not tracklists:
        print("No tracklists found. Exiting.")
        sys.exit(1)

    # Print all tracklists
    print_tracklists(tracklists)

    # Save combined tracklist immediately (before asking to search stores)
    combined_tracklist = "\n\n".join([
        f"# {mix_data['title']}\n{mix_data['tracklist']}"
        for mix_data in tracklists
    ])

    # Save to file immediately
    from pathlib import Path
    tracklist_output = Path.cwd() / f"{artist_name.replace(' ', '_')}_combined_tracklist.txt"
    with open(tracklist_output, 'w', encoding='utf-8') as f:
        f.write(combined_tracklist)

    print(f"\n{'='*80}")
    print(f"Combined tracklist saved to: {tracklist_output}")
    print(f"{'='*80}\n")

    # Ask user if they want to proceed with searching
    print(f"\n{'='*80}")
    print("Press Enter to search for these tracks on digital music stores")
    print("Or type 'cancel' to exit")
    print(f"{'='*80}\n")

    user_input = input(">>> ").strip().lower()

    if user_input in ['cancel', 'c', 'quit', 'q', 'exit']:
        print("Cancelled. Exiting.")
        sys.exit(0)

    # Proceed with searching
    search_all_tracklists(tracklists)


if __name__ == "__main__":
    main()
