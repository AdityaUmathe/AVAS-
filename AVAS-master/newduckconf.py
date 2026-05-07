import keyboard
import win32gui
import time
import os

# -------------------------------
# Load config
# -------------------------------
CONF = "duckhunt.conf"

if not os.path.exists(CONF):
    raise FileNotFoundError("duckhunt.conf not found!")

cfg = {}
exec(open(CONF, "r", encoding="utf-8").read(), cfg)

policy   = cfg.get("policy", "normal").lower()
password = cfg.get("password", "")
blacklist = cfg.get("blacklist", "")

threshold = cfg.get("threshold", 30)
size = cfg.get("size", 25)
randdrop = cfg.get("randdrop", 6)
filename = cfg.get("filename", "log.txt")
allow_auto = cfg.get("allow_auto_type_software", True)

# ---------------------------------------
# Variables
# ---------------------------------------
history = [threshold + 1] * size
idx = 0
intrusion = False
pcounter = 0
prev = None

def get_window_name():
    try:
        return win32gui.GetWindowText(win32gui.GetForegroundWindow())
    except:
        return ""

def log_char(c):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(c)

def caught(key):
    global intrusion
    intrusion = True
    print("⚠️ Intrusion detected!")

    if policy == "logonly":
        log_char(key)
        return True

    if policy == "sneaky":
        return False

    if policy == "normal":
        log_char(key)
        return False

    if policy == "paranoid":
        return False

    return False

# ---------------------------------------
# Key event handler
# ---------------------------------------
def on_key(event):
    global prev, intrusion, idx, pcounter, history

    window = get_window_name()

    # Blacklist check
    for w in blacklist.split(","):
        if w.strip() and w.strip() in window:
            return caught(event.name)

    now = time.time() * 1000  # ms

    if prev is None:
        prev = now
        return

    diff = now - prev
    prev = now

    history[idx] = diff
    idx = (idx + 1) % size

    avg = sum(history) / len(history)

    if avg < threshold:
        return caught(event.name)

    intrusion = False

# Attach listener
keyboard.on_press(on_key)

print("✅ DuckHunter Python 3 version running...")
print("Press CTRL+C to exit.")

keyboard.wait()
