# Standalone Webapp: Planning Notes

Status: idea stage, not scoped or scaffolded yet. Decision so far: standalone, full-featured (not a thin frontend over the MCP server), packaged separately from the MCP server itself.

## Purpose

Same content as the docs in this folder, but browsable and searchable, plus an onboarding checklist, rather than a wall of markdown files someone has to scroll through manually.

## Rough scope

- Searchable reference mirroring 01 through 05 in this folder (single content source, so the docs here and the webapp do not drift apart over time).
- Cross-platform note callout (02-cross-platform.md content) since that is a key selling point for adoption.
- Xcode 27 integration section (04-xcode-integration.md content), since that is the most differentiated content in this doc set.
- Onboarding checklist: extensions, theme, vim mode if wanted, AI panel/ACP agent setup.
- Layout page: surfaces zed_layout's known settings-backed knobs (pane border size, inactive-pane opacity, bottom dock position, split drop-target ratio) with live current values and inline editing, backed by the same tool. Must show, not hide, the honest limitation: preset switching (Agentic vs Classic) has no external hook, so this page links out to the manual command-palette action instead of pretending to trigger it. A fake "apply" button that silently fails would be worse than no button.

## Packaging direction (matches fleet convention, not yet decided for this specific repo)

Other fleet servers with a webapp component (see excalidraw-mcp) use React/TS plus Tauri/NSIS packaging for a native Windows installer. Worth deciding explicitly for this repo rather than assuming: does zed-mcp's webapp get the same Tauri/NSIS treatment, or does it stay a simpler local webview since its job is reference content rather than an interactive tool?

## Not yet done

No scaffolding exists for this webapp as of 2026-07-21. This section is planning notes only; do not treat any of the above as implemented.
