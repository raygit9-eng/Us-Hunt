#!/usr/bin/env python3
"""US HUNT - local HTTP server + cloudflared quick tunnel with visitor logging."""

import os
import sys
import re
import csv
import time
import shutil
import signal
import threading
import subprocess
import functools
import http.server
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "Files")
LOG_FILE = os.path.join(SCRIPT_DIR, "visitors.log")
CSV_FILE = os.path.join(SCRIPT_DIR, "logs_export.csv")
PORT = 8080

HTTPD = None
TUNNEL_PROC = None
SERVER_THREAD = None

BANNER = r"""
   __  _______    __  ____  ___   ________
  / / / / ___/   / / / / / / / | / /_  __/
 / / / /\__ \   / /_/ / / / /  |/ / / /
/ /_/ /___/ /  / __  / /_/ / /|  / / /
\____//____/  /_/ /_/\____/_/ |_/ /_/
"""

INFO_BOX = """╭────────────────────────────── INFO ──────────────────────────────╮
│ Tool : US HUNT                                                   │
│ Author : Ray                                                     │
│ Status : ● READY                                                 │
╰──────────────────────────────────────────────────────────────────╯"""

MENU_BOX = """╭────────────┬─────────────────────────────────────╮
│ 1          │ Start Server & Tunnel               │
│ 2          │ View Live Visits (with details)     │
│ 3          │ Show Visit Log (Last 50)            │
│ 4          │ Export Logs (CSV)                   │
│ 5          │ Clear Logs                          │
│ 6          │ Settings                            │
│ 7          │ Help                                │
│ 8          │ Edit HTML File & Set Default        │
│ 0          │ Exit                                │
╰────────────┴─────────────────────────────────────╯"""

DEFAULT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>US HUNT Page</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 3rem; background: #0b0f14; color: #e6e6e6; }
  h1 { color: #6cf; }
  code { background: #1a2230; padding: 2px 6px; border-radius: 4px; }
</style>
</head>
<body>
  <h1>US HUNT</h1>
  <p>This page is being served by <code>us_hunt.py</code>.</p>
</body>
</html>
"""


def safe_input(prompt=""):
    try:
        return input(prompt)
    except EOFError:
        print("\n[*] EOF received, exiting.")
        try:
            stop_server_and_tunnel()
        except Exception:
            pass
        sys.exit(0)
    except KeyboardInterrupt:
        return ""


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def ensure_dirs():
    try:
        os.makedirs(BASE_DIR, exist_ok=True)
    except OSError as e:
        print(f"[!] Could not create {BASE_DIR}: {e}")


def list_html_files():
    ensure_dirs()
    try:
        names = sorted(n for n in os.listdir(BASE_DIR) if n.lower().endswith(".html"))
    except OSError as e:
        print(f"[!] Could not list {BASE_DIR}: {e}")
        return []
    return names


def print_html_table(files):
    if not files:
        print("[*] No HTML files found in Files/. Use option 8 to create one.")
        return
    print("╭────┬──────────────────────────────────────┬────────────╮")
    print("│ #  │ File                                 │ Size       │")
    print("├────┼──────────────────────────────────────┼────────────┤")
    for i, name in enumerate(files, 1):
        path = os.path.join(BASE_DIR, name)
        try:
            size = os.path.getsize(path)
        except OSError:
            size = -1
        size_str = f"{size} B" if size >= 0 else "n/a"
        print(f"│ {i:<2} │ {name:<36} │ {size_str:<10} │")
    print("╰────┴──────────────────────────────────────┴────────────╯")


def stop_server_and_tunnel():
    global HTTPD, TUNNEL_PROC, SERVER_THREAD

    if HTTPD is not None:
        try:
            HTTPD.shutdown()
        except Exception:
            pass
        try:
            HTTPD.server_close()
        except Exception:
            pass
        HTTPD = None

    if TUNNEL_PROC is not None:
        try:
            TUNNEL_PROC.terminate()
            try:
                TUNNEL_PROC.wait(timeout=3)
            except subprocess.TimeoutExpired:
                TUNNEL_PROC.kill()
        except Exception:
            pass
        TUNNEL_PROC = None

    SERVER_THREAD = None
    print("[+] Server and tunnel stopped.")


class TrackingHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, selected_file="index.html", directory=None, **kwargs):
        self._selected_file = selected_file
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        try:
            real_ip = self.headers.get("CF-Connecting-IP") or self.client_address[0]
        except Exception:
            real_ip = self.client_address[0] if self.client_address else "unknown"

        if self.path in ("", "/"):
            self.path = "/" + self._selected_file

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] IP: {real_ip} -> {self.path}"
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

        try:
            super().do_GET()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print(f"[!] Request handling error: {type(e).__name__}: {e}")

    def log_message(self, *args):
        pass

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except Exception as e:
            print(f"[!] Request handling error: {type(e).__name__}: {e}")


def prompt_for_html_file():
    files = list_html_files()
    print_html_table(files)
    print()
    choice = safe_input("Enter file number, name, or leave empty to cancel: ").strip()
    if not choice:
        return None

    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(files):
            return files[idx - 1]
        print(f"[!] Invalid index: {idx}")
        return None

    name = choice
    if not name.lower().endswith(".html"):
        name += ".html"
    if name not in files:
        # allow selecting an existing but non-listed path within BASE_DIR
        candidate = os.path.join(BASE_DIR, name)
        if not os.path.isfile(candidate):
            print(f"[!] File not found: {name}")
            return None
    return name


def check_cloudflared():
    try:
        result = subprocess.run(
            ["cloudflared", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
        )
        print(f"[*] cloudflared: {result.stdout.strip() or 'ok'}")
        return True
    except FileNotFoundError:
        print("[!] cloudflared not found in PATH.")
        print("[*] Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        return False
    except subprocess.TimeoutExpired:
        print("[!] cloudflared --version timed out.")
        return False
    except Exception as e:
        print(f"[!] cloudflared check failed: {type(e).__name__}: {e}")
        return False


def start_server_and_tunnel():
    global HTTPD, TUNNEL_PROC, SERVER_THREAD

    if HTTPD is not None or TUNNEL_PROC is not None:
        print("[!] Server or tunnel already running. Stop it first (option 0 exits).")
        return

    ensure_dirs()

    filename = prompt_for_html_file()
    if not filename:
        print("[*] Cancelled.")
        return

    full_path = os.path.join(BASE_DIR, filename)
    if not os.path.isfile(full_path):
        print(f"[!] File no longer exists: {full_path}")
        return

    if not check_cloudflared():
        return

    handler = functools.partial(
        TrackingHandler,
        selected_file=filename,
        directory=BASE_DIR,
    )

    try:
        HTTPD = http.server.HTTPServer(("", PORT), handler)
    except OSError as e:
        print(f"[!] Could not bind port {PORT}: {e}")
        print("[*] The port may be in use. Kill the other process or change PORT.")
        HTTPD = None
        return
    except Exception as e:
        print(f"[!] Server start failed: {type(e).__name__}: {e}")
        HTTPD = None
        return

    SERVER_THREAD = threading.Thread(target=HTTPD.serve_forever, daemon=True)
    SERVER_THREAD.start()
    print(f"[+] HTTP server listening on port {PORT} (serving {filename})")

    try:
        TUNNEL_PROC = subprocess.Popen(
            [
                "cloudflared",
                "tunnel",
                "--url",
                f"http://localhost:{PORT}",
                "--no-autoupdate",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        print("[!] cloudflared disappeared from PATH.")
        stop_server_and_tunnel()
        return
    except Exception as e:
        print(f"[!] Failed to launch cloudflared: {type(e).__name__}: {e}")
        stop_server_and_tunnel()
        return

    url_re = re.compile(r"https://([a-zA-Z0-9-]+)\.trycloudflare\.com")
    public_url = None
    deadline = time.time() + 30.0

    while time.time() < deadline:
        if TUNNEL_PROC.poll() is not None:
            remaining = ""
            try:
                if TUNNEL_PROC.stdout is not None:
                    remaining = TUNNEL_PROC.stdout.read() or ""
            except Exception:
                pass
            print(f"[!] cloudflared exited early (code {TUNNEL_PROC.returncode}).")
            if remaining.strip():
                print(remaining)
            TUNNEL_PROC = None
            stop_server_and_tunnel()
            return

        try:
            line = TUNNEL_PROC.stdout.readline()
        except Exception as e:
            print(f"[!] Error reading cloudflared output: {e}")
            break

        if not line:
            time.sleep(0.1)
            continue

        print(f"[cloudflared] {line.rstrip()}")
        m = url_re.search(line)
        if m and m.group(1) != "api":
            public_url = m.group(0)
            break

    if not public_url:
        print("[!] No public URL appeared within 30 seconds.")
        print("[*] Diagnostic hints:")
        print("      dig +short api.trycloudflare.com")
        print("      curl -4 -v https://api.trycloudflare.com")
        print("      env | grep -i proxy")
        print("[*] Common causes:")
        print("      - ISP blocking Cloudflare / trycloudflare")
        print("      - Broken IPv6 route (force IPv4 or disable IPv6)")
        print("      - Missing HTTP(S)_PROXY for outbound requests")
        print("      - DNS resolution failure for api.trycloudflare.com")
        stop_server_and_tunnel()
        return

    banner = f"""
╭──────────────────────────────────────────────────────────────────╮
│  [+] PUBLIC URL READY                                            │
│                                                                  │
│  🌐  {public_url:<58} │
│                                                                  │
│  Serving: {filename:<53} │
│  Local:   http://localhost:{PORT:<44} │
╰──────────────────────────────────────────────────────────────────╯
"""
    print(banner)
    print("[*] The server is running in the background.")
    print("[*] Use option 2 for live visits, option 3 for the last 50 lines.")


def view_live_visits():
    if not os.path.isfile(LOG_FILE):
        print("[*] No log file yet. Start the server first.")
        return
    print("[*] Streaming live visits. Press Ctrl+C to stop.\n")
    try:
        subprocess.run(["tail", "-f", LOG_FILE])
    except KeyboardInterrupt:
        print("\n[*] Stopped live view.")
    except FileNotFoundError:
        print("[!] 'tail' not available on this system.")
    except Exception as e:
        print(f"[!] Live view failed: {type(e).__name__}: {e}")


def show_last_50():
    if not os.path.isfile(LOG_FILE):
        print("[*] No log file yet.")
        return
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"[!] Could not read log: {e}")
        return
    if not lines:
        print("[*] Log is empty.")
        return
    tail = lines[-50:]
    print(f"[*] Showing last {len(tail)} of {len(lines)} lines:\n")
    for line in tail:
        print(line.rstrip())


def export_csv():
    if not os.path.isfile(LOG_FILE):
        print("[*] No log file to export.")
        return
    pattern = re.compile(r"\[(.*?)\] IP: (.*?) -> (.*)")
    count = 0
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as fin, \
             open(CSV_FILE, "w", encoding="utf-8", newline="") as fout:
            writer = csv.writer(fout)
            writer.writerow(["Timestamp", "IP", "Path"])
            for line in fin:
                m = pattern.match(line.strip())
                if m:
                    writer.writerow([m.group(1), m.group(2), m.group(3)])
                    count += 1
    except OSError as e:
        print(f"[!] Export failed: {e}")
        return
    print(f"[+] Exported {count} rows -> {CSV_FILE}")


def clear_logs():
    if not os.path.isfile(LOG_FILE):
        print("[*] No log file to clear.")
        return
    try:
        with open(LOG_FILE, "w", encoding="utf-8"):
            pass
        print("[+] Log file cleared.")
    except OSError as e:
        print(f"[!] Could not clear log: {e}")


def settings():
    print("(Not implemented yet)")


def help_menu():
    print("US HUNT - help")
    print("  1  Start Server & Tunnel    - pick an HTML file, run HTTP server + cloudflared")
    print("  2  View Live Visits         - tail -f the visitors.log")
    print("  3  Show Visit Log (Last 50) - print the last 50 log lines")
    print("  4  Export Logs (CSV)        - parse log -> logs_export.csv")
    print("  5  Clear Logs               - truncate visitors.log")
    print("  6  Settings                 - placeholder")
    print("  7  Help                     - this screen")
    print("  8  Edit HTML File           - create/edit an HTML file in Files/")
    print("  0  Exit                     - stop server/tunnel and quit")


def resolve_editor():
    env_editor = os.environ.get("EDITOR")
    if env_editor:
        return env_editor
    for candidate in ("nano", "vim", "vi"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def edit_html_file():
    ensure_dirs()
    files = list_html_files()
    if files:
        print_html_table(files)
        print("(enter a number to edit, or a new name to create)")

    choice = safe_input("Selection / filename: ").strip()
    if not choice:
        print("[*] Cancelled.")
        return

    if choice.isdigit() and files:
        idx = int(choice)
        if 1 <= idx <= len(files):
            filename = files[idx - 1]
        else:
            print(f"[!] Invalid index: {idx}")
            return
    else:
        filename = choice
        if not filename.lower().endswith(".html"):
            filename += ".html"

    file_path = os.path.join(BASE_DIR, filename)

    if not os.path.isfile(file_path):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(DEFAULT_HTML)
            print(f"[+] Created default template: {file_path}")
        except OSError as e:
            print(f"[!] Could not create file: {e}")
            return

    editor = resolve_editor()
    if not editor:
        print("[!] No editor found. Set $EDITOR or install nano/vim/vi.")
        return

    print(f"[*] Opening {file_path} with {editor}...")
    try:
        subprocess.call([editor, file_path])
    except FileNotFoundError:
        print(f"[!] Editor not found: {editor}")
    except KeyboardInterrupt:
        print("\n[*] Editor interrupted.")
    except Exception as e:
        print(f"[!] Editor failed: {type(e).__name__}: {e}")


def draw_menu():
    clear_screen()
    print(BANNER)
    print(INFO_BOX)
    print("─" * 66)
    print(MENU_BOX)
    print("─" * 66)


def main():
    ensure_dirs()
    while True:
        try:
            draw_menu()
            choice = safe_input("\nSelect an option: ").strip()

            if choice == "1":
                start_server_and_tunnel()
            elif choice == "2":
                view_live_visits()
            elif choice == "3":
                show_last_50()
            elif choice == "4":
                export_csv()
            elif choice == "5":
                clear_logs()
            elif choice == "6":
                settings()
            elif choice == "7":
                help_menu()
            elif choice == "8":
                edit_html_file()
            elif choice == "0":
                stop_server_and_tunnel()
                sys.exit(0)
            elif choice == "":
                pass
            else:
                print(f"[!] Unknown option: {choice}")

            try:
                safe_input("\nPress Enter to continue...")
            except SystemExit:
                raise
        except KeyboardInterrupt:
            print("\n[*] Interrupted. Returning to menu.")
            continue
        except SystemExit:
            raise
        except Exception as e:
            print(f"[!] Unexpected error: {type(e).__name__}: {e}")
            try:
                safe_input("\nPress Enter to continue...")
            except SystemExit:
                raise


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] Exiting.")
        stop_server_and_tunnel()
        sys.exit(0)
    except SystemExit:
        raise
