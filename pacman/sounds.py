"""SoundManager: tiny, dependency-light sound effects.

Rather than ship binary audio files, we *synthesise* short retro blips at
start-up with NumPy and hand them to pygame's mixer. This keeps the project to
a single ``pip install`` and makes the effects easy to tweak in code.

Everything here degrades gracefully: if NumPy is missing, or the machine has no
audio device, the manager simply becomes silent instead of crashing the game.
"""

import pygame

try:
    import numpy as np
    _HAVE_NUMPY = True
except ImportError:  # pragma: no cover - optional dependency
    _HAVE_NUMPY = False


class SoundManager:
    """Builds and plays the game's synthesised sound effects."""

    SAMPLE_RATE = 22050

    def __init__(self):
        self.enabled = False
        self._sounds = {}
        self._chomp_toggle = False

        if not _HAVE_NUMPY:
            return

        # Initialise the mixer in mono so our 1-D arrays map cleanly to samples.
        try:
            pygame.mixer.pre_init(self.SAMPLE_RATE, -16, 1, 512)
            pygame.mixer.init()
        except pygame.error:
            # No audio device (common on CI / headless machines): stay silent.
            return

        # Synthesising the effects can still fail on exotic audio backends, so
        # guard it: worst case we run silently rather than crash.
        try:
            self._build_sounds()
            self.enabled = True
        except Exception:
            self.enabled = False

    # -- synthesis helpers -------------------------------------------------
    def _tone(self, frequency, duration, volume=0.4, wave="square"):
        """Return a pygame Sound for a single tone with a click-free envelope."""
        n = int(self.SAMPLE_RATE * duration)
        t = np.arange(n) / self.SAMPLE_RATE
        if wave == "square":
            raw = np.sign(np.sin(2 * np.pi * frequency * t))
        else:  # sine
            raw = np.sin(2 * np.pi * frequency * t)
        # A short attack/release fade stops the speakers from popping.
        env = np.ones(n)
        fade = max(1, int(n * 0.15))
        env[:fade] = np.linspace(0, 1, fade)
        env[-fade:] = np.linspace(1, 0, fade)
        samples = (raw * env * volume * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(samples)

    def _sweep(self, f_start, f_end, duration, volume=0.4, wave="square"):
        """A tone that glides from one frequency to another."""
        n = int(self.SAMPLE_RATE * duration)
        t = np.arange(n) / self.SAMPLE_RATE
        freqs = np.linspace(f_start, f_end, n)
        phase = 2 * np.pi * np.cumsum(freqs) / self.SAMPLE_RATE
        raw = np.sign(np.sin(phase)) if wave == "square" else np.sin(phase)
        env = np.ones(n)
        fade = max(1, int(n * 0.1))
        env[:fade] = np.linspace(0, 1, fade)
        env[-fade:] = np.linspace(1, 0, fade)
        samples = (raw * env * volume * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(samples)

    def _sequence(self, notes, volume=0.4):
        """Concatenate several (frequency, duration) notes into one Sound."""
        chunks = []
        for freq, dur in notes:
            n = int(self.SAMPLE_RATE * dur)
            t = np.arange(n) / self.SAMPLE_RATE
            raw = np.sign(np.sin(2 * np.pi * freq * t))
            env = np.ones(n)
            fade = max(1, int(n * 0.1))
            env[:fade] = np.linspace(0, 1, fade)
            env[-fade:] = np.linspace(1, 0, fade)
            chunks.append(raw * env)
        samples = (np.concatenate(chunks) * volume * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(samples)

    def _build_sounds(self):
        """Create every effect once, up front."""
        # Two alternating blips give the trademark "waka waka" chomp.
        self._sounds["chomp_a"] = self._tone(420, 0.045, volume=0.30)
        self._sounds["chomp_b"] = self._tone(310, 0.045, volume=0.30)
        self._sounds["power"] = self._sequence(
            [(330, 0.07), (440, 0.07), (550, 0.07), (660, 0.09)], volume=0.35)
        self._sounds["eat_ghost"] = self._sweep(300, 1000, 0.30, volume=0.4)
        self._sounds["death"] = self._sweep(700, 90, 0.9, volume=0.45)
        self._sounds["fruit"] = self._sequence(
            [(660, 0.06), (880, 0.06), (990, 0.10)], volume=0.35)
        self._sounds["extra_life"] = self._sequence(
            [(660, 0.08), (880, 0.08), (1320, 0.12)], volume=0.4)
        self._sounds["intro"] = self._sequence(
            [(523, 0.12), (659, 0.12), (784, 0.12), (1047, 0.18)], volume=0.4)

    # -- playback ----------------------------------------------------------
    def _play(self, key):
        if not self.enabled:
            return
        sound = self._sounds.get(key)
        if sound is not None:
            sound.play()

    def play_chomp(self):
        """Alternate the two blips so eating sounds like the arcade."""
        self._play("chomp_a" if self._chomp_toggle else "chomp_b")
        self._chomp_toggle = not self._chomp_toggle

    def play_power(self):
        self._play("power")

    def play_eat_ghost(self):
        self._play("eat_ghost")

    def play_death(self):
        self._play("death")

    def play_fruit(self):
        self._play("fruit")

    def play_extra_life(self):
        self._play("extra_life")

    def play_intro(self):
        self._play("intro")
