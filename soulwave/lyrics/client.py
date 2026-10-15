"""syncedlyrics-powered lyrics fetching backend with async worker and caching."""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional, Set
import syncedlyrics
from syncedlyrics.utils import identify_lyrics_type

from .cache import LyricsCache
from .parser import LRCParser

logger = logging.getLogger(__name__)


class LyricsClient:
    """Fetches synchronized and plain lyrics using the syncedlyrics package."""

    def __init__(self, cache: LyricsCache | None = None) -> None:
        self.cache = cache or LyricsCache()
        self._lock = threading.Lock()
        self._active_requests: Set[str] = set()
        self._latest_request_id: int = 0

    def _build_search_query(self, artist: str, title: str, album: str = "") -> str:
        """Formulates an effective search query string from metadata."""
        # Clean up YouTube video annotations in title (e.g. "Song Name (Official Music Video)")
        import re
        clean_title = re.sub(r"[\(\[\{].*?(official|video|audio|lyrics|hd|4k|mv).*?[\)\]\}]", "", title, flags=re.IGNORECASE).strip()
        clean_artist = re.sub(r"[\(\[\{].*?[\)\]\}]", "", artist).strip()
        
        # In YouTube/streaming, artist is often prefixed into the title
        if clean_artist and clean_artist.lower() not in clean_title.lower():
            query = f"{clean_artist} - {clean_title}"
        else:
            query = clean_title or title

        return query.strip()

    def fetch_lyrics_sync(
        self,
        artist: str,
        title: str,
        album: str = "",
        duration: float = 0.0,
    ) -> Optional[dict]:
        """Fetch lyrics synchronously, checking local cache first.
        
        Returns a dict:
        {
            "syncedLyrics": str | None,
            "plainLyrics": str | None,
            "is_synced": bool,
            "source": str,
        }
        or None if not found / error.
        """
        if not title or title.strip() in ("", "No Track Playing", "Unknown Track"):
            return None

        # 1. Check cache
        cached = self.cache.get_lyrics(artist, title)
        if cached is not None:
            if cached.get("is_miss"):
                logger.debug("Lyrics cache hit (negative miss) for %s - %s", artist, title)
                return None
            return cached

        search_query = self._build_search_query(artist, title, album)
        if not search_query:
            return None

        logger.info("Searching lyrics via syncedlyrics for: '%s'", search_query)

        synced_lrc: Optional[str] = None
        plain_lrc: Optional[str] = None

        try:
            # 2. Try synced lyrics first across all available providers
            synced_lrc = syncedlyrics.search(search_query, synced_only=True)
            if synced_lrc:
                parsed_lines = LRCParser.parse(synced_lrc)
                if len(parsed_lines) >= 1:
                    result = {
                        "syncedLyrics": synced_lrc,
                        "plainLyrics": None,
                        "is_synced": True,
                        "source": "syncedlyrics",
                    }
                    self.cache.save_lyrics(artist, title, result)
                    return result

            # 3. If synced lyrics are unavailable, fallback to plain lyrics
            plain_lrc = syncedlyrics.search(search_query, plain_only=True)
            if plain_lrc and plain_lrc.strip():
                result = {
                    "syncedLyrics": None,
                    "plainLyrics": plain_lrc.strip(),
                    "is_synced": False,
                    "source": "syncedlyrics",
                }
                self.cache.save_lyrics(artist, title, result)
                return result

            # Not found from any provider
            self.cache.save_miss(artist, title, "No lyrics found from providers")
            return None

        except Exception as e:
            logger.warning("Error searching lyrics for '%s': %s", search_query, e)
            self.cache.save_miss(artist, title, str(e))
            return None

    def fetch_lyrics_async(
        self,
        artist: str,
        title: str,
        album: str = "",
        duration: float = 0.0,
        callback: Callable[[Optional[dict]], None] | None = None,
    ) -> None:
        """Fetch lyrics in a background thread, preventing duplicates and discarding stale tracks."""
        track_key = self.cache.get_track_key(artist, title)

        with self._lock:
            self._latest_request_id += 1
            request_id = self._latest_request_id

            if track_key in self._active_requests:
                logger.debug("Request for track '%s' already in progress, skipping duplicate", track_key)
                return
            self._active_requests.add(track_key)

        def worker():
            try:
                result = self.fetch_lyrics_sync(artist, title, album, duration)
            finally:
                with self._lock:
                    self._active_requests.discard(track_key)

            # Check if track is still current
            with self._lock:
                if request_id != self._latest_request_id:
                    logger.debug("Discarding lyrics result for outdated request_id=%d (current=%d)", request_id, self._latest_request_id)
                    return

            if callback:
                try:
                    callback(result)
                except Exception as e:
                    logger.error("Callback error in fetch_lyrics_async: %s", e)

        t = threading.Thread(target=worker, daemon=True, name=f"LyricsFetch-{track_key[:15]}")
        t.start()
