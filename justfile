set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

# zed-mcp
server:
    uv run python -m zed_mcp

lint:
    uv run ruff check src/

fmt:
    uv run ruff format src/

lint-fix:
    uv run ruff check --fix src/

# Bootstrap: install dev deps + pre-commit hook
bootstrap:
    uv sync --group dev
    uv run pre-commit install
    Write-Host "Pre-commit hooks installed." -ForegroundColor Green