#!/usr/bin/env python3
"""Jarvis Desktop App Readiness Check.
Usage:
  python scripts/check_desktop.py          # human-readable
  python scripts/check_desktop.py --json   # JSON output

Checks Electron, npm, frontend, backend, and packaging readiness.
Does NOT launch the app or install anything.
"""

import json
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
JSON_MODE = "--json" in sys.argv

CRITICAL = 0
WARN = 0
OK = 0
results = []

def check(name, passed, critical=False, detail=""):
    global CRITICAL, WARN, OK
    if passed:
        status = "ok"
        OK += 1
        icon = "✅"
    elif critical:
        status = "fail"
        CRITICAL += 1
        icon = "❌"
    else:
        status = "warn"
        WARN += 1
        icon = "⚠️"
    if not JSON_MODE:
        print(f"  {icon} {name}{' — ' + detail if detail else ''}")
    results.append({"name": name, "status": status, "critical": critical, "detail": detail})

# ── 1. Package.json ──
print("1️⃣  Frontend / Electron Config")
pkg_json = PROJECT_DIR / "frontend" / "package.json"
if pkg_json.exists():
    pkg = json.loads(pkg_json.read_text())
    scripts = pkg.get("scripts", {})
    for s in ["desktop:dev", "dev", "build"]:
        check(f"npm script: {s}", s in scripts, critical=True)
    main_entry = pkg.get("main", "")
    check(f"main entry: {main_entry}", main_entry == "electron/main.js", critical=True)
else:
    check("package.json exists", False, critical=True, detail="frontend/package.json missing")

# ── 2. Electron files ──
print("2️⃣  Electron Files")
electron_dir = PROJECT_DIR / "frontend" / "electron"
for f in ["main.js", "preload.js", "backendManager.js"]:
    check(f"electron/{f}", (electron_dir / f).exists(), critical=True)

# ── 3. node_modules ──
print("3️⃣  Node Dependencies")
nm = PROJECT_DIR / "frontend" / "node_modules"
if nm.exists():
    check("node_modules exists", True)
    electron_pkg = nm / "electron"
    if electron_pkg.exists():
        check("electron installed", True)
    else:
        check("electron not installed", False, critical=False, detail="npm install electron (optional, only for desktop mode)")
else:
    check("node_modules missing", False, critical=True, detail="run: cd frontend && npm install")

# ── 4. Frontend dist ──
print("4️⃣  Frontend Build")
dist = PROJECT_DIR / "frontend" / "dist" / "index.html"
if dist.exists():
    check("dist/index.html built", True)
else:
    check("dist not built", False, critical=True, detail="run: cd frontend && npm run build")

# ── 5. Python / venv ──
print("5️⃣  Python Backend")
venv_python = (PROJECT_DIR / ".venv" / "bin" / "python") if sys.platform != "win32" else (PROJECT_DIR / ".venv" / "Scripts" / "python.exe")
if venv_python.exists():
    check(".venv Python exists", True)
else:
    check(".venv Python missing", False, critical=True, detail="run: scripts/setup_local_*.sh")

backend_main = PROJECT_DIR / "backend" / "main.py"
check("backend/main.py", backend_main.exists(), critical=True)

req_file = PROJECT_DIR / "requirements.txt"
check("requirements.txt", req_file.exists(), critical=True)

# ── 6. Ports ──
print("6️⃣  Port Availability")
import socket

def port_free(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        return result != 0
    except:
        return None

for port, name in [(8400, "Backend"), (5173, "Vite dev"), (11434, "Ollama")]:
    free = port_free(port)
    check(f"Port {port} ({name})", free if port != 11434 else True, critical=(port != 11434),
          detail="free" if free else "in use" if free is not None else "unknown")

# ── 7. Start scripts ──
print("7️⃣  Start Scripts")
scripts_dir = PROJECT_DIR / "scripts"
for s in [
    "setup_local_linux.sh", "setup_local_macos.sh", "setup_local_windows.ps1",
    "start_jarvis_linux.sh", "start_jarvis_macos.sh", "start_jarvis_windows.ps1",
    "check_environment.py", "smoke_test.py",
]:
    check(f"scripts/{s}", (scripts_dir / s).exists(), critical=True if "start_jarvis" in s else False)

# ── 8. Docs ──
print("8️⃣  Documentation")
docs_dir = PROJECT_DIR / "docs"
for d in ["portable-desktop.md", "setup-wizard.md", "troubleshooting.md", "security.md", "roadmap.md"]:
    check(f"docs/{d}", (docs_dir / d).exists(), critical=False, detail="present" if (docs_dir / d).exists() else "missing")

# ── 9. .env ──
print("9️⃣  Configuration")
env = PROJECT_DIR / ".env"
env_exists = env.exists()
if env_exists:
    check(".env exists", True)
else:
    check(".env missing", False, critical=False, detail="copy .env.example → .env")
env_example = PROJECT_DIR / ".env.example"
check(".env.example exists", env_example.exists(), critical=True)

# ── Summary ──
print()
print("=" * 50)
total = OK + WARN + CRITICAL
if CRITICAL == 0 and WARN == 0:
    msg = "🎉 DESKTOP READY"
elif CRITICAL == 0:
    msg = f"✅ DESKTOP READY ({WARN} advisory)"
else:
    msg = f"⚠️  {CRITICAL} ISSUE(S) — fix before desktop launch"
print(f"  {msg}")
print(f"  {OK} ok, {WARN} warnings, {CRITICAL} critical")
print("=" * 50)

if not JSON_MODE and CRITICAL > 0:
    print()
    print("💡 Fix critical issues:")
    print("   bash scripts/setup_local_linux.sh    # One-time setup")
    print("   cd frontend && npm install            # Node deps")
    print("   cd frontend && npm run build          # Build frontend")

if JSON_MODE:
    print(json.dumps({"critical": CRITICAL, "warnings": WARN, "ok": OK, "items": results}, indent=2))

sys.exit(0 if CRITICAL == 0 else 1)
