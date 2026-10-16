"""Disk cache for lyrics and manual synchronization offsets."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Dict, Optional, Tuple


class LyricsCache:
    """Stores fetched lyrics, miss/failure backoffs, and per-song timing offset preferences."""

    NEGATIVE_CACHE_TTL: float = 60.0  # 1 minute before retrying a failed lookup
    MAX_RETRIES: int = 3  # Maximum failed attempts within retry window

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or (Path.home() / ".cache" / "soulwave" / "lyrics")
        self.offsets_file = self.cache_dir / "offsets.json"
        self._offsets: Dict[str, float] = {}
        self._load_offsets()

    def _normalize(self, val: str) -> str:
        """Normalizes track strings into stable, filesystem-safe alphanumeric keys."""
        # Lowercase, remove common punctuation and extraneous features (e.g. feat., ft., official video, etc.)
        cleaned = val.lower().strip()
        cleaned = re.sub(r"[\(\[\{].*?[\)\]\}]", "", cleaned)  # remove parenthesized terms like (Official Music Video)
        cleaned = re.sub(r"\b(feat|ft)\b.*", "", cleaned)      # remove feat. ...
        cleaned = re.sub(r"[^\w\s]", "", cleaned)              # remove special punctuation
        cleaned = re.sub(r"\s+", "_", cleaned).strip("_")      # collapse spaces to underscore
        return cleaned or "unknown"

    def get_track_key(self, artist: str, title: str) -> str:
        """Returns stable, normalized track key."""
        return f"{self._normalize(artist)}__{self._normalize(title)}"

    def _load_offsets(self) -> None:
        if self.offsets_file.is_file():
            try:
                with open(self.offsets_file, "r", encoding="utf-8") as f:
                    self._offsets = json.load(f)
            except Exception:
                self._offsets = {}

    def _save_offsets(self) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.offsets_file, "w", encoding="utf-8") as f:
                json.dump(self._offsets, f, indent=2)
        except Exception:
            pass

    def get_offset(self, artist: str, title: str) -> float:
        """Get manual sync offset in seconds for this song."""
        key = self.get_track_key(artist, title)
        return self._offsets.get(key, 0.0)

    def set_offset(self, artist: str, title: str, offset: float) -> None:
        """Save manual sync offset in seconds for this song."""
        key = self.get_track_key(artist, title)
        self._offsets[key] = round(offset, 2)
        self._save_offsets()

    def get_lyrics(self, artist: str, title: str) -> Optional[dict]:
        """Load cached lyrics payload if present and not an unexpired negative miss."""
        key = self.get_track_key(artist, title)
        path = self.cache_dir / f"{key}.json"
        if not path.is_file():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if this is a cached miss / failure
            if data.get("is_miss"):
                cached_at = float(data.get("timestamp", 0))
                retry_count = int(data.get("retry_count", 1))
                if time.time() - cached_at < self.NEGATIVE_CACHE_TTL and retry_count >= self.MAX_RETRIES:
                    return {"is_miss": True, "error": data.get("error", "No lyrics found")}
                # Expired or retry allowed
                return None

            return data
        except Exception:
            return None

    def save_lyrics(self, artist: str, title: str, payload: dict) -> None:
        """Cache successful lyrics payload to disk."""
        key = self.get_track_key(artist, title)
        path = self.cache_dir / f"{key}.json"
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

    def save_miss(self, artist: str, title: str, error_msg: str = "Not found") -> None:
        """Record a search miss or failure to prevent repetitive network spam."""
        key = self.get_track_key(artist, title)
        path = self.cache_dir / f"{key}.json"
        retries = 1
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    old = json.load(f)
                    if old.get("is_miss"):
                        retries = int(old.get("retry_count", 0)) + 1
            except Exception:
                pass

        miss_payload = {
            "is_miss": True,
            "error": error_msg,
            "timestamp": time.time(),
            "retry_count": retries,
        }
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(miss_payload, f, indent=2)
        except Exception:
            pass
