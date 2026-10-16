"""Tests for PixelSprite, MascotAnimator, and RoomScene."""

from soulwave.mascot.sprite import PixelSprite
from soulwave.mascot.frames import FrameLibrary, IDLE_F0
from soulwave.mascot.animator import MascotAnimator, MascotState
from soulwave.mascot.scene import RoomScene


def test_pixel_sprite_basic():
    sprite = PixelSprite(width=4, height=4)
    assert sprite.width == 4
    assert sprite.height == 4

    sprite.set_pixel(0, 0, (255, 0, 0))
    sprite.set_pixel(0, 1, (0, 255, 0))

    assert sprite.get_pixel(0, 0) == (255, 0, 0)
    assert sprite.get_pixel(0, 1) == (0, 255, 0)
    assert sprite.get_pixel(1, 1) is None


def test_half_block_rendering():
    sprite = PixelSprite(width=2, height=2)
    # top row: red, blue
    sprite.set_pixel(0, 0, (255, 0, 0))
    sprite.set_pixel(1, 0, (0, 0, 255))
    # bottom row: green, transparent
    sprite.set_pixel(0, 1, (0, 255, 0))

    rich_text = sprite.render_to_rich_text()
    plain = rich_text.plain
    # Should contain half-block character
    assert "▀" in plain or "▄" in plain


def test_mascot_animator_tempo():
    anim = MascotAnimator()
    anim.set_track("Yellow", "Coldplay")
    bpm1 = anim.bpm
    assert 85.0 <= bpm1 <= 125.0

    # Same track should produce identical BPM
    anim.set_track("Yellow", "Coldplay")
    assert anim.bpm == bpm1

    # Different track should have its own deterministic tempo
    anim.set_track("Midnight Coffee", "Soulwave Chill")
    bpm2 = anim.bpm
    assert 85.0 <= bpm2 <= 125.0


def test_mascot_state_transitions():
    anim = MascotAnimator()
    anim.update_playback_state(is_playing=True, is_connected=True)
    assert anim.state == MascotState.PLAYING

    # Disconnected or no song -> sleeping state
    anim.update_playback_state(is_playing=False, is_connected=False)
    assert anim.state == MascotState.SLEEPING

    anim.update_playback_state(is_playing=False, is_connected=True, has_track=False)
    assert anim.state == MascotState.SLEEPING

    anim.trigger_reaction(MascotState.VOL_UP, duration=0.5)
    assert anim.state == MascotState.VOL_UP

    sprite = anim.tick()
    assert sprite.width > 0
    assert sprite.height > 0


def test_room_scene_particles():
    scene = RoomScene(width=30, height=10)
    assert len(scene.particles) == 0

    scene.spawn_note((100, 200, 250))
    assert len(scene.particles) == 1

    scene.update(is_playing=True, is_paused=False)
    # Particles update coordinates
    assert scene.particles[0].lifetime > 0


def test_room_scene_ambient_symbols():
    scene = RoomScene(width=34, height=12)
    # 2-3 subtle symbols anchored outside mascot
    assert 2 <= len(scene.ambient_symbols) <= 3
    for sym in scene.ambient_symbols:
        assert sym["char"] in ["♪", "♫", "✧", "✦"]
        # Positioned outside center mascot area (x < 7 or x > 26)
        assert sym["base_x"] < 7.0 or sym["base_x"] > 26.0

    # Advance when playing
    init_phase = scene._ambient_phase
    scene.update(is_playing=True, is_paused=False)
    assert scene._ambient_phase > init_phase
    assert scene._is_playing is True

    # When paused: slower advance and paused flag set
    p_phase = scene._ambient_phase
    scene.update(is_playing=False, is_paused=True)
    assert scene._is_paused is True
    assert scene._ambient_phase > p_phase

    # When idle: sleeping state
    scene.update(is_playing=False, is_paused=False, is_idle=True)
    assert scene._is_idle is True
