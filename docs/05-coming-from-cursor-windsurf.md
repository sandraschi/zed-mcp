# Coming From Cursor / Windsurf: What Transfers and What Does Not

Last updated: 2026-07-21. This is a starting map, not a verified 1:1 keybinding table. Both Cursor and Windsurf are VS Code forks, and Zed ships a "VS Code compatible" base keymap, so most of what transfers, transfers because all three ultimately derive their defaults from VS Code, not because Zed copied Cursor or Windsurf specifically.

## What transfers close to directly (VS Code-derived defaults, confirmed for Zed)

- Ctrl/Cmd+P: quick file open, same in all three.
- Ctrl/Cmd+Shift+P: command palette, same in all three. In Zed everything routes through this: any doc instruction written as "zed: do something" or "editor: do something" means run it from here.
- Ctrl/Cmd+Shift+F: project-wide search, same in all three.
- Ctrl/Cmd+/: toggle comment.

## What you should NOT assume transfers

- The AI/agent surface. Cursor centralizes almost everything into one Composer/chat panel. Zed splits this into an Agent panel (agent threads) versus Text Threads (plain chat), which has confused people coming specifically from Cursor's single-surface model. Do not assume Cursor's Composer muscle memory maps onto a single Zed panel; it does not.
- Codebase-wide AI context. Cursor's @codebase indexes the whole repo for cross-file Q&A automatically. Zed's own native AI context is file/buffer-scoped; wider context in Zed comes from whichever external agent you have wired in via ACP (Claude Code, etc.) doing its own repo-awareness, not from Zed itself.
- Base keymap can be switched explicitly. Zed has a setting (base_keymap) that can emulate other editors' default bindings, and a "zed: toggle base keymap selector" command palette action. Worth checking during setup rather than assuming Zed's raw defaults are what you want.

## Genuinely different concepts (not just renamed, actually different)

- Multibuffer: Zed can show and edit results from many files/search hits in a single scrollable buffer. Neither Cursor nor Windsurf (nor plain VS Code) has a direct equivalent; this is closer to how a structural refactor tool presents matches.
- CRDT-based live collaboration: built into the editor's data model, not a bolted-on extension like VS Code Live Share. If you ever pair-program, this is worth learning deliberately rather than assuming it behaves like Live Share.
- Windsurf's "Cascade" agent concept and its own conventions do not have a direct Zed equivalent as a single named feature; the closest analog is Zed's Agentic Editing plus whichever external agent you have configured via ACP, but it is not a rename of Cascade, it is a different architecture (protocol-based, multi-agent) versus Windsurf's single built-in agent.

## What is still unverified in this doc set (be honest about this rather than guessing)

A full side-by-side keybinding table (every Cursor/Windsurf shortcut mapped to its literal Zed equivalent) has not been built and verified yet. What exists above is confirmed from Zed's own docs and multiple independent cheat-sheet sources; anything not listed here should be checked in Zed's live keymap editor (Ctrl/Cmd+K then Ctrl/Cmd+S) rather than assumed.
