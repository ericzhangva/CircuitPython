import board
import wifi
import socketpool
import microcontroller
import neopixel
import adafruit_ntp
import time
from adafruit_httpserver import Server, Request, Response, Redirect

# ────────────────────────────────────────────────
# 1. HARDWARE & WIFI SETUP
# ────────────────────────────────────────────────
# Using board.NEOPIXEL as found in your dir(board)
pixels = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2, auto_write=True)
pixels[0] = (0, 0, 32) # Blue during boot

SSID = "EZ2.4GHz"
PASSWORD = "Shen33312"

print("\n--- ESP32-S3 Web Server ---")
try:
    print(f"Connecting to {SSID}...")
    wifi.radio.connect(SSID, PASSWORD)
    ip_address = str(wifi.radio.ipv4_address)
    pixels[0] = (0, 64, 0) # Green when connected
    print(f"Connected! IP: {ip_address}")
except Exception as e:
    pixels[0] = (64, 0, 0) # Red if connection fails
    print(f"Wi-Fi Connection Failed: {e}")
    ip_address = None

# ────────────────────────────────────────────────
# 2. NTP & SERVER SETUP
# ────────────────────────────────────────────────
if ip_address:
    pool = socketpool.SocketPool(wifi.radio)
    ntp = adafruit_ntp.NTP(pool, tz_offset=-8)
    server = Server(pool, "/static")

    def get_formatted_time():
        try:
            now = ntp.datetime
            return f"{now.tm_hour:02}:{now.tm_min:02}:{now.tm_sec:02}"
        except:
            return "NTP Pending..."

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
        if color == "red":
            pixels[0] = (64, 0, 0)
        elif color == "green":
            pixels[0] = (0, 64, 0)
        elif color == "blue":
            pixels[0] = (0, 0, 64)
        elif color == "white":
            pixels[0] = (64, 64, 64)
        else:
            pixels[0] = (0, 0, 0)
        return Redirect(request, "/")

    # ────────────────────────────────────────────────
    # 3. START SERVER WITH PORT RECOVERY
    # ────────────────────────────────────────────────
    current_port = 80
    server_started = False

    while not server_started and current_port < 90:
        try:
            server.start(host=ip_address, port=current_port)
            print(f"Server ACTIVE at http://{ip_address}:{current_port}")
            server_started = True
        except OSError as e:
            if e.errno == 112:
                print(f"Port {current_port} busy, trying {current_port + 1}...")
                current_port += 1
                time.sleep(0.5)
            else:
                raise e

    # ────────────────────────────────────────────────
    # 4. MAIN LOOP
    # ────────────────────────────────────────────────
    while True:
        try:
            server.poll()
        except Exception as e:
            print(f"Server Poll Error: {e}")
            time.sleep(1)
else:
    print("Critical Error: No IP address. System halted.")
    while True:
        pass
