# Blender apply-layout snippet (execute_blender_code)

> Purpose: import assets from asset_manifest.json, then apply transforms from layout_solution_v1.json.
> Convention: Blender object name == object_id.

```python
import os, json
import bpy

# --- set this from the CLI JSON workspace_path ---
workspace_path = r"REPLACE_WITH_WORKSPACE_PATH"

ws = os.path.abspath(workspace_path)

def load_json(rel):
    path = os.path.join(ws, rel)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

asset_manifest = load_json("asset_manifest.json")
layout = load_json("layout_solution_v1.json")

# asset_manifest format assumption:
# { "assets": { "<object_id>": { "path": "assets/xxx.glb" , ... } } }
assets = asset_manifest.get("assets", asset_manifest.get("mapping", {}))

def import_asset(object_id, relpath):
    abspath = os.path.join(ws, relpath)
    ext = os.path.splitext(abspath)[1].lower()

    # Import (extend as needed)
    if ext in [".glb", ".gltf"]:
        bpy.ops.import_scene.gltf(filepath=abspath)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=abspath)
    elif ext == ".obj":
        bpy.ops.import_scene.obj(filepath=abspath)
    else:
        raise RuntimeError(f"Unsupported asset extension: {ext} ({abspath})")

    # Heuristic: rename last selected object (you may refine to collection-based import)
    imported = bpy.context.selected_objects
    if not imported:
        raise RuntimeError(f"Import produced no selected objects for {object_id}")

    # Pick an object to represent this asset
    root = imported[0]
    root.name = object_id
    return root

# Import assets if missing in scene
for object_id, meta in assets.items():
    if bpy.data.objects.get(object_id):
        continue
    relpath = meta["path"] if isinstance(meta, dict) else meta
    import_asset(object_id, relpath)

# Apply layout
placements = layout.get("placements", layout.get("objects", []))
missing = []

for p in placements:
    oid = p.get("object_id") or p.get("id")
    obj = bpy.data.objects.get(oid)
    if not obj:
        missing.append(oid)
        continue

    loc = p.get("location", [0,0,0])
    rot = p.get("rotation_euler", [0,0,0])
    scl = p.get("scale", [1,1,1])

    obj.location = loc
    obj.rotation_euler = rot
    obj.scale = scl

if missing:
    print("WARNING missing objects in Blender for layout:", missing)

# Save blend
blend_path = os.path.join(ws, "blender_scene.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("Saved:", blend_path)