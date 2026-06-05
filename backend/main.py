"""JARVIS Desktop Assistant — FastAPI Application Entry Point.

This is the main backend server that exposes:
- REST API for the UI frontend
- Skill execution endpoints
- Workflow & automation management
- Voice endpoints
- Settings & logging

Start with: uvicorn backend.main:app --host 127.0.0.1 --port 8400 --reload
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.assistant import assistant
from backend.core.config import settings
from backend.core.logger import logger, setup_logging

# ── Overlay HTML (Ctrl+Shift quick query page) ──

OVERLAY_HTML = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JARVIS Overlay</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,sans-serif;background:#0f1117;color:#e4e6f0;height:100vh;display:flex;flex-direction:column;overflow:hidden}
.overlay-header{padding:16px 20px;background:#161822;border-bottom:1px solid #2a2d3e;display:flex;align-items:center;gap:8px;-webkit-app-region:drag}
.overlay-header span{font-size:1rem;font-weight:700;background:linear-gradient(135deg,#6366f1,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.overlay-input-area{padding:20px;display:flex;flex-direction:column;flex:1}
.overlay-input-area textarea{flex:1;background:#1a1d2e;border:1px solid #2a2d3e;border-radius:12px;color:#e4e6f0;padding:16px;font-family:inherit;font-size:0.95rem;resize:none;outline:none;min-height:80px}
.overlay-input-area textarea:focus{border-color:#6366f1}
.overlay-actions{display:flex;gap:8px;margin-top:12px}
.btn{background:#6366f1;color:#fff;border:none;padding:10px 20px;border-radius:8px;font-size:0.9rem;cursor:pointer;font-weight:600;transition:background 0.2s}
.btn:hover{background:#818cf8}
.btn-ghost{background:transparent;color:#8b8fa3;border:1px solid #2a2d3e}
.btn-ghost:hover{background:#232740;color:#e4e6f0}
.quick-actions{display:flex;gap:6px;flex-wrap:wrap}
.quick-btn{background:#1a1d2e;border:1px solid #2a2d3e;color:#8b8fa3;padding:6px 12px;border-radius:6px;font-size:0.8rem;cursor:pointer;transition:all 0.2s}
.quick-btn:hover{background:#232740;border-color:#6366f1;color:#e4e6f0}
.result-area{padding:0 20px 20px;max-height:200px;overflow:auto;display:none}
.result-area.show{display:block}
.result-card{background:#1a1d2e;border:1px solid #2a2d3e;border-radius:8px;padding:16px;line-height:1.6;font-size:0.9rem;white-space:pre-line}
.status{font-size:0.8rem;color:#5a5d73;text-align:center;padding:8px}
.error{color:#ef4444}
.loading{display:flex;align-items:center;justify-content:center;gap:8px;padding:20px;color:#8b8fa3}
.spinner{width:16px;height:16px;border:2px solid #2a2d3e;border-top-color:#6366f1;border-radius:50%;animation:s .6s linear infinite}
@keyframes s{to{transform:rotate(360deg)}}
.tts-btn{position:absolute;top:12px;right:60px;width:36px;height:36px;border-radius:50%;border:1px solid #2a2d3e;background:#1a1d2e;color:#8b8fa3;font-size:1.1rem;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.2s;z-index:10}
.tts-btn:hover{background:#232740;border-color:#6366f1}
.tts-btn.active{background:#6366f1;border-color:#6366f1;color:#fff}
</style>
</head>
<body>
<div class="overlay-header"><span>⚡ JARVIS</span><span style="font-size:0.7rem;color:#5a5d73;margin-left:4px">Ctrl+Shift</span>
<select id="monitorSel" style="margin-left:auto;background:#1a1d2e;border:1px solid #2a2d3e;color:#e4e6f0;padding:4px 8px;border-radius:6px;font-size:0.75rem;cursor:pointer">
<option value="1">🖥️ Monitor 1</option>
<option value="2">🖥️ Monitor 2</option>
<option value="0">🖥️ Tutti</option>
</select>
</div>
<button class="tts-btn" id="ttsBtn" onclick="toggleTTS()" title="Voice OFF — click to hear responses">🔇</button>
<div class="overlay-input-area">
<textarea id="q" placeholder="Chiedi a JARVIS... es. 'Cosa significa questo errore?' o 'Riassumi questa pagina'" autofocus></textarea>
<div class="quick-actions">
<button class="quick-btn" onclick="ask('Cosa significa questo errore?')">🐛 Spiega errore</button>
<button class="quick-btn" onclick="ask('Riassumi cosa vedo sullo schermo')">📋 Riassumi</button>
<button class="quick-btn" onclick="ask('Traduci questo testo in italiano')">🌐 Traduci</button>
<button class="quick-btn" onclick="ask('Cosa fa questo codice?')">💻 Spiega codice</button>
</div>
<div class="overlay-actions">
<button class="btn" onclick="analyze()" id="goBtn">🔍 Analizza Schermo</button>
<button class="btn btn-ghost" onclick="window.close()">✕ Chiudi</button>
</div>
</div>
<div class="result-area" id="result"><div class="result-card" id="resultContent"></div></div>
<div class="status" id="status">Premi Enter o clicca Analizza — JARVIS catturerà lo schermo e analizzerà</div>
<script>
const API='http://127.0.0.1:8400';
const q=document.getElementById('q');
const go=document.getElementById('goBtn');
const result=document.getElementById('result');
const content=document.getElementById('resultContent');
const status=document.getElementById('status');

// TTS toggle
let ttsOn=false;
const ttsBtn=document.getElementById('ttsBtn');
let ttsAudio=null;

function toggleTTS(){
ttsOn=!ttsOn;
if(ttsOn){ttsBtn.textContent='🔊';ttsBtn.classList.add('active');ttsBtn.title='Voice ON — click to mute'}
else{ttsBtn.textContent='🔇';ttsBtn.classList.remove('active');ttsBtn.title='Voice OFF — click to hear responses';
if(ttsAudio){ttsAudio.pause();ttsAudio=null}}
}

q.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();analyze()}});

function ask(question){q.value=question;analyze()}

async function analyze(){
const question=q.value.trim();
if(!question){q.focus();return}
const mon=parseInt(document.getElementById('monitorSel').value)||1;
go.disabled=true;
go.textContent='⏳ Analisi...';
result.classList.remove('show');
status.innerHTML='<div class="loading"><div class="spinner"></div>Cattura schermo + OCR + AI...</div>';

try{
const r=await fetch(API+'/api/desktop/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,monitor:mon})});
const d=await r.json();
if(d.success){
content.innerHTML=d.response;
result.classList.add('show');
status.textContent='✅ Analisi completata';
// TTS: read response aloud if enabled
if(ttsOn&&d.response){
const t=d.response.replace(/\\*\\*/g,'').replace(/\\*/g,'').replace(/_/g,'').replace(/`/g,'');
if(ttsAudio){ttsAudio.pause();ttsAudio=null}
ttsAudio=new Audio(API+'/api/voice/speak-stream?text='+encodeURIComponent(t));
ttsAudio.play().catch(()=>{})
}
}else{
content.innerHTML='<div class="error">❌ '+d.response+'</div>';
result.classList.add('show');
status.textContent='⚠️ Errore: '+(d.error||'sconosciuto');
}
}catch(e){
content.innerHTML='<div class="error">❌ Connessione fallita. Backend offline?</div>';
result.classList.add('show');
status.textContent='❌ '+e.message;
}

go.disabled=false;
go.textContent='🔍 Analizza Schermo';
q.focus();
}
</script>
</body>
</html>"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Startup
    setup_logging()
    logger.info("🚀 JARVIS Desktop Assistant starting — env={}", settings.env)

    # Ensure backend is on path
    backend_dir = Path(__file__).resolve().parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    # Initialize subsystems
    try:
        assistant.initialize()
    except Exception as exc:
        logger.error("Failed to initialize subsystems: {}", exc)

    # Initialize LLM Gateway
    try:
        from backend.llm.gateway import llm_gateway
        llm_gateway.initialize_from_config()
        logger.info("LLM Gateway initialized")
    except Exception as exc:
        logger.warning("LLM Gateway initialization skipped: {}", exc)

    # Initialize Voice Gateway
    try:
        from backend.voice.gateway import voice_gateway
        voice_gateway.initialize()
        logger.info("Voice Gateway initialized")
    except Exception as exc:
        logger.warning("Voice Gateway initialization skipped: {}", exc)

    # Auto-detect apps on first run
    try:
        from backend.apps.config_store import app_config_store
        from backend.apps.detection import detect_apps
        existing = app_config_store.get_all()
        if not existing:
            logger.info("No apps configured — running auto-detection...")
            detected = detect_apps()
            app_config_store.import_from_detection(detected)
            logger.info("Auto-detected and imported {} apps", len(detected))
        else:
            logger.info("App config loaded: {} apps", len(existing))
    except Exception as exc:
        logger.warning("App auto-detection skipped: {}", exc)

    # Start Automation Engine scheduler
    try:
        from backend.automation.engine import automation_engine
        automation_engine.start_scheduler()
        logger.info("Automation Engine scheduler started")
    except Exception as exc:
        logger.warning("Automation Engine scheduler start skipped: {}", exc)

    yield

    # Stop Automation Engine scheduler
    try:
        from backend.automation.engine import automation_engine
        automation_engine.stop_scheduler()
    except Exception:
        pass

    # Shutdown
    logger.info("👋 JARVIS shutting down")


# ── App ──

app = FastAPI(
    title="Jarvis Desktop Assistant",
    description="Modular AI desktop assistant — control your PC, chat, execute commands, manage workflows and automations.",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Root ──

@app.get("/overlay")
def overlay():
    """Serve the overlay UI for Ctrl+Shift quick queries."""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=OVERLAY_HTML)


@app.get("/")
def root():
    """Serve frontend if built, otherwise health JSON."""
    FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        from fastapi.responses import FileResponse
        return FileResponse(index_path)
    return {
        "name": "Jarvis Desktop Assistant",
        "version": "0.3.0",
        "status": "running",
        "skills_loaded": len(_get_skills()),
    }


def _get_skills() -> list[str]:
    try:
        from backend.core.registry import skill_registry
        return skill_registry.skill_names
    except Exception:
        return []


@app.get("/health")
async def health():
    """Detailed health check with LLM status."""
    llm_status = {"provider": "none", "available": False, "model": ""}
    try:
        from backend.llm.gateway import llm_gateway
        llm_status = await llm_gateway.get_status()
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "0.2.0",
        "env": settings.env,
        "skills": _get_skills(),
        "llm": llm_status,
    }


# ── Include API Routers ──

from backend.api.chat import router as chat_router
from backend.api.command import router as command_router
from backend.api.conversations import router as conversations_router
from backend.api.skills import router as skills_router
from backend.api.settings import router as settings_router
from backend.api.voice import router as voice_router
from backend.api.habits import router as habits_router
from backend.api.documents import router as documents_router
from backend.api.setup import router as setup_router
from backend.api.diagnostics import router as diagnostics_router
from backend.api.apps_wizard import router as apps_wizard_router
from backend.api.pending_actions import router as pending_actions_router
from backend.api.timers import router as timers_router
from backend.api.study import router as study_router
from backend.api.desktop_api import router as desktop_router
from backend.api.hotkeys import router as hotkeys_router

app.include_router(chat_router, prefix="/api")
app.include_router(command_router, prefix="/api")
app.include_router(conversations_router)
app.include_router(skills_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(habits_router, prefix="/api")
app.include_router(documents_router)
app.include_router(setup_router)
app.include_router(diagnostics_router)
app.include_router(pending_actions_router)
app.include_router(timers_router, prefix="/api")
app.include_router(study_router, prefix="/api")
app.include_router(desktop_router, prefix="/api")
app.include_router(hotkeys_router, prefix="/api")
app.include_router(apps_wizard_router)


# ── Serve Frontend SPA (only if built) ──

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    # Mount entire dist as SPA — StaticFiles with html=True handles:
    #   /          → index.html
    #   /chat      → index.html (SPA fallback)
    #   /assets/*  → actual files
    # Previously registered routes (/health, /api/*) remain active.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend_spa")
    logger.info("🎨 Frontend SPA mounted from {}", FRONTEND_DIST)
else:
    logger.info("ℹ️  Frontend not built — API-only mode. Run 'npm run build' to enable UI.")
