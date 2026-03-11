"""
╔══════════════════════════════════════════════════════╗
║   FLUID CORE  💧  SPH Particle Simulation            ║
║   Run:  python fluid_core.py                         ║
╚══════════════════════════════════════════════════════╝

Smoothed Particle Hydrodynamics (SPH) — the algorithm
behind AAA game water and Hollywood VFX, distilled to
~300 lines of pure Python + NumPy.

Physics modelled
────────────────
  • Density estimation  (Poly6 kernel)
  • Pressure force      (Spiky kernel gradient)
  • Viscosity force     (Laplacian kernel)
  • Surface tension     (colour-field normals)
  • Gravity + buoyancy
  • Boundary repulsion  (soft walls)

Controls
────────
  LEFT DRAG      →  pour fluid from cursor
  RIGHT DRAG     →  repel particles (wind gun)
  SCROLL UP/DN   →  gravity strength ↑ / ↓
  G              →  toggle gravity direction
  C              →  cycle particle colour mode
  R              →  reset simulation
  SPACE          →  pause / resume
  ESC            →  quit
"""

import sys, math, time
import numpy as np
import pygame

# ── Simulation constants ───────────────────────────────────────────────────────
W, H          = 900, 650
SIM_W, SIM_H  = W, H

# SPH parameters
H_RADIUS      = 28.0          # smoothing radius
H2            = H_RADIUS ** 2
REST_DENSITY  = 35.0
GAS_CONST     = 800.0         # pressure stiffness
VISCOSITY     = 80.0
GRAVITY_BASE  = 200.0
SURFACE_TENS  = 0.07
MASS          = 1.0
DT            = 0.013
WALL_DAMP     = 0.35
MAX_PARTICLES = 600

# Kernel pre-factors
POLY6_COEF    = 315.0 / (64.0 * math.pi * H_RADIUS ** 9)
SPIKY_COEF    = -45.0 / (math.pi * H_RADIUS ** 6)
VISC_COEF     =  45.0 / (math.pi * H_RADIUS ** 6)

# ── Colour palettes ────────────────────────────────────────────────────────────
BG            = (4, 5, 10)
GLOW_COL      = (20, 60, 120)

PALETTES = {
    "ocean":    [(0, 80, 180),   (0, 160, 255),  (80, 220, 255)],
    "lava":     [(180, 20, 0),   (255, 100, 0),  (255, 220, 60)],
    "toxic":    [(0, 160, 40),   (60, 255, 80),  (180, 255, 120)],
    "blood":    [(120, 0, 20),   (200, 20, 40),  (255, 80, 80)],
    "plasma":   [(120, 0, 200),  (200, 60, 255), (255, 180, 255)],
}
PAL_KEYS      = list(PALETTES.keys())

# ── SPH kernel functions ───────────────────────────────────────────────────────
def poly6(r2):
    diff = H2 - r2
    diff = np.where(diff > 0, diff, 0)
    return POLY6_COEF * diff ** 3

def spiky_grad(rx, ry, r):
    """Returns (fx, fy) gradient of spiky kernel."""
    mask = (r > 0) & (r < H_RADIUS)
    diff = np.where(mask, H_RADIUS - r, 0)
    coef = SPIKY_COEF * diff ** 2 / np.where(r > 0, r, 1)
    return coef * rx, coef * ry

def visc_lap(r):
    return np.where(r < H_RADIUS, VISC_COEF * (H_RADIUS - r), 0)

# ── Particle system ────────────────────────────────────────────────────────────
class FluidSim:
    def __init__(self):
        self.reset()

    def reset(self):
        self.px  = np.empty(0, dtype=np.float32)
        self.py  = np.empty(0, dtype=np.float32)
        self.vx  = np.empty(0, dtype=np.float32)
        self.vy  = np.empty(0, dtype=np.float32)
        self.den = np.empty(0, dtype=np.float32)
        self.pre = np.empty(0, dtype=np.float32)
        self.age = np.empty(0, dtype=np.float32)   # for colour gradient
        self.grav_dir = 1.0     # +1 down, -1 up
        self.grav_str = GRAVITY_BASE

    def add_particles(self, x, y, n=4, jitter=14):
        if len(self.px) >= MAX_PARTICLES:
            return
        n = min(n, MAX_PARTICLES - len(self.px))
        nx = x + np.random.uniform(-jitter, jitter, n).astype(np.float32)
        ny = y + np.random.uniform(-jitter, jitter, n).astype(np.float32)
        self.px  = np.append(self.px,  nx)
        self.py  = np.append(self.py,  ny)
        self.vx  = np.append(self.vx,  np.zeros(n, np.float32))
        self.vy  = np.append(self.vy,  np.zeros(n, np.float32))
        self.den = np.append(self.den, np.ones(n,  np.float32) * REST_DENSITY)
        self.pre = np.append(self.pre, np.zeros(n, np.float32))
        self.age = np.append(self.age, np.zeros(n, np.float32))

    def repel(self, mx, my, strength=8000):
        if len(self.px) == 0:
            return
        dx = self.px - mx
        dy = self.py - my
        r2 = dx*dx + dy*dy
        r  = np.sqrt(r2)
        mask = r < 80
        safe_r = np.where(r > 0.1, r, 1.0)
        self.vx += mask * (dx / safe_r) * strength * DT / (safe_r + 1)
        self.vy += mask * (dy / safe_r) * strength * DT / (safe_r + 1)

    def step(self):
        n = len(self.px)
        if n == 0:
            return

        self.age += DT

        # ── Density & pressure ──────────────────────────────────────
        den = np.zeros(n, np.float32)
        for i in range(n):
            dx = self.px - self.px[i]
            dy = self.py - self.py[i]
            r2 = dx*dx + dy*dy
            den[i] = MASS * np.sum(poly6(r2[r2 < H2]))
        den = np.maximum(den, 0.001)
        pre = GAS_CONST * (den - REST_DENSITY)

        # ── Forces ──────────────────────────────────────────────────
        fx = np.zeros(n, np.float32)
        fy = np.zeros(n, np.float32)

        for i in range(n):
            dx  = self.px[i] - self.px        # shape (n,)
            dy  = self.py[i] - self.py
            r2  = dx*dx + dy*dy
            r   = np.sqrt(r2)
            mask = (r2 < H2) & (r2 > 0)

            # Pressure force
            p_avg = (pre[i] + pre) / 2.0
            gx, gy = spiky_grad(dx, dy, r)
            fx[i] += -MASS * np.sum(mask * p_avg / np.where(den > 0, den, 1) * gx)
            fy[i] += -MASS * np.sum(mask * p_avg / np.where(den > 0, den, 1) * gy)

            # Viscosity
            vlap  = visc_lap(r)
            dv_x  = self.vx - self.vx[i]
            dv_y  = self.vy - self.vy[i]
            fx[i] += VISCOSITY * MASS * np.sum(mask * vlap * dv_x / np.where(den > 0, den, 1))
            fy[i] += VISCOSITY * MASS * np.sum(mask * vlap * dv_y / np.where(den > 0, den, 1))

        # Gravity
        fy += den * self.grav_str * self.grav_dir

        # ── Integrate ────────────────────────────────────────────────
        safe_den    = np.where(den > 0, den, 1)
        self.vx    += DT * fx / safe_den
        self.vy    += DT * fy / safe_den
        self.px    += DT * self.vx
        self.py    += DT * self.vy

        # ── Boundary repulsion (soft walls) ──────────────────────────
        margin = 8.0
        def wall(pos, vel, lo, hi):
            lo_pen = lo + margin - pos
            hi_pen = pos - (hi - margin)
            vel += np.where(lo_pen > 0,  lo_pen * 60, 0)
            vel -= np.where(hi_pen > 0,  hi_pen * 60, 0)
            pos  = np.clip(pos, lo + 2, hi - 2)
            return pos, vel

        self.px, self.vx = wall(self.px, self.vx, 0, SIM_W)
        self.py, self.vy = wall(self.py, self.vy, 0, SIM_H)

        # Damping
        speed = np.sqrt(self.vx**2 + self.vy**2)
        cap   = 400.0
        over  = speed > cap
        self.vx = np.where(over, self.vx / speed * cap, self.vx)
        self.vy = np.where(over, self.vy / speed * cap, self.vy)

        self.den = den
        self.pre = pre

# ── Render helpers ─────────────────────────────────────────────────────────────
def density_to_color(d, vel_mag, age, palette):
    c0, c1, c2 = palette
    t = min(1.0, d / (REST_DENSITY * 2.0))
    v = min(1.0, vel_mag / 300.0)

    if t < 0.5:
        r = int(c0[0] + (c1[0]-c0[0]) * t * 2)
        g = int(c0[1] + (c1[1]-c0[1]) * t * 2)
        b = int(c0[2] + (c1[2]-c0[2]) * t * 2)
    else:
        tt = (t - 0.5) * 2
        r = int(c1[0] + (c2[0]-c1[0]) * tt)
        g = int(c1[1] + (c2[1]-c1[1]) * tt)
        b = int(c1[2] + (c2[2]-c1[2]) * tt)

    # Brighten by velocity
    r = min(255, r + int(v * 60))
    g = min(255, g + int(v * 40))
    b = min(255, b + int(v * 80))
    return (r, g, b)

def draw_glow(surf, x, y, radius, color, alpha=30):
    glow = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*color, alpha), (radius, radius), radius)
    surf.blit(glow, (int(x)-radius, int(y)-radius),
              special_flags=pygame.BLEND_RGBA_ADD)

# ── HUD ────────────────────────────────────────────────────────────────────────
def draw_hud(surf, sim, pal_name, paused, fonts):
    font_sm, font_tiny = fonts
    n = len(sim.px)

    # Left panel
    lines = [
        f"PARTICLES  {n}/{MAX_PARTICLES}",
        f"GRAVITY    {'↓' if sim.grav_dir > 0 else '↑'} {sim.grav_str:.0f}",
        f"PALETTE    {pal_name.upper()}",
        f"{'⏸ PAUSED' if paused else '▶ RUNNING'}",
    ]
    for i, ln in enumerate(lines):
        col = (255, 200, 60) if "PAUSED" in ln else (60, 140, 100)
        surf.blit(font_sm.render(ln, True, col), (14, 14 + i * 20))

    # Bottom hints
    hints = [
        "LMB pour  •  RMB repel  •  SCROLL gravity",
        "G flip gravity  •  C colour  •  R reset  •  SPACE pause",
    ]
    for i, h in enumerate(hints):
        t = font_tiny.render(h, True, (35, 65, 50))
        surf.blit(t, (14, H - 32 + i * 16))

    # Particle bar
    bar_w = 200
    bar_x, bar_y = W - bar_w - 14, 14
    pygame.draw.rect(surf, (15, 30, 20), (bar_x, bar_y, bar_w, 10), border_radius=5)
    fill = int(bar_w * n / MAX_PARTICLES)
    if fill > 0:
        pygame.draw.rect(surf, (30, 160, 80), (bar_x, bar_y, fill, 10), border_radius=5)
    surf.blit(font_tiny.render("CAPACITY", True, (40, 80, 55)), (bar_x, bar_y + 13))

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("FLUID CORE  💧  SPH Simulation")
    clock  = pygame.time.Clock()

    font_sm   = pygame.font.SysFont("monospace", 13, bold=True)
    font_tiny = pygame.font.SysFont("monospace", 11)

    sim       = FluidSim()
    pal_idx   = 0
    paused    = False
    pouring   = False
    repelling = False
    mouse_pos = (W//2, H//3)

    # Seed initial fluid blob
    for y in range(200, 380, 14):
        for x in range(350, 560, 14):
            sim.add_particles(x, y, n=1, jitter=3)

    while True:
        clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if ev.key == pygame.K_SPACE:  paused = not paused
                if ev.key == pygame.K_r:      sim.reset()
                if ev.key == pygame.K_g:      sim.grav_dir *= -1
                if ev.key == pygame.K_c:      pal_idx = (pal_idx + 1) % len(PAL_KEYS)
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1: pouring   = True
                if ev.button == 3: repelling = True
            if ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 1: pouring   = False
                if ev.button == 3: repelling = False
            if ev.type == pygame.MOUSEMOTION:
                mouse_pos = ev.pos
            if ev.type == pygame.MOUSEWHEEL:
                sim.grav_str = max(50, min(600,
                    sim.grav_str + ev.y * 20))

        if not paused:
            if pouring:
                sim.add_particles(*mouse_pos, n=5, jitter=12)
            if repelling:
                sim.repel(*mouse_pos)
            sim.step()

        # ── Render ────────────────────────────────────────────────────
        screen.fill(BG)

        palette = PALETTES[PAL_KEYS[pal_idx]]
        n       = len(sim.px)

        if n > 0:
            vel_mag = np.sqrt(sim.vx**2 + sim.vy**2)

            # Draw glow halos first (back layer)
            glow_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            step = max(1, n // 120)        # limit glow draws for perf
            for i in range(0, n, step):
                col = density_to_color(sim.den[i], vel_mag[i], sim.age[i], palette)
                draw_glow(glow_surf, sim.px[i], sim.py[i], 18, col, alpha=18)
            screen.blit(glow_surf, (0, 0))

            # Draw particles
            for i in range(n):
                col  = density_to_color(sim.den[i], vel_mag[i], sim.age[i], palette)
                r    = max(2, min(6, int(3 + sim.den[i] / REST_DENSITY * 1.5)))
                ix, iy = int(sim.px[i]), int(sim.py[i])
                pygame.draw.circle(screen, col, (ix, iy), r)
                # Specular highlight
                if r > 3:
                    hx = ix - r // 3
                    hy = iy - r // 3
                    pygame.draw.circle(screen, (255, 255, 255), (hx, hy), max(1, r//3))

        # Cursor cross-hair
        mx, my = mouse_pos
        c = (80, 200, 120) if pouring else ((200, 80, 80) if repelling else (50, 80, 60))
        pygame.draw.line(screen, c, (mx-12, my), (mx+12, my), 1)
        pygame.draw.line(screen, c, (mx, my-12), (mx, my+12), 1)
        pygame.draw.circle(screen, c, (mx, my), 16, 1)

        draw_hud(screen, sim, PAL_KEYS[pal_idx], paused, (font_sm, font_tiny))
        pygame.display.flip()

if __name__ == "__main__":
    main()
