# AI and Agents in Zed

Last updated: 2026-07-21.

## Built-in AI features

Four native pieces as of 2026:

- Agentic Editing: multi-file edits driven by natural language, Zed's own flagship agent feature.
- Edit Prediction (model name: Zeta): predicts structural next-edits from recent context, not just token-level autocomplete.
- Inline Assistant: a gutter-level panel for targeted file-level help.
- Text Threads: a plain-text LLM chat interface without leaving the editor.

Zed AI (the paid, Claude-backed tier) costs $10/month. Bring-your-own-key works for Anthropic, OpenAI, and others without that subscription, and local models via Ollama are supported too.

## Agent Client Protocol (ACP)

Zed co-developed ACP with JetBrains, announced January 2026. It is open and Apache-licensed: the goal is that any AI coding agent can plug into any editor rather than being locked to one vendor's UI.

Documented external agents in Zed via ACP: Claude Code, Gemini CLI, Codex CLI, OpenCode. This is the actual point of interest for a fleet workflow: run whichever agent fits the task (Claude Code for a deep refactor, something lighter for repetitive codegen) with Zed as the shared surface where edits land and get reviewed, rather than committing to one vendor's agent forever.

## MCP support inside Zed

MCP server configuration lives in the Agent Panel section of Zed's settings UI (moved there as of the July 1, 2026 stable release, alongside LLM providers and external agents). This is the door zed-mcp itself would need to be registered through if you want zed-mcp's own tools available to an agent running inside Zed, not just to an agent running outside Zed that happens to be reading these docs.

## Known rough edges (as of mid-2026, do not oversell this)

- Not all Claude Code slash commands behave correctly inside Zed's Agent panel yet.
- Memory is not a native turnkey feature in Zed; you have to compose it yourself via MCP, same as any other project.
- The distinction between "agent threads" and "text threads" in the UI has confused people coming from Cursor, where there is one primary AI surface.
- No native codebase-wide indexing for cross-file AI Q&A the way Cursor's @codebase does it; wider context has to come through an external agent's own indexing (e.g. Claude Code's own repo-awareness), not Zed itself.

## Why this is relevant to Xcode 27

See 04-xcode-integration.md: Xcode 27 is adopting MCP and ACP as well, which is the actual bridge between these two tools rather than them being isolated silos.
