#!/usr/bin/env python3
"""Jarvis Environment Checker — runs locally without any installed deps.
Usage:
  python scripts/check_environment.py          # human-readable
  python scripts/check_environment.py --json   # JSON output
  python scripts/check_environment.py --quiet  # only errors
"""

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
JSON_MODE = "--json" in sys.argv
QUIET = "--quiet" in sys.argv


def log(msg, ok=True):
    if JSON_MODE:
        return
    if QUIET and ok:
        return
    icon = "✅" if ok else "❌"
    print(f"  {icon} {msg}")


def get_python_info():
    return {
        "version": sys.version,
        "executable": sys.executable,
        "has_venv": (PROJECT_DIR / ".venv").exists(),
    }


def get_node_info():
    try:
        v = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        npm_v = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=5)
        return {
            "found": True,
            "node": v.stdout.strip(),
            "npm": npm_v.stdout.strip(),
        }
    except Exception:
        return {"found": False}


def get_os_info():
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }


def check_port(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        return result == 0
    except Exception:
        return None


def check_backend_health():
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:8400/health")
        res = urllib.request.urlopen(req, timeout=2)
        data = json.loads(res.read().decode())
        return {"online": True, "status": data.get("status", "ok"), "version": data.get("version", "?")}
    except Exception:
        return {"online": False}


def check_requirements():
    req_file = PROJECT_DIR / "requirements.txt"
    if not req_file.exists():
        return {"installed": True, "missing": []}
    try:
        import pkg_resources
        with open(req_file) as f:
            required = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        missing = []
        for req in required:
            try:
                pkg_resources.require(req)
            except Exception:
                missing.append(req)
        return {"installed": len(missing) == 0, "missing": missing}
    except Exception:
        return {"installed": None, "error": "Cannot check"}


def check_ollama():
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags")
        res = urllib.request.urlopen(req, timeout=2)
        data = json.loads(res.read().decode())
        models = [m.get("name", "?") for m in data.get("models", [])]
        return {"reachable": True, "models": models}
    except Exception as e:
        return {"reachable": False, "error": str(e)}


def check_frontend():
    dist = PROJECT_DIR / "frontend" / "dist" / "index.html"
    node_modules = PROJECT_DIR / "frontend" / "node_modules"
    electron_main = PROJECT_DIR / "frontend" / "electron" / "main.js"
    return {
        "dist_built": dist.exists(),
        "node_modules": node_modules.exists(),
        "electron_config": electron_main.exists(),
    }


def run():
    results = {}

    # OS
    results["os"] = get_os_info()
    if not JSON_MODE:
        print("🔍 Jarvis Environment Check")
        print(f"   OS: {results['os']['system']} {results['os']['release']} ({results['os']['machine']})")
        print()

    # Python
    python = get_python_info()
    results["python"] = python
    ok = sys.version_info >= (3, 10)
    if not JSON_MODE:
        print(f"Python:  {python['version']}")
        log(f"Python 3.10+", ok)
        log(f".venv exists", python["has_venv"])

    # Node
    node = get_node_info()
    results["node"] = node
    if not JSON_MODE:
        if node["found"]:
            log(f"Node.js {node['node']} (npm {node['npm']})", True)
        else:
            log("Node.js not found", False)

    # Ports
    port_8400 = check_port(8400)
    results["ports"] = {"8400": port_8400}
    if not JSON_MODE:
        if port_8400:
            log("Port 8400 in use (backend running)")
        else:
            log("Port 8400 free (backend not running)")

    # Backend
    backend = check_backend_health()
    results["backend"] = backend
    if not JSON_MODE:
        if backend["online"]:
            log(f"Backend: online (v{backend['version']})", True)
        else:
            log("Backend: offline", False)

    # Requirements
    reqs = check_requirements()
    results["requirements"] = reqs
    if not JSON_MODE:
        if reqs["installed"] is True:
            log("Python requirements installed", True)
        elif reqs["installed"] is False:
            log(f"Missing packages: {', '.join(reqs['missing'][:5])}...", False)

    # Frontend
    fe = check_frontend()
    results["frontend"] = fe
    if not JSON_MODE:
        log(f"Frontend dist", fe["dist_built"])
        log(f"node_modules", fe["node_modules"])
        log(f"Electron config", fe["electron_config"])

    # Ollama
    ollama = check_ollama()
    results["ollama"] = ollama
    if not JSON_MODE:
        if ollama["reachable"]:
            log(f"Ollama reachable with {len(ollama['models'])} model(s)", True)
            for m in ollama["models"][:3]:
                print(f"     📦 {m}")
        else:
            log("Ollama not reachable (offline/uninstalled)", False)
            print("     💡 Install: curl -fsSL https://ollama.com/install.sh | sh")

    # Summary
    issues = []
    if not ok: issues.append("Python version < 3.10")
    if not node["found"]: issues.append("Node.js not found")
    if not python["has_venv"]: issues.append(".venv missing")
    if not fe["dist_built"]: issues.append("Frontend not built")
    if not fe["node_modules"]: issues.append("node_modules missing")
    if not backend["online"]: issues.append("Backend offline")
    if not ollama["reachable"]: issues.append("Ollama offline (optional)")

    results["summary"] = {
        "issues": issues,
        "ready": len([i for i in issues if "Ollama" not in i and "optional" not in i]) == 0,
    }

    if JSON_MODE:
        print(json.dumps(results, indent=2))
    else:
        print()
        if results["summary"]["ready"]:
            print("✅ Jarvis environment is ready!")
        else:
            print("⚠️  Issues found:")
            for issue in issues:
                print(f"   - {issue}")
            print()
            print("Run scripts/setup_local_*.sh to fix.")


if __name__ == "__main__":
    run()
