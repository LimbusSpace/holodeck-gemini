# Holodeck-Claude 项目结构

## 📁 项目根目录

```
holodeck-claude/
├── .claude/                         # Claude Code 配置目录
├── .claude-plugin/                 # Claude Code插件配置
│   └── plugin.json                 # 插件清单
├── .venv/                          # Python 虚拟环境
├── .git/                           # Git 版本控制
│
├── holodeck_core/                  # 核心Python库 (业务逻辑层)
│   ├── __init__.py
│   ├── schemas/                    # 数据模型层 (18个Pydantic Schema)
│   ├── storage/                    # 存储层
│   ├── object_gen/                 # 3D资产生成模块
│   └── scene_analysis/             # 场景分析模块
│
├── holodeck_cli/                   # 命令行接口
│   ├── __init__.py
│   └── main.py
│
├── servers/                        # MCP 服务器实现
│   └── blender/
│
├── commands/                       # 命令实现
│
├── config/                         # 配置文件
│
├── docs/                           # 项目文档
│   ├── PROJECT_STRUCTURE.md         # 项目结构文档 (本文档)
│   ├── README_HUNYUAN_3D.md        # 混元3D集成文档
│   ├── cleanup/                    # 清理操作文档
│   │   ├── CLEANUP_SUMMARY.md
│   │   └── FINAL_CLEANUP_REPORT.md
│   ├── reports/                    # 项目报告文档
│   └── development-log.md          # 开发日志
│
├── tests/                          # 测试代码
│   ├── integration/                # 集成测试
│   │   ├── test_hunyuan3d_workflow_integration.py
│   │   ├── test_hunyuan_integration.py
│   │   ├── test_integration_complete.py
│   │   └── test_simple_integration.py
│   └── unit/                       # 单元测试 (待添加)
│
├── examples/                       # 示例代码
│
├── workspace/                      # 工作空间
│
├── simple_gothic_models/           # 示例模型
│
└── blender-mcp-main/               # Blender MCP 集成

## 📄 根目录配置文件

- `README.md` - 项目主文档和快速开始指南
- `CLAUDE.MD` - Claude Code 配置和使用说明
- `.env` - 环境变量配置 (不要提交到版本控制)
- `.env.example` - 环境变量示例
- `.gitignore` - Git 忽略配置
- `.mcp.json` - MCP 服务器配置
- `.python-version` - Python 版本配置
- `pyproject.toml` - 项目构建和依赖配置
- `uv.lock` - 依赖锁定文件

## 🚀 快速开始

### 环境设置
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (Unix/macOS)
source .venv/bin/activate

# 安装依赖
uv sync
```

### 运行测试
```bash
# 运行所有测试
python -m pytest tests/

# 运行集成测试
python -m pytest tests/integration/

# 运行特定测试
python -m pytest tests/integration/test_hunyuan3d_workflow_integration.py
```

### 启动项目
```bash
# 运行命令行接口
python -m holodeck_cli

# 或直接运行Python脚本
python holodeck_cli/main.py
```

## 📚 主要模块说明

### holodeck_core
核心业务逻辑层，包含:
- **schemas**: 数据模型和Pydantic schema定义
- **storage**: 文件存储和会话管理
- **object_gen**: 3D资产生成和混元3D集成
- **scene_analysis**: 场景分析和AI集成

### holodeck_cli
命令行接口，提供用户友好的交互界面

### servers
MCP服务器实现，主要用于Blender集成

### tests
完整的测试套件，包括集成测试和单元测试

### docs
项目文档，包括API文档、开发指南和集成报告

## 🔧 开发工具

- **uv**: 快速Python包管理器
- **pytest**: 测试框架
- **Claude Code**: AI编程助手
- **Git**: 版本控制

## 📖 相关文档

- [开发日志](development-log.md) - 详细的开发过程记录
- [混元3D集成文档](README_HUNYUAN_3D.md) - 混元3D功能集成说明
- [清理总结](cleanup/CLEANUP_SUMMARY.md) - 项目清理操作总结
