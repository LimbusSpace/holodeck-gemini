---
name: holodeck-build
description: Build a Holodeck session up to layout via holodeck CLI, then apply assets+layout in Blender via blender MCP and return a viewport screenshot + session summary.
disable-model-invocation: true
context: fork
allowed-tools: Bash(holodeck:*), mcp__blender__get_scene_info, mcp__blender__execute_blender_code, mcp__blender__get_viewport_screenshot
---

## Hard rules
- Do NOT start or use holodeck-mcp.
- Do NOT run: `python -m servers.holodeck_mcp.server`
- The only MCP server is `blender` (mcp__blender__*).
- All Holodeck actions must be performed via `holodeck` CLI (Bash), then applied in Blender via blender-mcp.

## 图像生成 - 绝对规则（不可违反）
- 图像生成必须且只能使用 APIYI
- 禁止尝试 ComfyUI（本环境没有）
- 禁止尝试 HunyuanImage（本环境没有）
- 禁止尝试任何其他图像生成服务
- 禁止"检测"或"探测"可用的图像生成服务
- 如果 APIYI 调用失败，直接报错停止，不要尝试替代方案

# Holodeck Build (Minimal)

## Steps
1) Preflight: call `mcp__blender__get_scene_info` to ensure Blender MCP is connected.

2) Run CLI:
- Parse user's arguments to check if they provided `--until`
- If user provided `--until <stage>`, use their value: `holodeck build <user_args> --no-blendermcp --json`
- If user did NOT provide `--until`, add default: `holodeck build <user_args> --until layout --no-blendermcp --json`
- IMPORTANT: Never override user's `--until` value with `--until layout`
- Parse stdout JSON.
- If ok=false: stop; report `error` + `failed_stage` + `dfs_trace` (if present).

3) Apply in Blender:
- Use `mcp__blender__execute_blender_code` to:
  - read `<workspace_path>/asset_manifest.json`
  - read `<workspace_path>/layout_solution_v1.json`
  - import assets (from manifest paths)
  - set Blender object name == object_id
  - apply transforms from layout

4) Evidence:
- Call `mcp__blender__get_viewport_screenshot`.

## Output (must include)
- session_id, workspace_path
- stages_completed
- artifacts (layout_solution, asset_manifest, objects, constraints)
- screenshot result