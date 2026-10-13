# zed-mcp

## Build & Run
- Run server: `uv run python -m zed_mcp`
- Lint: `ruff check src/`
- Format: `ruff format src/`

## Architecture
- FastMCP 3.4+ server, stdio transport only
- Reads Zed config from %APPDATA%\Zed
- 12 tools: settings, themes, extensions, projects, agents
- No webapp, no Tauri wrapper (stdio-only MCP)
