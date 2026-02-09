# Holodeck 标准数据格式规范

## 概述

为了确保CLI和blender之间的稳定接口，定义以下标准数据格式。这些格式提供了清晰的object_id到位置/资产/命名映射，使得Blender端可以编写通用的apply脚本。

## 1. layout_solution.json

**路径**: `sessions/<session_id>/layout_solution_v1.json`

**用途**: 定义每个对象的空间位置、旋转和缩放

**格式**:
```json
{
  "version": "v1",
  "success": true,
  "object_placements": {
    "obj_001": {
      "pos": [1.5, 2.0, 0.0],
      "rot_euler": [0, 0, 45],
      "scale": [1.0, 1.0, 1.0]
    },
    "obj_002": {
      "pos": [3.0, 1.5, 0.0],
      "rot_euler": [0, 0, 0],
      "scale": [1.0, 1.0, 1.0]
    }
  },
  "metadata": {
    "solver_version": "dfs_v1",
    "solve_time": 2.45,
    "constraint_satisfaction": 0.95
  }
}
```

**字段说明**:
- `object_placements`: object_id到位置信息的映射
- `pos`: [x, y, z] 位置坐标（米）
- `rot_euler`: [rx, ry, rz] 欧拉角旋转（度）
- `scale`: [sx, sy, sz] 缩放比例

## 2. asset_manifest.json

**路径**: `sessions/<session_id>/asset_manifest.json`

**用途**: 定义每个对象对应的3D资产文件

**格式**:
```json
{
  "version": "v1",
  "assets": {
    "obj_001": {
      "asset_path": "sessions/<session_id>/assets/chair.glb",
      "format": "glb",
      "size_bytes": 245678,
      "checksum": "sha256:abc123...",
      "metadata": {
        "vertices": 1250,
        "faces": 2400,
        "materials": 2
      }
    },
    "obj_002": {
      "asset_path": "sessions/<session_id>/assets/table.fbx",
      "format": "fbx",
      "size_bytes": 567890,
      "checksum": "sha256:def456...",
      "metadata": {
        "vertices": 2100,
        "faces": 4200,
        "materials": 3
      }
    }
  },
  "total_assets": 2,
  "total_size_mb": 0.79
}
```

**字段说明**:
- `assets`: object_id到资产信息的映射
- `asset_path`: 资产文件的相对或绝对路径
- `format`: 文件格式（glb, gltf, obj, fbx）
- `size_bytes`: 文件大小（字节）
- `checksum`: 文件校验和（可选）
- `metadata`: 资产的几何和材质信息

## 3. blender_object_map.json

**路径**: `sessions/<session_id>/blender_object_map.json`

**用途**: 定义Blender中对象的命名规则和层级结构

**格式**:
```json
{
  "version": "v1",
  "naming_convention": "object_id_as_name",
  "object_mapping": {
    "obj_001": {
      "blender_name": "obj_001",
      "collection": "HolodeckScene",
      "parent":,
      "type": "MESH",
      "visibility": true,
      "renderable": true
    },
    "obj_002": {
      "blender_name": "obj_002",
      "collection": "HolodeckScene",
      "parent":,
      "type": "MESH",
      "visibility": true,
      "renderable": true
    }
  },
  "collections": {
    "HolodeckScene": {
      "name": "HolodeckScene",
      "parent": null,
      "color": "NONE"
    }
  },
  "scene_settings": {
    "unit_system": "METRIC",
    "scale_length": 1.0,
    "frame_rate": 24,
    "frame_start": 1,
    "frame_end": 250
  }
}
```

**字段说明**:
- `naming_convention`: 命名约定（当前使用"object_id_as_name"）
- `object_mapping`: object_id到Blender对象属性的映射
- `blender_name`: Blender中的对象名称（等于object_id）
- `collection`: 对象所属的集合
- `parent`: 父对象（表示无父对象）
- `type`: 对象类型（MESH, LIGHT, CAMERA等）
- `collections`: 场景中的集合定义
- `scene_settings`: 场景全局设置

## 4. 使用示例

### Blender通用Apply脚本伪代码
```python
import bpy
import json

def apply_holodeck_scene(session_dir):
    """通用Holodeck场景应用脚本"""

    # 1. 加载标准文件
    layout_data = load_json(f"{session_dir}/layout_solution_v1.json")
    asset_data = load_json(f"{session_dir}/asset_manifest.json")
    object_map = load_json(f"{session_dir}/blender_object_map.json")

    # 2. 设置场景
    setup_scene(object_map["scene_settings"])

    # 3. 创建集合
    create_collections(object_map["collections"])

    # 4. 导入并放置对象
    for object_id, placement in layout_data["object_placements"].items():
        asset_info = asset_data["assets"][object_id]
        obj_mapping = object_map["object_mapping"][object_id]

        # 导入资产
        obj = import_asset(asset_info["asset_path"], asset_info["format"])

        # 设置对象属性
        obj.name = obj_mapping["blender_name"]
        obj.hide_viewport = not obj_mapping["visibility"]
        obj.hide_render = not obj_mapping["renderable"]

        # 应用变换
        obj.location = placement["pos"]
        obj.rotation_euler = euler_from_degrees(placement["rot_euler"])
        obj.scale = placement["scale"]

        # 链接到集合
        collection = bpy.data.collections[obj_mapping["collection"]]
        collection.objects.link(obj)

    print(f"Applied Holodeck scene with {len(layout_data['object_placements'])} objects")
```

## 5. 版本控制和兼容性

- 所有文件格式都包含`version`字段
- 向后兼容性：新版本应该能够读取旧版本的文件
- 向前兼容性：旧版本在遇到新字段时应该忽略未知字段

## 6. 文件生成时机

- `layout_solution.json`: 在layout阶段生成
- `asset_manifest.json`: 在assets阶段生成
- `blender_object_map.json`: 在layout阶段生成（因为依赖对象信息）

这些标准格式确保了CLI和blender之间的稳定接口，使得Blender端可以编写通用的场景应用脚本。