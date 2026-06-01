import logging
import asyncio
from typing import List, Optional, Callable
from urllib.parse import quote_plus, urljoin
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from app.services.parser import ParsedTrack

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    platform: str
    artist: str
    title: str
    url: str
    price: str = ""


class AsyncMusicStoreSearcher:
    """Async searcher for multiple digital music platforms"""

    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    async def _send_progress(self, message_type: str, data: dict):
        """Send progress update via callback if provided"""
        if self.progress_callback:
            await self.progress_callback(message_type, data)

    async def search_bandcamp(self, artist: str, title: str) -> List[SearchResult]:
        """Search Bandcamp for a track"""
        results = []
        try:
            query = f"{artist} {title}".strip()
            if not query:
                return results

            url = f"https://bandcamp.com/search?q={quote_plus(query)}"

            async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
                response = await client.get(url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                search_results = soup.find_all('li', class_='searchresult')

                for result in search_results[:3]:
                    try:
                        link_elem = result.find('a')
                        if link_elem:
                            result_url = urljoin('https://bandcamp.com', link_elem.get('href', ''))

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

    async def search_beatport(self, artist: str, title: str) -> List[SearchResult]:
        """Search Beatport for a track"""
        results = []
        try:
            query = f"{artist} {title}".strip()
            if not query:
                return results

            url = f"https://www.beatport.com/search?q={quote_plus(query)}"

            async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
                response = await client.get(url)

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

    async def search_traxsource(self, artist: str, title: str) -> List[SearchResult]:
        """Search Traxsource for a track"""
        results = []
        try:
            query = f"{artist} {title}".strip()
            if not query:
                return results

            url = f"https://www.traxsource.com/search?term={quote_plus(query)}"

            async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
                response = await client.get(url)

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

    async def search_hardwax(self, artist: str, title: str) -> List[SearchResult]:
        """Search Hardwax for a track"""
        results = []
        try:
            query = f"{artist} {title}".strip()
            if not query:
                return results

            url = f"https://hardwax.com/?search={quote_plus(query)}"

            async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
                response = await client.get(url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                results_container = soup.find('div', id='search-results')
                if results_container:
                    items = results_container.find_all('div', class_='search-item')[:3]

                    for item in items:
                        try:
                            link_elem = item.find('a')
                            if link_elem:
                                result_url = urljoin('https://hardwax.com', link_elem.get('href', ''))
                                title_elem = item.find('span', class_='track-title')
                                result_title = title_elem.get_text(strip=True) if title_elem else ""

                                artist_elem = item.find('span', class_='track-artist')
                                result_artist = artist_elem.get_text(strip=True) if artist_elem else ""

                                results.append(SearchResult(
                                    platform="Hardwax",
                                    artist=result_artist,
                                    title=result_title,
                                    url=result_url
                                ))
                        except Exception as e:
                            logger.warning(f"Error parsing Hardwax result: {e}")
                            continue

        except Exception as e:
            logger.error(f"Hardwax search error for '{artist} - {title}': {e}")

        return results

    async def search_all_platforms(self, track: ParsedTrack) -> List[SearchResult]:
        """Search all platforms for a track"""
        tasks = [
            self.search_bandcamp(track.artist, track.title),
            self.search_beatport(track.artist, track.title),
            self.search_traxsource(track.artist, track.title),
            self.search_hardwax(track.artist, track.title)
        ]

        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and filter out exceptions
        all_results = []
        for results in results_lists:
            if isinstance(results, list):
                all_results.extend(results)
            else:
                logger.error(f"Search task failed: {results}")

        # Rate limiting delay
        await asyncio.sleep(1)

        return all_results
