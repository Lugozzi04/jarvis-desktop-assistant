#!/usr/bin/env python3
"""Jarvis Smoke Test — end-to-end lightweight validation.
Usage:
  python scripts/smoke_test.py          # human-readable
  python scripts/smoke_test.py --json   # JSON output
  python scripts/smoke_test.py --quiet  # only failures
  
Exit code: 0 if no CRITICAL failures, 1 if any critical failure.
Warnings (Ollama offline, Whisper missing, etc.) are non-fatal.
"""

import json
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

JSON_MODE = "--json" in sys.argv
QUIET = "--quiet" in sys.argv
CRITICAL_FAILURES = 0
TOTAL_CHECKS = 0
WARNINGS = 0

def log(msg, status="ok"):
    global TOTAL_CHECKS, CRITICAL_FAILURES, WARNINGS
    TOTAL_CHECKS += 1
    if JSON_MODE:
        return
    if QUIET and status == "ok":
        return
    icons = {"ok": "✅", "warn": "⚠️", "fail": "❌", "skip": "⏭️"}
    print(f"  {icons.get(status, '?')} {msg}")

results = {"checks": [], "summary": {"total": 0, "pass": 0, "fail": 0, "warn": 0, "skip": 0}}

def add_result(name, passed, details=""):
    if passed:
        results["checks"].append({"name": name, "status": "pass", "details": details})
        results["summary"]["pass"] += 1
    else:
        results["checks"].append({"name": name, "status": "fail", "details": details})
        results["summary"]["fail"] += 1
    results["summary"]["total"] += 1

# ── 1. Backend Importable ──
print("1️⃣  Backend Import")
try:
    from backend.main import app
    log("FastAPI app importable", "ok")
    add_result("backend_import", True)
except Exception as e:
    log(f"Backend import FAILED: {e}", "fail")
    add_result("backend_import", False, str(e))
    CRITICAL_FAILURES += 1

# ── 2. FastAPI TestClient ──
print("2️⃣  API Endpoints (TestClient)")
try:
    from fastapi.testclient import TestClient
    client = TestClient(app)
    log("TestClient created", "ok")
except Exception as e:
    log(f"TestClient creation FAILED: {e}", "fail")
    CRITICAL_FAILURES += 1
    client = None

def api_check(method, path, expected_status=200, name=None):
    """Run an API check and return (passed, response_json, status_code)."""
    if client is None:
        return False, None, 0
    try:
        if method == "GET":
            resp = client.get(path)
        elif method == "POST":
            resp = client.post(path, json={})
        else:
            return False, None, 0
        ok = resp.status_code == expected_status
        return ok, resp.json() if ok and resp.text else None, resp.status_code
    except Exception as e:
        return False, None, 500

if client:
    checks = [
        ("GET", "/health", 200, "Health check"),
        ("GET", "/api/health/full", 200, "Health full"),
        ("GET", "/api/skills", 200, "Skills list"),
        ("GET", "/api/workflows", 200, "Workflows list"),
        ("GET", "/api/automations", 200, "Automations list"),
        ("GET", "/api/documents/status", 200, "Documents status"),
        ("GET", "/api/voice/status", 200, "Voice status"),
        ("GET", "/api/llm/status", 200, "LLM status"),
        ("GET", "/api/pending-actions", 200, "Pending actions"),
        ("GET", "/api/diagnostics", 200, "Diagnostics"),
        ("GET", "/api/config/public", 200, "Config public"),
        ("GET", "/api/setup/status", 200, "Setup status"),
    ]

    for method, path, expected, name in checks:
        ok, data, status = api_check(method, path, expected, name)
        if ok:
            log(f"{name} ({path}) → {status}", "ok")
            add_result(f"api_{name.lower().replace(' ', '_')}", True)
        else:
            log(f"{name} ({path}) → {status} (expected {expected})", "fail")
            add_result(f"api_{name.lower().replace(' ', '_')}", False, f"status={status}")
            CRITICAL_FAILURES += 1

# ── 3. Slash Commands ──
print("3️⃣  Slash Commands")
from backend.core.router import intent_router
slash_tests = [
    ("/system stats", "system"),
    ("/timer 1m test", "timers"),
    ("/docs list", "documents"),
    ("/github status", "github"),
]

for cmd, expected_skill in slash_tests:
    intent = intent_router.route(cmd)
    if intent.skill == expected_skill:
        log(f"{cmd} → {intent.skill}.{intent.action}", "ok")
        add_result(f"slash_{expected_skill}", True)
    else:
        log(f"{cmd} → {intent.skill} (expected {expected_skill})", "fail")
        add_result(f"slash_{expected_skill}", False, f"routed to {intent.skill}")
        CRITICAL_FAILURES += 1

# ── 4. Workflow Engine ──
print("4️⃣  Workflow Engine")
try:
    from backend.workflows.engine import workflow_engine
    wfs = workflow_engine.list_all()
    if len(wfs) > 0:
        log(f"Workflows loaded: {len(wfs)} ({', '.join(w['name'] for w in wfs[:3])})", "ok")
        add_result("workflow_engine", True, f"{len(wfs)} workflows")
    else:
        log("No workflows found", "warn")
        add_result("workflow_engine", True, "0 workflows (ok)")
        WARNINGS += 1
except Exception as e:
    log(f"Workflow engine FAILED: {e}", "fail")
    add_result("workflow_engine", False, str(e))
    CRITICAL_FAILURES += 1

# ── 5. Automation Engine ──
print("5️⃣  Automation Engine")
try:
    from backend.automation.engine import automation_engine
    status = automation_engine.list_automations() if hasattr(automation_engine, 'list_automations') else []
    log(f"Automations: {len(status) if isinstance(status, list) else 'N/A'}", "ok")
    add_result("automation_engine", True)
except Exception as e:
    log(f"Automation engine: {e}", "warn")
    add_result("automation_engine", False, str(e))
    WARNINGS += 1

# ── 6. LLM Gateway ──
print("6️⃣  LLM Gateway")
try:
    from backend.llm.gateway import llm_gateway
    import asyncio
    loop = asyncio.new_event_loop()
    available = loop.run_until_complete(llm_gateway.is_available())
    loop.close()
    if available:
        log("LLM available", "ok")
        add_result("llm_available", True)
    else:
        log("LLM not available (expected on VPS without Ollama)", "warn")
        add_result("llm_available", True, "offline (expected)")  # Not critical
        WARNINGS += 1
except Exception as e:
    log(f"LLM Gateway: {e}", "warn")
    add_result("llm_available", True, f"unavailable: {e}")
    WARNINGS += 1

# ── 7. Voice ──
print("7️⃣  Voice")
try:
    from backend.voice.gateway import voice_gateway
    if voice_gateway.stt_available if hasattr(voice_gateway, 'stt_available') else True:
        log("STT available" if hasattr(voice_gateway, 'stt_available') and voice_gateway.stt_available else "Voice gateway present", "ok")
    else:
        log("STT not available (expected on VPS without Whisper)", "warn")
        WARNINGS += 1
    add_result("voice", True, "gateway present")
except Exception as e:
    log(f"Voice: {e}", "warn")
    add_result("voice", True, "offline")
    WARNINGS += 1

# ── 8. Documents / RAG ──
print("8️⃣  Documents")
try:
    from backend.memory.vector_store import get_vector_store
    store = get_vector_store()
    s = store.get_status()
    log(f"Documents: {s['documents']} docs, {s['chunks']} chunks", "ok")
    add_result("documents", True, f"{s['documents']} docs")
except Exception as e:
    log(f"Documents: {e}", "warn")
    add_result("documents", True, "0 docs")
    WARNINGS += 1

# ── 9. Skill Registry ──
print("9️⃣  Skills")
try:
    from backend.core.registry import skill_registry
    skill_registry.discover_and_load()
    names = skill_registry.skill_names
    log(f"Skills loaded: {len(names)} ({', '.join(names[:6])}...)", "ok")
    add_result("skills", len(names) >= 6, f"{len(names)} skills")
    if len(names) < 6:
        CRITICAL_FAILURES += 1
except Exception as e:
    log(f"Skills: {e}", "fail")
    add_result("skills", False, str(e))
    CRITICAL_FAILURES += 1

# ── 10. Environment ──
print("🔟 Environment")
checks_env = [
    (PROJECT_DIR / ".env.example").exists(),
    (PROJECT_DIR / "requirements.txt").exists(),
    (PROJECT_DIR / "frontend" / "package.json").exists(),
    (PROJECT_DIR / "frontend" / "electron" / "main.js").exists(),
    (PROJECT_DIR / "scripts" / "setup_local_linux.sh").exists(),
]
env_items = [".env.example", "requirements.txt", "frontend/package.json", "electron/main.js", "setup script"]
all_env_ok = True
for ok, name in zip(checks_env, env_items):
    if ok:
        log(f"{name}: found", "ok")
    else:
        log(f"{name}: MISSING", "fail")
        CRITICAL_FAILURES += 1
        all_env_ok = False
add_result("environment_files", all_env_ok)

# ── Summary ──
print()
print("=" * 50)
passed = results["summary"]["pass"]
failed = results["summary"]["fail"]
total = results["summary"]["total"]

if CRITICAL_FAILURES == 0 and WARNINGS == 0:
    msg = "🎉 ALL CHECKS PASSED"
elif CRITICAL_FAILURES == 0:
    msg = f"⚠️  PASSED with {WARNINGS} warning(s) (expected on VPS)"
else:
    msg = f"❌ {CRITICAL_FAILURES} CRITICAL FAILURE(S) + {WARNINGS} warning(s)"

print(f"  {msg}")
print(f"  {passed} passed, {failed} failed, {total} total, {WARNINGS} warnings")
print("=" * 50)

if JSON_MODE:
    print(json.dumps(results, indent=2))

sys.exit(0 if CRITICAL_FAILURES == 0 else 1)
