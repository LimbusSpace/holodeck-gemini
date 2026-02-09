# Holodeck 测试套件

本项目包含完整的测试套件，用于验证Holodeck 3D场景生成系统的各个组件。

## 📁 测试目录结构

```
tests/
├── unit/                    # 单元测试
│   ├── basic_validation.py  # 基础验证测试
│   ├── test_blender_mcp_fix.py  # Blender MCP修复测试
│   └── test_e2e_basic.py    # 基础端到端测试
│
├── integration/             # 集成测试
│   └── pipeline/            # 管道集成测试
│       ├── test_comfyui_integration.py
│       ├── test_editing_workflow.py
│       └── test_integration.py
│
├── e2e/                     # 端到端测试
│   ├── blender/             # Blender相关E2E测试
│   │   ├── test_blender_integration.py
│   │   └── test_smoke_blender.py
│   ├── test_e2e_test.py     # 完整E2E测试
│   ├── test_e2e_test_simple.py  # 简化E2E测试
│   ├── run_e2e_test.bat     # E2E测试脚本(Windows)
│   └── run_e2e_test.sh      # E2E测试脚本(Unix)
│
├── sf3d/                    # SF3D资产生成测试
│   ├── test_sf3d.py         # SF3D基础测试
│   ├── test_sf3d_debug.py   # SF3D调试测试
│   ├── test_sf3d_detailed.py # SF3D详细测试
│   ├── test_sf3d_fix.py     # SF3D修复验证
│   ├── test_sf3d_generation.py # SF3D生成测试
│   └── test_sf3d_simple.py  # SF3D简化测试
│
├── demo/                    # 演示和示例测试
│   ├── demo_glb_import.py   # GLB导入演示
│   ├── demo_testing.py      # 测试演示
│   ├── glb_import_demo.py   # GLB导入演示
│   ├── test_glb_import.py   # GLB导入测试
│   ├── test_glb_import_mcp.py # GLB导入MCP测试
│   ├── test_glb_import_simple.py # GLB导入简化测试
│   ├── test_import_auto.py  # 自动导入测试
│   └── test_import_custom.py # 自定义导入测试
│
├── fixtures/                # 测试数据文件
│   └── test_objects.json    # 测试对象定义
│
├── helpers/                 # 测试辅助工具
├── conftest.py              # Pytest配置文件
└── __init__.py              # 包初始化文件
```

## 🚀 运行测试

### 运行所有测试
```bash
python -m pytest tests/ -v
```

### 运行特定测试类别
```bash
# 单元测试
python -m pytest tests/unit/ -v

# 集成测试
python -m pytest tests/integration/ -v

# 端到端测试
python -m pytest tests/e2e/ -v

# SF3D测试
python -m pytest tests/sf3d/ -v

# 演示测试
python -m pytest tests/demo/ -v
```

### 运行特定测试文件
```bash
python -m pytest tests/sf3d/test_sf3d_simple.py -v
```

## 📋 测试类型说明

### 单元测试 (unit/)
- 验证单个组件的功能
- 基础项目结构验证
- 配置文件和设置验证

### 集成测试 (integration/)
- 测试多个组件的协同工作
- 管道工作流程验证
- 外部服务集成测试

### 端到端测试 (e2e/)
- 完整用户场景测试
- Blender集成验证
- 整个工作流程端到端验证

### SF3D测试 (sf3d/)
- 3D资产生成功能测试
- ComfyUI SF3D工作流验证
- 图像到3D转换测试

### 演示测试 (demo/)
- 功能演示脚本
- GLB导入导出测试
- 示例代码验证

## 🔧 测试环境要求

- Python 3.11+
- Blender 3.6+ (用于E2E测试)
- ComfyUI + SF3D插件 (用于3D生成测试)
- 必要的Python依赖包

## 📊 测试覆盖率

要生成测试覆盖率报告：
```bash
python -m pytest tests/ --cov=holodeck_core --cov-report=html
```

这将在 `htmlcov/` 目录中生成HTML覆盖率报告。