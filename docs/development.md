# Development Guide

## Setup for Development

```bash
# Clone
git clone https://github.com/Lugozzi04/jarvis-desktop-assistant
cd jarvis-desktop-assistant

# Create venv
uv venv
source .venv/bin/activate

# Install deps
uv pip install -e ".[dev]"

# Run tests
pytest

# Run backend
uvicorn backend.main:app --reload
```

## Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_router.py -v

# With coverage
pytest --cov=backend --cov-report=html
```

## Code Style

- Python 3.11+ with type hints
- Pydantic v2 for all data models
- SQLAlchemy 2.0 for database
- Loguru for logging (not print)
- Follow existing patterns in `backend/core/`

## Adding a Skill

1. Create `backend/skills/<name>/manifest.json`
2. Create `backend/skills/<name>/skill.py`
3. Inherit from `BaseSkill`, implement `execute()`
4. Return `ActionResult` objects
5. Test with: `curl -X POST localhost:8400/api/skills/<name>/execute?...`

## Commit Conventions

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation
- `refactor:` — code restructuring
- `test:` — tests
- `chore:` — build, deps, config

## Branch Strategy

- `main` — stable, deployable
- Feature branches from `main`
- PR review before merge
