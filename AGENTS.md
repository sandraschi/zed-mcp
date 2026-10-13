# AGENTS.md

## zed-mcp — Zed Editor Bridge

A FastMCP server for managing Zed editor settings, themes, extensions, recent projects, and external agents.

### Quick Start
```bash
uv run python -m zed_mcp
```

### Tools
- `zed_get_settings`, `zed_set_setting` — settings management
- `zed_get_theme`, `zed_set_theme`, `zed_list_themes` — theme control
- `zed_list_extensions`, `zed_install_extension`, `zed_uninstall_extension` — extensions
- `zed_open_file`, `zed_get_recent_projects` — project navigation
- `zed_version`, `zed_list_agents`, `zed_help` — info & diagnostics

### Configuration
- Config dir: `%APPDATA%\Zed` (override: `ZED_CONFIG_DIR`)
- CLI required for install/open operations
