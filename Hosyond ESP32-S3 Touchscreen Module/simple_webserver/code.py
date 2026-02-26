import board
import busio
import displayio
import fourwire
import adafruit_ili9341
import terminalio
import digitalio
import wifi
import socketpool
import microcontroller
import neopixel
import adafruit_ntp
from adafruit_display_text import label
from adafruit_httpserver import Server, Request, Response, Redirect

# ────────────────────────────────────────────────
# 1. DISPLAY & BACKLIGHT SETUP (ES3C28P Pins)
# ────────────────────────────────────────────────
# Backlight on IO45
backlight = digitalio.DigitalInOut(board.IO45)
backlight.direction = digitalio.Direction.OUTPUT
backlight.value = True

displayio.release_displays()

# SPI Bus for ILI9341V
tft_scl = board.IO12
tft_sda = board.IO11
tft_cs = board.IO10
tft_dc = board.IO46

spi = busio.SPI(clock=tft_scl, MOSI=tft_sda)

display_bus = fourwire.FourWire(
    spi,
    command=tft_dc,
    chip_select=tft_cs,
    reset=None
)

display = adafruit_ili9341.ILI9341(
    display_bus,
    width=320,
    height=240,
    rotation=0
)

# Apply Hardware Inversion Fix
display.bus.send(0x21, b'')

# ────────────────────────────────────────────────
# 2. UI GROUP SETUP (SHIFTED RIGHT)
# ────────────────────────────────────────────────
main_group = displayio.Group()
display.root_group = main_group

# Black Background
bg_bitmap = displayio.Bitmap(320, 240, 1)
bg_palette = displayio.Palette(1)
bg_palette[0] = 0x000000
main_group.append(displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette))

# Title Label (Shifted Right)
title_lbl = label.Label(terminalio.FONT, text="SYSTEM STATUS", color=0x888888, x=120, y=30)
main_group.append(title_lbl)

# Status Label (Shifted Right - Shows LED Color)
status_lbl = label.Label(terminalio.FONT, text="CONNECTING...", color=0xFFFF00, x=110, y=110, scale=2)
main_group.append(status_lbl)

# IP Label (Shifted Right)
ip_lbl = label.Label(terminalio.FONT, text="IP: 0.0.0.0", color=0x00FFFF, x=110, y=160, scale=1)
main_group.append(ip_lbl)

# ────────────────────────────────────────────────
# 3. HARDWARE & WIFI
# ────────────────────────────────────────────────
pixels = neopixel.NeoPixel(board.IO42, 1, brightness=0.3, auto_write=True)
pixels[0] = (0, 0, 32) # Blue during boot

SSID = "EZ2.4GHz"
PASSWORD = "Shen33312"

print("Connecting to Wi-Fi...")
wifi.radio.connect(SSID, PASSWORD)

ip_address = str(wifi.radio.ipv4_address)
ip_lbl.text = f"IP: {ip_address}"
status_lbl.text = "READY"
status_lbl.color = 0x00FF00
pixels[0] = (0, 64, 0) # Green when connected
print(f"Connected to {SSID}")

# ────────────────────────────────────────────────
# 4. NTP & SERVER SETUP
# ────────────────────────────────────────────────
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=-8)

def get_formatted_time():
    try:
        now = ntp.datetime
        return f"{now.tm_hour:02}:{now.tm_min:02}:{now.tm_sec:02}"
    except:
        return "00:00:00"

server = Server(pool, "/")

@server.route("/", "GET")
def root(request: Request):
    try:
        with open("index.html", "r") as f:
            html = f.read()

        html = html.replace("{{ cpu_temp }}", f"{microcontroller.cpu.temperature:.1f}")
        html = html.replace("{{ ip_address }}", ip_address)
        html = html.replace("{{ local_time }}", get_formatted_time())

        return Response(request, html, content_type="text/html")
    except Exception as e:
        return Response(request, f"Error: {e}", status=500)

@server.route("/set_color", "POST")
def set_color(request: Request):
    data = request.form_data
    color = data.get("color", "off").lower()

    # Update Display Text and Pixel
    status_lbl.text = f"COLOR: {color.upper()}"

    if color == "red":
        pixels[0] = (32, 0, 0)
        status_lbl.color = 0xFF0000
    elif color == "green":
        pixels[0] = (0, 32, 0)
        status_lbl.color = 0x00FF00
    elif color == "blue":
        pixels[0] = (0, 0, 32)
        status_lbl.color = 0x0000FF
    elif color == "white":
        pixels[0] = (32, 32, 32)
        status_lbl.color = 0xFFFFFF
    else:
        pixels[0] = (0, 0, 0)
        status_lbl.text = "LED: OFF"
        status_lbl.color = 0x666666

    return Redirect(request, "/")

# ────────────────────────────────────────────────
# 5. MAIN LOOP
# ────────────────────────────────────────────────
server.start(host=ip_address, port=80)
print(f"Server listening on http://{ip_address}")

while True:
    try:
        server.poll()
    except Exception as e:
        print(f"Server error: {e}")
        continue
