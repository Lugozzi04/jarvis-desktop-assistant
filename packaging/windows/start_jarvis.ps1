# Jarvis Desktop Assistant — Windows startup script
# Place a shortcut to this script in: shell:startup
# Or schedule with Task Scheduler:
#   Trigger: At log on
#   Action: Start a program → powershell.exe -ExecutionPolicy Bypass -File "C:\path\to\jarvis-desktop-assistant\packaging\windows\start_jarvis.ps1"

$ProjectDir = "~\jarvis-desktop-assistant"

# Start backend
Start-Process -WindowStyle Hidden -FilePath "$ProjectDir\.venv\Scripts\python.exe" `
  -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8400"

Start-Sleep -Seconds 3

# Start frontend
Set-Location "$ProjectDir\frontend"
Start-Process -WindowStyle Hidden -FilePath "npm" -ArgumentList "run", "dev"

Write-Host "Jarvis started. Backend: http://localhost:8400 | Frontend: http://localhost:5173"
