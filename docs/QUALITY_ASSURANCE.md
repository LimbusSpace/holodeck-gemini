# Holodeck 质量保证体系

## 概述

本质量保证体系确保 Holodeck 项目的稳定性和可靠性，通过多层次的测试覆盖从基础配置到端到端流程的所有关键环节。

## 测试层级

### 1. 基础验证层

**目的**: 验证项目结构和配置完整性

**测试文件**: `tests/test_e2e_basic.py`

**验证内容**:
- ✅ E2E 脚本可以正常导入
- ✅ 项目结构完整（CLI、核心模块、测试文件）
- ✅ 配置文件正确（.mcp.json）
- ✅ 标准格式文档存在

**运行命令**:
```bash
python tests/test_e2e_basic.py
```

### 2. 端到端验收层

**目的**: 验证完整的 build 流程

**测试文件**: `tests/e2e_test.py`

**测试场景**: "一个空房间，里面有一个立方体桌子"

**验证流程**:
1. ✅ CLI 执行（holodeck build）
2. ✅ Session 文件生成
3. ✅ layout_solution.json 格式验证
4. ✅ asset_manifest.json 格式验证
5. ✅ blender_object_map.json 格式验证
6. ✅ Blender apply 脚本生成
7. ✅ 测试报告生成

**运行命令**:
```bash
# 完整测试
python tests/e2e_test.py

# 使用测试运行器
python test_runner.py --mode full
```

### 3. 回归测试层

**目的**: 防止功能回归

**测试运行器**: `test_runner.py`

**测试模式**:
- `quick`: 仅运行基础验证
- `full`: 仅运行端到端测试
- `all`: 运行所有测试（默认）

**运行命令**:
```bash
# 快速验证
python test_runner.py --mode quick

# 完整回归测试
python test_runner.py --mode all
```

## 标准文件格式验证

### layout_solution_v1.json

**必需字段**:
```json
{
  "success": true,
  "object_placements": {
    "obj_001": {
      "pos": [x, y, z],
      "rot_euler": [rx, ry, rz],
      "scale": [sx, sy, sz]
    }
  },
  "version": "v1"
}
```

**验证规则**:
- ✅ success 字段存在且为布尔值
- ✅ object_placements 为字典
- ✅ 每个对象包含 pos、rot_euler、scale
- ✅ 所有数值字段为长度为3的数组

### asset_manifest.json

**必需字段**:
```json
{
  "version": "v1",
  "assets": {
    "obj_001": {
      "asset_path": "assets/table.glb",
      "format": "glb",
      "size_bytes": 12345,
      "checksum": "sha256:...",
      "metadata": {
        "vertices": 1000,
        "faces": 2000,
        "materials": 1
      }
    }
  },
  "total_assets": 1,
  "total_size_mb": 0.012
}
```

**验证规则**:
- ✅ version 字段存在
- ✅ assets 为字典
- ✅ 每个资产包含所有必需字段
- ✅ 数值字段类型正确

### blender_object_map.json

**必需字段**:
```json
{
  "naming_convention": "object_name_equals_id",
  "description": "Blender中对象名称直接使用object_id",
  "mapping": {
    "obj_001": "obj_001"
  }
}
```

**验证规则**:
- ✅ naming_convention 为 "object_name_equals_id"
- ✅ mapping 为字典
- ✅ 映射关系正确

## Blender Apply 脚本

### 通用脚本规范

测试系统会生成一个通用的 Blender apply 脚本示例，展示如何：

1. **读取标准文件**
   ```python
   # 读取 asset_manifest.json
   # 读取 layout_solution_v1.json
   # 读取 blender_object_map.json
   ```

2. **导入资产**
   ```python
   # 使用 bpy.ops.import_scene.gltf
   # 设置对象名称（遵循命名约定）
   ```

3. **应用布局**
   ```python
   # 设置位置: obj.location = placement["pos"]
   # 设置旋转: obj.rotation_euler = placement["rot_euler"]
   # 设置缩放: obj.scale = placement["scale"]
   ```

### 验收标准

**通用性**: 脚本应该能够处理任何符合标准格式的 session
**健壮性**: 包含错误处理和日志记录
**可重用性**: 可以作为模板集成到其他项目中

## 测试报告

### 报告格式

每次测试运行都会生成 `test_report.json`，包含：

```json
{
  "test_name": "Holodeck E2E Build Test",
  "test_prompt": "一个空房间，里面有一个立方体桌子",
  "session_id": "2026-01-22T17-43-23Z_xxx",
  "status": "PASSED",
  "artifacts": {
    "layout_solution": {
      "objects_count": 1,
      "success": true
    },
    "asset_manifest": {
      "assets_count": 1,
      "total_size_mb": 0.012
    }
  },
  "cli_output_summary": {
    "ok": true,
    "stages_completed": ["scene_ref", "objects", "constraints", "layout"]
  }
}
```

### 报告用途

- **开发调试**: 快速定位问题
- **CI/CD**: 自动化测试验证
- **质量保证**: 记录测试历史和趋势
- **文档**: 展示预期输出格式

## 运行指南

### 日常开发

```bash
# 快速验证项目状态
python test_runner.py --mode quick
```

### 功能开发完成后

```bash
# 完整验证
python test_runner.py --mode all
```

### CI/CD 集成

```bash
# 在 CI 中运行
python test_runner.py --mode all

# 检查退出码
if [ $? -eq 0 ]; then
    echo "✅ 测试通过"
else
    echo "❌ 测试失败"
    exit 1
fi
```

### 发布前验证

```bash
# 发布前完整测试
python test_runner.py --mode all

# 检查测试报告
python -c "
import json
with open('test_report.json') as f:
    report = json.load(f)
assert report['status'] == 'PASSED'
print('✅ 发布前验证通过')
"
```

## 故障排除

### 常见测试失败原因

1. **CLI 导入错误**
   - 检查 Python 路径
   - 验证依赖安装

2. **JSON 格式错误**
   - 检查 CLI 输出编码
   - 验证 JSON 解析逻辑

3. **文件路径错误**
   - 检查工作目录
   - 验证相对路径处理

4. **标准格式不匹配**
   - 参考 STANDARD_FORMATS.md
   - 检查版本兼容性

### 调试技巧

1. **启用详细日志**
   ```bash
   python tests/e2e_test.py 2>&1 | tee test_debug.log
   ```

2. **检查中间文件**
   ```bash
   # 查看生成的 JSON 文件
   cat workspace/sessions/*/layout_solution_v1.json
   cat workspace/sessions/*/asset_manifest.json
   ```

3. **手动验证 CLI**
   ```bash
   python -m holodeck_cli.cli build "一个空房间，里面有一个立方体桌子" --until layout --no-blendermcp --json
   ```

## 扩展测试

### 添加新测试场景

1. **多对象场景**
   ```python
   # 在 e2e_test.py 中添加
   def test_multi_object_scene(self):
       self.test_prompt = "一个客厅，包含沙发、茶几、电视"
       # ... 测试逻辑
   ```

2. **约束测试**
   ```python
   # 验证复杂约束处理
   def test_constraint_solving(self):
       self.test_prompt = "一个餐厅，椅子围绕桌子摆放"
       # ... 测试逻辑
   ```

3. **性能测试**
   ```python
   # 验证大规模场景性能
   def test_performance(self):
       self.test_prompt = "一个大型商场，包含多个商铺"
       # ... 性能测试逻辑
   ```

### 集成测试

1. **Blender 实际集成**
   ```python
   # 使用 blender-mcp 工具验证
   def test_blender_integration(self):
       # 调用 mcp__blender__execute_blender_code
       # 验证场景应用结果
   ```

2. **资产生成测试**
   ```python
   # 验证 3D 资产生成
   def test_asset_generation(self):
       # 测试 Hunyuan3D/Hyper3D 集成
       # 验证资产质量
   ```

## 质量指标

### 测试覆盖率目标

- ✅ 基础验证: 100%
- ✅ 端到端流程: 100%
- ✅ 标准文件格式: 100%
- ✅ 错误处理: 90%+

### 性能指标

- ✅ 快速验证: < 30秒
- ✅ 端到端测试: < 5分钟
- ✅ 内存使用: < 500MB
- ✅ 磁盘使用: < 100MB

### 稳定性指标

- ✅ 测试通过率: 95%+
- ✅ 回归测试频率: 每次提交
- ✅ 问题响应时间: < 24小时

---

**最后更新**: 2026年1月22日
**质量保证版本**: 1.0
**适用版本**: Holodeck CLI v1.0+