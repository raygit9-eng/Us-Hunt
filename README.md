US HUNT – Cloudflare Tunnel IP Tracker

«Track every visitor. Expose any HTML page. Zero traces.»

Description

US HUNT is a lightweight Python tool that serves any HTML file from a local directory, exposes it to the internet via a Cloudflare Tunnel, and logs every visitor's real public IP address in real time.

No port forwarding. No static IP. Just a single command and a shareable link.

Works on:

- Termux (Android)
- Linux (Debian, Ubuntu, Kali, Arch, etc.)
- macOS
- Windows (via WSL or native Python)

---

Features

- Instant Public URL – Get a "*.trycloudflare.com" link in seconds.
- Real Visitor IP Extraction – Uses Cloudflare's "CF-Connecting-IP" header (not local "127.0.0.1").
- Live Monitoring – Watch incoming requests and IPs stream directly in your terminal.
- File Management – Create or edit HTML files directly from the tool (nano).
- Log Export – Save all visits as CSV with timestamp, IP, and requested path.
- Log Control – View last 50 entries, clear logs, or tail live.

---

Repository

git clone https://github.com/raygit9-eng/Us-Hunt.git
cd Us-Hunt

---

Installation

1. Install Python 3.6+

Termux (Android)

pkg update && pkg upgrade
pkg install python

Python is now available in Termux.

Linux (Debian/Ubuntu/Kali)

sudo apt update
sudo apt install python3 python3-pip -y

Linux (Arch)

sudo pacman -S python python-pip

macOS

brew install python

Windows

Download and install Python from python.org.

Make sure to check "Add Python to PATH" during installation.

---

2. Install Cloudflared (Tunnel Client)

Termux (Android)

Option A – Direct package (recommended):

pkg install cloudflared -y

Option B – Manual download (if package fails):

wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm
mv cloudflared-linux-arm cloudflared
chmod +x cloudflared
mv cloudflared $PREFIX/bin/

Linux (Debian/Ubuntu/Kali)

Option A – Using apt (recommended):

sudo apt update
sudo apt install cloudflared -y

Option B – Manual download:

wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

Linux (Arch)

sudo pacman -S cloudflared

macOS

brew install cloudflared

Windows

Option A – Using Chocolatey:

choco install cloudflared

Option B – Manual download:

1. Go to Cloudflared releases
2. Download cloudflared-windows-amd64.exe
3. Rename to cloudflared.exe and place it in a folder included in your PATH (e.g., C:\Windows\System32)

---

3. Install Nano (for Option 8 – HTML editing)

Termux

pkg install nano -y

Linux (Debian/Ubuntu/Kali)

sudo apt install nano -y

Linux (Arch)

sudo pacman -S nano

macOS

brew install nano

Windows

Nano is available via WSL, or you can use Notepad/any editor of your choice.

Note: Option 8 may need adjustment if nano is not available.

---

Usage

Directory Structure

Us-Hunt/
├── us_hunt.py
└── Files/                # Place your .html files here
    ├── index.html
    ├── page2.html
    └── ...

Run the Tool

python3 us_hunt.py

Menu Options

Option Description

1 Start Server & Tunnel – Prompts for an HTML file name (must exist in Files/), launches the local server and Cloudflare tunnel, then displays the public URL.

2 View Live Visits – Streams incoming requests with timestamps and IPs (uses tail -f on log file).

3 Show Last 50 Logs – Displays the most recent 50 log entries.

4 Export Logs (CSV) – Converts visitors.log into logs_export.csv with columns: Timestamp, IP, Path.

5 Clear Logs – Empties the entire visitors.log file.

6 Settings – (Placeholder for future config)

7 Help – Shows this quick reference.

8 Edit/Create HTML File – Asks for a file name, creates it with a basic template if missing, opens it in nano for editing, and sets it as the default selection for option 1.

0 Exit – Stops the server and tunnel gracefully.

---

Example Workflow

$ python3 us_hunt.py

➜ Enter your choice: 8
Enter HTML file name: mypage.html
[+] Created new file: mypage.html
[*] Opening 'mypage.html' in nano. Edit and save when done.
[+] File 'mypage.html' set as default.

➜ Enter your choice: 1
Enter HTML file name: mypage.html
[+] Local server started on port 8080

════════════════════════════════════════════════════════════
  Public URL (share this)
════════════════════════════════════════════════════════════
  https://amazing-words-1234.trycloudflare.com
════════════════════════════════════════════════════════════

[*] Monitoring visitors... (Press Ctrl+C to stop)
[2025-01-01 12:00:00] IP: 192.168.1.100 -> /mypage.html
[2025-01-01 12:00:05] IP: 10.0.0.50 -> /mypage.html

---

How It Works

1. Local Server – Python's http.server serves the chosen HTML file from the Files/ directory.
2. Cloudflare Tunnel – cloudflared creates a secure outbound connection, generating a public *.trycloudflare.com URL.
3. IP Extraction – Cloudflare injects the CF-Connecting-IP header into every request. The handler reads this header and logs it.
4. Logging – All visits are written to visitors.log with timestamps and request paths.

---

Configuration

You can tweak the following constants at the top of us_hunt.py:

PORT = 8080                 # Local server port
BASE_DIR = "Files"          # Directory for HTML files
LOG_FILE = "visitors.log"   # Log file name

---

Log Format

[2025-01-01 12:00:00] IP: 192.168.1.100 -> /index.html
[2025-01-01 12:00:05] IP: 10.0.0.50 -> /page2.html

---

Requirements

- Python 3.6+
- cloudflared (must be in $PATH)
- nano (for option 8 – can be replaced with vim or any editor)

---

Troubleshooting

"cloudflared: command not found"

- Ensure cloudflared is installed and in your PATH.
- On Termux, try pkg install cloudflared or manually download the binary.
- On Linux, check if it's installed via which cloudflared.

"No module named 'http'"

- This is a built-in Python module. Ensure you're using Python 3.6+.

Public URL shows api.trycloudflare.com

- The tool filters out api. subdomains automatically. Wait a few seconds for the correct URL to appear.

Nano doesn't open on Windows

- Use a different editor by modifying the edit_and_set_default() function in us_hunt.py.

---

Author

Ray – GitHub

---

Disclaimer

This tool is intended for educational and authorized testing purposes only. Do not use it to track individuals without explicit consent. The author is not responsible for any misuse.

---

License

MIT – Use freely, modify, and distribute.

---

Happy hunting
