"""FastMCP server for Zed editor — extensions, settings, collaborator bridge."""
from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

log = logging.getLogger(__name__)

_ZED_DIR = Path(os.getenv("ZED_CONFIG_DIR", os.path.expanduser("~/.config/zed")))
_ZED_SETTINGS = _ZED_DIR / "settings.json"
_ZED_EXTENSIONS = _ZED_DIR / "extensions"

mcp = FastMCP(
    "zed-mcp",
    instructions="MCP server for Zed editor — read settings, manage extensions, open files.",
    version="0.1.0",
)

_READ_ONLY = {"readonly": True}
_MUTATING = {}


@mcp.tool(annotations=_READ_ONLY)
async def zed_get_settings(ctx: Any = None) -> dict:
    """Read the current Zed settings.json.

    ## Return Format
    {"settings": dict}
    """
    if not _ZED_SETTINGS.is_file():
        return {"settings": {}}
    try:
        data = json.loads(_ZED_SETTINGS.read_text(encoding="utf-8"))
        return {"settings": data}
    except (json.JSONDecodeError, OSError) as e:
        return {"error": f"Failed to read settings: {e}"}


@mcp.tool(annotations=_READ_ONLY)
async def zed_list_extensions(ctx: Any = None) -> dict:
    """List installed Zed extensions.

    Scans the extensions directory for installed extension manifests.

    ## Return Format
    {"extensions": [{"id": str}], "count": int}
    """
    if not _ZED_EXTENSIONS.is_dir():
        return {"extensions": [], "count": 0}
    exts = []
    for entry in sorted(_ZED_EXTENSIONS.iterdir()):
        if entry.is_dir() and (entry / "extension.json").is_file():
            try:
                meta = json.loads((entry / "extension.json").read_text(encoding="utf-8"))
                exts.append({"id": entry.name, "name": meta.get("name", entry.name), "version": meta.get("version", "")})
            except (json.JSONDecodeError, OSError):
                exts.append({"id": entry.name})
    return {"extensions": exts, "count": len(exts)}


@mcp.tool(annotations=_MUTATING)
async def zed_open_file(file_path: str, ctx: Any = None) -> dict:
    """Open a file in Zed editor via the CLI.

    Requires `zed` CLI in PATH.

    ## Return Format
    {"success": bool, "file": str}

    ## Examples
    zed_open_file("D:/Dev/repos/README.md")
    """
    if not Path(file_path).exists():
        return {"success": False, "error": f"File not found: {file_path}"}
    try:
        subprocess.run(["zed", file_path], check=True, timeout=10)
        return {"success": True, "file": file_path}
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return {"success": False, "error": f"Failed to open in Zed: {e}"}


@mcp.tool(annotations=_READ_ONLY)
async def zed_help(ctx: Any = None) -> dict:
    """Show available zed-mcp tools and usage."""
    return {
        "tools": [
            {"name": "zed_get_settings", "description": "Read Zed settings"},
            {"name": "zed_list_extensions", "description": "List installed extensions"},
            {"name": "zed_open_file", "description": "Open a file in Zed"},
        ],
        "config_dir": str(_ZED_DIR),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp.run()


if __name__ == "__main__":
    main()
