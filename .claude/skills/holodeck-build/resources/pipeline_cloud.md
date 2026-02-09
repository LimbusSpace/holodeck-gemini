# pipeline_cloud.md — Cloud Pipeline (No ComfyUI/SF3D Required)

## Goal
Avoid requiring local ComfyUI/SF3D by using cloud/backed assets via blender-mcp:
1) Holodeck CLI does analysis + constraints + layout (can be text-only).
2) Assets are generated/downloaded/imported in Blender via blender-mcp (Hunyuan3D / Hyper3D / Sketchfab / PolyHaven).
3) Export/import bookkeeping writes assets into session workspace and produces `asset_manifest.json`.
4) Apply layout + screenshot.

Use this pipeline when:
- User machine does NOT have ComfyUI/SF3D deployed.
- You want predictable demo results with minimal local infra.

---

## Preconditions
- Blender is running and blender-mcp addon is connected.
- At least one cloud source is configured/available:
  - Hunyuan3D OR Hyper3D OR Sketchfab (fallback) OR PolyHaven (textures/HDRI)

---

## Step A — Build session up to objects/cards (no local generation required)
From repo root:

~~~bash
holodeck build "<TEXT>" --until object_cards --no-blendermcp --json
~~~

Expected artifacts:
- request.json
- objects.json
- object_cards/ (can be text-based cards; images optional)
- blender_object_map.json (naming convention)

If your current implementation requires local image generation during object_cards, then use:
~~~bash
holodeck build "<TEXT>" --until objects --no-blendermcp --json
~~~
and treat object specs as `objects.json` only.

---

## Step B — Generate/import assets in Blender via blender-mcp
### Preferred order
1) Hunyuan3D (fast path)
2) Hyper3D (Rodin)
3) Sketchfab (download a model)
4) PolyHaven (materials/HDRI/props; mainly for lookdev)

### Minimal per-object pattern (conceptual)
- generate model from text (object card summary or object name)
- poll job status
- import generated asset into Blender
- rename the imported root object name == object_id

Tools involved (examples):
- `mcp__blender__generate_hunyuan3d_model` → `mcp__blender__poll_hunyuan_job_status` → `mcp__blender__import_generated_asset_hunyuan`
- `mcp__blender__generate_hyper3d_model_via_text` → `mcp__blender__poll_rodin_job_status` → `mcp__blender__import_generated_asset`

---

## Step C — Export imported assets to session workspace + write asset_manifest.json
Because Holodeck CLI expects `asset_manifest.json` in the session folder, use:

- `mcp__blender__execute_blender_code` to:
  1) Create `<workspace_path>/assets/` directory if missing
  2) For each object_id in `objects.json`, find Blender object by name (object_id)
  3) Export object (GLB recommended) to `<workspace_path>/assets/<object_id>.glb`
  4) Write `<workspace_path>/asset_manifest.json` mapping object_id → relative asset path

This step is what “makes cloud assets look like local assets” for the rest of the pipeline.

---

## Step D — Solve constraints + layout using the generated assets
Now that assets exist + manifest exists, run:

~~~bash
holodeck build "<TEXT>" --session <session_id> --from constraints --until layout --no-blendermcp --json
~~~

Artifacts:
- constraints_v1.json
- layout_solution_v1.json
- (on failure) dfs_trace_v1.json

---

## Step E — Apply layout + screenshot
- `mcp__blender__execute_blender_code`:
  - read `layout_solution_v1.json`
  - apply transforms to objects named by object_id
  - save `blender_scene.blend`

- `mcp__blender__get_viewport_screenshot`

---

## Failure handling
- If a cloud generator is unavailable (missing key, rate limit, etc):
  - fallback to Sketchfab download for that object
  - or reduce object count (`--max-objects`) and rerun

- If layout fails:
  - use `holodeck debug show-trace --session <id>` and adjust constraints / room-size