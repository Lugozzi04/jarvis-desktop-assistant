"""Custom exceptions for JARVIS.

Structured error types that propagate through the execution pipeline
and get logged appropriately.
"""

from __future__ import annotations


class JarvisError(Exception):
    """Base exception for all JARVIS errors."""

    def __init__(self, message: str, *, code: str = "UNKNOWN", recoverable: bool = True):
        super().__init__(message)
        self.code = code
        self.recoverable = recoverable


class SkillNotFoundError(JarvisError):
    """The requested skill is not registered or enabled."""

    def __init__(self, skill_name: str):
        super().__init__(
            f"Skill not found: {skill_name}",
            code="SKILL_NOT_FOUND",
            recoverable=True,
        )


class ActionNotSupportedError(JarvisError):
    """The skill does not support this action."""

    def __init__(self, skill_name: str, action: str):
        super().__init__(
            f"Skill '{skill_name}' does not support action '{action}'",
            code="ACTION_NOT_SUPPORTED",
            recoverable=True,
        )


class PermissionDeniedError(JarvisError):
    """The action was denied by the permission guard."""

    def __init__(self, reason: str):
        super().__init__(reason, code="PERMISSION_DENIED", recoverable=True)


class ConfirmationRequiredError(JarvisError):
    """The action requires user confirmation before execution."""

    def __init__(self, message: str, action_id: str = ""):
        super().__init__(message, code="CONFIRMATION_REQUIRED", recoverable=True)
        self.action_id = action_id


class LLMError(JarvisError):
    """LLM gateway or provider error."""

    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(
            f"[{provider}] {message}",
            code="LLM_ERROR",
            recoverable=True,
        )


class ConfigError(JarvisError):
    """Configuration error."""

    def __init__(self, message: str):
        super().__init__(message, code="CONFIG_ERROR", recoverable=False)


class SkillExecutionError(JarvisError):
    """A skill failed during execution."""

    def __init__(self, skill: str, action: str, original_error: str):
        super().__init__(
            f"Skill '{skill}.{action}' failed: {original_error}",
            code="SKILL_EXECUTION_ERROR",
            recoverable=True,
        )
