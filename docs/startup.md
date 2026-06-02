# Auto‑starting Jarvis on Boot

This guide covers how to make Jarvis Desktop Assistant start automatically when you log in, on Linux, Windows, and macOS. Production‑grade templates live under `packaging/<os>/`; simpler dev‑launcher scripts are in `scripts/`.

---

## Quick Reference

| OS | Method | Template / Script |
|----|--------|-------------------|
| Linux | systemd user service | `packaging/linux/jarvis-backend.service` |
| Linux | Desktop autostart (.desktop) | `packaging/linux/jarvis-desktop.desktop` |
| Windows | PowerShell + Task Scheduler | `packaging/windows/start_jarvis.ps1` |
| macOS | LaunchAgent plist | `packaging/macos/com.jarvis.desktop.plist` |
| **All** | **Dev launcher (simpler)** | `scripts/dev_start_*.sh` / `.ps1` |

---

## Prerequisites (all platforms)

* Python 3.10+ with a virtual environment created in the project root (`python3 -m venv .venv`)
* Frontend dependencies installed (`cd frontend && npm install`)
* A `.env` file in the project root (copy from `.env.example` if missing)
* The repository cloned to your home directory at `~/jarvis-desktop-assistant`

If you installed the project somewhere else, adjust every `~/jarvis-desktop-assistant` path in the templates and commands below.

---

## 1. Dev‑Launcher Scripts (Simplest, Manual Start)

If you just want a one‑command way to launch everything **now** (not on boot), use the dev launchers. They auto‑create the venv, install deps, copy `.env`, and start both backend + frontend.

### Linux / macOS

```bash
bash ~/jarvis-desktop-assistant/scripts/dev_start_linux.sh    # Linux
bash ~/jarvis-desktop-assistant/scripts/dev_start_macos.sh    # macOS
```

### Windows (PowerShell)

```powershell
# Right-click → "Run with PowerShell", or from a terminal:
& "$env:USERPROFILE\jarvis-desktop-assistant\scripts\dev_start_windows.ps1"
```

Press **Ctrl+C** to stop both servers. Use these scripts while developing — they include `--reload` so code changes are picked up automatically.

---

## 2. Linux — Auto‑Start on Login

### Option A: systemd User Service (Backend Only)

This runs the FastAPI backend as a user‑level systemd service that survives logouts and restarts on failure. The frontend is not included — start it separately with the desktop file or launcher.

#### 2A‑1. Copy the template to the user systemd directory

```bash
mkdir -p ~/.config/systemd/user
cp ~/jarvis-desktop-assistant/packaging/linux/jarvis-backend.service \
   ~/.config/systemd/user/jarvis-backend.service
```

#### 2A‑2. Enable and start immediately

```bash
systemctl --user daemon-reload
systemctl --user enable --now jarvis-backend.service
```

#### 2A‑3. Useful commands

```bash
# Check status
systemctl --user status jarvis-backend.service

# View live logs
journalctl --user -u jarvis-backend -f

# Restart after editing config / .env
systemctl --user restart jarvis-backend.service

# Disable auto-start
systemctl --user disable jarvis-backend.service
```

The service file expects the project at `~/jarvis-desktop-assistant` and the virtual environment at `.venv` inside it. It reads environment variables from `~/jarvis-desktop-assistant/.env`.

> **Note:** systemd user services require `linger` to be enabled if you want the service to start at boot (before the first login). Enable it once:
> ```bash
> sudo loginctl enable-linger $USER
> ```

---

### Option B: Desktop Autostart File (Backend + Frontend)

Placing a `.desktop` entry in `~/.config/autostart/` runs the full dev‑launcher (backend + frontend) when you log into your graphical session.

#### 2B‑1. Copy the template

```bash
mkdir -p ~/.config/autostart
cp ~/jarvis-desktop-assistant/packaging/linux/jarvis-desktop.desktop \
   ~/.config/autostart/jarvis-desktop.desktop
```

#### 2B‑2. (Optional) Adjust the path

If your project lives outside `~/jarvis-desktop-assistant`, edit the `Exec=` line:

```bash
nano ~/.config/autostart/jarvis-desktop.desktop
```

Change the `cd` path and the script path accordingly.

#### 2B‑3. Enable / Disable

* **Enable:** The file simply must exist in `~/.config/autostart/`. It runs on your next login.
* **Disable:** Delete it or move it out of the directory.

To test immediately without logging out:

```bash
gtk-launch jarvis-desktop.desktop
```

---

## 3. Windows — Auto‑Start on Login

### Option A: Startup Folder (Simplest)

Drop a shortcut to the PowerShell startup script into the `shell:startup` folder.

#### 3A‑1. Create a shortcut

```powershell
$source = "$env:USERPROFILE\jarvis-desktop-assistant\packaging\windows\start_jarvis.ps1"
$dest   = [Environment]::GetFolderPath("Startup") + "\JarvisDesktop.lnk"

$WScriptShell = New-Object -ComObject WScript.Shell
$shortcut = $WScriptShell.CreateShortcut($dest)
$shortcut.TargetPath  = "powershell.exe"
$shortcut.Arguments   = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$source`""
$shortcut.WindowStyle = 7          # Minimised
$shortcut.Save()
```

Copy‑paste the entire block into a **PowerShell** window (run as Administrator is not required).

#### 3A‑2. Verify

Press `Win+R`, type `shell:startup`, and confirm `JarvisDesktop.lnk` is present. The script will run on your next login.

#### 3A‑3. Remove

Delete `JarvisDesktop.lnk` from the Startup folder (`Win+R` → `shell:startup`).

---

### Option B: Task Scheduler (More Control)

Task Scheduler gives you fine‑grained triggers, restart-on-failure, and the ability to run whether the user is logged in or not.

#### 3B‑1. Import the XML task (recommended)

Create a temporary XML file and import it:

```powershell
$xml = @'
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-ExecutionPolicy Bypass -WindowStyle Hidden -File "$env:USERPROFILE\jarvis-desktop-assistant\packaging\windows\start_jarvis.ps1"</Arguments>
    </Exec>
  </Actions>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
  </Settings>
</Task>
'@

$xml | Out-File "$env:TEMP\JarvisTask.xml" -Encoding Unicode

Register-ScheduledTask `
  -TaskName "Jarvis Desktop Assistant" `
  -Xml (Get-Content "$env:TEMP\JarvisTask.xml" -Raw) `
  -TaskPath "\" `
  -Force
```

#### 3B‑2. Or create manually via GUI

1. Press `Win`, type **Task Scheduler**, and open it.
2. Click **Create Task…** in the right pane.
3. **General tab:** Name = `Jarvis Desktop Assistant`, check *Run with highest privileges* if desired.
4. **Triggers tab → New…:** *Begin the task:* **At log on**, *Specific user* = your account.
5. **Actions tab → New…:** *Action:* **Start a program**
   * **Program/script:** `powershell.exe`
   * **Arguments:**
     ```
     -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Users\YourName\jarvis-desktop-assistant\packaging\windows\start_jarvis.ps1"
     ```
6. Click **OK**, enter your password when prompted.

---

## 4. macOS — Auto‑Start on Login (LaunchAgent)

macOS uses `launchd` LaunchAgents for user‑level background services. The plist template runs the full dev‑launcher (backend + frontend) at login.

#### 4‑1. Copy the plist to ~/Library/LaunchAgents

```bash
mkdir -p ~/Library/LaunchAgents
cp ~/jarvis-desktop-assistant/packaging/macos/com.jarvis.desktop.plist \
   ~/Library/LaunchAgents/com.jarvis.desktop.plist
```

#### 4‑2. Load it immediately (no logout needed)

```bash
launchctl load ~/Library/LaunchAgents/com.jarvis.desktop.plist
```

#### 4‑3. Useful commands

```bash
# Check if it's running
launchctl list | grep jarvis

# View logs
tail -f /tmp/jarvis.stdout.log
tail -f /tmp/jarvis.stderr.log

# Stop it
launchctl unload ~/Library/LaunchAgents/com.jarvis.desktop.plist

# Remove from auto-start
rm ~/Library/LaunchAgents/com.jarvis.desktop.plist
```

The plist assumes the project is at `~/jarvis-desktop-assistant`. If you placed it elsewhere, edit the `ProgramArguments` array inside the plist:

```bash
nano ~/Library/LaunchAgents/com.jarvis.desktop.plist
```

Then reload:

```bash
launchctl unload ~/Library/LaunchAgents/com.jarvis.desktop.plist
launchctl load ~/Library/LaunchAgents/com.jarvis.desktop.plist
```

---

## Troubleshooting

### Backend doesn't start

* Is the Python virtual environment present at `~/jarvis-desktop-assistant/.venv`? Create it: `python3 -m venv ~/jarvis-desktop-assistant/.venv`
* Are backend dependencies installed? Activate the venv and run `pip install -r requirements.txt`
* Check logs: `journalctl --user -u jarvis-backend -f` (Linux) or `/tmp/jarvis.stderr.log` (macOS)

### Frontend doesn't start

* Are Node.js and npm installed? Run `node --version` and `npm --version`.
* Did you run `npm install` inside the `frontend/` directory?
* Is port 5173 already in use? Kill the existing process or change the port.

### .env file missing

The dev launchers auto‑copy `.env.example` → `.env`. The systemd service reads from `.env` via `EnvironmentFile`. If the file is missing, the backend may fail to find required API keys.

```bash
cp ~/jarvis-desktop-assistant/.env.example ~/jarvis-desktop-assistant/.env
# Then edit .env with your API keys
```

### Port conflicts

Default ports: backend **8400**, frontend **5173**. Change them in:
* Linux: edit `ExecStart=` in `jarvis-backend.service` and the `Exec=` line in `jarvis-desktop.desktop`
* Windows: edit `start_jarvis.ps1`
* macOS: edit the `ProgramArguments` array in `com.jarvis.desktop.plist`

---

## Summary

| What you want | What to use |
|---------------|-------------|
| Just launch it now, no persistence | Dev launcher scripts (`scripts/dev_start_*.sh/.ps1`) |
| Auto‑start backend on Linux boot | systemd user service |
| Auto‑start full app on Linux login | `.desktop` file in `~/.config/autostart/` |
| Auto‑start on Windows login | Startup‑folder shortcut or Task Scheduler |
| Auto‑start on macOS login | LaunchAgent plist |
