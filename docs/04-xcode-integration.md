# Zed + Xcode: iOS and macOS Development

Last updated: 2026-07-21. Xcode 27 is in public beta as of this writing (announced WWDC26, June 8-12 2026), public release expected around September 14, 2026 alongside iOS 27.

## The core problem

Zed does not natively understand Xcode project files (.xcodeproj, .xcworkspace). Out of the box it only understands plain Swift Package Manager projects. Real iOS/macOS app development (storyboard-free SwiftUI projects included) usually lives in an Xcode project, so getting Zed to a real build/run/debug cycle takes setup.

## Getting Zed to understand an Xcode project

1. Install the xcode-build-server tool (community project, not from Apple or Zed Industries).
2. Generate a buildServer.json at the project root:
   - Workspace: xcode-build-server config -scheme SCHEME_NAME -workspace WORKSPACE_NAME.xcworkspace
   - Plain project: xcode-build-server config -scheme SCHEME_NAME -project PROJECT_NAME.xcodeproj
3. That buildServer.json is what lets sourcekit-lsp (Apple's own Swift language server, which Zed already uses for plain Swift) resolve imports, do code completion, and navigate an actual Xcode project instead of only plain packages.
4. For build/run/debug on simulator and physical devices from inside Zed rather than switching to Xcode for that step, there is a community tool (xcede-dap, itself written in Swift with a Python helper script) that wires up runnables and a debug adapter. This is third-party, not officially supported by Zed Industries or Apple; expect occasional breakage on Zed updates (one report noted a recent Zed release breaking project diagnostics for this setup).

## What Zed is good for versus what still wants Xcode

Good in Zed: everyday editing, navigation, refactoring, git workflow, working with agents on the actual code, working on large production apps (one report specifically mentions this working better than Xcode on a large CocoaPods project).

Still wants Xcode: Interface Builder/storyboard work if the project still uses them, some visual debugging tools, and definitely the final signing/App Store Connect submission step.

## Xcode 27 specifically

Announced at WWDC26. Ships Swift 6.4 and SDKs for iOS 27 / iPadOS 27 / tvOS 27 / macOS 27 / visionOS 27. Requires macOS Tahoe 26.4 or later to run the beta.

The part that matters for this repo: Xcode 27 is bringing first-class coding agents from Anthropic, Google, and OpenAI directly into the IDE, and doing it via the same open standards Zed already uses:

- MCP: defines what an agent is allowed to do inside Xcode (read files, build, run tests, read diagnostics) via an mcpbridge tool.
- ACP: Xcode 27 adopts this too, the same protocol Zed co-developed with JetBrains.

That is a real, non-hypothetical convergence point. It means the agent-interop story between Zed and Xcode should keep getting easier over time rather than staying two disconnected islands: a workflow where an agent does deep work in Zed and hands off to Xcode 27 for device testing and submission sits on the same protocol family on both ends, rather than needing a custom bridge.

## Practical workflow for this fleet's use case (iOS/macOS dev on Windows + Mac)

1. Write and refactor Swift in Zed on Windows (or Mac), with an agent via ACP doing the heavy lifting.
2. Push to the Mac (or Mac-in-cloud) only when you need simulator/device runs, Xcode 27's Device Hub, or signing.
3. As Xcode 27's own MCP/ACP support matures, the handoff step in (2) should get more automatable rather than being a manual context-switch.
