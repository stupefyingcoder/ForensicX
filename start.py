#!/usr/bin/env python3
"""Cross-platform start script for ForensicX. Works on macOS, Linux, and Windows."""

import os
import platform
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
VENV_DIR = BACKEND_DIR / "venv"
WEIGHTS_DIR = BACKEND_DIR / "weights"
RUNTIME_DIR = ROOT_DIR / ".runtime"
TEMP_DIR = RUNTIME_DIR / "tmp"
PIP_CACHE_DIR = RUNTIME_DIR / "pip-cache"
NPM_CACHE_DIR = RUNTIME_DIR / "npm-cache"
FRONTEND_PORT = os.getenv("FRONTEND_PORT", "5174")

IS_WINDOWS = platform.system() == "Windows"
PYTHON_CMD = sys.executable  # Use whatever Python is running this script
VENV_BIN_DIR = VENV_DIR / ("Scripts" if IS_WINDOWS else "bin")
VENV_PYTHON = VENV_BIN_DIR / ("python.exe" if IS_WINDOWS else "python")
VENV_UVICORN = VENV_BIN_DIR / ("uvicorn.exe" if IS_WINDOWS else "uvicorn")

processes: list[subprocess.Popen] = []


def log(msg: str) -> None:
    print(f"[ForensicX] {msg}", flush=True)


def err(msg: str) -> None:
    print(f"[ForensicX] ERROR: {msg}", file=sys.stderr, flush=True)


def cleanup(*_: object) -> None:
    log("Shutting down...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            p.kill()
    log("Done.")
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def check_command(name: str, install_hint: str) -> bool:
    if shutil.which(name):
        return True
    err(f"{name} not found. {install_hint}")
    return False


def download_file(url: str, dest: Path) -> None:
    if dest.exists():
        return
    log(f"Downloading {dest.name}...")
    try:
        urllib.request.urlretrieve(url, str(dest))
        log(f"{dest.name} downloaded ({dest.stat().st_size // (1024*1024)}MB).")
    except Exception as e:
        err(f"Failed to download {dest.name}: {e}")
        if dest.exists():
            dest.unlink()


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> None:
    result = subprocess.run(cmd, cwd=cwd)
    if check and result.returncode != 0:
        err(f"Command failed: {' '.join(str(c) for c in cmd)}")
        sys.exit(1)


def main() -> None:
    log("Checking prerequisites...")

    for directory in (TEMP_DIR, PIP_CACHE_DIR, NPM_CACHE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TMP", str(TEMP_DIR))
    os.environ.setdefault("TEMP", str(TEMP_DIR))
    os.environ.setdefault("PIP_CACHE_DIR", str(PIP_CACHE_DIR))
    os.environ.setdefault("npm_config_cache", str(NPM_CACHE_DIR))
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")

    # Check Python version
    if sys.version_info < (3, 10):
        err(f"Python 3.10+ required, got {sys.version}. Install from https://python.org")
        sys.exit(1)
    log(f"Python {sys.version.split()[0]}")

    # Check Node.js
    if not check_command("node", "Install from https://nodejs.org"):
        sys.exit(1)
    if not check_command("npm", "Install from https://nodejs.org"):
        sys.exit(1)

    # --- Backend setup ---
    log("Setting up backend...")

    if not VENV_DIR.exists():
        log("Creating virtual environment...")
        run([PYTHON_CMD, "-m", "venv", str(VENV_DIR)])

    log("Installing backend dependencies...")
    run([str(VENV_PYTHON), "-m", "pip", "install", "--quiet", "--no-cache-dir", "--upgrade", "pip"])
    run([str(VENV_PYTHON), "-m", "pip", "install", "--quiet", "--no-cache-dir", "-r", str(BACKEND_DIR / "requirements.txt")])

    # --- Download model weights ---
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    # Lightweight models only (~5MB each) — BSRGAN/x4plus omitted (too heavy for 8GB machines)
    weights = {
        "realesr-general-x4v3.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth",
        "realesr-general-wdn-x4v3.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth",
    }

    for name, url in weights.items():
        download_file(url, WEIGHTS_DIR / name)

    # SRGAN weights — check if they exist (custom trained, not publicly hosted)
    srgan_path = WEIGHTS_DIR / "srgan_generator.pth"
    if not srgan_path.exists():
        log(f"WARNING: {srgan_path.name} not found. SRGAN model will not be available.")
        log("  Place the weights file in backend/weights/ manually.")

    # --- Frontend setup ---
    log("Setting up frontend...")
    npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"

    if not (FRONTEND_DIR / "node_modules").exists():
        log("Installing frontend dependencies...")
        run([npm_cmd, "install"], cwd=FRONTEND_DIR)
    else:
        log("Frontend dependencies already installed.")

    # --- Create .env if missing ---
    frontend_env = FRONTEND_DIR / ".env"
    if not frontend_env.exists():
        log("Creating frontend .env...")
        frontend_env.write_text("VITE_API_BASE=http://127.0.0.1:8000/api\n")

    # --- Ensure a strong JWT secret (persisted across runs) ---
    # Without this the app falls back to the built-in default ("change-this-in-
    # production", 25 bytes) which is insecure and below JWT's 32-byte minimum.
    if not os.environ.get("JWT_SECRET"):
        jwt_secret_file = RUNTIME_DIR / "jwt_secret"
        if jwt_secret_file.exists():
            os.environ["JWT_SECRET"] = jwt_secret_file.read_text(encoding="utf-8").strip()
        else:
            import secrets
            secret = secrets.token_hex(32)  # 64 hex chars
            jwt_secret_file.write_text(secret, encoding="utf-8")
            os.environ["JWT_SECRET"] = secret
            log("Generated a new JWT secret (stored in .runtime/jwt_secret).")

    # --- Start backend ---
    log("Starting backend on http://127.0.0.1:8000 ...")
    backend = subprocess.Popen(
        # --reload-dir app: only watch source, not the venv. Watching the whole
        # backend dir made StatReload walk thousands of venv files and crash on
        # Windows with WinError 1450 (insufficient system resources).
        [str(VENV_UVICORN), "app.main:app", "--reload", "--reload-dir", "app",
         "--port", "8000", "--host", "127.0.0.1"],
        cwd=BACKEND_DIR,
    )
    processes.append(backend)

    # Wait for backend
    log("Waiting for backend...")
    for i in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2)
            log("Backend is ready.")
            break
        except Exception:
            if i == 29:
                err("Backend failed to start. Check the logs above.")
                cleanup()
            time.sleep(1)

    # --- Start frontend ---
    log(f"Starting frontend on http://localhost:{FRONTEND_PORT} ...")
    frontend = subprocess.Popen([npm_cmd, "run", "dev", "--", "--host", "127.0.0.1", "--port", FRONTEND_PORT], cwd=FRONTEND_DIR)
    processes.append(frontend)

    time.sleep(2)
    print()
    log("=========================================")
    log("  ForensicX is running!")
    log(f"  Frontend: http://localhost:{FRONTEND_PORT}")
    log("  Backend:  http://127.0.0.1:8000")
    log("  API docs: http://127.0.0.1:8000/docs")
    log("=========================================")
    log("Press Ctrl+C to stop both servers.")
    print()

    # Wait for either process to exit
    try:
        while True:
            if backend.poll() is not None or frontend.poll() is not None:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
