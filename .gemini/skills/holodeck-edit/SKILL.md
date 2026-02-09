---
name: holodeck-edit
description: Edit an existing Holodeck session via holodeck CLI, then apply updated layout in Blender via blender MCP and return a viewport screenshot + summary.
disable-model-invocation: true
context: fork
allowed-tools: Bash(holodeck:*), mcp__blender__get_scene_info, mcp__blender__execute_blender_code, mcp__blender__get_viewport_screenshot
---

## Hard rules
- Do NOT start or use holodeck-mcp.
- Do NOT run: `python -m servers.holodeck_mcp.server`
- The only MCP server is `blender` (mcp__blender__*).
- All Holodeck actions must be performed via `holodeck` CLI (Bash), then applied in Blender via blender-mcp.

# Holodeck Edit (Minimal)

## Expected usage
`/holodeck-edit <session_id> <edit_request>`

## Steps
1) Preflight: `mcp__blender__get_scene_info`.

2) Run CLI edit (must output JSON):
~~~bash
holodeck edit --session "<session_id>" "<edit_request>" --no-blendermcp --json
~~~
- If ok=false: stop; report error + failed_stage (+ dfs_trace if present).

3) Apply updated layout in Blender:
- `mcp__blender__execute_blender_code` reads the session workspace and applies the latest layout.

4) Evidence:
- `mcp__blender__get_viewport_screenshot`.

## Output (must include)
- session_id
- CLI message / changed stage(s)
- updated artifact filenames (layout_solution*, constraints*, dfs_trace* if any)
- screenshot result