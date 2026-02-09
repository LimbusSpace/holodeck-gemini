---
name: holodeck-debug
description: Debug a Holodeck session failure using holodeck debug commands, and capture Blender viewport evidence via blender MCP.
disable-model-invocation: true
context: fork
allowed-tools: Bash(holodeck:*), mcp__blender__get_scene_info, mcp__blender__get_viewport_screenshot
---

## Hard rules
- Do NOT start or use holodeck-mcp.
- Do NOT run: `python -m servers.holodeck_mcp.server`
- The only MCP server is `blender` (mcp__blender__*).
- All Holodeck actions must be performed via `holodeck` CLI (Bash), then applied in Blender via blender-mcp.

# Holodeck Debug (Minimal)

## Steps
1) Environment:
~~~bash
holodeck debug validate
~~~
Then: `mcp__blender__get_scene_info`.

2) Session triage:
~~~bash
holodeck debug status --session "<session_id>"
holodeck debug list-artifacts --session "<session_id>"
~~~

3) If solver/layout failed:
~~~bash
holodeck debug show-trace --session "<session_id>"
holodeck debug show-constraints --session "<session_id>"
holodeck debug show-layout --session "<session_id>"
~~~

4) Evidence:
- `mcp__blender__get_viewport_screenshot`

## Output format
- problem category
- evidence summary (key lines + missing artifacts)
- next action (smallest step)