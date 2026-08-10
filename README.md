# Remote Mouse Server Pro

A Python-based local network server that transforms a mobile device into a fully functional trackpad and keyboard for a Windows PC. 
Overview
This application uses a Flask web server and Socket.IO to provide real-time, low-latency communication between a mobile web browser and a host PC. It directly interfaces with the Windows API (ctypes.windll.user32) to simulate hardware-level mouse and keyboard inputs, ensuring accurate and native-feeling control. It is specifically built with 64-bit compatibility structures. 


## Features
•	Mouse Control: Simulates raw mouse movement, scrolling, and clicking (Left, Right, and Double-click). 
•	Keyboard Input: Features a hidden text input field on the mobile UI to send Unicode characters, Backspace, and Enter commands. 
•	System Shortcuts: Includes dedicated system commands to show the desktop (Win+D), open Task View (Win+Tab), and navigate web browsers (Alt+Left/Right). 
•	Adjustable Sensitivity: Features a built-in UI slider to adjust trackpad sensitivity from 0.5 to 5.0. 
•	Real-Time Logging: Outputs a live activity log directly in the host machine's terminal. 

## Supported Touch Gestures
The mobile web interface supports advanced multi-touch gestures: 
•	1-Finger: Move the cursor, tap to click, or long-press to initiate a drag/hold action. 
•	2-Finger: Scroll vertically (with horizontal finger placement). Swipe left or right for browser forward/back navigation. Pinch in/out to trigger Ctrl+Wheel zooming. 
•	3-Finger: Swipe up to open Windows Task View. Swipe down to show the Desktop. 

### Technology Stack
•	Backend: Python 3, Flask, and Flask-SocketIO (using the Eventlet async mode). 
•	System Integration: Python's built-in ctypes library to interact with Windows KEYBDINPUT, MOUSEINPUT, and HARDWAREINPUT C-structures. 
•	Frontend: A single-page HTML/JS/CSS interface served directly from the Python script, utilizing the Socket.IO client library. 

## Prerequisites
•	Operating System: Windows (relies entirely on windll.user32). 
•	Application/Library: Python installed and added to system PATH.
•	Network: The PC and mobile device must be connected to the same local area network (LAN). 

## Installation
Run the Setup.exe file to install dependencies.
Please refer to the SETUP_README.md file for detailed instructions on how to install the necessary dependencies (Flask, flask-socketio, eventlet) using the included automated setup utility.

## Usage
Run the remote_mouse3.exe file. 
OR,
1.	Start the Server:
Bash
python remote_mouse3.py
2.	Connect:
o	Upon starting, the terminal will clear and display the Remote Mouse Server Pro header. 
o	It will output a local URL operating on port 5000 (e.g., [http://192.168.1.](http://192.168.1.)X:5000). 
o	Open this URL in your mobile device's web browser. 
3.	Interface Options:
o	Use the Sync button to force a reconnection if the connection drops. 
o	Use the Keyboard button to trigger the mobile device's native on-screen keyboard. 
o	Use the FS button to toggle full screen mode for a native app experience.

###	IF APPLICATION (.exe) DOES NOT WORK
Open a terminal in the /Code directory, and run the following command:
“python Setup.py”
“python Remote_Mouse.py”
