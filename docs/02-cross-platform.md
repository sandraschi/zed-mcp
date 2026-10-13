# Zed Across Platforms

Last updated: 2026-07-21.

## Platform support

Zed runs on macOS, Windows, and Linux from the same codebase, same as Cursor and opencode. This matters for anyone doing iOS/macOS dev on a Windows daily driver: you can write and review Swift on Windows in Zed, then hand off to a Mac (or a Mac-in-the-cloud, or a physical Mac) only for the steps that genuinely require Apple's toolchain: simulator runs, device debugging, signing, App Store submission.

Windows Subsystem for Linux (WSL) integration exists for Windows users who need a Linux toolchain alongside Windows-native work.

## What differs by platform in practice

- Windows: fully supported, GPU rendering backend implemented for Windows (DirectX-based). Some agent-related Windows-specific bugs get fixed in most weekly releases (path handling with spaces, drive-letter prefixes, OAuth sign-in quirks) -- check the current release notes if something Windows-specific misbehaves, it may already be fixed upstream.
- macOS: the platform Zed was originally built for; native debugging and Swift tooling assumptions lean macOS-first even though the editor itself runs everywhere.
- Linux: first-class, was actually the first officially announced non-macOS platform (mid-2024) before Windows arrived.

## Why this matters for a Cursor/Windsurf-hopping workflow

Because Zed, Cursor, and opencode all run on both Mac and Windows, none of them lock you to one OS. The friction in hopping between them is not "which OS is this on" but "which keybindings and mental model am I in right now." See 05-coming-from-cursor-windsurf.md for that mapping.
