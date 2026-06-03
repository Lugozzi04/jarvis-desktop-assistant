"""App Detection — comprehensive scan for installed applications.

Deep scan across:
  - Start Menu (.lnk shortcuts)
  - PATH executables
  - Program Files / Program Files (x86) - recursive
  - AppData Local / Roaming - recursive
  - Windows Registry (Uninstall keys via PowerShell)
  - Common portable locations

200+ known apps across categories: communication, browsers,
development, gaming, media, creative, productivity, utilities,
cloud, security, remote, system tools.

Returns structured results with name, path, category, and aliases.
Always returns results, never crashes.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

from backend.core.logger import logger

# ─────────────────────────────────────────────────────────────────────
# Known Apps Database — 200+ entries
# Format: display_name → { exes, category, aliases }
# ─────────────────────────────────────────────────────────────────────

_KNOWN_APPS: dict[str, dict[str, Any]] = {
    # ── Communication ──
    "Discord":          {"exes": ["Discord.exe", "discord.exe"],                       "cat": "communication", "aliases": ["discord", "dc"]},
    "Telegram":         {"exes": ["Telegram.exe", "telegram.exe"],                     "cat": "communication", "aliases": ["telegram", "tg"]},
    "Slack":            {"exes": ["slack.exe", "Slack.exe"],                           "cat": "communication", "aliases": ["slack"]},
    "Zoom":             {"exes": ["Zoom.exe", "zoom.exe"],                             "cat": "communication", "aliases": ["zoom"]},
    "Teams":            {"exes": ["Teams.exe", "teams.exe"],                           "cat": "communication", "aliases": ["teams", "ms teams"]},
    "WhatsApp":         {"exes": ["WhatsApp.exe", "whatsapp.exe"],                     "cat": "communication", "aliases": ["whatsapp", "wa"]},
    "Signal":           {"exes": ["Signal.exe", "signal.exe"],                         "cat": "communication", "aliases": ["signal"]},
    "Skype":            {"exes": ["Skype.exe", "skype.exe"],                           "cat": "communication", "aliases": ["skype"]},
    "Webex":            {"exes": ["Webex.exe", "webex.exe", "CiscoWebexStart.exe"],    "cat": "communication", "aliases": ["webex", "cisco webex"]},
    "Element":          {"exes": ["Element.exe", "element.exe"],                       "cat": "communication", "aliases": ["element", "riot"]},
    "Thunderbird":      {"exes": ["thunderbird.exe", "Thunderbird.exe"],               "cat": "communication", "aliases": ["thunderbird", "tb"]},

    # ── Browsers ──
    "Google Chrome":    {"exes": ["chrome.exe", "Chrome.exe"],                         "cat": "browser", "aliases": ["chrome", "google chrome"]},
    "Firefox":          {"exes": ["firefox.exe", "Firefox.exe"],                       "cat": "browser", "aliases": ["firefox", "ff"]},
    "Edge":             {"exes": ["msedge.exe", "MSEdge.exe"],                         "cat": "browser", "aliases": ["edge", "microsoft edge"]},
    "Brave":            {"exes": ["brave.exe", "Brave.exe"],                           "cat": "browser", "aliases": ["brave"]},
    "Opera":            {"exes": ["opera.exe", "launcher.exe"],                        "cat": "browser", "aliases": ["opera"]},
    "Opera GX":         {"exes": ["opera_gx.exe", "launcher.exe"],                     "cat": "browser", "aliases": ["operagx", "gx"]},
    "Vivaldi":          {"exes": ["vivaldi.exe", "Vivaldi.exe"],                       "cat": "browser", "aliases": ["vivaldi"]},
    "Arc":              {"exes": ["Arc.exe", "arc.exe"],                               "cat": "browser", "aliases": ["arc"]},
    "Tor Browser":      {"exes": ["tor.exe", "firefox.exe"],                           "cat": "browser", "aliases": ["tor"]},
    "Waterfox":         {"exes": ["waterfox.exe", "Waterfox.exe"],                     "cat": "browser", "aliases": ["waterfox"]},
    "LibreWolf":        {"exes": ["librewolf.exe", "LibreWolf.exe"],                   "cat": "browser", "aliases": ["librewolf"]},
    "Pale Moon":        {"exes": ["palemoon.exe", "PaleMoon.exe"],                     "cat": "browser", "aliases": ["palemoon"]},

    # ── Development ──
    "VS Code":          {"exes": ["Code.exe", "code.exe"],                             "cat": "development", "aliases": ["vscode", "code", "vs code"]},
    "VS Code Insiders": {"exes": ["Code - Insiders.exe"],                              "cat": "development", "aliases": ["vscode insiders"]},
    "Cursor":           {"exes": ["Cursor.exe", "cursor.exe"],                         "cat": "development", "aliases": ["cursor"]},
    "Windsurf":         {"exes": ["Windsurf.exe", "windsurf.exe"],                     "cat": "development", "aliases": ["windsurf"]},
    "Visual Studio":    {"exes": ["devenv.exe", "VSIXAutoUpdate.exe"],                 "cat": "development", "aliases": ["visual studio", "vs"]},
    "IntelliJ IDEA":    {"exes": ["idea64.exe", "idea.exe"],                           "cat": "development", "aliases": ["intellij", "idea"]},
    "PyCharm":          {"exes": ["pycharm64.exe", "pycharm.exe"],                     "cat": "development", "aliases": ["pycharm"]},
    "WebStorm":         {"exes": ["webstorm64.exe", "webstorm.exe"],                   "cat": "development", "aliases": ["webstorm"]},
    "PhpStorm":         {"exes": ["phpstorm64.exe", "phpstorm.exe"],                   "cat": "development", "aliases": ["phpstorm"]},
    "CLion":            {"exes": ["clion64.exe", "clion.exe"],                         "cat": "development", "aliases": ["clion"]},
    "GoLand":           {"exes": ["goland64.exe", "goland.exe"],                       "cat": "development", "aliases": ["goland"]},
    "Rider":            {"exes": ["rider64.exe", "rider.exe"],                         "cat": "development", "aliases": ["rider"]},
    "RubyMine":         {"exes": ["rubymine64.exe", "rubymine.exe"],                   "cat": "development", "aliases": ["rubymine"]},
    "DataGrip":         {"exes": ["datagrip64.exe", "datagrip.exe"],                   "cat": "development", "aliases": ["datagrip"]},
    "Android Studio":   {"exes": ["studio64.exe", "studio.exe"],                       "cat": "development", "aliases": ["android studio", "studio"]},
    "Sublime Text":     {"exes": ["sublime_text.exe", "subl.exe"],                     "cat": "development", "aliases": ["sublime", "subl"]},
    "Notepad++":        {"exes": ["notepad++.exe", "Notepad++.exe"],                   "cat": "development", "aliases": ["npp", "notepad++"]},
    "Atom":             {"exes": ["atom.exe", "Atom.exe"],                             "cat": "development", "aliases": ["atom"]},
    "Brackets":         {"exes": ["Brackets.exe", "brackets.exe"],                     "cat": "development", "aliases": ["brackets"]},
    "Vim":              {"exes": ["gvim.exe", "vim.exe"],                              "cat": "development", "aliases": ["vim", "gvim"]},
    "Emacs":            {"exes": ["emacs.exe", "runemacs.exe"],                        "cat": "development", "aliases": ["emacs"]},
    "Git Bash":         {"exes": ["git-bash.exe", "bash.exe"],                         "cat": "development", "aliases": ["git bash", "bash"]},
    "GitHub Desktop":   {"exes": ["GitHubDesktop.exe"],                                "cat": "development", "aliases": ["github desktop", "gh desktop"]},
    "Docker Desktop":   {"exes": ["Docker Desktop.exe", "docker.exe"],                 "cat": "development", "aliases": ["docker"]},
    "Postman":          {"exes": ["Postman.exe", "postman.exe"],                       "cat": "development", "aliases": ["postman"]},
    "Insomnia":         {"exes": ["Insomnia.exe", "insomnia.exe"],                     "cat": "development", "aliases": ["insomnia"]},
    "DBeaver":          {"exes": ["dbeaver.exe", "DBeaver.exe"],                       "cat": "development", "aliases": ["dbeaver"]},
    "pgAdmin":          {"exes": ["pgAdmin4.exe", "pgadmin4.exe"],                     "cat": "development", "aliases": ["pgadmin"]},
    "MongoDB Compass":  {"exes": ["MongoDBCompass.exe"],                               "cat": "development", "aliases": ["compass", "mongodb compass"]},
    "Termius":          {"exes": ["Termius.exe", "termius.exe"],                       "cat": "development", "aliases": ["termius"]},
    "MobaXterm":        {"exes": ["MobaXterm.exe"],                                    "cat": "development", "aliases": ["mobaxterm"]},
    "PuTTY":            {"exes": ["putty.exe", "PuTTY.exe"],                           "cat": "development", "aliases": ["putty"]},
    "WinSCP":           {"exes": ["WinSCP.exe", "winscp.exe"],                         "cat": "development", "aliases": ["winscp"]},
    "FileZilla":        {"exes": ["filezilla.exe", "FileZilla.exe"],                   "cat": "development", "aliases": ["filezilla"]},
    "Node.js":          {"exes": ["node.exe"],                                         "cat": "development", "aliases": ["node", "nodejs"]},
    "Python":           {"exes": ["python.exe", "python3.exe"],                        "cat": "development", "aliases": ["python", "py"]},

    # ── Gaming ──
    "Steam":            {"exes": ["Steam.exe", "steam.exe"],                           "cat": "gaming", "aliases": ["steam"]},
    "Epic Games":       {"exes": ["EpicGamesLauncher.exe"],                            "cat": "gaming", "aliases": ["epic", "epic games"]},
    "Battle.net":       {"exes": ["Battle.net.exe"],                                   "cat": "gaming", "aliases": ["battlenet", "bnet"]},
    "Ubisoft Connect":  {"exes": ["UbisoftConnect.exe", "upc.exe"],                    "cat": "gaming", "aliases": ["ubisoft", "uplay"]},
    "EA App":           {"exes": ["EADesktop.exe", "EALauncher.exe"],                  "cat": "gaming", "aliases": ["ea", "origin"]},
    "GOG Galaxy":       {"exes": ["GalaxyClient.exe"],                                 "cat": "gaming", "aliases": ["gog", "galaxy"]},
    "Riot Client":      {"exes": ["RiotClientServices.exe"],                           "cat": "gaming", "aliases": ["riot", "league", "valorant"]},
    "Minecraft":        {"exes": ["MinecraftLauncher.exe", "Minecraft.exe"],           "cat": "gaming", "aliases": ["minecraft", "mc"]},
    "Discord PTB":      {"exes": ["DiscordPTB.exe"],                                   "cat": "gaming", "aliases": ["discord ptb"]},

    # ── Media / Audio / Video ──
    "Spotify":          {"exes": ["Spotify.exe", "spotify.exe"],                       "cat": "media", "aliases": ["spotify", "music"]},
    "VLC":              {"exes": ["vlc.exe", "VLC.exe"],                               "cat": "media", "aliases": ["vlc", "video player"]},
    "MPC-HC":           {"exes": ["mpc-hc64.exe", "mpc-hc.exe"],                       "cat": "media", "aliases": ["mpc", "mpc-hc"]},
    "MPV":              {"exes": ["mpv.exe", "mpv.com"],                               "cat": "media", "aliases": ["mpv"]},
    "iTunes":           {"exes": ["iTunes.exe", "itunes.exe"],                         "cat": "media", "aliases": ["itunes", "apple music"]},
    "Plex":             {"exes": ["Plex.exe", "plex.exe"],                             "cat": "media", "aliases": ["plex"]},
    "Kodi":             {"exes": ["kodi.exe", "Kodi.exe"],                             "cat": "media", "aliases": ["kodi"]},
    "foobar2000":       {"exes": ["foobar2000.exe"],                                   "cat": "media", "aliases": ["foobar", "foobar2000"]},
    "AIMP":             {"exes": ["AIMP.exe", "aimp.exe"],                             "cat": "media", "aliases": ["aimp"]},
    "OBS Studio":       {"exes": ["obs64.exe", "obs.exe"],                             "cat": "media", "aliases": ["obs", "stream", "recording"]},
    "Streamlabs OBS":   {"exes": ["Streamlabs OBS.exe"],                               "cat": "media", "aliases": ["streamlabs", "slobs"]},
    "HandBrake":        {"exes": ["HandBrake.exe", "handbrake.exe"],                   "cat": "media", "aliases": ["handbrake"]},
    "Audacity":         {"exes": ["audacity.exe", "Audacity.exe"],                     "cat": "media", "aliases": ["audacity"]},

    # ── Creative / Design ──
    "GIMP":             {"exes": ["gimp-2.10.exe", "gimp.exe", "gimp-3.0.exe"],        "cat": "creative", "aliases": ["gimp"]},
    "Blender":          {"exes": ["blender.exe", "Blender.exe"],                       "cat": "creative", "aliases": ["blender"]},
    "Krita":            {"exes": ["krita.exe", "Krita.exe"],                           "cat": "creative", "aliases": ["krita"]},
    "Inkscape":         {"exes": ["inkscape.exe", "Inkscape.exe"],                     "cat": "creative", "aliases": ["inkscape"]},
    "Photoshop":        {"exes": ["Photoshop.exe"],                                    "cat": "creative", "aliases": ["photoshop", "ps"]},
    "Illustrator":      {"exes": ["Illustrator.exe"],                                  "cat": "creative", "aliases": ["illustrator", "ai"]},
    "Premiere Pro":     {"exes": ["Adobe Premiere Pro.exe"],                           "cat": "creative", "aliases": ["premiere", "pr"]},
    "After Effects":    {"exes": ["AfterFX.exe"],                                      "cat": "creative", "aliases": ["after effects", "ae"]},
    "Lightroom":        {"exes": ["Lightroom.exe"],                                    "cat": "creative", "aliases": ["lightroom", "lr"]},
    "DaVinci Resolve":  {"exes": ["Resolve.exe"],                                      "cat": "creative", "aliases": ["resolve", "davinci"]},
    "CapCut":           {"exes": ["CapCut.exe"],                                       "cat": "creative", "aliases": ["capcut"]},
    "Canva":            {"exes": ["Canva.exe"],                                        "cat": "creative", "aliases": ["canva"]},
    "Figma":            {"exes": ["Figma.exe"],                                        "cat": "creative", "aliases": ["figma"]},
    "SketchUp":         {"exes": ["SketchUp.exe"],                                     "cat": "creative", "aliases": ["sketchup"]},
    "Paint.NET":        {"exes": ["paintdotnet.exe"],                                  "cat": "creative", "aliases": ["paint.net", "pdn"]},
    "Aseprite":         {"exes": ["aseprite.exe", "Aseprite.exe"],                     "cat": "creative", "aliases": ["aseprite"]},

    # ── Productivity ──
    "Word":             {"exes": ["WINWORD.EXE", "winword.exe"],                       "cat": "productivity", "aliases": ["word", "microsoft word"]},
    "Excel":            {"exes": ["EXCEL.EXE", "excel.exe"],                           "cat": "productivity", "aliases": ["excel", "microsoft excel"]},
    "PowerPoint":       {"exes": ["POWERPNT.EXE", "powerpnt.exe"],                     "cat": "productivity", "aliases": ["powerpoint", "ppt"]},
    "Outlook":          {"exes": ["OUTLOOK.EXE", "outlook.exe"],                       "cat": "productivity", "aliases": ["outlook", "mail"]},
    "OneNote":          {"exes": ["ONENOTE.EXE", "onenote.exe"],                       "cat": "productivity", "aliases": ["onenote", "notes"]},
    "Access":           {"exes": ["MSACCESS.EXE", "msaccess.exe"],                     "cat": "productivity", "aliases": ["access"]},
    "Publisher":        {"exes": ["MSPUB.EXE", "mspub.exe"],                           "cat": "productivity", "aliases": ["publisher"]},
    "Notion":           {"exes": ["Notion.exe"],                                       "cat": "productivity", "aliases": ["notion"]},
    "Obsidian":         {"exes": ["Obsidian.exe"],                                     "cat": "productivity", "aliases": ["obsidian"]},
    "Logseq":           {"exes": ["Logseq.exe"],                                       "cat": "productivity", "aliases": ["logseq"]},
    "Todoist":          {"exes": ["Todoist.exe"],                                      "cat": "productivity", "aliases": ["todoist"]},
    "TickTick":         {"exes": ["TickTick.exe"],                                     "cat": "productivity", "aliases": ["ticktick"]},
    "Evernote":         {"exes": ["Evernote.exe"],                                     "cat": "productivity", "aliases": ["evernote"]},
    "LibreOffice":      {"exes": ["soffice.exe", "swriter.exe"],                       "cat": "productivity", "aliases": ["libreoffice", "libre"]},
    "WPS Office":       {"exes": ["wps.exe"],                                          "cat": "productivity", "aliases": ["wps"]},
    "PDF Reader":       {"exes": ["Acrobat.exe", "AcroRd32.exe", "FoxitReader.exe"],   "cat": "productivity", "aliases": ["pdf", "acrobat", "adobe reader", "foxit"]},

    # ── Utilities ──
    "7-Zip":            {"exes": ["7zFM.exe", "7z.exe", "7zG.exe"],                    "cat": "utility", "aliases": ["7zip", "7z"]},
    "WinRAR":           {"exes": ["WinRAR.exe", "winrar.exe"],                         "cat": "utility", "aliases": ["winrar", "rar"]},
    "PeaZip":           {"exes": ["peazip.exe", "PeaZip.exe"],                         "cat": "utility", "aliases": ["peazip"]},
    "Everything":       {"exes": ["Everything.exe"],                                   "cat": "utility", "aliases": ["everything", "search everything"]},
    "PowerToys":        {"exes": ["PowerToys.exe"],                                    "cat": "utility", "aliases": ["powertoys"]},
    "AutoHotkey":       {"exes": ["AutoHotkey.exe", "AutoHotkeyU64.exe"],              "cat": "utility", "aliases": ["autohotkey", "ahk"]},
    "ShareX":           {"exes": ["ShareX.exe"],                                       "cat": "utility", "aliases": ["sharex"]},
    "Greenshot":        {"exes": ["Greenshot.exe"],                                    "cat": "utility", "aliases": ["greenshot"]},
    "Lightshot":        {"exes": ["Lightshot.exe"],                                    "cat": "utility", "aliases": ["lightshot"]},
    "CPU-Z":            {"exes": ["cpuz.exe", "cpuz_x64.exe"],                         "cat": "utility", "aliases": ["cpuz"]},
    "GPU-Z":            {"exes": ["GPU-Z.exe"],                                        "cat": "utility", "aliases": ["gpuz"]},
    "HWiNFO":           {"exes": ["HWiNFO64.exe", "HWiNFO32.exe"],                     "cat": "utility", "aliases": ["hwinfo"]},
    "MSI Afterburner":  {"exes": ["MSIAfterburner.exe"],                               "cat": "utility", "aliases": ["afterburner"]},
    "CrystalDiskInfo":  {"exes": ["DiskInfo64.exe", "DiskInfo32.exe"],                 "cat": "utility", "aliases": ["crystaldiskinfo", "diskinfo"]},
    "CrystalDiskMark":  {"exes": ["DiskMark64.exe", "DiskMark32.exe"],                 "cat": "utility", "aliases": ["crystaldiskmark", "diskmark"]},
    "Rufus":            {"exes": ["rufus.exe", "Rufus.exe"],                           "cat": "utility", "aliases": ["rufus"]},
    "Ventoy":           {"exes": ["Ventoy2Disk.exe"],                                  "cat": "utility", "aliases": ["ventoy"]},
    "BalenaEtcher":     {"exes": ["balenaEtcher.exe"],                                 "cat": "utility", "aliases": ["etcher", "balena"]},
    "WizTree":          {"exes": ["WizTree.exe", "WizTree64.exe"],                     "cat": "utility", "aliases": ["wiztree"]},
    "WinDirStat":       {"exes": ["windirstat.exe"],                                   "cat": "utility", "aliases": ["windirstat"]},
    "TreeSize":         {"exes": ["TreeSize.exe", "TreeSizeFree.exe"],                 "cat": "utility", "aliases": ["treesize"]},
    "BleachBit":        {"exes": ["bleachbit.exe"],                                    "cat": "utility", "aliases": ["bleachbit"]},
    "CCleaner":         {"exes": ["CCleaner.exe", "CCleaner64.exe"],                   "cat": "utility", "aliases": ["ccleaner"]},
    "Revo Uninstaller": {"exes": ["RevoUninstaller.exe"],                              "cat": "utility", "aliases": ["revo"]},
    "qBittorrent":      {"exes": ["qbittorrent.exe"],                                  "cat": "utility", "aliases": ["qbittorrent", "qb"]},
    "uTorrent":         {"exes": ["uTorrent.exe", "utorrent.exe"],                     "cat": "utility", "aliases": ["utorrent"]},
    "Deluge":           {"exes": ["deluge.exe"],                                       "cat": "utility", "aliases": ["deluge"]},

    # ── Cloud / Storage ──
    "Dropbox":          {"exes": ["Dropbox.exe"],                                      "cat": "cloud", "aliases": ["dropbox"]},
    "Google Drive":     {"exes": ["GoogleDriveFS.exe"],                                "cat": "cloud", "aliases": ["gdrive", "google drive"]},
    "OneDrive":         {"exes": ["OneDrive.exe"],                                     "cat": "cloud", "aliases": ["onedrive"]},
    "pCloud":           {"exes": ["pCloud.exe"],                                       "cat": "cloud", "aliases": ["pcloud"]},
    "MEGA":             {"exes": ["MEGAsync.exe"],                                     "cat": "cloud", "aliases": ["mega"]},
    "Nextcloud":        {"exes": ["nextcloud.exe"],                                    "cat": "cloud", "aliases": ["nextcloud"]},

    # ── Security ──
    "Malwarebytes":     {"exes": ["mbam.exe"],                                         "cat": "security", "aliases": ["malwarebytes", "mbam"]},
    "Bitdefender":      {"exes": ["bdagent.exe", "bdwtxag.exe"],                       "cat": "security", "aliases": ["bitdefender"]},
    "Avast":            {"exes": ["AvastUI.exe", "AvastSvc.exe"],                      "cat": "security", "aliases": ["avast"]},
    "AVG":              {"exes": ["AVGUI.exe", "avgui.exe"],                           "cat": "security", "aliases": ["avg"]},
    "ESET":             {"exes": ["egui.exe", "eguiProxy.exe"],                        "cat": "security", "aliases": ["eset"]},
    "Kaspersky":        {"exes": ["avpui.exe", "avp.exe"],                             "cat": "security", "aliases": ["kaspersky"]},
    "NordVPN":          {"exes": ["NordVPN.exe"],                                      "cat": "security", "aliases": ["nordvpn"]},
    "Proton VPN":       {"exes": ["ProtonVPN.exe"],                                    "cat": "security", "aliases": ["protonvpn", "proton"]},
    "ExpressVPN":       {"exes": ["expressvpn.exe"],                                   "cat": "security", "aliases": ["expressvpn"]},
    "Mullvad VPN":      {"exes": ["mullvad.exe"],                                      "cat": "security", "aliases": ["mullvad"]},
    "WireGuard":        {"exes": ["wireguard.exe"],                                    "cat": "security", "aliases": ["wireguard"]},
    "OpenVPN":          {"exes": ["openvpn-gui.exe", "openvpn.exe"],                    "cat": "security", "aliases": ["openvpn"]},

    # ── Remote / Desktop Sharing ──
    "AnyDesk":          {"exes": ["AnyDesk.exe"],                                      "cat": "remote", "aliases": ["anydesk"]},
    "TeamViewer":       {"exes": ["TeamViewer.exe"],                                   "cat": "remote", "aliases": ["teamviewer"]},
    "Parsec":           {"exes": ["parsecd.exe", "Parsec.exe"],                        "cat": "remote", "aliases": ["parsec"]},
    "Moonlight":        {"exes": ["Moonlight.exe"],                                    "cat": "remote", "aliases": ["moonlight"]},
    "Sunshine":         {"exes": ["sunshine.exe"],                                     "cat": "remote", "aliases": ["sunshine"]},
    "RustDesk":         {"exes": ["rustdesk.exe"],                                     "cat": "remote", "aliases": ["rustdesk"]},
    "VNC Viewer":       {"exes": ["vncviewer.exe"],                                    "cat": "remote", "aliases": ["vnc", "vnc viewer"]},
    "NoMachine":        {"exes": ["nxplayer.exe"],                                     "cat": "remote", "aliases": ["nomachine"]},

    # ── Virtualization ──
    "VirtualBox":       {"exes": ["VirtualBox.exe", "VBoxManage.exe"],                 "cat": "virtualization", "aliases": ["virtualbox", "vbox"]},
    "VMware":           {"exes": ["vmware.exe", "vmplayer.exe"],                       "cat": "virtualization", "aliases": ["vmware"]},
    "WSL":              {"exes": ["wsl.exe"],                                          "cat": "virtualization", "aliases": ["wsl"]},

    # ── System Tools ──
    "Terminal":         {"exes": ["wt.exe", "WindowsTerminal.exe"],                    "cat": "system", "aliases": ["terminal", "wt", "windows terminal"]},
    "PowerToys Run":    {"exes": ["PowerToys.PowerLauncher.exe"],                      "cat": "system", "aliases": ["powertoys run", "run"]},
    "Process Explorer":  {"exes": ["procexp64.exe", "procexp.exe"],                    "cat": "system", "aliases": ["process explorer", "procexp"]},
    "Process Monitor":  {"exes": ["Procmon64.exe", "Procmon.exe"],                     "cat": "system", "aliases": ["process monitor", "procmon"]},
    "Autoruns":         {"exes": ["Autoruns64.exe", "Autoruns.exe"],                   "cat": "system", "aliases": ["autoruns"]},
    "RegEdit":          {"exes": ["regedit.exe"],                                      "cat": "system", "aliases": ["regedit", "registry"]},
    "Device Manager":   {"exes": ["devmgmt.msc"],                                      "cat": "system", "aliases": ["device manager", "devmgmt"]},
    "Event Viewer":     {"exes": ["eventvwr.msc"],                                     "cat": "system", "aliases": ["event viewer", "eventvwr"]},
    "Disk Management":   {"exes": ["diskmgmt.msc"],                                    "cat": "system", "aliases": ["disk management", "diskmgmt"]},
    "Services":         {"exes": ["services.msc"],                                     "cat": "system", "aliases": ["services", "service"]},
}

# Built-in Windows apps (always available, no scan needed)
_BUILTIN_APPS: dict[str, str] = {
    "Calculator": "calc.exe",
    "Notepad": "notepad.exe",
    "File Explorer": "explorer.exe",
    "Settings": "start ms-settings:",
    "Task Manager": "taskmgr.exe",
    "Control Panel": "control.exe",
    "Paint": "mspaint.exe",
    "Snipping Tool": "snippingtool.exe",
    "Command Prompt": "cmd.exe",
    "PowerShell": "powershell.exe",
    "Run": "explorer shell:::{2559a1f3-21d7-11d4-bdaf-00c04f60b9f0}",
    "Microsoft Store": "start ms-windows-store:",
    "Camera": "start microsoft.windows.camera:",
    "Calendar": "start outlookcal:",
    "Mail": "start outlookmail:",
    "Clock": "start ms-clock:",
    "Maps": "start bingmaps:",
    "Photos": "start ms-photos:",
    "Xbox": "start xbox:",
    "Xbox Game Bar": "start ms-gamebar:",
    "Clipchamp": "start clipchamp:",
    "Media Player": "start wmplayer:",
}


# ─────────────────────────────────────────────────────────────────────
# Scanners
# ─────────────────────────────────────────────────────────────────────

def _scan_start_menu() -> dict[str, str]:
    """Scan Start Menu for .lnk shortcuts. Returns {name_lower: .lnk_path}."""
    found: dict[str, str] = {}

    start_menu_roots = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path("C:/ProgramData") / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]

    for base in start_menu_roots:
        if not base.exists():
            continue
        try:
            for lnk in base.rglob("*.lnk"):
                try:
                    name = lnk.stem.lower()
                    if name not in found:
                        found[name] = str(lnk)
                except Exception:
                    pass
        except PermissionError:
            continue

    return found


def _search_path() -> dict[str, str]:
    """Search PATH for known executables. Returns {app_key: path}."""
    found: dict[str, str] = {}
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    for app_name, info in _KNOWN_APPS.items():
        key = app_name.lower()
        for exe_name in info["exes"]:
            for d in path_dirs:
                p = Path(d) / exe_name
                if p.is_file():
                    found[key] = str(p)
                    break
            if key in found:
                break

    return found


def _scan_dirs(roots: list[Path], max_depth: int = 3) -> dict[str, str]:
    """Scan directory trees for known executables. Returns {app_key: path}."""
    found: dict[str, str] = {}

    for app_name, info in _KNOWN_APPS.items():
        key = app_name.lower()
        if key in found:
            continue

        for exe_name in info["exes"]:
            for root in roots:
                if not root.exists():
                    continue
                try:
                    # First try direct path (fast)
                    direct = root / exe_name
                    if direct.is_file():
                        found[key] = str(direct)
                        break

                    # Then scan subdirectories up to max_depth
                    depth = 0
                    for candidate in root.rglob(exe_name):
                        if candidate.is_file():
                            # Check depth
                            rel = candidate.relative_to(root)
                            if len(rel.parts) <= max_depth:
                                found[key] = str(candidate)
                                break
                    if key in found:
                        break
                except PermissionError:
                    continue
            if key in found:
                break

    return found


def _scan_program_files() -> dict[str, str]:
    """Scan Program Files directories. Returns {app_key: path}."""
    roots: list[Path] = []
    for pf_var in ["ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"]:
        pf = os.environ.get(pf_var)
        if pf and Path(pf).exists():
            roots.append(Path(pf))
    return _scan_dirs(roots, max_depth=3)


def _scan_appdata() -> dict[str, str]:
    """Scan AppData directories. Returns {app_key: path}."""
    roots: list[Path] = []
    for var in ["LOCALAPPDATA", "APPDATA"]:
        ad = os.environ.get(var)
        if ad and Path(ad).exists():
            roots.append(Path(ad))
    return _scan_dirs(roots, max_depth=4)


def _scan_registry() -> dict[str, str]:
    """Scan Windows Registry for installed applications. Returns {app_key: path}."""
    found: dict[str, str] = {}
    if platform.system() != "Windows":
        return found

    try:
        ps_cmd = (
            "Get-ChildItem -Path "
            "'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall', "
            "'HKLM:\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall', "
            "'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall' "
            "-ErrorAction SilentlyContinue | "
            "Where-Object { $_.PSChildName -notmatch '^{.*}$' } | "
            "ForEach-Object { "
            "  try { $p = Get-ItemProperty $_.PsPath -ErrorAction Stop; "
            "    if ($p.DisplayName) { @{Name=$p.DisplayName; Location=$p.InstallLocation} } "
            "  } catch {} "
            "} | ConvertTo-Json -Compress -Depth 2"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return found

        entries = json.loads(result.stdout)
        if isinstance(entries, dict):
            entries = [entries]

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("Name", "")
            location = entry.get("Location", "")
            if not name or not location:
                continue

            name_lower = name.lower()
            for app_name, info in _KNOWN_APPS.items():
                key = app_name.lower()
                if key in found:
                    continue
                # Match: app name or any exe name (without .exe) in the install name
                exe_stems = [e.lower().replace(".exe", "") for e in info["exes"]]
                if app_name.lower() in name_lower or any(stem in name_lower for stem in exe_stems):
                    # Find actual executable in the install location
                    loc_path = Path(location)
                    if loc_path.exists():
                        for exe_name in info["exes"]:
                            p = loc_path / exe_name
                            if p.is_file():
                                found[key] = str(p)
                                break
                            # Try one directory deeper
                            for sub in loc_path.glob("*/" + exe_name):
                                if sub.is_file():
                                    found[key] = str(sub)
                                    break
                            if key in found:
                                break
                    # If no exe found, mark as detected with location
                    if key not in found:
                        found[key] = str(loc_path)
    except Exception:
        pass

    return found


def _resolve_lnk_target(lnk_path: str) -> str | None:
    """Try to resolve a .lnk file to its target executable."""
    try:
        import subprocess as sp
        result = sp.run(
            ["powershell", "-NoProfile", "-Command",
             f"(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk_path}').TargetPath"],
            capture_output=True, text=True, timeout=5,
        )
        target = result.stdout.strip()
        if target and Path(target).exists():
            return target
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────
# Main Detection
# ─────────────────────────────────────────────────────────────────────

def detect_apps() -> list[dict[str, Any]]:
    """Deep scan the system for installed applications.

    Returns a list of detected apps with name, command, path, category,
    and aliases. Always returns results, never crashes.
    """
    apps: list[dict[str, Any]] = []

    # ── Built-in Windows apps (always available) ──
    for name, cmd in _BUILTIN_APPS.items():
        apps.append({
            "name": name,
            "command": cmd,
            "path": cmd,
            "category": "system",
            "aliases": [name.lower(), name.lower().replace(" ", "")],
            "builtin": True,
            "detected": True,
        })

    # Non-Windows: return built-in only
    if platform.system() != "Windows":
        logger.info("App detection: non-Windows — returning {} built-in apps", len(apps))
        return apps

    logger.info("🔍 Deep scanning for installed applications...")

    # ── Scan from multiple sources ──
    start_menu = _scan_start_menu()
    path_found = _search_path()
    prog_files = _scan_program_files()
    appdata = _scan_appdata()
    registry = _scan_registry()

    logger.info(
        "Scan results — Start Menu: {} | PATH: {} | ProgFiles: {} | AppData: {} | Registry: {}",
        len(start_menu), len(path_found), len(prog_files), len(appdata), len(registry),
    )

    # Merge: priority = prog_files > appdata > registry > path > start_menu
    all_found: dict[str, str] = {}
    for source in [prog_files, appdata, registry, path_found]:
        for name, path in source.items():
            if name not in all_found:
                all_found[name] = path

    # Also match Start Menu entries to known apps
    for sm_name, sm_path in start_menu.items():
        for app_name, info in _KNOWN_APPS.items():
            key = app_name.lower()
            if key in all_found:
                continue
            # Check if start menu name matches app name or aliases
            if (app_name.lower() in sm_name or
                info["cat"] == sm_name or
                any(alias in sm_name for alias in info["aliases"]) or
                any(exe.lower().replace(".exe", "") in sm_name for exe in info["exes"])):
                # Try to resolve .lnk to actual target
                target = _resolve_lnk_target(sm_path)
                all_found[key] = target or sm_path
                break

    # ── Build results ──
    for app_name, info in _KNOWN_APPS.items():
        key = app_name.lower()
        if key in all_found:
            apps.append({
                "name": app_name,
                "command": all_found[key],
                "path": all_found[key],
                "category": info["cat"],
                "aliases": [app_name.lower(), key.replace(" ", "")] + info["aliases"],
                "builtin": False,
                "detected": True,
            })

    logger.info("✅ Detection complete: {} apps found ({} built-in + {} detected)",
                len(apps), len(_BUILTIN_APPS), len(apps) - len(_BUILTIN_APPS))
    return apps
