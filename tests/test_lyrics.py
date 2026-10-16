"""Tests for LRC parsing, line selection, lyrics cache, and syncedlyrics client."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from soulwave.lyrics.parser import LRCParser, LyricLine
from soulwave.lyrics.cache import LyricsCache
from soulwave.lyrics.client import LyricsClient

RAW_LRC = """
[00:05.20] Look at the stars
[00:10.50] Look how they shine for you
[00:18.00] And everything you do
[00:25.80] Yeah, they were all yellow
"""


def test_lrc_parser():
    lines = LRCParser.parse(RAW_LRC)
    assert len(lines) == 4

    assert abs(lines[0].timestamp - 5.20) < 0.01
    assert lines[0].text == "Look at the stars"

    assert abs(lines[1].timestamp - 10.50) < 0.01
    assert lines[1].text == "Look how they shine for you"


def test_find_active_index():
    lines = LRCParser.parse(RAW_LRC)

    # Before first line
    assert LRCParser.find_active_index(lines, 2.0) == -1

    # Right on first line
    assert LRCParser.find_active_index(lines, 5.25) == 0

    # Between line 1 and 2
    assert LRCParser.find_active_index(lines, 12.0) == 1

    # After last line
    assert LRCParser.find_active_index(lines, 50.0) == 3

    # With offset
    # If offset is +3.0s, at current_time=3.0, adjusted time is 6.0s -> line 0
    assert LRCParser.find_active_index(lines, 3.0, offset_seconds=3.0) == 0


def test_lyrics_cache_hits_and_offsets():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LyricsCache(Path(tmpdir))
        assert cache.get_offset("Artist", "Title") == 0.0

        cache.set_offset("Artist", "Title", 0.3)
        assert cache.get_offset("Artist", "Title") == 0.3

        # Payload caching
        data = {"syncedLyrics": RAW_LRC, "plainLyrics": None, "is_synced": True}
        cache.save_lyrics("Coldplay", "Yellow", data)
        loaded = cache.get_lyrics("Coldplay", "Yellow")
        assert loaded == data

        # Normalized key check (ignores case, extra punctuation, feat/video tags)
        loaded_normalized = cache.get_lyrics("coldplay", "Yellow (Official Video)")
        assert loaded_normalized == data


def test_lyrics_cache_negative_misses_and_retries():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LyricsCache(Path(tmpdir))

        # First miss: not locked out yet (retry count 1 < MAX_RETRIES 3)
        cache.save_miss("Artist", "Song")
        assert cache.get_lyrics("Artist", "Song") is None

        # Repeat misses up to MAX_RETRIES
        cache.save_miss("Artist", "Song")
        cache.save_miss("Artist", "Song")

        # Now locked out as negative miss
        res = cache.get_lyrics("Artist", "Song")
        assert res is not None
        assert res.get("is_miss") is True


@patch("syncedlyrics.search")
def test_lyrics_client_synced_success(mock_search):
    mock_search.return_value = RAW_LRC

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LyricsCache(Path(tmpdir))
        client = LyricsClient(cache)

        res = client.fetch_lyrics_sync("Coldplay", "Yellow")
        assert res is not None
        assert res["is_synced"] is True
        assert res["syncedLyrics"] == RAW_LRC
        assert mock_search.called

        # Second call should hit disk cache without calling search again
        mock_search.reset_mock()
        cached_res = client.fetch_lyrics_sync("Coldplay", "Yellow")
        assert cached_res == res
        assert not mock_search.called


@patch("syncedlyrics.search")
def test_lyrics_client_plain_fallback(mock_search):
    # Synced search returns None, plain search returns text
    def side_effect(query, synced_only=False, plain_only=False, **kwargs):
        if synced_only:
            return None
        if plain_only:
            return "Plain lyrics line 1\nPlain lyrics line 2"
        return None

    mock_search.side_effect = side_effect

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LyricsCache(Path(tmpdir))
        client = LyricsClient(cache)

        res = client.fetch_lyrics_sync("Instrumental Artist", "Acoustic Melody")
        assert res is not None
        assert res["is_synced"] is False
        assert res["syncedLyrics"] is None
        assert "Plain lyrics" in res["plainLyrics"]


@patch("syncedlyrics.search")
def test_lyrics_client_async_outdated_track_discarded(mock_search):
    import threading

    t1_started = threading.Event()
    t2_submitted = threading.Event()
    t2_done = threading.Event()

    # Simulate slow search for track 1, then fast search for track 2
    def slow_search(query, **kwargs):
        if "Track 1" in query:
            t1_started.set()
            # Wait until Track 2 has been dispatched so Track 1 is definitely superseded
            assert t2_submitted.wait(timeout=5.0), "Timed out waiting for Track 2 to be submitted"
            return "[00:10.00] Track 1 lyrics"
        return "[00:05.00] Track 2 lyrics"

    mock_search.side_effect = slow_search

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LyricsCache(Path(tmpdir))
        client = LyricsClient(cache)

        results = []

        def cb1(data):
            results.append(("track1", data))

        def cb2(data):
            results.append(("track2", data))
            t2_done.set()

        # Launch track 1
        client.fetch_lyrics_async("Artist", "Track 1", callback=cb1)
        # Wait until track 1 search thread has definitely begun
        assert t1_started.wait(timeout=5.0), "Track 1 search thread failed to start"
        # While Track 1 is waiting, immediately change track to track 2
        client.fetch_lyrics_async("Artist", "Track 2", callback=cb2)
        # Now release Track 1; its request_id is now outdated compared to Track 2
        t2_submitted.set()

        # Wait for track 2 to finish
        assert t2_done.wait(timeout=5.0), "Track 2 callback never fired"

        # Give background threads a short moment to ensure cb1 did not fire
        time.sleep(0.1)

        # cb1 must have been discarded because track 1 was superseded!
        assert len(results) == 1
        assert results[0][0] == "track2"
        assert results[0][1]["syncedLyrics"] == "[00:05.00] Track 2 lyrics"


@patch("syncedlyrics.search")
def test_lyrics_client_network_failure(mock_search):
    mock_search.side_effect = ConnectionError("Network unreachable")

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LyricsCache(Path(tmpdir))
        client = LyricsClient(cache)

        # Must not raise exception, returns None gracefully
        res = client.fetch_lyrics_sync("Artist", "Offline Track")
        assert res is None


def test_plain_lyrics_progressive_scrolling():
    from soulwave.ui.widgets.lyrics_panel import LyricsPanelView

    panel = LyricsPanelView()
    plain = """Line 1: First verse
Line 2: Second verse
Line 3: Chorus starts
Line 4: Chorus ends
Line 5: Outro"""
    panel.set_lyrics(None, plain, duration=100.0)

    # At t=0s, active line should be Line 1
    panel.update_position(0.0, (56, 189, 248), duration=100.0)
    render_0 = panel.render().plain
    assert "▸ Line 1: First verse" in render_0

    # At t=50s (midpoint of 100s), active line should be Line 3 (index 2)
    panel.update_position(50.0, (56, 189, 248), duration=100.0)
    render_50 = panel.render().plain
    assert "▸ Line 3: Chorus starts" in render_50

    # Pausing: position unchanging keeps reading position frozen
    panel.update_position(50.0, (56, 189, 248), duration=100.0)
    render_paused = panel.render().plain
    assert "▸ Line 3: Chorus starts" in render_paused

    # Seeking: jumping to 95s recalculates active line immediately to Outro
    panel.update_position(95.0, (56, 189, 248), duration=100.0)
    render_seek = panel.render().plain
    assert "▸ Line 5: Outro" in render_seek

    # Missing duration fallback: duration_seconds = 0.0 uses safe fallback
    panel.set_lyrics(None, plain, duration=0.0)
    panel.update_position(10.0, (56, 189, 248), duration=0.0)
    render_fallback = panel.render().plain
    assert "── PLAIN LYRICS (UNSYNCHRONIZED) ──" in render_fallback
    assert "▸ " in render_fallback

    # Empty lyrics handling
    panel.set_lyrics(None, "")
    render_empty = panel.render().plain
    assert "No lyrics found" in render_empty


def test_youtube_metadata_query_cleaning():
    """Verify YouTube channel names, annotations, and title formatting are cleaned smartly."""
    client = LyricsClient()

    # 1. YouTube video title containing "Artist - Title" with channel name as artist
    q1 = client._build_search_queries("The Vibe Guide", "LOVIXX, STOSLIV - Don't tell your dreams (Lyrics)")
    # Must prioritize the song title directly rather than prepending the channel name
    assert "LOVIXX, STOSLIV - Don't tell your dreams" in q1
    assert q1[0] == "LOVIXX, STOSLIV - Don't tell your dreams"

    # 2. VEVO channel cleaning
    q2 = client._build_search_queries("TheKidLaroiVEVO", "STAY (Official Video)")
    assert any("TheKidLaroi - STAY" in q for q in q2)

    # 3. Topic channel cleaning
    q3 = client._build_search_queries("Shashwat Sachdev - Topic", "Naal Nachna")
    assert any("Shashwat Sachdev - Naal Nachna" in q for q in q3)


@patch("syncedlyrics.search")
def test_fast_providers_priority(mock_search):
    """Verify lyrics queries prioritize Lrclib as first provider."""
    mock_search.return_value = RAW_LRC

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = LyricsCache(Path(tmpdir))
        client = LyricsClient(cache)
        res = client.fetch_lyrics_sync("ArtistA", "TrackA")

        assert res is not None
        assert mock_search.called
        kwargs = mock_search.call_args[1]
        assert kwargs.get("providers") == ["Lrclib", "NetEase", "Megalobiz", "Musixmatch", "Genius"]


def test_synced_lyrics_intro_rendering():
    """Verify before the first lyric line timestamp, line 0 is not highlighted as active."""
    from soulwave.ui.widgets.lyrics_panel import LyricsPanelView

    panel = LyricsPanelView()
    panel.set_lyrics(RAW_LRC, None, duration=180.0)

    # First timestamp in RAW_LRC is at 00:05.20
    # At t=2.0s (during intro), line 0 must NOT be marked with '▸'
    panel.update_position(2.0, (56, 189, 248), duration=180.0)
    rendered_intro = panel.render().plain
    assert "Look at the stars" in rendered_intro
    assert "▸ Look at the stars" not in rendered_intro

    # At t=6.0s (after first timestamp), line 0 MUST be active with '▸'
    panel.update_position(6.0, (56, 189, 248), duration=180.0)
    rendered_active = panel.render().plain
    assert "▸ Look at the stars" in rendered_active

