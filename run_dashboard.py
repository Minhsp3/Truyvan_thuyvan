from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
APP_FILE = PROJECT_DIR / "streamlit_app.py"
PREFERRED_PORT = int(os.environ.get("DASHBOARD_PORT", "8501"))


def get_lan_ip() -> str:
    """Return the preferred private-network address without sending data."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.connect(("8.8.8.8", 80))
            address = connection.getsockname()[0]
            if address and not address.startswith("127."):
                return address
    except OSError:
        pass

    try:
        for result in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = result[4][0]
            if address and not address.startswith("127."):
                return address
    except OSError:
        pass
    return "127.0.0.1"


def find_available_port(preferred_port: int, attempts: int = 50) -> int:
    """Use the preferred port, or the next available port if it is occupied."""
    for port in range(preferred_port, preferred_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            try:
                listener.bind(("0.0.0.0", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"Không tìm thấy cổng trống từ {preferred_port}.")


def main() -> int:
    if not APP_FILE.exists():
        print(f"Không tìm thấy ứng dụng: {APP_FILE}", file=sys.stderr)
        return 1

    lan_ip = get_lan_ip()
    port = find_available_port(PREFERRED_PORT)
    if port != PREFERRED_PORT:
        print(f"Cổng {PREFERRED_PORT} đang được sử dụng, chuyển sang cổng {port}.")
    print(f"Dashboard local: http://127.0.0.1:{port}")
    print(f"LAN access: http://{lan_ip}:{port}")
    print(f"Data folder: {PROJECT_DIR}")
    print("Nhấn Ctrl+C để dừng dashboard.\n", flush=True)

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(APP_FILE),
        f"--server.port={port}",
        "--server.address=0.0.0.0",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
    try:
        return subprocess.call(command, cwd=PROJECT_DIR)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
