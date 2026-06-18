#!/usr/bin/env python3
"""Cross-platform stop script for ForensicX. Works on macOS, Linux, and Windows."""

import platform
import subprocess
import sys


def log(msg: str) -> None:
    print(f"[ForensicX] {msg}", flush=True)


def kill_port(port: int, name: str) -> None:
    system = platform.system()
    try:
        if system == "Windows":
            # Find PIDs listening on the port
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True,
            )
            pids = set()
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        pids.add(parts[-1])
            if pids:
                for pid in pids:
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                log(f"{name} stopped (port {port}).")
            else:
                log(f"No {name} running on port {port}.")
        else:
            # macOS / Linux
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True,
            )
            pids = result.stdout.strip()
            if pids:
                for pid in pids.splitlines():
                    subprocess.run(["kill", "-9", pid.strip()], capture_output=True)
                log(f"{name} stopped (port {port}).")
            else:
                log(f"No {name} running on port {port}.")
    except Exception as e:
        log(f"Could not stop {name}: {e}")


def main() -> None:
    kill_port(8000, "Backend")
    kill_port(5173, "Frontend")
    log("All stopped.")


if __name__ == "__main__":
    main()
