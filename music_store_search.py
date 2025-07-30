#!/usr/bin/env python3
"""
Music Store Search Script
Searches multiple digital music platforms for tracks from a DJ set or playlist
"""

import requests
import time
import csv
import json
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
import re
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Track:
    timestamp: str
    artist: str
    title: str
    remix_info: str = ""
    
    @classmethod
    def parse_tracklist_line(cls, line: str) -> 'Track':
        """Parse a single line from the tracklist"""
        # Split timestamp from track info
        parts = line.strip().split(' ', 1)
        if len(parts) < 2:
            raise ValueError(f"Invalid line format: {line}")
        
        timestamp = parts[0]
        track_info = parts[1]
        
        # Extract remix info if present
        remix_match = re.search(r'\((.*(?:Remix|Mix|Dub).*)\)$', track_info, re.IGNORECASE)
        remix_info = remix_match.group(1) if remix_match else ""
        
        # Remove remix info from track_info for artist/title parsing
        if remix_info:
            track_info = re.sub(r'\s*\(.*(?:Remix|Mix|Dub).*\)$', '', track_info, flags=re.IGNORECASE)
        
        # Split artist and title
        if ' - ' in track_info:
            artist, title = track_info.split(' - ', 1)
        else:
            # Fallback if no clear separator
            artist = track_info
            title = ""
        
        return cls(timestamp=timestamp, artist=artist.strip(), title=title.strip(), remix_info=remix_info)

@dataclass
class SearchResult:
    platform: str
    artist: str
    title: str
    url: str
    price: str = ""
    available: bool = True

class MusicStoreSearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def search_bandcamp(self, artist: str, title: str) -> List[SearchResult]:
        """Search Bandcamp for a track"""
        results = []
        try:
            query = f"{artist} {title}".strip()
            if not query:
                return results
                
            url = f"https://bandcamp.com/search?q={quote_plus(query)}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                search_results = soup.find_all('li', class_='searchresult')
                
                for result in search_results[:3]:  # Limit to top 3 results
                    try:
                        link_elem = result.find('a')
                        if link_elem:
                            result_url = urljoin('https://bandcamp.com', link_elem.get('href', ''))
                            
                            # Extract artist and title from result
                            result_artist = ""
                            result_title = ""
                            
                            artist_elem = result.find('div', class_='subhead')
                            if artist_elem:
                                result_artist = artist_elem.get_text(strip=True).replace('by ', '')
                            
                            title_elem = result.find('div', class_='heading')
                            if title_elem:
                                result_title = title_elem.get_text(strip=True)
                            
                            results.append(SearchResult(
                                platform="Bandcamp",
                                artist=result_artist,
                                title=result_title,
                                url=result_url
                            ))
                    except Exception as e:
                        logger.warning(f"Error parsing Bandcamp result: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Bandcamp search error for '{artist} - {title}': {e}")
            
        return results
    
    def search_beatport(self, artist: str, title: str) -> List[SearchResult]:
        """Search Beatport for a track"""
        results = []
        try:
            query = f"{artist} {title}".strip()
            if not query:
                return results
                
            # Beatport search API endpoint
            url = f"https://www.beatport.com/search?q={quote_plus(query)}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                track_results = soup.find_all('li', class_='bucket-item')
                
                for result in track_results[:3]:
                    try:
                        link_elem = result.find('a', class_='buk-track-title')
                        if link_elem:
                            result_url = urljoin('https://www.beatport.com', link_elem.get('href', ''))
                            result_title = link_elem.get_text(strip=True)
                            
                            artist_elem = result.find('a', class_='buk-track-artists')
                            result_artist = artist_elem.get_text(strip=True) if artist_elem else ""
                            
                            price_elem = result.find('span', class_='buk-track-price')
                            price = price_elem.get_text(strip=True) if price_elem else ""
                            
                            results.append(SearchResult(
                                platform="Beatport",
                                artist=result_artist,
                                title=result_title,
                                url=result_url,
                                price=price
                            ))
                    except Exception as e:
                        logger.warning(f"Error parsing Beatport result: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Beatport search error for '{artist} - {title}': {e}")
            
        return results
    
    def search_traxsource(self, artist: str, title: str) -> List[SearchResult]:
        """Search Traxsource for a track"""
        results = []
        try:
            query = f"{artist} {title}".strip()
            if not query:
                return results
                
            url = f"https://www.traxsource.com/search?term={quote_plus(query)}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                track_results = soup.find_all('div', class_='trk-cell')
                
                for result in track_results[:3]:
                    try:
                        link_elem = result.find('a', class_='com-link')
                        if link_elem:
                            result_url = urljoin('https://www.traxsource.com', link_elem.get('href', ''))
                            
                            title_elem = result.find('div', class_='title')
                            result_title = title_elem.get_text(strip=True) if title_elem else ""
                            
                            artist_elem = result.find('div', class_='artists')
                            result_artist = artist_elem.get_text(strip=True) if artist_elem else ""
                            
                            results.append(SearchResult(
                                platform="Traxsource",
                                artist=result_artist,
                                title=result_title,
                                url=result_url
                            ))
                    except Exception as e:
                        logger.warning(f"Error parsing Traxsource result: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Traxsource search error for '{artist} - {title}': {e}")
            
        return results
    
    def search_hardwax(self, artist: str, title: str) -> List[SearchResult]:
        """Search Hardwax for a track"""
        results = []
        try:
            query = f"{artist} {title}".strip()
            if not query:
                return results
                
            url = f"https://hardwax.com/?search={quote_plus(query)}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Hardwax has a unique structure, adjust selectors as needed
                results_container = soup.find('div', id='search-results')
                if results_container:
                    items = results_container.find_all('div', class_='search-item')[:3]
                    
                    for item in items:
                        try:
                            link_elem = item.find('a')
                            if link_elem:
                                result_url = urljoin('https://hardwax.com', link_elem.get('href', ''))
                                
                                # Extract title and artist from the link text or other elements
                                result_text = link_elem.get_text(strip=True)
                                
                                results.append(SearchResult(
                                    platform="Hardwax",
                                    artist="",  # May need to parse differently
                                    title=result_text,
                                    url=result_url
                                ))
                        except Exception as e:
                            logger.warning(f"Error parsing Hardwax result: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Hardwax search error for '{artist} - {title}': {e}")
            
        return results
    
    def search_all_platforms(self, track: Track) -> Dict[str, List[SearchResult]]:
        """Search all platforms for a single track"""
        logger.info(f"Searching for: {track.artist} - {track.title}")
        
        all_results = {}
        
        # Search each platform
        platforms = {
            'bandcamp': self.search_bandcamp,
            'beatport': self.search_beatport,
            'traxsource': self.search_traxsource,
            'hardwax': self.search_hardwax
        }
        
        for platform_name, search_func in platforms.items():
            try:
                results = search_func(track.artist, track.title)
                if results:
                    all_results[platform_name] = results
                time.sleep(1)  # Be respectful with requests
            except Exception as e:
                logger.error(f"Error searching {platform_name}: {e}")
                
        return all_results

def parse_tracklist(tracklist_text: str) -> List[Track]:
    """Parse the entire tracklist"""
    tracks = []
    lines = tracklist_text.strip().split('\n')
    
    for line in lines:
        if line.strip():
            try:
                track = Track.parse_tracklist_line(line)
                tracks.append(track)
            except Exception as e:
                logger.warning(f"Could not parse line: '{line}' - {e}")
                
    return tracks

def save_results_to_csv(tracks: List[Track], all_results: Dict[int, Dict[str, List[SearchResult]]], filename: str = "music_search_results.csv"):
    """Save search results to CSV file"""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['timestamp', 'original_artist', 'original_title', 'remix_info', 'platform', 'found_artist', 'found_title', 'url', 'price']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for i, track in enumerate(tracks):
            track_results = all_results.get(i, {})
            
            if not track_results:
                # Write a row even if no results found
                writer.writerow({
                    'timestamp': track.timestamp,
                    'original_artist': track.artist,
                    'original_title': track.title,
                    'remix_info': track.remix_info,
                    'platform': 'No results found',
                    'found_artist': '',
                    'found_title': '',
                    'url': '',
                    'price': ''
                })
            else:
                for platform, results in track_results.items():
                    for result in results:
                        writer.writerow({
                            'timestamp': track.timestamp,
                            'original_artist': track.artist,
                            'original_title': track.title,
                            'remix_info': track.remix_info,
                            'platform': result.platform,
                            'found_artist': result.artist,
                            'found_title': result.title,
                            'url': result.url,
                            'price': result.price
                        })

def read_tracklist_file(filename: str) -> str:
    """Read tracklist from a file."""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        logger.error(f"Error: File '{filename}' not found.")
        raise
    except Exception as e:
        logger.error(f"Error reading file '{filename}': {e}")
        raise

def main():
    import argparse
    
    # Set up argument parser
    import datetime
    
    # Generate default output filename with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    default_output = f'music_search_results_{timestamp}.csv'
    
    parser = argparse.ArgumentParser(description='Search for tracks across multiple music platforms.')
    parser.add_argument('input_file', nargs='?', default='tracklist.txt',
                      help='Path to the tracklist file (default: tracklist.txt)')
    parser.add_argument('-o', '--output', default=default_output,
                      help=f'Output CSV file (default: {default_output})')
    
    args = parser.parse_args()
    
    # Read tracklist from file
    try:
        tracklist_text = read_tracklist_file(args.input_file)
        logger.info(f"Read tracklist from {args.input_file}")
    except Exception as e:
        logger.error("Failed to read tracklist. Exiting.")
        return
    
    # Parse tracklist
    tracks = parse_tracklist(tracklist_text)
    logger.info(f"Parsed {len(tracks)} tracks")
    
    # Initialize searcher
    searcher = MusicStoreSearcher()
    
    # Search for all tracks
    all_results = {}
    for i, track in enumerate(tracks):
        results = searcher.search_all_platforms(track)
        if results:
            all_results[i] = results
        
        # Progress indicator
        print(f"Processed {i+1}/{len(tracks)} tracks")
        
        # Be respectful with rate limiting
        time.sleep(2)
    
    # Save results
    save_results_to_csv(tracks, all_results, args.output)
    logger.info(f"Results saved to {args.output}")
    
    # Print summary
    print(f"\nSearch complete! Found results for {len([k for k, v in all_results.items() if v])} out of {len(tracks)} tracks")
    print(f"Results saved to '{args.output}'")

if __name__ == "__main__":
    main()