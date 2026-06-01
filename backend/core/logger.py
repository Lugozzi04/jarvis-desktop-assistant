"""Structured logger using Loguru.

Every action in JARVIS is logged with full context — input, intent,
skill, action, parameters, risk, result, errors, and timing.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from backend.core.config import settings


def setup_logging() -> None:
    """Configure Loguru with console and file sinks."""
    logger.remove()

    # Console output — colored, compact
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File output — structured, full detail
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    logger.add(
        logs_dir / "jarvis_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
    )

    # Audit log — only action-level events
    logger.add(
        logs_dir / "audit_{time:YYYY-MM-DD}.log",
        level="INFO",
        format="{time:ISO} | {message}",
        rotation="10 MB",
        retention="90 days",
        filter=lambda record: record["extra"].get("audit", False),
    )

    logger.info("Logging configured — env={}", settings.env)


def audit_log(
    action: str,
    skill: str | None = None,
    parameters: dict | None = None,
    risk: str = "safe",
    result: str = "",
    duration_ms: float = 0.0,
) -> None:
    """Write an audit log entry (structured, searchable)."""
    logger.bind(audit=True).info(
        "action={action} skill={skill} risk={risk} "
        "params={params} result={result} duration_ms={duration_ms:.0f}",
        action=action,
        skill=skill or "-",
        risk=risk,
        params=parameters or {},
        result=result,
        duration_ms=duration_ms,
    )


__all__ = ["logger", "setup_logging", "audit_log"]
