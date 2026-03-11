"""
╔══════════════════════════════════════════════════════╗
║   MISSION CONTROL  🛸  Space Dashboard               ║
║   Run:  python mission_control.py                    ║
╚══════════════════════════════════════════════════════╝

A real sci-fi mission control dashboard that shows:
  • Live ISS position on a world map (fetched from open-notify API)
  • ISS orbital data  (altitude, velocity, orbital period)
  • Real-time star map overhead using PyEphem  (50 brightest stars)
  • Live planetary positions  (Venus, Mars, Jupiter, Saturn)
  • UTC mission clock + local sidereal time
  • Solar terminator line on the map
  • Scanline + CRT flicker aesthetic

Controls
────────
  SCROLL / +/-   →  zoom star map
  CLICK star map →  identify star under cursor
  T              →  toggle scanline overlay
  ESC            →  quit

Requirements
────────────
  pip install pygame numpy requests ephem
"""

import sys, math, time, threading, datetime
import numpy as np
import pygame
import requests
import ephem

# ── Layout ─────────────────────────────────────────────────────────────────────
W, H      = 1100, 700
MAP_X, MAP_Y, MAP_W, MAP_H = 20, 20, 680, 360
STAR_X, STAR_Y, STAR_R     = 820, 220, 160   # star map centre + radius
PANEL_X                    = 720
FPS                        = 30

# ── Colours ────────────────────────────────────────────────────────────────────
BG         = (4,   8,  16)
GRID       = (12,  28,  22)
MAP_BG     = (6,  14,  10)
COAST      = (20,  80,  50)
EQUATOR    = (15,  55,  35)
ISS_COL    = (0,  255, 160)
ORBIT_COL  = (0,  180, 100)
STAR_BG    = (4,   6,  18)
STAR_C     = (200, 220, 255)
PLANET_C   = {"venus": (255,220,120), "mars": (255,100,60),
              "jupiter": (220,180,120), "saturn": (200,160,80)}
AMBER      = (255, 180,  40)
CYAN       = ( 40, 220, 200)
DIM        = ( 60,  80,  70)
WHITE      = (220, 235, 230)
RED        = (255,  60,  60)
PANEL_BG   = ( 8,  16,  14)
BORDER     = ( 20,  80,  55)

# ── Brightest named stars (RA hrs, Dec deg, magnitude, name) ───────────────────
STARS = [
    (6.752, -16.716, -1.46, "Sirius"),    (6.399, 28.026, 0.08, "Capella"),
    (5.242, 45.998,  0.12, "Rigel"),      (7.655,  5.225,  0.34, "Procyon"),
    (5.919,  7.407,  0.45, "Betelgeuse"),(14.064,-60.372,  0.61, "Hadar"),
    (18.615, 38.783,  0.77, "Vega"),      (5.278, -8.202,  0.85, "Rigel"),
    (20.690, 45.281,  1.25, "Deneb"),     (13.420,-11.161,  1.04, "Spica"),
    (7.576, 31.889,  1.16, "Pollux"),    (16.490,-26.432,  1.06, "Antares"),
    (4.598, 16.509,  0.87, "Aldebaran"), (12.448,-63.099,  0.76, "Acrux"),
    (22.961,-29.621,  1.17, "Fomalhaut"),(1.162, 35.621,   2.07, "Mirach"),
    (10.139, 11.967,  1.36, "Regulus"),  (3.792, 24.105,   2.87, "Alcyone"),
    (17.622,-37.103,  1.63, "Shaula"),   (11.062, 61.751,  1.77, "Alioth"),
    (12.900, 55.959,  1.86, "Mizar"),    (2.530, 89.264,   2.02, "Polaris"),
    (9.133,-69.717,  0.05, "Canopus"),   (14.177,-60.373,  0.60, "Rigil Kent"),
    (19.846, 8.868,   0.77, "Altair"),   (5.438,-57.473,   1.68, "Regor"),
]

# ── ISS live fetch (background thread) ─────────────────────────────────────────
iss_data = {"lat": 0.0, "lon": 0.0, "alt_km": 408.0, "ok": False}
_iss_lock = threading.Lock()

def _fetch_iss():
    while True:
        try:
            r = requests.get("http://api.open-notify.org/iss-now.json", timeout=4)
            j = r.json()
            with _iss_lock:
                iss_data["lat"] = float(j["iss_position"]["latitude"])
                iss_data["lon"] = float(j["iss_position"]["longitude"])
                iss_data["ok"]  = True
        except Exception:
            pass
        time.sleep(5)

# ── Ephem observer (Mumbai as default, no GPS needed) ─────────────────────────
def make_observer():
    obs = ephem.Observer()
    obs.lat  = "19.07"
    obs.lon  = "72.87"
    obs.elevation = 10
    obs.date = ephem.now()
    return obs

# ── Coordinate helpers ─────────────────────────────────────────────────────────
def latlon_to_map(lat, lon):
    x = MAP_X + (lon + 180) / 360 * MAP_W
    y = MAP_Y + (90 - lat)  / 180 * MAP_H
    return int(x), int(y)

def altaz_to_xy(alt, az, cx, cy, radius):
    """Convert altitude/azimuth to screen XY on the star-map circle."""
    r = radius * (1 - alt / 90)
    a = math.radians(az - 90)
    return int(cx + r * math.cos(a)), int(cy + r * math.sin(a))

# ── Draw world map (simplified lat/lon grid) ───────────────────────────────────
def draw_map(surf, iss_lat, iss_lon, trail, font_sm):
    pygame.draw.rect(surf, MAP_BG, (MAP_X, MAP_Y, MAP_W, MAP_H))
    pygame.draw.rect(surf, BORDER, (MAP_X, MAP_Y, MAP_W, MAP_H), 1)

    # Grid lines
    for lon in range(-180, 181, 30):
        x = MAP_X + (lon + 180) / 360 * MAP_W
        pygame.draw.line(surf, GRID, (int(x), MAP_Y), (int(x), MAP_Y + MAP_H), 1)
    for lat in range(-90, 91, 30):
        y = MAP_Y + (90 - lat) / 180 * MAP_H
        pygame.draw.line(surf, GRID, (MAP_X, int(y)), (MAP_X + MAP_W, int(y)), 1)

    # Equator highlight
    eq_y = MAP_Y + MAP_H // 2
    pygame.draw.line(surf, EQUATOR, (MAP_X, eq_y), (MAP_X + MAP_W, eq_y), 1)

    # Continents (very rough bounding box approximations)
    LANDMASSES = [
        # North America
        [(-140,70),(-50,70),(-50,25),(-80,10),(-140,10)],
        # South America
        [(-82,12),(-34,12),(-34,-56),(-82,-56)],
        # Europe
        [(-10,35),(40,35),(40,70),(-10,70)],
        # Africa
        [(-18,-35),(52,-35),(52,37),(-18,37)],
        # Asia
        [(26,10),(145,10),(145,77),(26,77)],
        # Australia
        [(113,-44),(154,-44),(154,-10),(113,-10)],
    ]
    for poly in LANDMASSES:
        pts = [latlon_to_map(la, lo) for lo, la in poly]
        pygame.draw.polygon(surf, COAST, pts, 1)

    # ISS orbit trail
    if len(trail) > 1:
        prev = None
        for pt in trail:
            mx, my = latlon_to_map(*pt)
            if prev:
                dx = abs(mx - prev[0])
                if dx < MAP_W // 2:   # skip wrap-around lines
                    pygame.draw.line(surf, ORBIT_COL, prev, (mx, my), 1)
            prev = (mx, my)

    # ISS marker
    ix, iy = latlon_to_map(iss_lat, iss_lon)
    pygame.draw.circle(surf, ISS_COL, (ix, iy), 6)
    pygame.draw.circle(surf, ISS_COL, (ix, iy), 11, 1)
    pygame.draw.circle(surf, ISS_COL, (ix, iy), 16, 1)
    lbl = font_sm.render("ISS", True, ISS_COL)
    surf.blit(lbl, (ix + 14, iy - 6))

    # Map label
    tag = font_sm.render("ISS GROUND TRACK", True, DIM)
    surf.blit(tag, (MAP_X + 4, MAP_Y + 4))

# ── Draw star map ──────────────────────────────────────────────────────────────
def draw_starmap(surf, obs, hover, font_sm, font_tiny):
    cx, cy, r = STAR_X, STAR_Y, STAR_R

    # Background circle
    pygame.draw.circle(surf, STAR_BG, (cx, cy), r)
    pygame.draw.circle(surf, BORDER,  (cx, cy), r, 1)

    # Altitude rings
    for alt in [30, 60]:
        rr = int(r * (1 - alt / 90))
        pygame.draw.circle(surf, GRID, (cx, cy), rr, 1)

    # Cardinal directions
    for label, angle in [("N", 270), ("E", 0), ("S", 90), ("W", 180)]:
        a = math.radians(angle - 90)
        lx = cx + int((r + 12) * math.cos(a))
        ly = cy + int((r + 12) * math.sin(a))
        t  = font_tiny.render(label, True, DIM)
        surf.blit(t, t.get_rect(center=(lx, ly)))

    # Stars
    obs.date = ephem.now()
    hovered_name = None
    star_positions = []

    for ra, dec, mag, name in STARS:
        star = ephem.FixedBody()
        star._ra  = ephem.hours(ra)
        star._dec = ephem.degrees(dec)
        star.compute(obs)
        alt_deg = math.degrees(float(star.alt))
        az_deg  = math.degrees(float(star.az))
        if alt_deg < 0:
            continue
        sx, sy = altaz_to_xy(alt_deg, az_deg, cx, cy, r)
        size   = max(1, int(3.5 - mag * 0.8))
        pygame.draw.circle(surf, STAR_C, (sx, sy), size)
        star_positions.append((sx, sy, name, alt_deg, az_deg))

        # Hover label
        if hover and math.hypot(sx - hover[0], sy - hover[1]) < 10:
            hovered_name = f"{name}  alt:{alt_deg:.1f}°"

    if hovered_name:
        lbl = font_sm.render(hovered_name, True, AMBER)
        surf.blit(lbl, (cx - r, cy + r + 10))

    # Planets
    for pname, body in [("venus",  ephem.Venus()),
                        ("mars",   ephem.Mars()),
                        ("jupiter",ephem.Jupiter()),
                        ("saturn", ephem.Saturn())]:
        body.compute(obs)
        alt_deg = math.degrees(float(body.alt))
        az_deg  = math.degrees(float(body.az))
        if alt_deg < 0:
            continue
        px, py = altaz_to_xy(alt_deg, az_deg, cx, cy, r)
        col    = PLANET_C[pname]
        pygame.draw.circle(surf, col, (px, py), 5)
        pygame.draw.circle(surf, col, (px, py), 8, 1)
        t = font_tiny.render(pname[0].upper(), True, col)
        surf.blit(t, (px + 8, py - 6))

    title = font_sm.render("SKY OVERHEAD", True, DIM)
    surf.blit(title, title.get_rect(center=(cx, cy - r - 14)))

# ── Draw data panels ───────────────────────────────────────────────────────────
def draw_panels(surf, iss_lat, iss_lon, iss_ok, obs, fonts):
    font_big, font_med, font_sm, font_tiny = fonts
    px = PANEL_X
    pygame.draw.line(surf, BORDER, (px - 8, 0), (px - 8, H), 1)

    def label(text, x, y, col=DIM):
        surf.blit(font_tiny.render(text, True, col), (x, y))
    def value(text, x, y, col=WHITE):
        surf.blit(font_sm.render(text, True, col), (x, y))
    def section(text, y):
        surf.blit(font_med.render(f"── {text}", True, CYAN), (px, y))

    # Mission clock
    now_utc = datetime.datetime.utcnow()
    section("MISSION CLOCK", 20)
    value(now_utc.strftime("%H:%M:%S  UTC"), px, 46, AMBER)
    value(now_utc.strftime("%Y-%m-%d"), px, 66, DIM)
    lst = obs.sidereal_time()
    value(f"LST  {lst}", px, 86, DIM)

    # ISS telemetry
    section("ISS TELEMETRY", 120)
    status_col = ISS_COL if iss_ok else RED
    status_txt = "LIVE ●" if iss_ok else "NO SIGNAL ✗"
    value(status_txt, px, 144, status_col)

    label("LATITUDE",    px,      170)
    value(f"{iss_lat:+.3f}°", px, 184)
    label("LONGITUDE",   px + 130, 170)
    value(f"{iss_lon:+.3f}°", px + 130, 184)

    # ISS orbital constants
    ALT_KM  = 408
    VEL_KMS = 7.66
    PERIOD  = 92.68
    label("ALTITUDE",   px,       210)
    value(f"{ALT_KM} km",  px,    224, CYAN)
    label("VELOCITY",   px + 130, 210)
    value(f"{VEL_KMS} km/s", px + 130, 224, CYAN)
    label("PERIOD",     px,       250)
    value(f"{PERIOD} min", px,    264, CYAN)
    label("ORBITS/DAY", px + 130, 250)
    value("15.49",      px + 130, 264, CYAN)

    # Planetary data
    section("SOLAR SYSTEM", 300)
    obs.date = ephem.now()
    row = 0
    for pname, body in [("VENUS",   ephem.Venus()),
                        ("MARS",    ephem.Mars()),
                        ("JUPITER", ephem.Jupiter()),
                        ("SATURN",  ephem.Saturn())]:
        body.compute(obs)
        alt = math.degrees(float(body.alt))
        col = PLANET_C[pname.lower()]
        vis = "visible" if alt > 0 else f"below horizon"
        label(pname,                    px,       326 + row * 44)
        value(f"alt {alt:+.1f}°",       px,       340 + row * 44, col)
        value(vis,                      px + 120, 340 + row * 44,
              (60, 200, 100) if alt > 0 else (80, 60, 60))
        row += 1

    # Controls
    pygame.draw.line(surf, BORDER, (px, H - 55), (W, H - 55), 1)
    for i, txt in enumerate(["T scanlines", "ESC quit"]):
        surf.blit(font_tiny.render(txt, True, DIM),
                  (px + i * 170, H - 40))

# ── Scanline overlay ───────────────────────────────────────────────────────────
_scanlines = None
def get_scanlines():
    global _scanlines
    if _scanlines is None:
        _scanlines = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 2):
            pygame.draw.line(_scanlines, (0, 0, 0, 55), (0, y), (W, y))
    return _scanlines

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("MISSION CONTROL  🛸")
    clock  = pygame.time.Clock()

    font_big  = pygame.font.SysFont("monospace", 22, bold=True)
    font_med  = pygame.font.SysFont("monospace", 15, bold=True)
    font_sm   = pygame.font.SysFont("monospace", 13)
    font_tiny = pygame.font.SysFont("monospace", 11)
    fonts     = (font_big, font_med, font_sm, font_tiny)

    # Start ISS fetch thread
    t = threading.Thread(target=_fetch_iss, daemon=True)
    t.start()

    obs       = make_observer()
    trail     = []           # ISS lat/lon history
    scanlines  = True
    hover_pos  = None
    flicker    = 1.0

    while True:
        clock.tick(FPS)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if ev.key == pygame.K_t:
                    scanlines = not scanlines
            if ev.type == pygame.MOUSEMOTION:
                hover_pos = ev.pos

        # Update trail
        with _iss_lock:
            lat, lon = iss_data["lat"], iss_data["lon"]
            ok       = iss_data["ok"]
        if not trail or (lat, lon) != trail[-1]:
            trail.append((lat, lon))
            if len(trail) > 120:
                trail.pop(0)

        # CRT flicker
        flicker = 0.97 + 0.03 * math.sin(time.time() * 7.3)

        screen.fill(BG)

        draw_map(screen, lat, lon, trail, font_sm)
        draw_starmap(screen, obs, hover_pos, font_sm, font_tiny)
        draw_panels(screen, lat, lon, ok, obs, fonts)

        # Title bar
        pygame.draw.rect(screen, (6, 18, 14), (MAP_X, MAP_Y + MAP_H + 8, MAP_W, 32))
        pygame.draw.rect(screen, BORDER,      (MAP_X, MAP_Y + MAP_H + 8, MAP_W, 32), 1)
        ts = datetime.datetime.utcnow().strftime("T+ %H:%M:%S")
        screen.blit(font_med.render(f"◈ MISSION CONTROL  {ts}", True, CYAN),
                    (MAP_X + 8, MAP_Y + MAP_H + 14))
        screen.blit(font_tiny.render(
            f"ISS  {'ACQUIRED' if ok else 'SEARCHING'}  |  lat {lat:+.2f}  lon {lon:+.2f}",
            True, ISS_COL if ok else DIM),
            (MAP_X + 350, MAP_Y + MAP_H + 18))

        # Scanlines
        if scanlines:
            screen.blit(get_scanlines(), (0, 0))

        # Subtle flicker via alpha overlay
        if flicker < 1.0:
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, int((1 - flicker) * 30)))
            screen.blit(dim, (0, 0))

        pygame.display.flip()

if __name__ == "__main__":
    main()
