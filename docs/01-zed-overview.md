# What Zed Actually Is

Last updated: 2026-07-21. Zed reached 1.0 on April 29, 2026.

## Not a VS Code fork

Zed is a from-scratch editor written in Rust by Nathan Sobo (co-creator of Atom) and the Zed Industries team. It does not use Electron, Chromium, or any web tech for its UI. Rendering goes through a custom GPU-accelerated framework called GPUI.

Practical effect: cold start around 0.1 to 0.4 seconds depending on source, roughly 2ms input latency, and it stays smooth on very large files where Electron-based editors start to stutter. Idle memory footprint is a fraction of VS Code's.

Cursor and opencode, by contrast, are both built on the VS Code/Electron base. That is the real architectural split in the current IDE landscape: Zed's native-GPU approach versus everyone else's Electron-plus-extensions approach.

Windows: a preview build shipped late 2025, matured to full stable support since.

## Core editing features

- Native LSP support across 80+ languages: completion, diagnostics, go-to-definition, hover docs, refactoring.
- Git built directly into the editor, not an extension: stage, commit, diff navigation inline.
- Built-in terminal with split panes.
- Multibuffer editing: view and edit results from multiple files/search hits in one scrollable buffer.
- Real-time collaboration built on CRDTs (Conflict-free Replicated Data Types), the same class of tech behind Google Docs and Figma live collaboration. This is baked into the editor's data model, not bolted on like VS Code Live Share.
- Debug Adapter Protocol (DAP) support for step-through debugging across languages that have a DAP server (native Swift debugging is not yet available as of mid-2026).

## What is NOT true (avoid overclaiming in this doc set)

- Zed does not do Cursor-style whole-codebase indexing for cross-file AI Q&A. Its native AI context is the current file and open buffers; anything wider currently goes through external agents (see 03-ai-agents-acp.md).
- Extension ecosystem is small compared to VS Code (roughly 800 vs 60,000+). If you depend on a niche VS Code extension, check it exists for Zed before switching entirely.
- No Composer-style native multi-file AI edit mode built into the core editor; multi-file agentic editing comes through external agents via ACP, not a first-party Zed feature.

## Licensing

Editor core: AGPL/GPL. The GPUI rendering framework: Apache/MIT. The company monetizes via Zed AI subscription ($10/month for Claude-backed AI) and team collaboration features, not the editor itself. Bring-your-own-key works for direct Anthropic/OpenAI API use without paying for Zed AI.
