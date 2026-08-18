#!/usr/bin/env python3
import os
import re
import sys
import time
import datetime
import subprocess
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

# ---------------------------------- CONSTANTS ----------------------------------
PORT = 8080
BASE_DIR = "Files"
LOG_FILE = "visitors.log"
SELECTED_FILE = ""
SERVER_PROC = None
TUNNEL_PROC = None
SERVER_THREAD = None
HTTPD = None

# ---------------------------------- SERVER ----------------------------------
class TrackingHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        real_ip = self.headers.get('CF-Connecting-IP')
        if not real_ip:
            real_ip = self.client_address[0]

        if self.path == '/':
            self.path = '/' + SELECTED_FILE

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] IP: {real_ip} -> {self.path}"
        print(log_entry)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")

        return SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, format, *args):
        pass

# ---------------------------------- UTILITY FUNCTIONS ----------------------------------
def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def print_banner():
    banner = r"""
   __  _______    __  ____  ___   ________
  / / / / ___/   / / / / / / / | / /_  __/
 / / / /\__ \   / /_/ / / / /  |/ / / /
/ /_/ /___/ /  / __  / /_/ / /|  / / /
\____//____/  /_/ /_/\____/_/ |_/ /_/
"""
    print(banner)
    print("╭────────────────────────────────────────────── INFO ──────────────────────────────────────────────╮")
    print("│ Tool : US HUNT                                                                                   │")
    print("│ Author : Ray                                                                                     │")
    print("│ Status : ● READY                                                                                 │")
    print("╰──────────────────────────────────────────────────────────────────────────────────────────────────╯")
    print("────────────────────────────────────────────────────────────────────────────────────────────────────")
    print("╭────────────┬─────────────────────────────────────╮")
    print("│ 1          │ Start Server & Tunnel               │")
    print("│ 2          │ View Live Visits (with details)     │")
    print("│ 3          │ Show Visit Log (Last 50)            │")
    print("│ 4          │ Export Logs (CSV)                   │")
    print("│ 5          │ Clear Logs                          │")
    print("│ 6          │ Settings                            │")
    print("│ 7          │ Help                                │")
    print("│ 8          │ Edit HTML File (nano) & Set Default │")
    print("│ 0          │ Exit                                │")
    print("╰────────────┴─────────────────────────────────────╯")
    print("────────────────────────────────────────────────────────────────────────────────────────────────────")

def list_html_files():
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
        return []
    files = [f for f in os.listdir(BASE_DIR) if f.endswith('.html') and os.path.isfile(os.path.join(BASE_DIR, f))]
    return files

def stop_server_and_tunnel():
    global HTTPD, TUNNEL_PROC
    if HTTPD:
        HTTPD.shutdown()
        HTTPD = None
    if TUNNEL_PROC:
        TUNNEL_PROC.terminate()
        TUNNEL_PROC = None
    print("[!] Server and tunnel stopped.")

def start_server_and_tunnel():
    global SELECTED_FILE, HTTPD, TUNNEL_PROC, SERVER_THREAD

    filename = input("Enter HTML file name (e.g., index.html): ").strip()
    if not filename:
        print("[!] No file name entered.")
        return
    if not filename.endswith('.html'):
        filename += '.html'

    file_path = os.path.join(BASE_DIR, filename)
    if not os.path.isfile(file_path):
        print(f"[!] File '{filename}' not found in '{BASE_DIR}'.")
        print("    Use option 8 to create or edit a file first.")
        return

    SELECTED_FILE = filename
    os.chdir(BASE_DIR)

    HTTPD = HTTPServer(('', PORT), TrackingHandler)
    SERVER_THREAD = threading.Thread(target=HTTPD.serve_forever, daemon=True)
    SERVER_THREAD.start()
    print(f"[+] Local server started on port {PORT}")

    cmd = ['cloudflared', 'tunnel', '--url', f'http://localhost:{PORT}']
    TUNNEL_PROC = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    url = None
    timeout = 15
    start_time = time.time()
    while time.time() - start_time < timeout:
        line = TUNNEL_PROC.stdout.readline()
        if not line:
            break
        match = re.search(r'https://([a-zA-Z0-9-]+)\.trycloudflare\.com', line)
        if match:
            if match.group(1) != 'api':
                url = match.group(0)
                break

    if not url:
        print("[!] Could not retrieve valid public URL. Make sure 'cloudflared' is installed and working.")
        print("    Check network connectivity and try again.")
        stop_server_and_tunnel()
        return

    border = "═" * 60
    print(f"\n{border}")
    print("  🌐  Public URL (share this)")
    print(border)
    print(f"  {url}")
    print(border)
    print("\n[*] Monitoring visitors... (Press Ctrl+C to stop)")

def view_live_visits():
    if not os.path.isfile(LOG_FILE):
        print("[!] No log file yet. Start the server first.")
        return
    print("\n[*] Live visits (Press Ctrl+C to stop):")
    try:
        subprocess.run(['tail', '-f', LOG_FILE])
    except KeyboardInterrupt:
        print("\n[!] Stopped live view.")

def show_last_50():
    if not os.path.isfile(LOG_FILE):
        print("[!] No log file.")
        return
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    last = lines[-50:] if len(lines) > 50 else lines
    for line in last:
        print(line.strip())

def export_csv():
    if not os.path.isfile(LOG_FILE):
        print("[!] No log file.")
        return
    csv_file = "logs_export.csv"
    with open(LOG_FILE, 'r', encoding='utf-8') as inf, open(csv_file, 'w', encoding='utf-8') as outf:
        outf.write("Timestamp,IP,Path\n")
        for line in inf:
            match = re.match(r'\[(.*?)\] IP: (.*?) -> (.*)', line.strip())
            if match:
                ts, ip, path = match.groups()
                outf.write(f"{ts},{ip},{path}\n")
    print(f"[+] Logs exported to '{csv_file}'.")

def clear_logs():
    if os.path.isfile(LOG_FILE):
        open(LOG_FILE, 'w').close()
        print("[+] Logs cleared.")
    else:
        print("[!] No log file to clear.")

def settings():
    print("[*] Settings: (Not implemented yet)")

def help_menu():
    print("""
    US HUNT – Help
    ===============
    1. Start Server & Tunnel   : Enter an HTML file name (must exist in Files/). Launches server and tunnel.
    2. View Live Visits        : Shows incoming requests in real-time (tail -f).
    3. Show Last 50 Logs       : Displays the most recent 50 entries.
    4. Export Logs (CSV)       : Creates logs_export.csv with timestamp, IP, path.
    5. Clear Logs              : Empties the visitor log file.
    6. Settings                : (Placeholder) Change port, directory, etc.
    7. Help                    : This screen.
    8. Edit HTML & Set Default : Creates/edits a file in nano and sets it as default (optional).
    0. Exit                    : Stops server and tunnel if running.
    """)

def edit_and_set_default():
    global SELECTED_FILE
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)

    filename = input("Enter HTML file name (e.g., index.html): ").strip()
    if not filename:
        print("[!] No name entered. Operation cancelled.")
        return
    if not filename.endswith('.html'):
        filename += '.html'

    file_path = os.path.join(BASE_DIR, filename)

    if not os.path.isfile(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>US HUNT Page</title>
</head>
<body>
    <h1>Hello from US HUNT</h1>
    <p>This is your custom page.</p>
</body>
</html>
""")
        print(f"[+] Created new file: {filename}")

    print(f"[*] Opening '{filename}' in nano. Edit and save when done.")
    subprocess.call(['nano', file_path])

    SELECTED_FILE = filename
    print(f"[+] File '{SELECTED_FILE}' set as default (for option 8 only).")

def main():
    global SELECTED_FILE
    while True:
        clear_screen()
        print_banner()
        choice = input("➜ Enter your choice [0/1/2/3/4/5/6/7/8]: ").strip()
        if choice == '0':
            stop_server_and_tunnel()
            print("[+] Exiting. Goodbye.")
            sys.exit(0)
        elif choice == '1':
            start_server_and_tunnel()
            input("\nPress Enter to continue...")
        elif choice == '2':
            view_live_visits()
            input("\nPress Enter to continue...")
        elif choice == '3':
            show_last_50()
            input("\nPress Enter to continue...")
        elif choice == '4':
            export_csv()
            input("\nPress Enter to continue...")
        elif choice == '5':
            clear_logs()
            input("\nPress Enter to continue...")
        elif choice == '6':
            settings()
            input("\nPress Enter to continue...")
        elif choice == '7':
            help_menu()
            input("\nPress Enter to continue...")
        elif choice == '8':
            edit_and_set_default()
            input("\nPress Enter to continue...")
        else:
            print("[!] Invalid choice.")
            time.sleep(1)

if __name__ == "__main__":
    main()