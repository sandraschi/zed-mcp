# zed-mcp

MCP server for the [Zed editor](https://zed.dev) — settings management, extension lifecycle, theme discovery, project navigation, and agent configuration.

## Tools

| Tool | Purpose |
|------|---------|
| `zed_get_settings` | Read full settings.json |
| `zed_set_setting` | Set a single setting (theme, font_size, etc.) |
| `zed_get_theme` | Get current theme name |
| `zed_set_theme` | Change theme |
| `zed_list_themes` | List all installed themes |
| `zed_list_extensions` | List installed extensions with versions |
| `zed_install_extension` | Install extension from marketplace |
| `zed_uninstall_extension` | Remove an extension |
| `zed_open_file` | Open file or project directory |
| `zed_get_recent_projects` | Read recent projects from local SQLite DB |
| `zed_version` | Get installed Zed version |
| `zed_list_agents` | List configured external MCP agents |
| `zed_help` | Tool reference and config paths |
| `zed_layout` | Inspect/set layout settings (pane border, opacity, dock position); preset switch is honest-fail, no external hook exists |

## Configuration

The server auto-detects your Zed config directory (`%APPDATA%\Zed`). No manual setup required.

Key paths:
- Settings: `%APPDATA%\Zed\settings.json`
- Extensions: `%APPDATA%\Zed\extensions\installed`
- Themes: `%APPDATA%\Zed\themes`
- Recent projects DB: `%LOCALAPPDATA%\Zed\db`

Override with `ZED_CONFIG_DIR` env var.

## Usage

```bash
# Run the server (stdio mode)
uv run zed-mcp

# Or from the repo root
uv run python -m zed_mcp
```

## Requirements

- Python 3.11+
- [Zed editor](https://zed.dev) installed
- `zed` CLI on PATH or at default install location

## Docs

In-depth Zed reference material lives in docs/, aimed at onboarding and cross-editor migration rather than just this server's tool API:

- docs/01-zed-overview.md: architecture, what Zed is and is not
- docs/02-cross-platform.md: Mac/Windows/Linux, why that matters for iOS/macOS dev on Windows
- docs/03-ai-agents-acp.md: ACP, MCP support inside Zed, external agents
- docs/04-xcode-integration.md: Zed plus Xcode 27 workflow for iOS/macOS dev
- docs/05-coming-from-cursor-windsurf.md: what transfers from Cursor/Windsurf and what does not
- docs/06-webapp-plan.md: planning notes for a standalone help webapp (not yet built)
