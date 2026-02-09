---
name: holodeck-director
description: Routes Holodeck requests to the correct skill (holodeck-build, holodeck-edit, holodeck-debug). Use when the user wants to create a new scene, modify a scene, or troubleshoot failures. This skill only recommends the next command; it must not execute commands or call tools.
context: fork
user-invocable: true
# 不写 allowed-tools：保持最小权限；也可以显式写 Read/Grep，但不要给 Bash/MCP
---

# Holodeck Director (Router Only)

## Hard rules
- Do NOT run any commands.
- Do NOT call any tools (no Bash, no MCP tools).
- Only decide which Holodeck skill to use next and show the exact slash command to run.

## Routing logic
- If user asks to create/generate/build a new 3D scene → recommend: `/holodeck-build <scene_description>`
- If user asks to move/delete/replace/add objects, or "make changes" → recommend: `/holodeck-edit <session_id> <edit_request>`
- If user reports errors/failures, missing assets, layout solve failed, Blender not responding → recommend: `/holodeck-debug <session_id>` (or ask them to provide session_id if missing)

## Output format (always)
1) Chosen skill: <one of holodeck-build|holodeck-edit|holodeck-debug>
2) One-line reason
3) The exact slash command to run next
4) What evidence the next skill will return (screenshot + session summary)