"""Parser for timestamped LRC lyrics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

TIMESTAMP_REGEX = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")


@dataclass
class LyricLine:
    timestamp: float  # Seconds
    text: str


class LRCParser:
    """Parses .lrc timestamped lyric strings with millisecond accuracy."""

    @classmethod
    def parse(cls, raw_lrc: str) -> List[LyricLine]:
        lines: List[LyricLine] = []
        if not raw_lrc:
            return lines

        for raw_line in raw_lrc.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            matches = list(TIMESTAMP_REGEX.finditer(raw_line))
            if not matches:
                continue

            # Strip all timestamp tags from line to extract text
            text = TIMESTAMP_REGEX.sub("", raw_line).strip()

            for match in matches:
                mins = int(match.group(1))
                secs = int(match.group(2))
                millis_str = match.group(3) or "0"
                if len(millis_str) == 2:
                    millis = int(millis_str) * 10
                elif len(millis_str) == 1:
                    millis = int(millis_str) * 100
                else:
                    millis = int(millis_str[:3])

                total_seconds = (mins * 60.0) + secs + (millis / 1000.0)
                lines.append(LyricLine(timestamp=total_seconds, text=text))

        # Sort lines by timestamp
        lines.sort(key=lambda item: item.timestamp)
        return lines

    @classmethod
    def find_active_index(
        cls,
        lines: List[LyricLine],
        current_time: float,
        offset_seconds: float = 0.0,
    ) -> int:
        """Find the index of the line currently being sung."""
        if not lines:
            return -1

        adjusted_time = current_time + offset_seconds
        if adjusted_time < lines[0].timestamp:
            return -1

        # Linear or binary search for the latest line where line.timestamp <= adjusted_time
        active_idx = -1
        for i, line in enumerate(lines):
            if line.timestamp <= adjusted_time:
                active_idx = i
            else:
                break
        return active_idx
