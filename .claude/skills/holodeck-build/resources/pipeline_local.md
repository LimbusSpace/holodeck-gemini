# pipeline_local.md — Local Pipeline (ComfyUI → SF3D → Layout → Blender Apply)

## Goal
Use local services to generate images and 3D assets:
1) ComfyUI generates scene/object imagery (scene_ref + object cards).
2) SF3D generates per-object meshes from object card images.
3) Holodeck CLI solves constraints + layout (up to `layout`).
4) Blender (via blender-mcp) imports assets + applies layout + returns screenshot.

This pipeline is best when:
- You have ComfyUI running locally and stable.
- You want fully local generation (privacy / speed / cost control).

---

## Preconditions (must be true)
- Local ComfyUI reachable (URL/port as configured in your project).
- Local SF3D backend reachable (as configured).
- Blender is running and the blender-mcp addon is connected.
- In your preference/config, providers should be set to local:
  - image generation -> ComfyUI
  - asset generation -> SF3D

If any precondition fails: switch to `pipeline_cloud.md`.

---

## Quickstart (one command to layout)
From repo root:

~~~bash
holodeck build "一个现代风格的客厅，有沙发和茶几" \
  --until layout \
  --no-blendermcp \
  --json
~~~

Expected successful JSON fields:
- ok=true
- session_id
- workspace_path
- artifacts.layout_solution = layout_solution_v1.json
- artifacts.asset_manifest = asset_manifest.json
- artifacts.objects = objects.json
- artifacts.constraints = constraints_v1.json

If ok=false:
- record `failed_stage`, `error`, and optional `dfs_trace`

---

## Staged execution (recommended for stability / reruns)
Use this if you see intermittent ComfyUI/SF3D issues.

### Stage 1: scene reference image
~~~bash
holodeck build "<TEXT>" --only scene_ref --no-blendermcp --json
~~~
Artifacts:
- scene_ref.png
- request.json

### Stage 2: objects extraction
~~~bash
holodeck build "<TEXT>" --from objects --until objects --no-blendermcp --json
~~~
Artifacts:
- objects.json

### Stage 3: object cards (images/text)
~~~bash
holodeck build "<TEXT>" --from object_cards --until object_cards --no-blendermcp --json
~~~
Artifacts:
- object_cards/...

### Stage 4: local assets via SF3D
~~~bash
holodeck build "<TEXT>" --from assets --until assets --no-blendermcp --json
~~~
Artifacts:
- assets/...
- asset_manifest.json

### Stage 5: constraints + layout
~~~bash
holodeck build "<TEXT>" --from constraints --until layout --no-blendermcp --json
~~~
Artifacts:
- constraints_v1.json
- layout_solution_v1.json
- (on failure) dfs_trace_v1.json

> Tip: if only assets failed, rerun only assets with `--force --only assets`.

---

## Apply to Blender (via blender-mcp)
This is executed by Skill (not by CLI).

1) Preflight:
- `mcp__blender__get_scene_info`

2) Apply:
- `mcp__blender__execute_blender_code` to:
  - read `<workspace_path>/asset_manifest.json`
  - import assets into Blender
  - ensure imported object name == object_id (per blender_object_map.json)
  - read `<workspace_path>/layout_solution_v1.json`
  - apply transforms
  - save `<workspace_path>/blender_scene.blend`

3) Evidence:
- `mcp__blender__get_viewport_screenshot`

---

## Failure handling (do NOT guess)
Always trust the CLI JSON error fields.

### ComfyUI connection failure
Symptoms:
- ok=false, failed_stage in [scene_ref, object_cards]
Action:
- fix ComfyUI availability (restart, correct base_url), then rerun:
  - `holodeck build "<TEXT>" --session <id> --only scene_ref --force --no-blendermcp --json`
  - or `--only object_cards`

### “Job lost” / missing outputs
Action:
- rerun only the affected stage with `--force --only <stage>`

### SF3D asset generation failure
Symptoms:
- ok=false, failed_stage=assets
Action:
- rerun:
  - `holodeck build "<TEXT>" --session <id> --only assets --force --no-blendermcp --json`
- if still unstable: switch to cloud pipeline

### Layout solve failure
Symptoms:
- ok=false, failed_stage=layout, dfs_trace present
Action:
- run:
  - `holodeck debug show-trace --session <id>`
  - `holodeck debug show-constraints --session <id>`
  - `holodeck debug show-layout --session <id>`
- then adjust constraints/room size/max objects and rerun only layout:
  - `holodeck build "<TEXT>" --session <id> --only layout --force --no-blendermcp --json`