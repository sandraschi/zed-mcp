"""FastMCP server for Zed editor — settings, extensions, themes, projects, diagnostics."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sqlite3
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

log = logging.getLogger(__name__)

_APPDATA = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
_ZED_DIR = Path(os.getenv("ZED_CONFIG_DIR", _APPDATA / "Zed"))
_ZED_SETTINGS = _ZED_DIR / "settings.json"
_ZED_EXTENSIONS = _ZED_DIR / "extensions" / "installed"
_ZED_THEMES = _ZED_DIR / "themes"
_ZED_DB_DIR = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Zed" / "db"

mcp = FastMCP(
    "zed-mcp",
    instructions="MCP server for Zed editor — settings, extensions, themes, projects, open files.",
    version="0.1.0",
)

_READ_ONLY = {"readonly": True}
_MUTATING = {}


def _zed_cli() -> str | None:
    """Find the zed CLI binary."""
    for candidate in [
        os.path.expanduser("~/.local/bin/zed"),
        "C:/Users/sandr/AppData/Local/Programs/Zed Preview/bin/zed.exe",
        "zed",
    ]:
        if Path(candidate).is_file() or candidate == "zed":
            return candidate
    return None


def _read_settings() -> dict:
    if not _ZED_SETTINGS.is_file():
        return {}
    try:
        return json.loads(_ZED_SETTINGS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_settings(data: dict) -> bool:
    try:
        _ZED_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        # Backup current settings before overwriting
        if _ZED_SETTINGS.is_file():
            bak = _ZED_SETTINGS.with_suffix(f".json.bak.{Path.home().name}")
            _ZED_SETTINGS.rename(bak)
        _ZED_SETTINGS.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


# ── Settings ──────────────────────────────────────────────────────────────────


@mcp.tool(annotations=_READ_ONLY)
async def zed_get_settings(ctx: Any = None) -> dict:
    """Read the full Zed settings.json.

    ## Return Format
    {"settings": dict, "path": str}
    """
    return {"settings": _read_settings(), "path": str(_ZED_SETTINGS)}


@mcp.tool(annotations=_MUTATING)
async def zed_set_setting(key: str, value: str, ctx: Any = None) -> dict:
    """Set a single Zed setting (e.g. theme, font_size, tab_size).

    Merges into existing settings.json. Creates a backup before writing.

    ## Return Format
    {"success": bool, "key": str, "value": any}

    ## Examples
    zed_set_setting("theme", "One Dark Pro")
    zed_set_setting("tab_size", "4")
    """
    current = _read_settings()
    # Coerce numeric values
    try:
        if "." in value:
            value_converted: Any = float(value)
        else:
            value_converted = int(value)
    except (ValueError, TypeError):
        value_converted = value
    current[key] = value_converted
    ok = _write_settings(current)
    return {"success": ok, "key": key, "value": value_converted}


# ── Themes ────────────────────────────────────────────────────────────────────


@mcp.tool(annotations=_READ_ONLY)
async def zed_get_theme(ctx: Any = None) -> dict:
    """Get the current Zed theme from settings.

    ## Return Format
    {"theme": str}
    """
    settings = _read_settings()
    return {"theme": settings.get("theme", "default")}


@mcp.tool(annotations=_MUTATING)
async def zed_set_theme(theme_name: str, ctx: Any = None) -> dict:
    """Change the Zed theme by writing to settings.json.

    ## Return Format
    {"success": bool, "theme": str}

    ## Examples
    zed_set_theme("catppuccin")
    zed_set_theme("One Dark Pro")
    """
    current = _read_settings()
    current["theme"] = theme_name
    ok = _write_settings(current)
    return {"success": ok, "theme": theme_name}


@mcp.tool(annotations=_READ_ONLY)
async def zed_list_themes(ctx: Any = None) -> dict:
    """List all installed themes available in Zed.

    Scans the themes directory and extension-installed themes.

    ## Return Format
    {"themes": [str], "count": int}
    """
    themes: set[str] = set()

    # Built-in themes from extensions
    if _ZED_EXTENSIONS.is_dir():
        for ext in _ZED_EXTENSIONS.iterdir():
            theme_dir = ext / "themes"
            if theme_dir.is_dir():
                for f in theme_dir.glob("*.json"):
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                        for t in data.get("themes", []):
                            if isinstance(t, dict) and "name" in t:
                                themes.add(t["name"])
                    except (json.JSONDecodeError, OSError):
                        pass

    # User-installed themes
    if _ZED_THEMES.is_dir():
        for f in _ZED_THEMES.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                for t in data.get("themes", []):
                    if isinstance(t, dict) and "name" in t:
                        themes.add(t["name"])
            except (json.JSONDecodeError, OSError):
                pass

    return {"themes": sorted(themes), "count": len(themes)}


# ── Extensions ────────────────────────────────────────────────────────────────


@mcp.tool(annotations=_READ_ONLY)
async def zed_list_extensions(ctx: Any = None) -> dict:
    """List all installed Zed extensions with name and version.

    ## Return Format
    {"extensions": [{"id": str, "name": str, "version": str}], "count": int}
    """
    if not _ZED_EXTENSIONS.is_dir():
        return {"extensions": [], "count": 0}
    exts = []
    for entry in sorted(_ZED_EXTENSIONS.iterdir()):
        if entry.is_dir():
            manifest = entry / "extension.json"
            if manifest.is_file():
                try:
                    meta = json.loads(manifest.read_text(encoding="utf-8"))
                    exts.append(
                        {
                            "id": entry.name,
                            "name": meta.get("name", entry.name),
                            "version": meta.get("version", ""),
                        }
                    )
                except (json.JSONDecodeError, OSError):
                    exts.append({"id": entry.name})
    return {"extensions": exts, "count": len(exts)}


@mcp.tool(annotations=_MUTATING)
async def zed_install_extension(extension_id: str, ctx: Any = None) -> dict:
    """Install a Zed extension from the marketplace.

    Uses `zed --install <extension_id>` CLI command.

    ## Return Format
    {"success": bool, "extension": str}

    ## Examples
    zed_install_extension("catppuccin")
    zed_install_extension("rust")
    """
    cli = _zed_cli()
    if not cli:
        return {"success": False, "error": "zed CLI not found"}
    try:
        subprocess.run(
            [cli, "--install", extension_id], check=True, timeout=60, capture_output=True
        )
        return {"success": True, "extension": extension_id}
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": f"Install failed: {e.stderr.decode() if e.stderr else e}",
        }
    except FileNotFoundError:
        return {"success": False, "error": "zed CLI not found"}


@mcp.tool(annotations=_MUTATING)
async def zed_uninstall_extension(extension_id: str, ctx: Any = None) -> dict:
    """Uninstall a Zed extension by removing its directory.

    ## Return Format
    {"success": bool, "extension": str}

    ## Examples
    zed_uninstall_extension("catppuccin")
    """
    ext_dir = _ZED_EXTENSIONS / extension_id
    if not ext_dir.is_dir():
        return {"success": False, "error": f"Extension '{extension_id}' not installed"}
    try:
        import shutil

        shutil.rmtree(ext_dir)
        return {"success": True, "extension": extension_id}
    except OSError as e:
        return {"success": False, "error": str(e)}


# ── Projects & Files ──────────────────────────────────────────────────────────


@mcp.tool(annotations=_MUTATING)
async def zed_open_file(file_path: str, ctx: Any = None) -> dict:
    """Open a file or project directory in Zed editor.

    ## Return Format
    {"success": bool, "target": str}

    ## Examples
    zed_open_file("D:/Dev/repos/README.md")
    zed_open_file("D:/Dev/repos/arxiv-mcp")
    """
    target = Path(file_path)
    if not target.exists():
        return {"success": False, "error": f"Path not found: {file_path}"}
    cli = _zed_cli()
    if not cli:
        return {"success": False, "error": "zed CLI not found"}
    try:
        subprocess.run([cli, str(target)], check=True, timeout=10)
        return {"success": True, "target": file_path}
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return {"success": False, "error": str(e)}


@mcp.tool(annotations=_READ_ONLY)
async def zed_get_recent_projects(ctx: Any = None) -> dict:
    """Read recent Zed projects from the local database.

    Queries the Zed SQLite DB for recent project paths.

    ## Return Format
    {"projects": [{"path": str, "name": str}], "count": int}
    """
    # Discover the latest Zed release DB
    db_candidates = sorted(_ZED_DB_DIR.glob("*/db.sqlite"), reverse=True)
    if not db_candidates:
        return {"projects": [], "count": 0}
    db_path = db_candidates[0]
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT path FROM project_panel_recent_selections ORDER BY timestamp DESC LIMIT 30"
        )
        projects = []
        for row in cursor.fetchall():
            p = Path(row[0])
            projects.append({"path": str(p), "name": p.name})
        conn.close()
        return {"projects": projects, "count": len(projects)}
    except (sqlite3.OperationalError, sqlite3.DatabaseError, IndexError) as e:
        return {"projects": [], "count": 0, "note": f"Could not query DB: {e}"}


# ── Editor Info ────────────────────────────────────────────────────────────────


@mcp.tool(annotations=_READ_ONLY)
async def zed_version(ctx: Any = None) -> dict:
    """Get the installed Zed editor version.

    ## Return Format
    {"version": str, "path": str}
    """
    cli = _zed_cli()
    if not cli:
        return {"version": "unknown", "path": ""}
    try:
        result = subprocess.run([cli, "--version"], capture_output=True, text=True, timeout=5)
        return {"version": result.stdout.strip() or result.stderr.strip(), "path": cli}
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return {"version": "unknown", "path": cli, "error": str(e)}


@mcp.tool(annotations=_READ_ONLY)
async def zed_list_agents(ctx: Any = None) -> dict:
    """List installed external Zed agents (MCP servers configured in Zed).

    Reads zed_agent_config.json or scans the external_agents directory.

    ## Return Format
    {"agents": [{"name": str}], "count": int}
    """
    agents_dir = _ZED_DIR / "external_agents"
    if not agents_dir.is_dir():
        return {"agents": [], "count": 0}
    agents = []
    for entry in sorted(agents_dir.iterdir()):
        if entry.suffix == ".json":
            try:
                data = json.loads(entry.read_text(encoding="utf-8"))
                agents.append({"name": entry.stem, "config": data})
            except (json.JSONDecodeError, OSError):
                agents.append({"name": entry.stem})
    return {"agents": agents, "count": len(agents)}


# ── Help ──────────────────────────────────────────────────────────────────────


@mcp.tool(annotations=_READ_ONLY)
async def zed_help(ctx: Any = None) -> dict:
    """Show all available zed-mcp tools and usage."""
    return {
        "tools": [
            {"name": "zed_get_settings", "description": "Read all Zed settings"},
            {
                "name": "zed_set_setting",
                "description": "Set a single setting (theme, font_size, etc.)",
            },
            {"name": "zed_get_theme", "description": "Get current theme"},
            {"name": "zed_set_theme", "description": "Change theme"},
            {"name": "zed_list_themes", "description": "List all installed themes"},
            {"name": "zed_list_extensions", "description": "List installed extensions"},
            {"name": "zed_install_extension", "description": "Install extension from marketplace"},
            {"name": "zed_uninstall_extension", "description": "Uninstall an extension"},
            {"name": "zed_open_file", "description": "Open file/project in Zed"},
            {"name": "zed_get_recent_projects", "description": "Read recent projects from DB"},
            {"name": "zed_version", "description": "Get Zed version"},
            {"name": "zed_list_agents", "description": "List configured external agents"},
        ],
        "config_dir": str(_ZED_DIR),
        "extensions_dir": str(_ZED_EXTENSIONS),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp.run()


if __name__ == "__main__":
    main()
