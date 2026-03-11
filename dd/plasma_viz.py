"""
╔══════════════════════════════════════╗
║   PLASMA STORM  — visual demo        ║
║   Run:  python plasma_viz.py         ║
║   Quit: ESC or close window          ║
╚══════════════════════════════════════╝

A real-time plasma / lava-lamp effect built with pure math.
No images, no assets — every pixel is computed live from
overlapping sine waves mapped through a fiery colour palette.

Controls
────────
  SPACE   →  cycle colour palette  (Fire / Ice / Acid / Vaporwave)
  ESC     →  quit
"""

import math, sys, time
import pygame

# ── Config ────────────────────────────────────────────────────────────────────
W, H   = 600, 600          # window size
SCALE  = 4                 # pixel block size  (lower = sharper but slower)
COLS   = W // SCALE
ROWS   = H // SCALE
FPS    = 60
TITLE  = "PLASMA STORM"

# ── Colour palettes (256 RGB entries each) ────────────────────────────────────
def _pal_fire():
    p = []
    for i in range(256):
        t = i / 255
        r = int(min(255, t * 3.0 * 255))
        g = int(min(255, max(0, t * 3.0 - 1.0) * 255))
        b = int(min(255, max(0, t * 3.0 - 2.0) * 255))
        p.append((r, g, b))
    return p

def _pal_ice():
    p = []
    for i in range(256):
        t = i / 255
        r = int(t * 80)
        g = int(t * 200)
        b = int(128 + t * 127)
        p.append((r, g, b))
    return p

def _pal_acid():
    p = []
    for i in range(256):
        t = i / 255
        r = int((math.sin(t * math.pi * 2) * 0.5 + 0.5) * 255)
        g = int((math.sin(t * math.pi * 2 + 2) * 0.5 + 0.5) * 255)
        b = int((math.sin(t * math.pi * 2 + 4) * 0.5 + 0.5) * 80)
        p.append((r, g, b))
    return p

def _pal_vaporwave():
    p = []
    for i in range(256):
        t = i / 255
        r = int((math.sin(t * math.pi + 0.0) * 0.5 + 0.5) * 255)
        g = int((math.sin(t * math.pi + 1.0) * 0.5 + 0.5) * 80)
        b = int((math.sin(t * math.pi + 2.0) * 0.5 + 0.5) * 255)
        p.append((r, g, b))
    return p

PALETTES = [_pal_fire(), _pal_ice(), _pal_acid(), _pal_vaporwave()]
PAL_NAMES = ["🔥 FIRE", "❄️  ICE", "☢️  ACID", "🌸 VAPORWAVE"]

# ── Plasma function ───────────────────────────────────────────────────────────
def plasma_value(x: int, y: int, t: float) -> int:
    cx = x + 0.5 * math.sin(t / 5)
    cy = y + 0.5 * math.cos(t / 3)
    v  = (math.sin(x * 0.3 + t)
        + math.sin(0.3 * (x * math.sin(t / 2) + y * math.cos(t / 3)) + t)
        + math.sin(math.sqrt(cx * cx + cy * cy + 1) + t)
        + math.sin(math.sqrt(x * x + y * y + 1)))
    return int((v + 4) / 8 * 255) % 256

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption(TITLE)
    clock  = pygame.time.Clock()

    # Surface we draw blocks onto
    surf   = pygame.Surface((W, H))

    pal_idx = 0
    font    = pygame.font.SysFont("monospace", 14, bold=True)

    # Pre-compute normalised grid coordinates once
    xs = [x / COLS for x in range(COLS)]
    ys = [y / ROWS for y in range(ROWS)]

    t0 = time.time()

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if ev.key == pygame.K_SPACE:
                    pal_idx = (pal_idx + 1) % len(PALETTES)

        t   = time.time() - t0
        pal = PALETTES[pal_idx]

        # Draw plasma
        for xi, xn in enumerate(xs):
            for yi, yn in enumerate(ys):
                v   = plasma_value(xn * 6, yn * 6, t)
                col = pal[v]
                pygame.draw.rect(surf, col,
                    (xi * SCALE, yi * SCALE, SCALE, SCALE))

        screen.blit(surf, (0, 0))

        # HUD overlay
        label = font.render(
            f"  {PAL_NAMES[pal_idx]}  |  SPACE: next palette  |  ESC: quit  ",
            True, (255, 255, 255), (0, 0, 0)
        )
        screen.blit(label, (8, 8))

        fps_lbl = font.render(f"{clock.get_fps():.0f} fps", True, (200, 200, 200))
        screen.blit(fps_lbl, (W - fps_lbl.get_width() - 8, 8))

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
