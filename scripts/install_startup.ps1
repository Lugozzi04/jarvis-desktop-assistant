# Jarvis — Installa avvio automatico (Windows)
# Esegui UNA VOLTA: powershell -ExecutionPolicy Bypass -File scripts\install_startup.ps1
#
# Crea uno shortcut in shell:startup così Jarvis parte
# in system tray mode ogni volta che accendi il PC.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  JARVIS — Avvio Automatico          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. Trova Python
$py = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $py = "python3" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $py = "py" }
else {
    Write-Host "❌ Python non trovato. Installa da https://python.org" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "✅ Python: $py" -ForegroundColor Green

# 2. Verifica che il venv esista
if (-not (Test-Path "$projectDir\.venv\Scripts\python.exe")) {
    Write-Host "❌ Virtual environment non trovato. Esegui start.ps1 prima." -ForegroundColor Red
    pause
    exit 1
}
Write-Host "✅ Virtual environment trovato" -ForegroundColor Green

# 3. Crea lo script di avvio
$launcherPath = "$projectDir\scripts\launcher_tray.ps1"
@"
# Jarvis Tray Launcher — avviato automaticamente all'accensione del PC
Set-Location "$projectDir"
& ".\\.venv\\Scripts\\python.exe" -m backend.desktop_tray
"@ | Out-File -FilePath $launcherPath -Encoding UTF8

Write-Host "✅ Script launcher creato: scripts\launcher_tray.ps1" -ForegroundColor Green

# 4. Crea shortcut in shell:startup
$startupDir = [Environment]::GetFolderPath('Startup')
$shortcutPath = "$startupDir\JARVIS.lnk"

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcherPath`""
$Shortcut.WorkingDirectory = $projectDir
$Shortcut.WindowStyle = 7  # Minimized
$Shortcut.IconLocation = "powershell.exe,0"
$Shortcut.Description = "JARVIS Desktop Assistant — System Tray Mode"
$Shortcut.Save()

Write-Host "✅ Shortcut creato in: $shortcutPath" -ForegroundColor Green

Write-Host ""
Write-Host "🎉 INSTALLAZIONE COMPLETATA!" -ForegroundColor Green
Write-Host ""
Write-Host "JARVIS partirà automaticamente in system tray al prossimo riavvio."
Write-Host "Per avviarlo SUBITO: premi Win+R, incolla questo e premi Invio:"
Write-Host ""
Write-Host "  powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcherPath`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "Requisiti:" -ForegroundColor White
Write-Host "  - Ollama in esecuzione (Start Menu → Ollama)" -ForegroundColor DarkGray
Write-Host "  - python, pystray, mss, pytesseract installati (start.ps1 li installa)" -ForegroundColor DarkGray
Write-Host "  - Tesseract-OCR installato: https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor DarkGray
Write-Host ""
pause
