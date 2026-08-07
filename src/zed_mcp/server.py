"""FastMCP server for Zed editor  --  settings, extensions, themes, projects, diagnostics."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

log = logging.getLogger(__name__)

_APPDATA = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
_ZED_DIR = Path(os.getenv("ZED_CONFIG_DIR", _APPDATA / "Zed"))
_ZED_SETTINGS = _ZED_DIR / "settings.json"
_ZED_EXTENSIONS = _ZED_DIR / "extensions" / "installed"
_ZED_THEMES = _ZED_DIR / "themes"
_ZED_DB_DIR = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Zed" / "db"

mcp = FastMCP(
    "zed-mcp",
    instructions="MCP server for Zed editor  --  settings, extensions, themes, projects, open files.",
    version="0.4.0",
)

_READ_ONLY = {"readonly": True}
_MUTATING = {}


def _error_response(error: str, error_type: str = "general", **kwargs: Any) -> dict:
    log.exception("Tool error: %s [%s]", error, error_type)
    return {
        "success": False,
        "error": error,
        "error_type": error_type,
        "message": error,
        **kwargs,
    }


def _zed_cli() -> str | None:
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
        if _ZED_SETTINGS.is_file():
            bak = _ZED_SETTINGS.with_suffix(f".json.bak.{Path.home().name}")
            _ZED_SETTINGS.rename(bak)
        _ZED_SETTINGS.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except OSError:
        log.warning("Failed to write settings to %s", _ZED_SETTINGS, exc_info=True)
        return False


# -- Settings ------------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY)
async def zed_get_settings(ctx: Any = None) -> dict:
    """Read the full Zed settings.json.

    ## Return Format
    {"settings": dict, "path": str}
    """
    s = _read_settings()
    return {
        "settings": s,
        "path": str(_ZED_SETTINGS),
        "message": f"Read settings from {_ZED_SETTINGS}",
    }


@mcp.tool(annotations=_MUTATING)
async def zed_set_setting(
    key: Annotated[str, Field(description="Setting name to set.")],
    value: Annotated[
        str, Field(description="Value to set (auto-coerced to int/float when numeric).")
    ],
    ctx: Any = None,
) -> dict:
    """Set a single Zed setting.

    Merges into existing settings.json. Creates a backup before writing.

    ## Return Format
    {"success": bool, "key": str, "value": any, "message": str}

    ## Examples
    zed_set_setting("theme", "One Dark Pro")
    zed_set_setting("tab_size", "4")
    """
    current = _read_settings()
    try:
        if "." in value:
            value_converted: Any = float(value)
        else:
            value_converted = int(value)
    except (ValueError, TypeError):
        value_converted = value
    current[key] = value_converted
    ok = _write_settings(current)
    if not ok:
        return _error_response(f"Failed to write setting '{key}'", error_type="write_error")
    return {
        "success": True,
        "key": key,
        "value": value_converted,
        "message": f"Set {key} to {value_converted}",
    }


# -- Themes --------------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY)
async def zed_get_theme(ctx: Any = None) -> dict:
    """Get the current Zed theme from settings.

    ## Return Format
    {"theme": str, "message": str}
    """
    settings = _read_settings()
    theme = settings.get("theme", "default")
    return {"theme": theme, "message": f"Current theme: {theme}"}


@mcp.tool(annotations=_MUTATING)
async def zed_set_theme(
    theme_name: Annotated[str, Field(description="Theme name to apply.")],
    ctx: Any = None,
) -> dict:
    """Change the Zed theme by writing to settings.json.

    ## Return Format
    {"success": bool, "theme": str, "message": str}

    ## Examples
    zed_set_theme("catppuccin")
    zed_set_theme("One Dark Pro")
    """
    current = _read_settings()
    current["theme"] = theme_name
    ok = _write_settings(current)
    if not ok:
        return _error_response(f"Failed to set theme '{theme_name}'", error_type="write_error")
    return {"success": True, "theme": theme_name, "message": f"Theme changed to {theme_name}"}


@mcp.tool(annotations=_READ_ONLY)
async def zed_list_themes(ctx: Any = None) -> dict:
    """List all installed themes available in Zed.

    Scans the themes directory and extension-installed themes.

    ## Return Format
    {"themes": [str], "count": int, "message": str}
    """
    themes: set[str] = set()

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

    if _ZED_THEMES.is_dir():
        for f in _ZED_THEMES.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                for t in data.get("themes", []):
                    if isinstance(t, dict) and "name" in t:
                        themes.add(t["name"])
            except (json.JSONDecodeError, OSError):
                pass

    sorted_themes = sorted(themes)
    return {
        "themes": sorted_themes,
        "count": len(sorted_themes),
        "message": f"Found {len(sorted_themes)} themes",
    }


# -- Extensions ----------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY)
async def zed_list_extensions(ctx: Any = None) -> dict:
    """List all installed Zed extensions with name and version.

    ## Return Format
    {"extensions": [{"id": str, "name": str, "version": str}], "count": int, "message": str}
    """
    if not _ZED_EXTENSIONS.is_dir():
        return {"extensions": [], "count": 0, "message": "No extensions directory found"}
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
    return {"extensions": exts, "count": len(exts), "message": f"Found {len(exts)} extensions"}


@mcp.tool(annotations=_MUTATING)
async def zed_install_extension(
    extension_id: Annotated[str, Field(description="Marketplace extension ID to install.")],
    ctx: Any = None,
) -> dict:
    """Install a Zed extension from the marketplace.

    Uses `zed --install <extension_id>` CLI command.

    ## Return Format
    {"success": bool, "extension": str, "message": str}

    ## Examples
    zed_install_extension("catppuccin")
    zed_install_extension("rust")
    """
    cli = _zed_cli()
    if not cli:
        return _error_response("zed CLI not found", error_type="cli_not_found")
    try:
        subprocess.run(
            [cli, "--install", extension_id], check=True, timeout=60, capture_output=True
        )
        return {
            "success": True,
            "extension": extension_id,
            "message": f"Installed extension: {extension_id}",
        }
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode() if e.stderr else str(e)
        return _error_response(f"Install failed: {err}", error_type="install_failed")
    except FileNotFoundError:
        return _error_response("zed CLI not found", error_type="cli_not_found")


@mcp.tool(annotations=_MUTATING)
async def zed_uninstall_extension(
    extension_id: Annotated[str, Field(description="Extension ID to remove.")],
    ctx: Any = None,
) -> dict:
    """Uninstall a Zed extension by removing its directory.

    ## Return Format
    {"success": bool, "extension": str, "message": str}

    ## Examples
    zed_uninstall_extension("catppuccin")
    """
    ext_dir = _ZED_EXTENSIONS / extension_id
    if not ext_dir.is_dir():
        return _error_response(f"Extension '{extension_id}' not installed", error_type="not_found")
    try:
        shutil.rmtree(ext_dir)
        return {
            "success": True,
            "extension": extension_id,
            "message": f"Uninstalled extension: {extension_id}",
        }
    except OSError as e:
        return _error_response(str(e), error_type="uninstall_failed")


# -- Projects & Files ----------------------------------------------------------


@mcp.tool(annotations=_MUTATING)
async def zed_open_file(
    file_path: Annotated[
        str, Field(description="Absolute path to file or directory to open in Zed.")
    ],
    ctx: Any = None,
) -> dict:
    """Open a file or project directory in Zed editor.

    ## Return Format
    {"success": bool, "target": str, "message": str}

    ## Examples
    zed_open_file("D:/Dev/repos/README.md")
    zed_open_file("D:/Dev/repos/arxiv-mcp")
    """
    target = Path(file_path)
    if not target.exists():
        return _error_response(f"Path not found: {file_path}", error_type="path_not_found")
    cli = _zed_cli()
    if not cli:
        return _error_response("zed CLI not found", error_type="cli_not_found")
    try:
        subprocess.run([cli, str(target)], check=True, timeout=10)
        return {"success": True, "target": file_path, "message": f"Opened {file_path} in Zed"}
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return _error_response(str(e), error_type="open_failed")


@mcp.tool(annotations=_READ_ONLY)
async def zed_get_recent_projects(ctx: Any = None) -> dict:
    """Read recent Zed projects from the local database.

    Queries the Zed SQLite DB for recent project paths.

    ## Return Format
    {"projects": [{"path": str, "name": str}], "count": int, "message": str}
    """
    db_candidates = sorted(_ZED_DB_DIR.glob("*/db.sqlite"), reverse=True)
    if not db_candidates:
        return {"projects": [], "count": 0, "message": "No Zed database found"}
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
        return {
            "projects": projects,
            "count": len(projects),
            "message": f"Found {len(projects)} recent projects",
        }
    except (sqlite3.OperationalError, sqlite3.DatabaseError, IndexError) as e:
        return {"projects": [], "count": 0, "message": f"Could not query DB: {e}", "note": str(e)}


# -- Editor Info ----------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY)
async def zed_version(ctx: Any = None) -> dict:
    """Get the installed Zed editor version.

    ## Return Format
    {"version": str, "path": str, "message": str}
    """
    cli = _zed_cli()
    if not cli:
        return {"version": "unknown", "path": "", "message": "zed CLI not found"}
    try:
        result = subprocess.run([cli, "--version"], capture_output=True, text=True, timeout=5)
        v = result.stdout.strip() or result.stderr.strip()
        return {"version": v, "path": cli, "message": f"Zed {v} at {cli}"}
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return {
            "version": "unknown",
            "path": cli,
            "message": f"Could not detect version: {e}",
            "error": str(e),
        }


@mcp.tool(annotations=_READ_ONLY)
async def zed_list_agents(ctx: Any = None) -> dict:
    """List installed external Zed agents (MCP servers configured in Zed).

    Reads the external_agents directory.

    ## Return Format
    {"agents": [{"name": str, "config": dict}], "count": int, "message": str}
    """
    agents_dir = _ZED_DIR / "external_agents"
    if not agents_dir.is_dir():
        return {"agents": [], "count": 0, "message": "No external agents directory found"}
    agents = []
    for entry in sorted(agents_dir.iterdir()):
        if entry.suffix == ".json":
            try:
                data = json.loads(entry.read_text(encoding="utf-8"))
                agents.append({"name": entry.stem, "config": data})
            except (json.JSONDecodeError, OSError):
                agents.append({"name": entry.stem})
    return {
        "agents": agents,
        "count": len(agents),
        "message": f"Found {len(agents)} external agents",
    }


# -- Help ----------------------------------------------------------------------


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
            {"name": "zed_open_tabs", "description": "List open editor tabs from DB"},
            {"name": "zed_workspace", "description": "Workspace status, diagnostics, bookmarks"},
            {"name": "zed_search_project", "description": "Search project files with ripgrep"},
            {"name": "zed_list_keybindings", "description": "Read keymap.json"},
            {"name": "zed_set_keybinding", "description": "Add or update a keybinding"},
            {"name": "zed_snippets", "description": "List, get, create, delete snippets"},
            {"name": "zed_git_blame", "description": "Git blame annotations for a file"},
            {"name": "zed_tasks", "description": "List or run .zed/tasks.json tasks"},
            {"name": "zed_layout", "description": "Inspect/set settings-backed layout knobs; set_preset is honest-fail (no external hook exists)"},
        ],
        "config_dir": str(_ZED_DIR),
        "extensions_dir": str(_ZED_EXTENSIONS),
        "message": "zed-mcp help: 22 tools available",
    }


# -- New helpers --------------------------------------------------------------


def _latest_db() -> Path | None:
    db_candidates = sorted(_ZED_DB_DIR.glob("*/db.sqlite"), reverse=True)
    return db_candidates[0] if db_candidates else None


def _db_cursor(db: Path) -> sqlite3.Connection | None:
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.DatabaseError:
        return None


def _keymap_path() -> Path:
    return _ZED_DIR / "keymap.json"


def _snippets_dir() -> Path:
    return _ZED_DIR / "snippets"


def _tasks_path(project_path: str) -> Path | None:
    for candidate in [
        Path(project_path) / ".zed" / "tasks.json",
        Path(project_path) / ".zed" / "tasks.jsonc",
    ]:
        if candidate.is_file():
            return candidate
    return None


def _str_decode(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return str(val)


# -- Open Tabs -----------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY)
async def zed_open_tabs(ctx: Any = None) -> dict:
    """List all open editor tabs in Zed.

    Queries the Zed SQLite DB for editors and items with their paths, language,
    and active state across all workspaces.

    ## Return Format
    {"tabs": [{"workspace_id": int, "path": str, "language": str, "active": bool, "position": int}], "count": int, "message": str}
    """
    db = _latest_db()
    if not db:
        return {"tabs": [], "count": 0, "message": "No Zed database found"}
    conn = _db_cursor(db)
    if not conn:
        return {"tabs": [], "count": 0, "message": "Could not open Zed database"}
    try:
        rows = conn.execute("""
            SELECT i.workspace_id, i.item_id, i.active, i.position,
                   e.path, e.language, e.buffer_path
            FROM items i
            LEFT JOIN editors e ON i.item_id = e.item_id AND i.workspace_id = e.workspace_id
            WHERE i.kind = 'Editor'
            ORDER BY i.workspace_id, i.position
        """).fetchall()
        tabs = []
        for r in rows:
            raw_path = r["path"] if r["path"] is not None else r["buffer_path"]
            path_str = _str_decode(raw_path)
            if path_str:
                tabs.append(
                    {
                        "workspace_id": r["workspace_id"],
                        "path": path_str,
                        "language": r["language"],
                        "active": bool(r["active"]),
                        "position": r["position"],
                    }
                )
        conn.close()
        return {"tabs": tabs, "count": len(tabs), "message": f"Found {len(tabs)} open tabs"}
    except sqlite3.DatabaseError as e:
        conn.close()
        return {"tabs": [], "count": 0, "message": f"Query failed: {e}"}


# -- Workspace portmanteau ------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY)
async def zed_workspace(
    operation: Annotated[
        str, Field(description="Operation: 'status' (default), 'diagnostics', 'bookmarks'.")
    ] = "status",
    project_path: Annotated[
        str | None, Field(description="Filter to workspace containing this path.")
    ] = None,
    ctx: Any = None,
) -> dict:
    """Query Zed workspace state  --  open tabs, active projects, bookmarks, toolchains.

    PORTMANTEAU RATIONALE: Consolidates workspace-level queries into one tool.
    Rather than separate calls for open projects, bookmarks, and toolchains, a
    single call returns the full workspace context the agent needs.

    Operations:
    - status: Workspace list, open tab count, panel visibility, active project
    - diagnostics: Open files with languages (LSP diagnostics not persisted to DB)
    - bookmarks: File bookmarks across workspaces

    ## Return Format
    {"success": bool, "operation": str, "data": {...}, "message": str}

    ## Examples
    zed_workspace("status")
    zed_workspace("status", project_path="D:/Dev/repos/zed-mcp")
    zed_workspace("bookmarks")
    """
    db = _latest_db()
    if not db:
        return {
            "success": False,
            "operation": operation,
            "data": {},
            "message": "No Zed database found",
        }
    conn = _db_cursor(db)
    if not conn:
        return {
            "success": False,
            "operation": operation,
            "data": {},
            "message": "Could not open DB",
        }

    try:
        if operation == "status":
            ws_filter = ""
            params: list = []
            if project_path:
                ws_filter = " WHERE w.paths LIKE ?"
                params.append(f"%{project_path}%")
            workspaces = conn.execute(
                f"""
                SELECT w.workspace_id, w.paths, w.timestamp, w.session_id,
                       w.left_dock_visible, w.right_dock_visible, w.bottom_dock_visible,
                       w.fullscreen, w.centered_layout,
                       (SELECT COUNT(*) FROM items i WHERE i.workspace_id = w.workspace_id AND i.kind = 'Editor') AS tab_count
                FROM workspaces w {ws_filter}
                ORDER BY w.timestamp DESC
                LIMIT 10
            """,
                params,
            ).fetchall()

            ws_list = []
            for w in workspaces:
                paths_raw = w["paths"]
                paths = paths_raw if isinstance(paths_raw, str) else _str_decode(paths_raw)
                ws_list.append(
                    {
                        "workspace_id": w["workspace_id"],
                        "paths": paths.split(",") if paths else [],
                        "last_active": w["timestamp"],
                        "session_id": w["session_id"],
                        "tab_count": w["tab_count"],
                        "panels": {
                            "left_dock": bool(w["left_dock_visible"]),
                            "right_dock": bool(w["right_dock_visible"]),
                            "bottom_dock": bool(w["bottom_dock_visible"]),
                        },
                        "fullscreen": bool(w["fullscreen"]),
                    }
                )
            conn.close()
            return {
                "success": True,
                "operation": "status",
                "data": {"workspaces": ws_list, "count": len(ws_list)},
                "message": f"Found {len(ws_list)} workspaces",
            }

        elif operation == "diagnostics":
            tabs = conn.execute("""
                SELECT e.path, e.language, e.buffer_path
                FROM items i
                JOIN editors e ON i.item_id = e.item_id AND i.workspace_id = e.workspace_id
                WHERE i.kind = 'Editor' AND e.path IS NOT NULL
                ORDER BY i.workspace_id, i.position
                LIMIT 50
            """).fetchall()
            files = []
            for t in tabs:
                path_str = _str_decode(t["path"] or t["buffer_path"])
                if path_str:
                    files.append({"path": path_str, "language": t["language"]})
            conn.close()
            return {
                "success": True,
                "operation": "diagnostics",
                "data": {
                    "open_files": files,
                    "count": len(files),
                    "note": "LSP diagnostics are not persisted to the Zed SQLite DB. Use zed_search_project() with ripgrep for code-level analysis.",
                },
                "message": f"Found {len(files)} open files",
            }

        elif operation == "bookmarks":
            try:
                rows = conn.execute(
                    "SELECT path, row, label FROM bookmarks ORDER BY path, row LIMIT 50"
                ).fetchall()
                bm = [
                    {"path": _str_decode(r["path"]), "row": r["row"], "label": r["label"]}
                    for r in rows
                ]
                conn.close()
                return {
                    "success": True,
                    "operation": "bookmarks",
                    "data": {"bookmarks": bm, "count": len(bm)},
                    "message": f"Found {len(bm)} bookmarks",
                }
            except sqlite3.OperationalError:
                conn.close()
                return {
                    "success": False,
                    "operation": "bookmarks",
                    "data": {"bookmarks": [], "count": 0},
                    "message": "Bookmarks table not found",
                }

        else:
            conn.close()
            return {
                "success": False,
                "operation": operation,
                "data": {},
                "message": f"Unknown operation: {operation}",
            }

    except sqlite3.DatabaseError as e:
        conn.close()
        return {
            "success": False,
            "operation": operation,
            "data": {},
            "message": f"Query failed: {e}",
        }


# -- Project Search -------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY)
async def zed_search_project(
    query: Annotated[str, Field(description="Text to search for in project files.")],
    project_path: Annotated[str, Field(description="Project directory root to search in.")],
    max_results: Annotated[
        int, Field(description="Max results (default 20, max 100).", ge=1, le=100)
    ] = 20,
    ctx: Any = None,
) -> dict:
    """Search across project files using ripgrep.

    Searches file contents in the given project directory. Also returns recent
    text finder queries from the Zed DB for context.

    ## Return Format
    {"results": [{"file": str, "line": int, "text": str}], "count": int, "recent_searches": [str], "message": str}

    ## Examples
    zed_search_project("FastMCP", "D:/Dev/repos/zed-mcp")
    """
    rg = shutil.which("rg")
    if not rg:
        return {
            "results": [],
            "count": 0,
            "recent_searches": [],
            "message": "ripgrep (rg) not found on PATH",
        }

    if not os.path.isdir(project_path):
        return {
            "results": [],
            "count": 0,
            "recent_searches": [],
            "message": f"Project path not found: {project_path}",
        }

    try:
        result = subprocess.run(
            [rg, "--no-heading", "--line-number", "--max-count", "3", "-i", query, project_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        results = []
        for line in lines[:max_results]:
            parts = line.split(":", 2)
            if len(parts) >= 3:
                results.append({"file": parts[0], "line": int(parts[1]), "text": parts[2]})
            elif len(parts) == 2:
                results.append({"file": parts[0], "line": int(parts[1]), "text": ""})

        # Also grab recent text finder queries from DB
        recent = []
        db = _latest_db()
        if db:
            try:
                conn2 = _db_cursor(db)
                if conn2:
                    for row in conn2.execute(
                        "SELECT query FROM text_finder_queries ORDER BY rowid DESC LIMIT 10"
                    ):
                        recent.append(row["query"])
                    conn2.close()
            except sqlite3.OperationalError:
                pass

        return {
            "results": results,
            "count": len(results),
            "recent_searches": recent,
            "message": f"Found {len(results)} matches",
        }
    except subprocess.TimeoutExpired:
        return {
            "results": [],
            "count": 0,
            "recent_searches": [],
            "message": "Search timed out (30s)",
        }
    except FileNotFoundError:
        return {
            "results": [],
            "count": 0,
            "recent_searches": [],
            "message": "ripgrep (rg) not found",
        }


# -- Keybindings ----------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY)
async def zed_list_keybindings(ctx: Any = None) -> dict:
    """Read the current Zed keymap.json.

    ## Return Format
    {"keybindings": list, "path": str, "message": str}
    """
    kp = _keymap_path()
    if not kp.is_file():
        return {"keybindings": [], "path": str(kp), "message": "No keymap.json found"}
    try:
        data = json.loads(kp.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {
                "keybindings": data,
                "path": str(kp),
                "message": f"Found {len(data)} keybindings",
            }
        return {"keybindings": [], "path": str(kp), "message": "keymap.json is not a list"}
    except (json.JSONDecodeError, OSError) as e:
        return {"keybindings": [], "path": str(kp), "message": f"Failed to read keymap: {e}"}


@mcp.tool(annotations=_MUTATING)
async def zed_set_keybinding(
    binding: Annotated[str, Field(description="Keybinding shortcut (e.g. 'ctrl-shift-p').")],
    command: Annotated[
        str, Field(description="Zed command to bind (e.g. 'workspace::ToggleRightDock').")
    ],
    context: Annotated[
        str | None, Field(description="Optional context (e.g. 'Editor', 'Workspace').")
    ] = None,
    ctx: Any = None,
) -> dict:
    """Add or update a keybinding in Zed's keymap.json.

    Merges into existing keybindings. Creates keymap.json if missing.

    ## Return Format
    {"success": bool, "binding": str, "command": str, "message": str}

    ## Examples
    zed_set_keybinding("ctrl-shift-p", "workspace::ToggleRightDock")
    """
    kp = _keymap_path()
    try:
        kp.parent.mkdir(parents=True, exist_ok=True)
        if kp.is_file():
            current = json.loads(kp.read_text(encoding="utf-8"))
            if not isinstance(current, list):
                current = []
        else:
            current = []

        entry = {"bindings": {binding: command}}
        if context:
            entry["context"] = context
        current.append(entry)

        kp.write_text(json.dumps(current, indent=2), encoding="utf-8")
        return {
            "success": True,
            "binding": binding,
            "command": command,
            "message": f"Bound {binding} to {command}",
        }
    except (OSError, json.JSONDecodeError) as e:
        return _error_response(f"Failed to write keybinding: {e}", error_type="write_error")


# -- Snippets -------------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY)
async def zed_snippets(
    operation: Annotated[
        str, Field(description="Operation: 'list' (default), 'get', 'create', 'delete'.")
    ] = "list",
    name: Annotated[
        str | None,
        Field(description="Snippet file name (without .json). Required for: get, create, delete."),
    ] = None,
    content: Annotated[
        str | None, Field(description="JSON snippet content. Required for: create.")
    ] = None,
    ctx: Any = None,
) -> dict:
    """Manage Zed user snippets.

    Snippets are stored as JSON files in `%APPDATA%/Zed/snippets/`.
    Each file contains a Zed-compatible snippet definition.

    Operations:
    - list: List all user snippet files
    - get: Read a specific snippet file by name
    - create: Create or overwrite a snippet file
    - delete: Remove a snippet file

    ## Return Format
    {"success": bool, "operation": str, "snippets": list, "message": str}

    ## Examples
    zed_snippets("list")
    zed_snippets("get", name="python")
    """
    sd = _snippets_dir()

    if operation == "list":
        if not sd.is_dir():
            return {
                "success": True,
                "operation": "list",
                "snippets": [],
                "message": "No snippets directory",
            }
        files = sorted([f.stem for f in sd.glob("*.json")])
        return {
            "success": True,
            "operation": "list",
            "snippets": files,
            "message": f"Found {len(files)} snippet files",
        }

    elif operation == "get":
        if not name:
            return {
                "success": False,
                "operation": "get",
                "snippets": [],
                "message": "name is required for get",
            }
        sp = sd / f"{name}.json"
        if not sp.is_file():
            return {
                "success": False,
                "operation": "get",
                "snippets": [],
                "message": f"Snippet '{name}' not found",
            }
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
            return {
                "success": True,
                "operation": "get",
                "snippets": [{"name": name, "content": data}],
                "message": f"Read snippet: {name}",
            }
        except (json.JSONDecodeError, OSError) as e:
            return {
                "success": False,
                "operation": "get",
                "snippets": [],
                "message": f"Failed to read snippet: {e}",
            }

    elif operation == "create":
        if not name or not content:
            return {
                "success": False,
                "operation": "create",
                "snippets": [],
                "message": "name and content are required for create",
            }
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "operation": "create",
                "snippets": [],
                "message": f"Invalid JSON content: {e}",
            }
        sd.mkdir(parents=True, exist_ok=True)
        sp = sd / f"{name}.json"
        try:
            sp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return {
                "success": True,
                "operation": "create",
                "snippets": [{"name": name}],
                "message": f"Created snippet: {name}",
            }
        except OSError as e:
            return {
                "success": False,
                "operation": "create",
                "snippets": [],
                "message": f"Failed to write: {e}",
            }

    elif operation == "delete":
        if not name:
            return {
                "success": False,
                "operation": "delete",
                "snippets": [],
                "message": "name is required for delete",
            }
        sp = sd / f"{name}.json"
        if not sp.is_file():
            return {
                "success": False,
                "operation": "delete",
                "snippets": [],
                "message": f"Snippet '{name}' not found",
            }
        try:
            sp.unlink()
            return {
                "success": True,
                "operation": "delete",
                "snippets": [],
                "message": f"Deleted snippet: {name}",
            }
        except OSError as e:
            return {
                "success": False,
                "operation": "delete",
                "snippets": [],
                "message": f"Failed to delete: {e}",
            }

    else:
        return {
            "success": False,
            "operation": operation,
            "snippets": [],
            "message": f"Unknown operation: {operation}",
        }


# -- Git Blame ------------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY)
async def zed_git_blame(
    file_path: Annotated[str, Field(description="Absolute path to the file to blame.")],
    ctx: Any = None,
) -> dict:
    """Get git blame annotations for a file.

    Runs `git blame --line-porcelain` in the file's repository. Returns
    per-line commit metadata (author, date, summary, line number).

    ## Return Format
    {"success": bool, "file": str, "repo": str, "lines": list, "count": int, "message": str}

    ## Examples
    zed_git_blame("D:/Dev/repos/zed-mcp/src/zed_mcp/server.py")
    """
    target = Path(file_path)
    if not target.is_file():
        return _error_response(f"File not found: {file_path}", error_type="not_found")

    repo = target.parent
    while repo.parent != repo:
        if (repo / ".git").is_dir():
            break
        repo = repo.parent
    else:
        return _error_response(f"Not in a git repository: {file_path}", error_type="not_in_repo")

    try:
        result = subprocess.run(
            ["git", "blame", "--line-porcelain", str(target)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(repo),
        )
        if result.returncode != 0:
            return _error_response(
                f"git blame failed: {result.stderr.strip()}", error_type="blame_failed"
            )

        lines = []
        current = {}
        for line in result.stdout.split("\n"):
            if line.startswith("\t"):
                current["code"] = line[1:]
                if current:
                    lines.append(current)
                current = {}
            elif " " in line:
                key, _, val = line.partition(" ")
                current[key] = val.strip()

        return {
            "success": True,
            "file": file_path,
            "repo": str(repo),
            "lines": lines,
            "count": len(lines),
            "message": f"Blamed {len(lines)} lines",
        }
    except subprocess.TimeoutExpired:
        return _error_response("git blame timed out (30s)", error_type="timeout")
    except FileNotFoundError:
        return _error_response("git not found on PATH", error_type="cli_not_found")


# -- Tasks ----------------------------------------------------------------------


@mcp.tool(annotations=_READ_ONLY)
async def zed_tasks(
    operation: Annotated[str, Field(description="Operation: 'list' (default), 'run'.")] = "list",
    project_path: Annotated[
        str, Field(description="Project root containing .zed/tasks.json.")
    ] = "",
    task_name: Annotated[
        str | None, Field(description="Task label to run. Required for: run.")
    ] = None,
    ctx: Any = None,
) -> dict:
    """List or run Zed build tasks from .zed/tasks.json.

    Zed tasks are configured per-project in `.zed/tasks.json`. This tool
    reads the task definitions and can trigger labelled tasks.

    Operations:
    - list: Parse and display tasks from .zed/tasks.json
    - run: Execute a task by label (uses zed CLI --run-task)

    ## Return Format
    {"success": bool, "operation": str, "tasks": list, "message": str}

    ## Examples
    zed_tasks("list", project_path="D:/Dev/repos/zed-mcp")
    zed_tasks("run", project_path="D:/Dev/repos/zed-mcp", task_name="test")
    """
    if not project_path:
        return {
            "success": False,
            "operation": operation,
            "tasks": [],
            "message": "project_path is required",
        }

    tp = _tasks_path(project_path)
    if not tp:
        return {
            "success": False,
            "operation": operation,
            "tasks": [],
            "message": "No .zed/tasks.json found in project",
        }

    try:
        data = json.loads(tp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {
            "success": False,
            "operation": operation,
            "tasks": [],
            "message": f"Failed to read tasks: {e}",
        }

    if operation == "list":
        task_list = []
        for label, task in data.items():
            task_list.append(
                {
                    "label": label,
                    "command": task.get("command", ""),
                    "args": task.get("args", []),
                    "tags": task.get("tags", []),
                }
            )
        return {
            "success": True,
            "operation": "list",
            "tasks": task_list,
            "message": f"Found {len(task_list)} tasks",
        }

    elif operation == "run":
        if not task_name:
            return {
                "success": False,
                "operation": "run",
                "tasks": [],
                "message": "task_name is required for run",
            }
        if task_name not in data:
            return {
                "success": False,
                "operation": "run",
                "tasks": [],
                "message": f"Task '{task_name}' not found in .zed/tasks.json",
            }
        cli = _zed_cli()
        if not cli:
            return {
                "success": False,
                "operation": "run",
                "tasks": [],
                "message": "zed CLI not found",
            }

        task = data[task_name]
        cmd = task.get("command", "")
        args = task.get("args", [])
        try:
            subprocess.run(
                [cli, "--run-task", task_name], check=True, timeout=120, cwd=project_path
            )
            return {
                "success": True,
                "operation": "run",
                "tasks": [{"label": task_name, "command": cmd, "args": args}],
                "message": f"Launched task: {task_name}",
            }
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return {
                "success": False,
                "operation": "run",
                "tasks": [],
                "message": f"Failed to run task: {e}",
            }

    else:
        return {
            "success": False,
            "operation": operation,
            "tasks": [],
            "message": f"Unknown operation: {operation}",
        }


# -- Main -----------------------------------------------------------------------


_KNOWN_LAYOUT_SETTINGS: dict[str, str] = {
    "active_pane_modifiers.border_size": "Size of the border around the active pane. 0 disables it.",
    "active_pane_modifiers.inactive_opacity": "Opacity (0.0-1.0) of inactive panes relative to the active one.",
    "bottom_dock_layout": "Bottom dock layout relative to left/right docks: \'contained\' or \'full\'.",
    "drop_target_size": "Relative size (0-0.5) of the drop zone that triggers a split when a file is dragged onto a pane.",
}

_LAYOUT_PRESETS = {"agentic", "classic"}


@mcp.tool(annotations=_READ_ONLY)
async def zed_layout(
    operation: Annotated[
        str,
        Field(
            description="Operation: \'list_options\' (default), \'get\', \'set\', \'set_preset\'."
        ),
    ] = "list_options",
    key: Annotated[
        str | None,
        Field(description="Layout setting key (dotted path). Required for: set."),
    ] = None,
    value: Annotated[
        str | None,
        Field(description="Value to write. Required for: set."),
    ] = None,
    preset: Annotated[
        str | None,
        Field(description="\'agentic\' or \'classic\'. Required for: set_preset."),
    ] = None,
    ctx: Any = None,
) -> dict:
    """Inspect or adjust Zed workspace layout.

    Covers settings-backed layout knobs (pane borders, inactive pane opacity,
    bottom dock position, split drop-target size). Does NOT cover live pane
    splitting/arrangement or switching between Zed's Agentic/Classic panel
    presets: those are runtime actions with no documented external hook (no
    `zed --run-action` equivalent exists the way `--run-task` does for tasks).
    set_preset is included for discoverability but honestly reports that it
    cannot execute the switch, and tells you the manual action name instead.

    Operations:
    - list_options: known settings-backed layout keys and what they do
    - get: current values of those keys from settings.json
    - set: write one known layout key to settings.json
    - set_preset: NOT SUPPORTED externally, returns the manual command palette
      action name to run instead

    ## Return Format
    {"success": bool, "operation": str, "data": {...}, "message": str}

    ## Examples
    zed_layout("list_options")
    zed_layout("get")
    zed_layout("set", key="bottom_dock_layout", value="full")
    zed_layout("set_preset", preset="agentic")
    """
    if operation == "list_options":
        return {
            "success": True,
            "operation": "list_options",
            "data": {"options": _KNOWN_LAYOUT_SETTINGS},
            "message": (
                "Known settings-backed layout keys. Exact key paths sourced from Zed's "
                "public docs, not independently verified against a live settings schema "
                "dump. Cross-check with \'zed: open default settings\' in Zed\'s command "
                "palette before relying on these for anything critical."
            ),
        }

    if operation == "get":
        settings = _read_settings()
        current = {}
        for dotted_key in _KNOWN_LAYOUT_SETTINGS:
            parts = dotted_key.split(".")
            node: Any = settings
            for p in parts:
                if isinstance(node, dict) and p in node:
                    node = node[p]
                else:
                    node = None
                    break
            current[dotted_key] = node
        return {
            "success": True,
            "operation": "get",
            "data": {"current": current},
            "message": "Read known layout settings from settings.json",
        }

    if operation == "set":
        if not key or value is None:
            return {
                "success": False,
                "operation": "set",
                "data": {},
                "message": "key and value are required for set",
            }
        if key not in _KNOWN_LAYOUT_SETTINGS:
            return {
                "success": False,
                "operation": "set",
                "data": {"known_keys": list(_KNOWN_LAYOUT_SETTINGS)},
                "message": f"Unknown layout key: {key}",
            }
        settings = _read_settings()
        parts = key.split(".")
        node = settings
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        try:
            if "." in value:
                coerced: Any = float(value)
            else:
                coerced = int(value)
        except (ValueError, TypeError):
            coerced = value
        node[parts[-1]] = coerced
        ok = _write_settings(settings)
        if not ok:
            return _error_response(f"Failed to write layout key \'{key}\'", error_type="write_error")
        return {
            "success": True,
            "operation": "set",
            "data": {"key": key, "value": coerced},
            "message": f"Set {key} to {coerced}",
        }

    if operation == "set_preset":
        if preset not in _LAYOUT_PRESETS:
            return {
                "success": False,
                "operation": "set_preset",
                "data": {"valid_presets": sorted(_LAYOUT_PRESETS)},
                "message": f"Unknown preset: {preset}",
            }
        action_name = (
            "workspace: use agentic layout" if preset == "agentic" else "workspace: use classic layout"
        )
        return {
            "success": False,
            "operation": "set_preset",
            "data": {"preset": preset, "manual_action": action_name},
            "message": (
                f"Not supported externally: Zed has no CLI/API hook to trigger this "
                f"action from outside a running instance. Run \'{action_name}\' from "
                f"Zed\'s command palette (Ctrl/Cmd+Shift+P) manually."
            ),
        }

    return {
        "success": False,
        "operation": operation,
        "data": {},
        "message": f"Unknown operation: {operation}",
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp.run()


if __name__ == "__main__":
    main()
