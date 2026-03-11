"""
╔══════════════════════════════════════════════╗
║   SYNTHWAVE SEQUENCER  🎹                    ║
║   An 8-step drum + melody looper             ║
║                                              ║
║   Run:  python synthwave_sequencer.py        ║
╚══════════════════════════════════════════════╝

A mini DAW in ~200 lines.
• 8-step grid for 4 instruments (kick, snare, hihat, synth melody)
• Click cells to toggle beats on/off
• Synth melody lets you pick pitch per step
• BPM slider
• Pure numpy sine/noise synthesis — no audio files needed

Controls
────────
  Click cell     → toggle beat on/off
  Right-click    → (melody row) cycle pitch  C D E G A
  SPACE          → play / pause
  R              → randomise pattern
  C              → clear all
  ↑ / ↓          → BPM +10 / -10
  ESC            → quit
"""

import sys, math, random, time
import numpy as np
import pygame
import pygame.sndarray

# ── Audio constants ───────────────────────────────────────────────────────────
SAMPLE_RATE = 44100
CHANNELS    = 1        # mono
BIT_DEPTH   = 16
AMP         = 28000

# ── Synthesis helpers ─────────────────────────────────────────────────────────
def _make_sound(arr: np.ndarray) -> pygame.mixer.Sound:
    arr = np.clip(arr, -32767, 32767).astype(np.int16)
    if CHANNELS == 2:
        arr = np.column_stack([arr, arr])
    snd = pygame.sndarray.make_sound(arr)
    return snd

def sine_wave(freq: float, dur: float, decay: float = 6.0) -> np.ndarray:
    n   = int(SAMPLE_RATE * dur)
    t   = np.linspace(0, dur, n, endpoint=False)
    env = np.exp(-decay * t)
    return (np.sin(2 * math.pi * freq * t) * env * AMP).astype(np.int16)

def kick(dur=0.45) -> np.ndarray:
    n   = int(SAMPLE_RATE * dur)
    t   = np.linspace(0, dur, n, endpoint=False)
    freq = 120 * np.exp(-30 * t)          # pitch drop
    env  = np.exp(-8 * t)
    return (np.sin(2 * math.pi * np.cumsum(freq) / SAMPLE_RATE) * env * AMP).astype(np.int16)

def snare(dur=0.2) -> np.ndarray:
    n    = int(SAMPLE_RATE * dur)
    t    = np.linspace(0, dur, n, endpoint=False)
    noise = np.random.uniform(-1, 1, n)
    tone  = np.sin(2 * math.pi * 200 * t)
    env   = np.exp(-20 * t)
    return ((noise * 0.7 + tone * 0.3) * env * AMP).astype(np.int16)

def hihat(dur=0.08) -> np.ndarray:
    n   = int(SAMPLE_RATE * dur)
    t   = np.linspace(0, dur, n, endpoint=False)
    noise = np.random.uniform(-1, 1, n)
    env   = np.exp(-40 * t)
    return (noise * env * AMP * 0.5).astype(np.int16)

# Note frequencies (one octave)
NOTES     = {"C": 261.63, "D": 293.66, "E": 329.63, "G": 392.00, "A": 440.00}
NOTE_KEYS = list(NOTES.keys())

def synth_note(note: str, dur=0.25) -> np.ndarray:
    freq = NOTES[note]
    n    = int(SAMPLE_RATE * dur)
    t    = np.linspace(0, dur, n, endpoint=False)
    # Slightly detuned double oscillator for that retro synth warmth
    osc  = (np.sin(2 * math.pi * freq * t) * 0.6
          + np.sin(2 * math.pi * freq * 1.005 * t) * 0.4)
    env  = np.exp(-5 * t)
    return (osc * env * AMP * 0.8).astype(np.int16)

# ── Colours ───────────────────────────────────────────────────────────────────
BG        = (10,  8, 20)
GRID_BG   = (22, 18, 40)
ACTIVE    = [(255, 80, 80), (255, 200, 60), (60, 220, 255), (160, 80, 255)]
INACTIVE  = [(50, 25, 35),  (50, 42, 20),  (15, 45, 55),   (32, 18, 55)]
CURSOR_C  = (255, 255, 255)
TEXT_C    = (180, 160, 220)
LABEL_C   = (220, 200, 255)

# ── Layout ────────────────────────────────────────────────────────────────────
W, H      = 780, 460
STEPS     = 8
ROWS      = 4                    # kick, snare, hihat, melody
ROW_NAMES = ["KICK", "SNARE", "HIHAT", "SYNTH"]
CELL_W    = 68
CELL_H    = 60
GRID_X    = 140
GRID_Y    = 80
GAP       = 8

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    pygame.mixer.pre_init(SAMPLE_RATE, -BIT_DEPTH, CHANNELS, 512)
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption("SYNTHWAVE SEQUENCER 🎹")
    screen = pygame.display.set_mode((W, H))
    clock  = pygame.time.Clock()

    font_big  = pygame.font.SysFont("monospace", 15, bold=True)
    font_sm   = pygame.font.SysFont("monospace", 12)
    font_note = pygame.font.SysFont("monospace", 13, bold=True)

    # Pre-bake sounds
    sounds = [
        _make_sound(kick()),
        _make_sound(snare()),
        _make_sound(hihat()),
    ]
    note_sounds = {n: _make_sound(synth_note(n)) for n in NOTE_KEYS}

    # State
    grid      = [[False] * STEPS for _ in range(ROWS)]
    pitches   = [0] * STEPS          # index into NOTE_KEYS for melody row
    bpm       = 120
    playing   = False
    step      = 0
    last_tick = time.time()

    def beat_dur():
        return 60 / bpm / 2          # 16th notes

    def fire_step(s):
        for r in range(ROWS - 1):
            if grid[r][s]:
                sounds[r].play()
        if grid[3][s]:
            note_sounds[NOTE_KEYS[pitches[s]]].play()

    def cell_rect(r, s):
        x = GRID_X + s * (CELL_W + GAP)
        y = GRID_Y + r * (CELL_H + GAP)
        return pygame.Rect(x, y, CELL_W, CELL_H)

    def randomise():
        for r in range(ROWS):
            for s in range(STEPS):
                # drums: sparser;  melody: moderate fill
                prob = [0.35, 0.25, 0.45, 0.4][r]
                grid[r][s] = random.random() < prob
        for s in range(STEPS):
            pitches[s] = random.randint(0, len(NOTE_KEYS) - 1)

    # ── Draw helpers ──────────────────────────────────────────────────────────
    def draw():
        screen.fill(BG)

        # Title
        title = font_big.render("▶  SYNTHWAVE SEQUENCER", True, LABEL_C)
        screen.blit(title, (GRID_X, 22))

        # BPM
        bpm_txt = font_big.render(f"BPM: {bpm}  [↑/↓]", True, TEXT_C)
        screen.blit(bpm_txt, (GRID_X + 420, 22))

        state_txt = font_big.render(
            "■ PAUSED  [SPACE]" if not playing else "● PLAYING [SPACE]",
            True, (255, 80, 80) if playing else (120, 100, 160)
        )
        screen.blit(state_txt, (GRID_X, 46))

        hint = font_sm.render("R=random  C=clear  Right-click synth=pitch", True, (90, 80, 110))
        screen.blit(hint, (GRID_X + 270, 48))

        for r in range(ROWS):
            # Row label
            lbl = font_big.render(ROW_NAMES[r], True, LABEL_C)
            screen.blit(lbl, (10, GRID_Y + r * (CELL_H + GAP) + CELL_H // 2 - 8))

            for s in range(STEPS):
                rect = cell_rect(r, s)
                on   = grid[r][s]
                col  = ACTIVE[r] if on else INACTIVE[r]

                # Highlight current step
                if playing and s == step:
                    pygame.draw.rect(screen, (255, 255, 255), rect.inflate(6, 6), border_radius=8)

                pygame.draw.rect(screen, col, rect, border_radius=7)

                # Melody: show note name
                if r == 3 and on:
                    note_lbl = font_note.render(NOTE_KEYS[pitches[s]], True, (20, 10, 40))
                    screen.blit(note_lbl, note_lbl.get_rect(center=rect.center))

                # Step number on top row
                if r == 0:
                    n_lbl = font_sm.render(str(s + 1), True, (80, 70, 100))
                    screen.blit(n_lbl, (rect.x + CELL_W // 2 - 5, GRID_Y - 18))

        # Bottom bar
        pygame.draw.line(screen, (40, 35, 65), (0, H - 40), (W, H - 40))
        tip = font_sm.render(
            "Click = toggle beat   |   Right-click SYNTH row = cycle pitch   |   ESC = quit",
            True, (70, 60, 95)
        )
        screen.blit(tip, (20, H - 26))

        pygame.display.flip()

    # ── Loop ──────────────────────────────────────────────────────────────────
    while True:
        now = time.time()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if ev.key == pygame.K_SPACE:
                    playing = not playing
                    step = 0
                    last_tick = now
                if ev.key == pygame.K_r:
                    randomise()
                if ev.key == pygame.K_c:
                    grid = [[False] * STEPS for _ in range(ROWS)]
                if ev.key == pygame.K_UP:
                    bpm = min(240, bpm + 10)
                if ev.key == pygame.K_DOWN:
                    bpm = max(40,  bpm - 10)

            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                for r in range(ROWS):
                    for s in range(STEPS):
                        if cell_rect(r, s).collidepoint(mx, my):
                            if ev.button == 1:
                                grid[r][s] = not grid[r][s]
                            elif ev.button == 3 and r == 3:
                                pitches[s] = (pitches[s] + 1) % len(NOTE_KEYS)
                                grid[r][s] = True   # auto-enable on pitch change

        # Advance sequencer
        if playing and now - last_tick >= beat_dur():
            fire_step(step)
            step = (step + 1) % STEPS
            last_tick = now

        draw()
        clock.tick(120)

if __name__ == "__main__":
    main()
