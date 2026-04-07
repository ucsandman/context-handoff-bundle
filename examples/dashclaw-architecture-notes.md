## Scope
Cross-project architecture review of the DashClaw platform and supporting projects.

## Projects mentioned
- DashClaw
- ClawdBot
- Context Handoff Bundle
- Smart Model Router

## Findings
- DashClaw is the primary dashboard for agent fleet governance, running Next.js on port 4200
- ClawdBot (OpenClaw) is the autonomous agent with calendar, email, desktop, file, and Vercel integrations
- Context Handoff Bundle provides durable cross-session context transfer for Claude Code
- Smart Model Router handles intelligent model selection based on task complexity and budget constraints
- There is significant overlap between ClawdBot's session management and Context Handoff Bundle's handoff storage
- DashClaw's governance model could benefit from direct integration with Context Handoff Bundle for fleet-wide context sharing

## Opportunities
- Integrate Context Handoff Bundle storage into DashClaw's agent oversight panel
- Consolidate session persistence between ClawdBot and Context Handoff Bundle
- Add model routing awareness to handoff bundles so loaded context can influence model selection
- Build a unified agent memory layer that spans DashClaw governance and individual agent sessions

## Open questions
- Should Context Handoff Bundle storage be centralized or distributed per-agent?
- How should bundle freshness interact with DashClaw's real-time monitoring?
- What is the right granularity for cross-agent context sharing vs per-agent isolation?
- How do we handle conflicting bundle versions across concurrent agent sessions?

## Evidence anchors
- C:\Projects\DashClaw\src\app\page.tsx
- C:\Users\sandm\clawd\dashboard\src\index.ts
- C:\Users\sandm\clawd\hooks\smart-model-router\handler.ts
- C:\Users\sandm\clawd\projects\context-handoff-bundle\src\context_handoff_bundle\cli.py
- C:\Projects\DashClaw\docs\superpowers\specs\2026-04-06-ps-fleet-governance-design.md
