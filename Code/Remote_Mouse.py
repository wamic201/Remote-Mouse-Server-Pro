import os
import socket
import time
import sys
import ctypes
import threading
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

# --- PERFORMANCE CONFIGURATION ---
PORT_WEB = 5000
# Direct Windows API Constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_LWIN = 0x5B
VK_CONTROL = 0x11
VK_MENU = 0x12 # Alt Key
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_D = 0x44
VK_TAB = 0x09
VK_BACK = 0x08
VK_RETURN = 0x0D

# --- Windows API Structures for 64-bit Compatibility ---
PUL = ctypes.POINTER(ctypes.c_ulong)
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_uint),
                ("time", ctypes.c_uint),
                ("dwExtraInfo", PUL)]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_uint),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_short)]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_uint),
                ("dwFlags", ctypes.c_uint),
                ("time", ctypes.c_uint),
                ("dwExtraInfo", PUL)]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT),
                ("mi", MOUSEINPUT),
                ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint),
                ("padding", ctypes.c_uint), # Required for 64-bit alignment
                ("u", INPUT_UNION)]

def move_mouse_raw(dx, dy):
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)

def mouse_click_raw(button='left', down=True):
    if button == 'left':
        flags = MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP
    else:
        flags = MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP
    ctypes.windll.user32.mouse_event(flags, 0, 0, 0, 0)

def mouse_scroll_raw(amount):
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(amount), 0)

def mouse_zoom_raw(amount):
    # Simulate Ctrl + Wheel
    ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(amount), 0)
    ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

def send_unicode_char(char):
    if char == "BACKSPACE":
        ctypes.windll.user32.keybd_event(VK_BACK, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_BACK, 0, KEYEVENTF_KEYUP, 0)
        return
    if char == "ENTER":
        ctypes.windll.user32.keybd_event(VK_RETURN, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
        return
    for c in char:
        extra = ctypes.c_ulong(0)
        ii_down = INPUT_UNION(); ii_down.ki = KEYBDINPUT(0, ord(c), KEYEVENTF_UNICODE, 0, ctypes.pointer(extra))
        input_down = INPUT(1, 0, ii_down)
        ii_up = INPUT_UNION(); ii_up.ki = KEYBDINPUT(0, ord(c), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
        input_up = INPUT(1, 0, ii_up)
        ctypes.windll.user32.SendInput(2, ctypes.byref((INPUT * 2)(input_down, input_up)), ctypes.sizeof(INPUT))

def send_win_d():
    ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_D, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_D, 0, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)

def send_win_tab():
    ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_TAB, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)

def send_browser_nav(direction):
    vk = VK_LEFT if direction == 'back' else VK_RIGHT
    ctypes.windll.user32.keybd_event(VK_MENU, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=10, ping_interval=5)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Pro Remote Controller</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        :root { --bg: #020617; --card: #0f172a; --accent: #3b82f6; }
        body { 
            margin: 0; padding: 0; background: var(--bg); color: white; 
            font-family: -apple-system, system-ui, sans-serif; touch-action: none; 
            overflow: hidden; height: 100vh; display: flex; flex-direction: column;
        }
        header {
            padding: 15px; background: var(--card); border-bottom: 1px solid #1e293b;
            display: flex; justify-content: space-between; align-items: center;
        }
        .status { font-size: 11px; display: flex; align-items: center; gap: 6px; }
        .dot { width: 8px; height: 8px; border-radius: 50%; background: #ef4444; }
        .online .dot { background: #22c55e; }
        #trackpad {
            flex-grow: 1; margin: 15px; background: var(--card); border-radius: 20px;
            border: 2px solid #334155; position: relative;
            display: flex; align-items: center; justify-content: center;
        }
        #trackpad.active { border-color: var(--accent); }
        #trackpad.holding { background: #1e293b; border-color: #fbbf24; }
        .controls { padding: 15px; background: var(--card); display: flex; flex-direction: column; gap: 10px; }
        .row { display: flex; justify-content: space-between; align-items: center; }
        .btn {
            background: #334155; border: none; color: white; padding: 10px 15px;
            border-radius: 8px; font-size: 13px; font-weight: 500;
        }
        .btn:active { background: #475569; }
        #hidden-input { position: absolute; left: -9999px; top: -9999px; opacity: 0; }
        input[type=range] { flex-grow: 1; margin: 0 15px; }
        .label { font-size: 12px; opacity: 0.7; }
    </style>
</head>
<body>
    <header>
        <div class="status" id="status-box"><div class="dot"></div><span id="status-text">Connecting...</span></div>
        <div style="display:flex; gap:8px;">
            <button class="btn" onclick="forceReconnect()">Sync</button>
            <button class="btn" id="kb-btn" onclick="showKeyboard()">Keyboard</button>
            <button class="btn" onclick="toggleFS()">FS</button>
        </div>
    </header>
    <input type="text" id="hidden-input" autocomplete="off" autocapitalize="off" spellcheck="false">
    <div id="trackpad">
        <div style="opacity: 0.2; text-align: center; font-size: 12px; pointer-events: none;">
            1-Finger: Move / Tap / Long-Press (Drag)<br>
            2-Finger Horizontal: Scroll<br>
            2-Finger Swipe: Left (Fwd) / Right (Back)<br>
            3-Finger Swipe: Up (Task View) / Down (Desktop)
        </div>
    </div>
    <div class="controls">
        <div class="row">
            <span class="label">Sens</span>
            <input type="range" id="sens" min="0.5" max="5.0" step="0.1" value="2.0">
            <span id="sens-val" style="width: 25px;">2.0</span>
        </div>
    </div>

    <script>
        const socket = io({ transports: ['websocket'], reconnection: true });
        const trackpad = document.getElementById('trackpad');
        const sensInput = document.getElementById('sens');
        const hiddenInput = document.getElementById('hidden-input');

        let lastX = 0, lastY = 0, startX = 0, startY = 0;
        let isMoving = false, isHolding = false, hasMoved = false;
        let touchStart = 0, lastTap = 0, longPressTimer = null;
        let numTouches = 0, maxTouches = 0;
        let initialPinchDist = 0, isScrollMode = false;

        function updateStatus(online, text) {
            const box = document.getElementById('status-box');
            document.getElementById('status-text').innerText = text;
            box.className = online ? "status online" : "status";
        }

        socket.on('connect', () => updateStatus(true, "Ready"));
        socket.on('disconnect', () => updateStatus(false, "Disconnected"));

        function forceReconnect() { socket.disconnect().connect(); }
        function toggleFS() { 
            if(!document.fullscreenElement) document.documentElement.requestFullscreen();
            else document.exitFullscreen();
        }

        function showKeyboard() { hiddenInput.value = " "; hiddenInput.focus(); }
        hiddenInput.addEventListener('input', (e) => {
            const val = hiddenInput.value;
            if (val.length > 1) { socket.emit('kb_input', { char: val.substring(1) }); hiddenInput.value = " "; }
            else if (val.length === 0) { socket.emit('kb_input', { char: "BACKSPACE" }); hiddenInput.value = " "; }
        });

        trackpad.addEventListener('touchstart', (e) => {
            e.preventDefault();
            numTouches = e.touches.length;
            if (numTouches > maxTouches) maxTouches = numTouches;
            
            // Anchoring: If we add a new finger, we anchor our relative tracking to it
            const t = e.touches[numTouches - 1]; 
            startX = t.clientX; startY = t.clientY;
            lastX = t.clientX; lastY = t.clientY;
            
            if (numTouches === 1) {
                touchStart = Date.now();
                isMoving = true; hasMoved = false;
                isScrollMode = false;
                trackpad.classList.add('active');
                longPressTimer = setTimeout(() => {
                    if (!hasMoved && numTouches === 1) {
                        isHolding = true;
                        socket.emit('mouse_hold', { action: 'down' });
                        trackpad.classList.add('holding');
                    }
                }, 450);
            } else if (numTouches === 2 && !isHolding) {
                initialPinchDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
                // Scroll only if fingers are placed horizontally (Y diff < 50px)
                if (Math.abs(e.touches[0].clientY - e.touches[1].clientY) < 50) {
                    isScrollMode = true;
                }
            }
        }, {passive: false});

        trackpad.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const currentNumTouches = e.touches.length;
            if (currentNumTouches > maxTouches) maxTouches = currentNumTouches;

            // Use the last finger added to drive movement (for handoff continuation)
            const t = e.touches[currentNumTouches - 1];
            const dx = (t.clientX - lastX) * parseFloat(sensInput.value);
            const dy = (t.clientY - lastY) * parseFloat(sensInput.value);

            if (Math.abs(t.clientX - startX) > 10 || Math.abs(t.clientY - startY) > 10) {
                hasMoved = true;
                if(!isHolding) clearTimeout(longPressTimer);
            }

            // CRITICAL: If we are in "Holding" mode, we LOCK movement and ignore all other gestures
            if (isHolding) {
                if (Math.abs(dx) > 0.1 || Math.abs(dy) > 0.1) {
                    socket.emit('mouse_move', { dx, dy });
                }
            } else {
                // Normal non-holding gestures
                if (currentNumTouches === 1) {
                    socket.emit('mouse_move', { dx, dy });
                } else if (currentNumTouches === 2) {
                    const currentDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
                    const pinchDiff = currentDist - initialPinchDist;
                    
                    if (Math.abs(pinchDiff) > 50) {
                        socket.emit('mouse_zoom', { amount: pinchDiff });
                        initialPinchDist = currentDist;
                        isScrollMode = false;
                    } else if (isScrollMode) {
                        socket.emit('mouse_scroll', { amount: (t.clientY - lastY) * -10 });
                    }
                }
            }
            lastX = t.clientX; lastY = t.clientY;
        }, {passive: false});

        trackpad.addEventListener('touchend', (e) => {
            clearTimeout(longPressTimer);
            
            // Only finalize gestures and handle hold-release when ALL fingers are gone
            if (e.touches.length === 0) {
                const now = Date.now();
                const distX = lastX - startX;
                const distY = lastY - startY;

                if (isHolding) {
                    socket.emit('mouse_hold', { action: 'up' });
                    isHolding = false; trackpad.classList.remove('holding');
                } else if (!hasMoved) {
                    if (maxTouches === 1) {
                        if (now - lastTap < 300) { socket.emit('mouse_click', { button: 'double' }); lastTap = 0; }
                        else { socket.emit('mouse_click', { button: 'left' }); lastTap = now; }
                    } else if (maxTouches === 2) socket.emit('mouse_click', { button: 'right' });
                } else {
                    if (maxTouches === 3) {
                        if (distY < -60) socket.emit('system_cmd', { cmd: 'taskview' });
                        else if (distY > 60) socket.emit('system_cmd', { cmd: 'desktop' });
                    } else if (maxTouches === 2 && !isScrollMode) {
                        if (distX > 70) socket.emit('system_cmd', { cmd: 'back' });
                        else if (distX < -70) socket.emit('system_cmd', { cmd: 'forward' });
                    }
                }
                isMoving = false; maxTouches = 0; isScrollMode = false; trackpad.classList.remove('active');
            } else {
                // Handoff: Reset tracking to the remaining finger to prevent jumps
                const t = e.touches[e.touches.length - 1];
                lastX = t.clientX; lastY = t.clientY;
                startX = t.clientX; startY = t.clientY;
            }
            numTouches = e.touches.length;
        });
        sensInput.oninput = () => { document.getElementById('sens-val').innerText = sensInput.value; };
    </script>
</body>
</html>
"""

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@socketio.on('connect')
def on_connect():
    log_event("connection", f"Client paired: {request.remote_addr}")

@socketio.on('mouse_move')
def handle_move(data): move_mouse_raw(data.get('dx', 0), data.get('dy', 0))

@socketio.on('mouse_click')
def handle_click(data):
    btn = data.get('button', 'left')
    if btn == 'double':
        mouse_click_raw('left', True); mouse_click_raw('left', False)
        mouse_click_raw('left', True); mouse_click_raw('left', False)
        log_event("action", "Double Click")
    else:
        mouse_click_raw(btn, True); mouse_click_raw(btn, False)
        log_event("action", f"{btn.capitalize()} Click")

@socketio.on('mouse_hold')
def handle_hold(data):
    is_down = data.get('action') == 'down'
    mouse_click_raw('left', is_down)
    log_event("action", "L-Button " + ("DOWN" if is_down else "UP"))

@socketio.on('mouse_scroll')
def handle_scroll(data): mouse_scroll_raw(data.get('amount', 0))

@socketio.on('mouse_zoom')
def handle_zoom(data):
    amount = data.get('amount', 0)
    mouse_zoom_raw(120 if amount > 0 else -120)
    log_event("action", f"Zoom {'In' if amount > 0 else 'Out'}")

@socketio.on('kb_input')
def handle_kb(data):
    char = data.get('char')
    if char:
        send_unicode_char(char)
        log_event("keyboard", f"Key: {char}")

@socketio.on('system_cmd')
def handle_system(data):
    cmd = data.get('cmd')
    if cmd == 'desktop': send_win_d()
    elif cmd == 'taskview': send_win_tab()
    elif cmd == 'back': send_browser_nav('back')
    elif cmd == 'forward': send_browser_nav('forward')
    log_event("system", f"Cmd: {cmd}")

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        return s.getsockname()[0]
    except: return '127.0.0.1'
    finally: s.close()

def log_event(event_type, details):
    print(f"[{time.strftime('%H:%M:%S')}] {event_type.upper():<12} | {details}")

def run_server():
    local_ip = get_ip()
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*50 + "\n      PRO REMOTE SERVER v4.7\n" + "="*50)
    print(f" URL: http://{local_ip}:{PORT_WEB}\n" + "="*50 + "\n REAL-TIME LOGS:")
    socketio.run(app, host='0.0.0.0', port=PORT_WEB, debug=False, log_output=False)

if __name__ == '__main__':
    while True:
        try: run_server()
        except KeyboardInterrupt: sys.exit(0)
        except Exception as e: print(f"Error: {e}"); time.sleep(2)