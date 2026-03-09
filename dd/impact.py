import random
import string
from datetime import datetime, timedelta

def generate_password(length=12):
    """Generate a random secure password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    return ''.join(random.choices(chars, k=length))

def random_date(start_year=2000, end_year=2024):
    """Generate a random date between two years."""
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)

def coin_flip_streak(n=100):
    """Simulate coin flips and find the longest streak."""
    flips = [random.choice(['H', 'T']) for _ in range(n)]
    max_streak = streak = 1
    for i in range(1, len(flips)):
        streak = streak + 1 if flips[i] == flips[i-1] else 1
        max_streak = max(max_streak, streak)
    return flips, max_streak

def random_walk(steps=10):
    """Simulate a 2D random walk."""
    x, y = 0, 0
    path = [(x, y)]
    directions = [(0,1),(0,-1),(1,0),(-1,0)]
    for _ in range(steps):
        dx, dy = random.choice(directions)
        x, y = x + dx, y + dy
        path.append((x, y))
    return path

# --- Run it ---
print("🔐 Password:", generate_password(16))
print("📅 Random date:", random_date().strftime("%B %d, %Y"))

flips, streak = coin_flip_streak(50)
print(f"🪙 Flips (first 20): {''.join(flips[:20])}")
print(f"   Longest streak: {streak}")

walk = random_walk(8)
print(f"🚶 Random walk path: {walk}")
print(f"   Ended at: {walk[-1]}, Distance from origin: {abs(walk[-1][0]) + abs(walk[-1][1])} steps")