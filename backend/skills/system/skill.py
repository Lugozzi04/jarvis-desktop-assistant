"""SystemSkill — monitor system resources and execute system actions.

Reads CPU, RAM, disk usage. Takes screenshots. Manages volume.
Cross-platform where possible, with graceful fallbacks.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Any

from backend.core.logger import logger
from backend.core.schemas import ActionResult
from backend.skills.base import BaseSkill


class SystemSkill(BaseSkill):
    """Monitor system resources and execute safe system actions."""

    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        if action in ("get_stats", "run_action"):
            sub_action = parameters.get("action", "stats")
            if sub_action == "stats":
                return self._get_stats()
            elif sub_action == "screenshot":
                return self._screenshot()
            else:
                return self._get_stats()
        elif action == "screenshot":
            return self._screenshot()
        else:
            return self._result(action, success=False, error=f"Unknown action: {action}")

    def _get_stats(self) -> ActionResult:
        """Collect system resource information."""
        stats: dict[str, Any] = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "processor": platform.processor() or "unknown",
        }

        # CPU usage
        try:
            cpu_percent = _get_cpu_percent()
            stats["cpu_percent"] = cpu_percent
        except Exception:
            stats["cpu_percent"] = "unavailable"

        # RAM usage
        try:
            mem = _get_memory()
            stats["memory"] = mem
        except Exception:
            stats["memory"] = {"error": "unavailable"}

        # Disk usage
        try:
            disk = shutil.disk_usage("/")
            stats["disk"] = {
                "total_gb": round(disk.total / (1024**3), 1),
                "used_gb": round(disk.used / (1024**3), 1),
                "free_gb": round(disk.free / (1024**3), 1),
                "percent": round((disk.used / disk.total) * 100, 1),
            }
        except Exception:
            stats["disk"] = {"error": "unavailable"}

        # Format output
        lines = [
            f"💻 {stats['platform']} {stats['platform_release']}",
            f"🖥️  CPU: {stats['cpu_percent']}%",
        ]
        if isinstance(stats.get("memory"), dict) and "error" not in stats["memory"]:
            mem = stats["memory"]
            lines.append(f"🧠 RAM: {mem.get('percent', '?')}% ({mem.get('used_gb', '?')}/{mem.get('total_gb', '?')} GB)")
        if isinstance(stats.get("disk"), dict) and "error" not in stats["disk"]:
            disk = stats["disk"]
            lines.append(f"💾 Disk: {disk['percent']}% ({disk['used_gb']}/{disk['total_gb']} GB used)")

        return self._result("get_stats", success=True, result="\n".join(lines))

    def _screenshot(self) -> ActionResult:
        """Take a screenshot using available system tools."""
        try:
            system = platform.system()
            output_path = os.path.expanduser("~/jarvis_screenshot.png")

            if system == "Linux":
                subprocess.run(
                    ["import", "-window", "root", output_path],
                    timeout=10, capture_output=True,
                )
            elif system == "Darwin":
                subprocess.run(
                    ["screencapture", output_path],
                    timeout=10, capture_output=True,
                )
            else:
                return self._result(
                    "screenshot",
                    success=False,
                    error="Screenshot not supported on this platform",
                )

            return self._result(
                "screenshot",
                success=True,
                result=f"Screenshot saved to {output_path}",
            )
        except FileNotFoundError:
            return self._result(
                "screenshot",
                success=False,
                error="Screenshot tool not found. Install imagemagick (Linux) or use built-in tools.",
            )
        except Exception as exc:
            return self._result("screenshot", success=False, error=str(exc))


# ── Platform-specific helpers ──

def _get_cpu_percent() -> float:
    """Get CPU usage percentage cross-platform."""
    try:
        import psutil
        return psutil.cpu_percent(interval=1)
    except ImportError:
        pass

    system = platform.system()
    try:
        if system == "Linux":
            result = subprocess.run(
                ["top", "-bn1"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.split("\n"):
                if "Cpu(s)" in line:
                    # Format: %Cpu(s): 12.3 us, ...
                    parts = line.split(",")[0].split(":")
                    if len(parts) > 1:
                        return float(parts[1].strip().split()[0])
        elif system == "Darwin":
            result = subprocess.run(
                ["top", "-l", "1", "-n", "0"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.split("\n"):
                if "CPU usage" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        pct = parts[1].strip().split("%")[0]
                        return float(pct)
    except Exception:
        pass

    return 0.0


def _get_memory() -> dict[str, Any]:
    """Get memory usage cross-platform."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 1),
            "used_gb": round(mem.used / (1024**3), 1),
            "percent": mem.percent,
        }
    except ImportError:
        pass

    system = platform.system()
    try:
        if system == "Linux":
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            total = _parse_meminfo(lines, "MemTotal:")
            available = _parse_meminfo(lines, "MemAvailable:")
            if total and available:
                used = total - available
                return {
                    "total_gb": round(total / (1024**2), 1),
                    "used_gb": round(used / (1024**2), 1),
                    "percent": round((used / total) * 100, 1),
                }
    except Exception:
        pass

    return {"error": "unavailable"}


def _parse_meminfo(lines: list[str], key: str) -> int | None:
    """Parse a value from /proc/meminfo."""
    for line in lines:
        if line.startswith(key):
            parts = line.split()
            if len(parts) >= 2:
                return int(parts[1])
    return None
