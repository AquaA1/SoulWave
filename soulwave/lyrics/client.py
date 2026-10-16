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

    def _build_search_queries(self, artist: str, title: str, album: str = "") -> List[str]:
        """Formulates search query variations handling punctuation, annotations and artist prefixes."""
        import re
        queries: List[str] = []

        clean_title = re.sub(
            r"[\(\[\{].*?(official|video|audio|lyrics|hd|4k|mv|remaster|remix|radio|edit|bonus).*?[\)\]\}]",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()
        clean_artist = re.sub(r"[\(\[\{].*?[\)\]\}]", "", artist).strip()

        # Query 1: Clean artist - clean title
        if clean_artist and clean_artist.lower() not in clean_title.lower():
            q1 = f"{clean_artist} - {clean_title}"
        else:
            q1 = clean_title or title
        q1 = q1.strip()
        if q1 and q1 not in queries:
            queries.append(q1)

        # Query 2: Normalized punctuation (curly quotes, dashes, ampersands)
        norm_title = clean_title.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-")
        norm_artist = clean_artist.replace("’", "'").replace("‘", "'").replace("–", "-")
        norm_title = re.sub(r"\s+", " ", norm_title).strip()
        norm_artist = re.sub(r"\s+", " ", norm_artist).strip()
        if norm_artist and norm_artist.lower() not in norm_title.lower():
            q2 = f"{norm_artist} - {norm_title}"
        else:
            q2 = norm_title
        q2 = q2.strip()
        if q2 and q2 not in queries:
            queries.append(q2)

        # Query 3: Without featuring artist if present
        feat_free_title = re.sub(r"\b(feat|ft)\b.*", "", norm_title, flags=re.IGNORECASE).strip()
        feat_free_artist = re.sub(r"\b(feat|ft)\b.*", "", norm_artist, flags=re.IGNORECASE).strip()
        if feat_free_artist and feat_free_artist.lower() not in feat_free_title.lower():
            q3 = f"{feat_free_artist} - {feat_free_title}".strip()
            if q3 and q3 not in queries:
                queries.append(q3)

        return queries

    def _build_search_query(self, artist: str, title: str, album: str = "") -> str:
        """Formulates an effective search query string from metadata."""
        queries = self._build_search_queries(artist, title, album)
        return queries[0] if queries else f"{artist} - {title}".strip()

    def _is_suspiciously_incomplete(self, synced_lrc: str, duration: float = 0.0) -> bool:
        """Determines if a synced lyrics response is clearly truncated or incomplete.

        Legitimate early-ending vocal tracks with long instrumental outros
        (e.g. substantial lyric lines or >= 40% coverage) are NOT classified as incomplete.
        """
        if not synced_lrc or duration <= 60.0:
            return False

        parsed_lines = LRCParser.parse(synced_lrc)
        non_empty = [l for l in parsed_lines if l.text.strip()]
        line_count = len(non_empty)
        if line_count == 0:
            return True

        last_ts = parsed_lines[-1].timestamp
        coverage = last_ts / duration

        # Suspiciously incomplete: very few lines (<4) ending in the first 35% of a >60s track
        if line_count < 4 and coverage < 0.35:
            return True

        # Suspiciously incomplete: fewer than 6 lines ending in the first 20% of the track
        if line_count < 6 and coverage < 0.20:
            return True

        return False

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

        queries = self._build_search_queries(artist, title, album)
        if not queries:
            return None

        primary_query = queries[0]
        logger.info("Searching lyrics via syncedlyrics for: '%s'", primary_query)

        best_synced: Optional[str] = None
        best_parsed_len: int = 0

        # 2. Try synced lyrics first across query variations
        for query in queries:
            try:
                synced_lrc = syncedlyrics.search(query, synced_only=True)
                if synced_lrc:
                    parsed = LRCParser.parse(synced_lrc)
                    if len(parsed) >= 1:
                        if not self._is_suspiciously_incomplete(synced_lrc, duration):
                            best_synced = synced_lrc
                            break
                        else:
                            if len(parsed) > best_parsed_len:
                                best_synced = synced_lrc
                                best_parsed_len = len(parsed)
            except Exception as e:
                logger.debug("Synced search error for '%s': %s", query, e)

        # If primary result is suspiciously incomplete or missing, try fallback providers
        if duration > 60.0 and (not best_synced or self._is_suspiciously_incomplete(best_synced, duration)):
            fallback_provider_groups = [["NetEase"], ["Megalobiz"], ["Musixmatch"], ["Genius"], ["Deezer"]]
            for prov in fallback_provider_groups:
                try:
                    alt_lrc = syncedlyrics.search(primary_query, synced_only=True, providers=prov)
                    if alt_lrc:
                        alt_parsed = LRCParser.parse(alt_lrc)
                        if len(alt_parsed) >= 1:
                            if not self._is_suspiciously_incomplete(alt_lrc, duration):
                                best_synced = alt_lrc
                                break
                            elif len(alt_parsed) > best_parsed_len:
                                best_synced = alt_lrc
                                best_parsed_len = len(alt_parsed)
                except Exception as e:
                    logger.debug("Provider fallback %s error: %s", prov, e)

        if best_synced:
            result = {
                "syncedLyrics": best_synced,
                "plainLyrics": None,
                "is_synced": True,
                "source": "syncedlyrics",
            }
            self.cache.save_lyrics(artist, title, result)
            return result

        # 3. If synced lyrics are unavailable, fallback to plain lyrics
        for query in queries:
            try:
                plain_lrc = syncedlyrics.search(query, plain_only=True)
                if plain_lrc and plain_lrc.strip():
                    result = {
                        "syncedLyrics": None,
                        "plainLyrics": plain_lrc.strip(),
                        "is_synced": False,
                        "source": "syncedlyrics",
                    }
                    self.cache.save_lyrics(artist, title, result)
                    return result
            except Exception as e:
                logger.debug("Plain search error for '%s': %s", query, e)

        # Not found from any provider
        self.cache.save_miss(artist, title, "No lyrics found from providers")
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
