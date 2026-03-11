"""
╔══════════════════════════════════════════════╗
║   IRON CLOCK  💪  HIIT Workout Timer         ║
║   Run:  python iron_clock.py                 ║
╚══════════════════════════════════════════════╝

A full HIIT session timer with:
  • Animated countdown arc that drains like a health bar
  • Pulse flash on every last-3-second warning
  • Auto-cycling through exercises + rest periods
  • Live session stats (calories est., total time, sets done)
  • Full session summary screen
  • Beep sounds synthesised with numpy — no audio files

Controls
────────
  SPACE        →  pause / resume
  N            →  skip to next exercise
  R            →  restart session
  ESC          →  quit
"""

import sys, math, time, random
import numpy as np
import pygame
import pygame.sndarray

# ── Audio ─────────────────────────────────────────────────────────────────────
SR = 44100

def _beep(freq=880, dur=0.08, vol=0.4):
    t   = np.linspace(0, dur, int(SR * dur), endpoint=False)
    wave = (np.sin(2 * math.pi * freq * t) * np.exp(-15 * t) * vol * 32767).astype(np.int16)
    snd  = pygame.sndarray.make_sound(wave)
    return snd

# ── Workout data ──────────────────────────────────────────────────────────────
EXERCISES = [
    {"name": "JUMPING JACKS",  "duration": 30, "emoji": "★", "kcal_rate": 8},
    {"name": "PUSH-UPS",       "duration": 30, "emoji": "▲", "kcal_rate": 7},
    {"name": "SQUAT JUMPS",    "duration": 30, "emoji": "◆", "kcal_rate": 10},
    {"name": "MOUNTAIN CLIMB", "duration": 30, "emoji": "▶", "kcal_rate": 9},
    {"name": "BURPEES",        "duration": 30, "emoji": "✦", "kcal_rate": 12},
    {"name": "HIGH KNEES",     "duration": 30, "emoji": "●", "kcal_rate": 9},
    {"name": "PLANK HOLD",     "duration": 40, "emoji": "■", "kcal_rate": 4},
    {"name": "TRICEP DIPS",    "duration": 30, "emoji": "◀", "kcal_rate": 6},
]
REST_DURATION = 10

# ── Colours ───────────────────────────────────────────────────────────────────
BG          = (8, 8, 12)
ACCENT      = (255, 60, 60)       # fierce red
ACCENT2     = (255, 140, 0)       # orange
REST_COL    = (40, 200, 120)      # green for rest
RING_TRACK  = (28, 24, 36)
WHITE       = (240, 235, 255)
DIM         = (90, 80, 110)
DARK        = (18, 15, 28)

W, H = 680, 560
CX, CY = W // 2, H // 2 - 20

# ── Helpers ───────────────────────────────────────────────────────────────────
def draw_arc(surface, color, cx, cy, radius, thickness, start_angle, end_angle, segments=200):
    """Draw a smooth thick arc using small line segments."""
    if end_angle <= start_angle:
        return
    pts = []
    for i in range(segments + 1):
        a = start_angle + (end_angle - start_angle) * i / segments
        pts.append((cx + math.cos(a) * radius, cy + math.sin(a) * radius))
    for i in range(len(pts) - 1):
        pygame.draw.line(surface, color, pts[i], pts[i+1], thickness)

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    pygame.mixer.pre_init(SR, -16, 1, 256)
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("IRON CLOCK 💪")
    clock  = pygame.time.Clock()

    beep_tick  = _beep(660, 0.06)
    beep_done  = _beep(1100, 0.18)
    beep_rest  = _beep(440, 0.20)

    font_huge  = pygame.font.SysFont("monospace", 88, bold=True)
    font_big   = pygame.font.SysFont("monospace", 26, bold=True)
    font_med   = pygame.font.SysFont("monospace", 18, bold=True)
    font_sm    = pygame.font.SysFont("monospace", 13)

    # ── Session state ─────────────────────────────────────────────────────────
    def make_session():
        return {
            "ex_idx":       0,
            "is_rest":      False,
            "time_left":    float(EXERCISES[0]["duration"]),
            "paused":       False,
            "done":         False,
            "total_elapsed":0.0,
            "total_kcal":   0.0,
            "sets_done":    0,
            "last_t":       time.time(),
            "pulse":        0.0,        # flash intensity 0-1
            "warned":       False,      # fired 3-sec warning beep
        }

    s = make_session()

    # ── Draw routines ─────────────────────────────────────────────────────────
    def draw_session():
        screen.fill(BG)

        ex      = EXERCISES[s["ex_idx"]]
        is_rest = s["is_rest"]
        total   = REST_DURATION if is_rest else ex["duration"]
        ratio   = max(0.0, s["time_left"] / total)
        accent  = REST_COL if is_rest else ACCENT

        # Pulse overlay
        if s["pulse"] > 0.01:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            a = int(s["pulse"] * 60)
            overlay.fill((*accent, a))
            screen.blit(overlay, (0, 0))

        # ── Outer glow ring (track) ──
        draw_arc(screen, RING_TRACK, CX, CY, 190, 22,
                 -math.pi / 2, -math.pi / 2 + 2 * math.pi)

        # ── Progress arc ──
        col = lerp_color(ACCENT2, accent, 1 - ratio)
        draw_arc(screen, col, CX, CY, 190, 22,
                 -math.pi / 2, -math.pi / 2 + 2 * math.pi * ratio)

        # ── Inner ring (thin) ──
        draw_arc(screen, (*col, 80), CX, CY, 168, 3,
                 -math.pi / 2, -math.pi / 2 + 2 * math.pi * ratio)

        # ── Countdown number ──
        secs = math.ceil(s["time_left"])
        num_surf = font_huge.render(f"{secs:02d}", True, WHITE)
        screen.blit(num_surf, num_surf.get_rect(center=(CX, CY - 10)))

        # ── Mode label ──
        mode_lbl = "REST" if is_rest else ex["emoji"] + " " + ex["name"]
        mode_surf = font_big.render(mode_lbl, True, accent)
        screen.blit(mode_surf, mode_surf.get_rect(center=(CX, CY + 90)))

        # ── Stats row ──
        pygame.draw.line(screen, (30, 26, 45), (40, H - 120), (W - 40, H - 120), 1)
        stats = [
            ("TIME",    f"{int(s['total_elapsed'] // 60):02d}:{int(s['total_elapsed'] % 60):02d}"),
            ("KCAL",    f"~{s['total_kcal']:.0f}"),
            ("SETS",    f"{s['sets_done']}/{len(EXERCISES)}"),
            ("NEXT",    "REST" if not is_rest else (EXERCISES[(s['ex_idx']+1) % len(EXERCISES)]["name"][:8])),
        ]
        col_w = (W - 80) // len(stats)
        for i, (label, val) in enumerate(stats):
            x = 40 + i * col_w + col_w // 2
            lbl_s = font_sm.render(label, True, DIM)
            val_s = font_med.render(val, True, WHITE)
            screen.blit(lbl_s, lbl_s.get_rect(center=(x, H - 100)))
            screen.blit(val_s, val_s.get_rect(center=(x, H - 80)))

        # ── Progress dots (exercise pipeline) ──
        dot_y = H - 38
        total_ex = len(EXERCISES)
        dot_gap  = 28
        start_x  = CX - (total_ex - 1) * dot_gap // 2
        for i in range(total_ex):
            dot_col = accent if i < s["ex_idx"] else (ACCENT if i == s["ex_idx"] else (35, 30, 50))
            r = 7 if i == s["ex_idx"] else 5
            pygame.draw.circle(screen, dot_col, (start_x + i * dot_gap, dot_y), r)

        # ── Controls hint ──
        hint = font_sm.render("SPACE pause  •  N skip  •  R restart  •  ESC quit", True, (50, 44, 70))
        screen.blit(hint, hint.get_rect(center=(CX, H - 12)))

        # ── Paused badge ──
        if s["paused"]:
            badge = font_big.render("⏸  PAUSED", True, ACCENT2)
            br    = badge.get_rect(center=(CX, 38))
            pygame.draw.rect(screen, DARK, br.inflate(24, 12), border_radius=8)
            screen.blit(badge, br)

        pygame.display.flip()

    def draw_summary():
        screen.fill(BG)
        title = font_big.render("SESSION COMPLETE  ✓", True, REST_COL)
        screen.blit(title, title.get_rect(center=(CX, 80)))

        lines = [
            ("TOTAL TIME",      f"{int(s['total_elapsed']//60):02d}:{int(s['total_elapsed']%60):02d}"),
            ("EXERCISES DONE",  f"{s['sets_done']} / {len(EXERCISES)}"),
            ("EST. CALORIES",   f"~{s['total_kcal']:.0f} kcal"),
        ]
        for i, (lbl, val) in enumerate(lines):
            y = 170 + i * 70
            pygame.draw.rect(screen, DARK, (CX - 200, y - 22, 400, 54), border_radius=10)
            l_s = font_sm.render(lbl,  True, DIM)
            v_s = font_big.render(val, True, WHITE)
            screen.blit(l_s, l_s.get_rect(center=(CX, y - 6)))
            screen.blit(v_s, v_s.get_rect(center=(CX, y + 18)))

        restart = font_med.render("Press  R  to restart   |   ESC to quit", True, DIM)
        screen.blit(restart, restart.get_rect(center=(CX, H - 40)))
        pygame.display.flip()

    # ── Game loop ─────────────────────────────────────────────────────────────
    while True:
        dt = clock.tick(60) / 1000.0

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if ev.key == pygame.K_SPACE and not s["done"]:
                    s["paused"] = not s["paused"]
                    s["last_t"] = time.time()
                if ev.key == pygame.K_r:
                    s = make_session()
                if ev.key == pygame.K_n and not s["done"] and not s["paused"]:
                    s["time_left"] = 0   # force advance

        if s["done"]:
            draw_summary()
            continue

        if not s["paused"]:
            now = time.time()
            elapsed = now - s["last_t"]
            s["last_t"] = now
            s["total_elapsed"] += elapsed

            # Calorie tick (only during exercise, not rest)
            if not s["is_rest"]:
                rate = EXERCISES[s["ex_idx"]]["kcal_rate"] / 60.0
                s["total_kcal"] += rate * elapsed

            s["time_left"] -= elapsed
            s["pulse"]      = max(0.0, s["pulse"] - dt * 4)

            # 3-second warning beep
            if s["time_left"] <= 3.0 and not s["warned"]:
                beep_tick.play()
                s["warned"] = True
                s["pulse"]  = 0.8

            # Advance to next phase
            if s["time_left"] <= 0:
                if s["is_rest"]:
                    # Move to next exercise
                    s["ex_idx"] += 1
                    if s["ex_idx"] >= len(EXERCISES):
                        s["done"] = True
                        beep_done.play()
                        continue
                    s["is_rest"]   = False
                    s["time_left"] = float(EXERCISES[s["ex_idx"]]["duration"])
                    s["warned"]    = False
                    beep_done.play()
                else:
                    # Start rest
                    s["sets_done"] += 1
                    s["is_rest"]    = True
                    s["time_left"]  = float(REST_DURATION)
                    s["warned"]     = False
                    s["pulse"]      = 1.0
                    beep_rest.play()

        draw_session()

if __name__ == "__main__":
    main()
