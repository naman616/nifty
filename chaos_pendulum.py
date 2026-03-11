"""
╔══════════════════════════════════════════════════════════╗
║   CHAOS PENDULUM  ⚖️   Double Pendulum Simulator         ║
║   Run:  python chaos_pendulum.py                         ║
╚══════════════════════════════════════════════════════════╝

The double pendulum is the textbook example of CHAOS THEORY.
Two pendulums start at nearly identical angles — their paths
diverge completely within seconds. This is the "butterfly
effect" made visible.

Physics
───────
  Equations of motion derived from the Lagrangian:
  Uses 4th-order Runge-Kutta (RK4) integration — the gold
  standard numerical method for ODEs.

  State vector per pendulum:  [θ1, ω1, θ2, ω2]
  where θ = angle, ω = angular velocity

  Full Lagrangian EOM (exact, no small-angle approx):
    dω1/dt = f(θ1, θ2, ω1, ω2, m1, m2, L1, L2, g)
    dω2/dt = g(θ1, θ2, ω1, ω2, m1, m2, L1, L2, g)

Controls
────────
  DRAG bob      →  reposition initial angle
  SPACE         →  pause / resume
  R             →  reset with new random offset
  T             →  toggle trails on/off
  E             →  toggle energy graph
  +  /  -       →  simulation speed
  1-4           →  preset scenarios
  ESC           →  quit
"""

import sys, math, random
import numpy as np
import pygame

# ── Window & colours ──────────────────────────────────────────────────────────
W, H        = 1000, 680
PIVOT       = (340, 200)          # pendulum anchor point

# Clean educational palette
BG          = (245, 243, 238)     # warm off-white
BG2         = (235, 232, 225)
GRID_C      = (210, 207, 200)
ROD_C       = (60,  60,  70)
BOB1_C      = (30,  90, 200)      # blue - bob 1
BOB2_C      = (220, 50,  50)      # red  - bob 2
GHOST_C     = (130, 170, 220)     # ghost pendulum
GHOST2_C    = (220, 150, 150)
TRAIL_COLS  = [(30, 90, 200), (220, 50, 50)]
TEXT_C      = (40,  40,  50)
DIM_C       = (140, 138, 130)
ACCENT      = (255, 140,   0)
PANEL_BG    = (255, 253, 248)
PANEL_BD    = (200, 197, 190)
GREEN_C     = (40, 160, 80)
ENERGY_C    = (255, 140, 0)

# ── Physics constants ─────────────────────────────────────────────────────────
G           = 9.81
PIX_PER_M   = 130.0       # pixels per metre

PRESETS = {
    "1": {"name": "Classic Chaos",    "t1": 120, "t2": -20,  "L1": 1.0, "L2": 1.0, "m1": 1.0, "m2": 1.0},
    "2": {"name": "Near-Vertical",    "t1": 179, "t2": 178,  "L1": 1.0, "L2": 1.0, "m1": 1.0, "m2": 1.0},
    "3": {"name": "Heavy Lower Bob",  "t1": 90,  "t2": 45,   "L1": 0.9, "L2": 0.9, "m1": 1.0, "m2": 3.0},
    "4": {"name": "Long-Short Arms",  "t1": 100, "t2": 60,   "L1": 1.2, "L2": 0.6, "m1": 1.0, "m2": 1.0},
}

# ── RK4 Lagrangian equations of motion ────────────────────────────────────────
def derivatives(state, m1, m2, L1, L2):
    t1, w1, t2, w2 = state
    dt   = t2 - t1
    denom1 = (m1 + m2) * L1 - m2 * L1 * math.cos(dt) ** 2
    denom2 = (L2 / L1) * denom1

    dw1 = (m2 * L1 * w1**2 * math.sin(dt) * math.cos(dt)
           + m2 * G  * math.sin(t2) * math.cos(dt)
           + m2 * L2 * w2**2 * math.sin(dt)
           - (m1 + m2) * G * math.sin(t1)) / denom1

    dw2 = (-m2 * L2 * w2**2 * math.sin(dt) * math.cos(dt)
           + (m1 + m2) * G * math.sin(t1) * math.cos(dt)
           - (m1 + m2) * L1 * w1**2 * math.sin(dt)
           - (m1 + m2) * G * math.sin(t2)) / denom2

    return (w1, dw1, w2, dw2)

def rk4_step(state, dt, m1, m2, L1, L2):
    k1 = derivatives(state,                          m1, m2, L1, L2)
    k2 = derivatives(tuple(state[i]+dt/2*k1[i] for i in range(4)), m1, m2, L1, L2)
    k3 = derivatives(tuple(state[i]+dt/2*k2[i] for i in range(4)), m1, m2, L1, L2)
    k4 = derivatives(tuple(state[i]+dt*k3[i]   for i in range(4)), m1, m2, L1, L2)
    return tuple(state[i] + dt/6*(k1[i]+2*k2[i]+2*k3[i]+k4[i]) for i in range(4))

# ── Energy calculation ─────────────────────────────────────────────────────────
def total_energy(state, m1, m2, L1, L2):
    t1, w1, t2, w2 = state
    # Kinetic
    v1sq = (L1*w1)**2
    v2sq = (L1*w1)**2 + (L2*w2)**2 + 2*L1*L2*w1*w2*math.cos(t1-t2)
    KE   = 0.5*m1*v1sq + 0.5*m2*v2sq
    # Potential (pivot = zero)
    PE   = -m1*G*L1*math.cos(t1) - m2*G*(L1*math.cos(t1)+L2*math.cos(t2))
    return KE + PE

# ── Pendulum class ─────────────────────────────────────────────────────────────
class Pendulum:
    def __init__(self, t1_deg, t2_deg, L1, L2, m1, m2, color1, color2):
        self.L1, self.L2 = L1, L2
        self.m1, self.m2 = m1, m2
        self.c1, self.c2 = color1, color2
        self.state = (math.radians(t1_deg), 0.0, math.radians(t2_deg), 0.0)
        self.trail = []
        self.energy_hist = []

    def bob_positions(self):
        t1, _, t2, _ = self.state
        p1x = PIVOT[0] + self.L1 * PIX_PER_M * math.sin(t1)
        p1y = PIVOT[1] + self.L1 * PIX_PER_M * math.cos(t1)
        p2x = p1x      + self.L2 * PIX_PER_M * math.sin(t2)
        p2y = p1y      + self.L2 * PIX_PER_M * math.cos(t2)
        return (int(p1x), int(p1y)), (int(p2x), int(p2y))

    def step(self, dt):
        self.state = rk4_step(self.state, dt, self.m1, self.m2, self.L1, self.L2)
        _, b2 = self.bob_positions()
        self.trail.append(b2)
        if len(self.trail) > 900:
            self.trail.pop(0)
        E = total_energy(self.state, self.m1, self.m2, self.L1, self.L2)
        self.energy_hist.append(E)
        if len(self.energy_hist) > 300:
            self.energy_hist.pop(0)

    def draw(self, surf, show_trail=True, alpha_trail=True):
        b1, b2 = self.bob_positions()
        r1 = max(8, int(self.m1 * 10))
        r2 = max(8, int(self.m2 * 10))

        # Trail
        if show_trail and len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                t  = i / len(self.trail)
                a  = int(t * 200)
                c  = (*self.c2[:3], a)
                pygame.draw.line(surf, self.c2, self.trail[i-1], self.trail[i],
                                 max(1, int(t * 2)))

        # Rods
        pygame.draw.line(surf, ROD_C, PIVOT, b1, 3)
        pygame.draw.line(surf, ROD_C, b1,    b2, 3)

        # Pivot
        pygame.draw.circle(surf, ROD_C, PIVOT, 6)
        pygame.draw.circle(surf, BG,    PIVOT, 3)

        # Bobs with shadow
        pygame.draw.circle(surf, (180,175,165), (b1[0]+3, b1[1]+3), r1)
        pygame.draw.circle(surf, self.c1,        b1,                 r1)
        pygame.draw.circle(surf, (255,255,255),  (b1[0]-r1//3, b1[1]-r1//3), max(2, r1//3))

        pygame.draw.circle(surf, (180,175,165), (b2[0]+3, b2[1]+3), r2)
        pygame.draw.circle(surf, self.c2,        b2,                 r2)
        pygame.draw.circle(surf, (255,255,255),  (b2[0]-r2//3, b2[1]-r2//3), max(2, r2//3))

# ── Info panel ─────────────────────────────────────────────────────────────────
def draw_panel(surf, pend, ghost, t_elapsed, paused, show_energy, speed, preset_name, fonts):
    font_title, font_med, font_sm, font_tiny = fonts
    px, py = 680, 20
    pw, ph = 300, H - 40

    pygame.draw.rect(surf, PANEL_BG, (px, py, pw, ph), border_radius=10)
    pygame.draw.rect(surf, PANEL_BD, (px, py, pw, ph), 1, border_radius=10)

    def txt(s, x, y, f=None, col=TEXT_C):
        surf.blit((f or font_sm).render(s, True, col), (x, y))

    def rule(y):
        pygame.draw.line(surf, PANEL_BD, (px+12, y), (px+pw-12, y), 1)

    y = py + 16
    txt("DOUBLE PENDULUM", px+14, y, font_title, TEXT_C);  y += 26
    txt("Chaos Theory Demo", px+14, y, font_tiny, DIM_C);  y += 26
    rule(y); y += 10

    # Preset name
    txt(f"Scenario: {preset_name}", px+14, y, font_sm, ACCENT); y += 22

    # State
    t1_d = math.degrees(pend.state[0]) % 360
    t2_d = math.degrees(pend.state[2]) % 360
    w1   = pend.state[1]
    w2   = pend.state[3]
    txt(f"θ₁ = {t1_d:6.1f}°    ω₁ = {w1:+5.2f} rad/s", px+14, y, font_tiny); y += 18
    txt(f"θ₂ = {t2_d:6.1f}°    ω₂ = {w2:+5.2f} rad/s", px+14, y, font_tiny); y += 18

    # Divergence
    dt1 = abs(pend.state[0] - ghost.state[0])
    dt2 = abs(pend.state[2] - ghost.state[2])
    div = math.sqrt(dt1**2 + dt2**2)
    div_col = GREEN_C if div < 0.5 else (ACCENT if div < 2 else (200, 40, 40))
    txt(f"Divergence: {div:.4f} rad", px+14, y, font_tiny, div_col); y += 22

    rule(y); y += 10

    # Parameters
    txt("Parameters", px+14, y, font_sm, DIM_C); y += 20
    txt(f"L₁ = {pend.L1:.2f} m   L₂ = {pend.L2:.2f} m", px+14, y, font_tiny); y += 16
    txt(f"m₁ = {pend.m1:.1f} kg  m₂ = {pend.m2:.1f} kg", px+14, y, font_tiny); y += 16
    txt(f"g  = {G:.2f} m/s²", px+14, y, font_tiny); y += 22

    rule(y); y += 10

    # Energy graph
    txt("Energy (conservation check)", px+14, y, font_sm, DIM_C); y += 18
    gx, gy, gw, gh = px+14, y, pw-28, 55
    pygame.draw.rect(surf, BG2, (gx, gy, gw, gh), border_radius=4)
    pygame.draw.rect(surf, PANEL_BD, (gx, gy, gw, gh), 1, border_radius=4)

    if len(pend.energy_hist) > 2:
        emin = min(pend.energy_hist)
        emax = max(pend.energy_hist)
        erange = max(emax - emin, 0.001)
        pts = []
        for i, e in enumerate(pend.energy_hist):
            ex_ = gx + int(i / len(pend.energy_hist) * gw)
            ey_ = gy + gh - int((e - emin) / erange * (gh - 4)) - 2
            pts.append((ex_, ey_))
        if len(pts) > 1:
            pygame.draw.lines(surf, ENERGY_C, False, pts, 2)

    y += gh + 8
    txt("Should be flat → energy conserved", px+14, y, font_tiny, DIM_C); y += 22

    rule(y); y += 10

    # Chaos explainer
    txt("What is Chaos?", px+14, y, font_sm, DIM_C); y += 18
    blurb = [
        "The ghost pendulum (faded)",
        "starts just 0.01° different.",
        "Within seconds, paths diverge",
        "completely — this is the",
        "butterfly effect in action.",
        "",
        "Not random. Deterministic",
        "but unpredictable.",
    ]
    for line in blurb:
        txt(line, px+14, y, font_tiny, (100, 98, 90)); y += 15

    y += 6; rule(y); y += 10

    # Controls
    controls = [
        ("SPACE",  "pause/resume"),
        ("R",      "reset"),
        ("T",      "toggle trails"),
        ("+/-",    "speed"),
        ("1-4",    "presets"),
    ]
    txt("Controls", px+14, y, font_sm, DIM_C); y += 18
    for k, v in controls:
        txt(f"  {k:<6} {v}", px+14, y, font_tiny, (110, 108, 100)); y += 14

    # Status bar
    status = f"{'⏸ PAUSED' if paused else '▶ RUNNING'}   t={t_elapsed:.1f}s   ×{speed}"
    s_col  = (200, 80, 30) if paused else GREEN_C
    txt(status, px+14, py+ph-26, font_tiny, s_col)

# ── Main ───────────────────────────────────────────────────────────────────────
def make_pendulums(preset_key="1", extra_deg=0.01):
    p  = PRESETS[preset_key]
    A  = Pendulum(p["t1"],             p["t2"],             p["L1"], p["L2"], p["m1"], p["m2"], BOB1_C, BOB2_C)
    B  = Pendulum(p["t1"]+extra_deg,   p["t2"]+extra_deg,   p["L1"], p["L2"], p["m1"], p["m2"], GHOST_C, GHOST2_C)
    return A, B, p["name"]

def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("CHAOS PENDULUM  ⚖️")
    clock  = pygame.time.Clock()

    font_title = pygame.font.SysFont("serif",   15, bold=True)
    font_med   = pygame.font.SysFont("monospace", 14, bold=True)
    font_sm    = pygame.font.SysFont("monospace", 13)
    font_tiny  = pygame.font.SysFont("monospace", 11)
    fonts      = (font_title, font_med, font_sm, font_tiny)

    preset_key    = "1"
    pend, ghost, preset_name = make_pendulums(preset_key)
    paused        = False
    show_trails   = True
    show_energy   = True
    speed         = 1
    t_elapsed     = 0.0
    SIM_DT        = 0.004      # physics step size (fixed, small for accuracy)
    dragging      = None       # None | "b1" | "b2"

    # Trail surface (persistent)
    trail_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    trail_surf.fill((0, 0, 0, 0))

    while True:
        clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if ev.key == pygame.K_SPACE:  paused = not paused
                if ev.key == pygame.K_t:      show_trails = not show_trails
                if ev.key == pygame.K_e:      show_energy = not show_energy
                if ev.key == pygame.K_r:
                    pend, ghost, preset_name = make_pendulums(preset_key)
                    t_elapsed = 0.0
                if ev.key == pygame.K_EQUALS or ev.key == pygame.K_PLUS:
                    speed = min(8, speed * 2)
                if ev.key == pygame.K_MINUS:
                    speed = max(1, speed // 2)
                for k in "1234":
                    if ev.key == getattr(pygame, f"K_{k}") and k in PRESETS:
                        preset_key = k
                        pend, ghost, preset_name = make_pendulums(k)
                        t_elapsed = 0.0

        # Physics: run `speed` sub-steps per frame
        if not paused:
            for _ in range(speed * 3):
                pend.step(SIM_DT)
                ghost.step(SIM_DT)
                t_elapsed += SIM_DT

        # ── Draw ──────────────────────────────────────────────────────
        screen.fill(BG)

        # Subtle grid
        for x in range(0, 670, 40):
            pygame.draw.line(screen, GRID_C, (x, 0), (x, H), 1)
        for y in range(0, H, 40):
            pygame.draw.line(screen, GRID_C, (0, y), (670, y), 1)

        # Circle guide (max reach)
        max_r = int((pend.L1 + pend.L2) * PIX_PER_M)
        pygame.draw.circle(screen, GRID_C, PIVOT, max_r, 1)
        pygame.draw.circle(screen, GRID_C, PIVOT, int(pend.L1 * PIX_PER_M), 1)

        # Ghost first (behind)
        ghost.draw(screen, show_trail=show_trails)

        # Main pendulum on top
        pend.draw(screen, show_trail=show_trails)

        # Legend
        lx, ly = 20, H - 70
        pygame.draw.circle(screen, BOB2_C,   (lx+8,  ly),    7)
        pygame.draw.circle(screen, GHOST2_C, (lx+8,  ly+22), 7)
        screen.blit(font_tiny.render("Main pendulum",   True, TEXT_C), (lx+20, ly-5))
        screen.blit(font_tiny.render("Ghost (+0.01°)",  True, DIM_C),  (lx+20, ly+17))

        draw_panel(screen, pend, ghost, t_elapsed, paused,
                   show_energy, speed, preset_name, fonts)

        pygame.display.flip()

if __name__ == "__main__":
    main()
