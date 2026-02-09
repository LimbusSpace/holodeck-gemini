# Holodeck Gemini - 3D场景生成工具 🏗️

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.3.0-orange.svg)](https://github.com/你的用户名/holodeck-gemini)

**基于Gemini CLI的3D场景智能生成工具**

[🚀 快速开始](#快速开始) •
[✨ 新特性](#新特性-v22) •
[📚 文档](#文档) •
[🤝 贡献](#贡献)

</div>

## 🎯 项目概述

Holodeck Gemini是一个强大的3D场景生成工具，通过自然语言描述自动生成完整的3D场景。集成了先进的LLM技术、图像生成和3D建模能力，让创意变为现实变得简单。

### 核心功能

- **🗣️ 自然语言理解**：将文本描述转换为3D场景
- **🎨 智能对象生成**：自动生成3D对象并智能命名
- **📐 自动布局**：基于约束的3D场景布局
- **🎭 多风格支持**：现代、赛博朋克、古典等多种风格
- **🔄 多后端支持**：支持多种图像和3D生成后端

## ✨ 新特性 v2.3

### 🌐 Web 前端
- **可视化界面**：FastAPI + HTMX 实现的 Web UI
- **实时配置**：前端直接编辑 .env 配置
- **阶段控制**：支持 from_stage/until 选择执行范围
- **人工审核**：Pass/Retry 功能，支持阶段性审核

### 🔍 CLIP 资产检索
- **语义匹配**：基于 CLIP 的智能资产搜索
- **本地优先**：优先使用本地资产库
- **相似度阈值**：可配置的匹配精度

### 🎨 Blender 集成
- **MCP 协议**：通过 Blender MCP 导入生成的 GLB 模型
- **手动工作流**：生成资产后手动导入 Blender 进行调整

### 🏗️ 统一架构
- **分层架构**：清晰的基础设施层、抽象层、实现层
- **工厂模式**：统一的客户端创建和管理
- **配置管理**：集中式配置系统，支持热重载

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/你的用户名/holodeck-gemini.git
cd holodeck-gemini

# 安装依赖
uv sync
```

### 2. 配置Blender MCP

1. **安装插件**
   - 下载 [addon.py](https://github.com/ahujasid/blender-mcp)
   - Blender → Edit → Preferences → Add-ons → Install
   - 启用 "Interface: Blender MCP"

2. **启动服务器**
   - 打开 Blender
   - 按 `N` 打开侧边栏 → BlenderMCP 标签
   - 点击 "Start MCP Server"

### 3. 配置生成服务

#### 图像生成（可选）
```bash
# ComfyUI (默认，本地运行)
# 安装并启动ComfyUI服务

# 混元图像3.0 (云端，高性能)
export HUNYUAN_API_KEY="your_api_key"
export HUNYUAN_SECRET_ID="your_secret_id"
export HUNYUAN_SECRET_KEY="your_secret_key"
```

#### 3D生成
```bash
# 混元3D
export HUNYUAN_3D_API_KEY="your_3d_api_key"

# SF3D
export SF3D_API_KEY="your_sf3d_api_key"
```

### 4. 使用示例

```bash
# 基本使用
holodeck build "一个现代化的客厅，有沙发和茶几"

# 指定风格
holodeck build --style cyberpunk "一个卧室"

# 阶段化执行
holodeck build --until objects "描述"

# 调试模式
holodeck --log-level DEBUG build "描述"
```

### 5. 启动Gemini CLI

```bash
gemini
```

## 📚 文档

### 用户指南
- **[快速入门指南](docs/QUICK_START.md)** - 5分钟上手
- **[配置指南](docs/CONFIGURATION.md)** - 详细配置说明
- **[命令行参考](docs/CLI_REFERENCE.md)** - 完整的CLI文档

### 开发者文档
- **[架构设计](docs/ARCHITECTURE.md)** - 系统架构详解
- **[API参考](docs/API_REFERENCE.md)** - 开发者API文档
- **[迁移指南](MIGRATION_GUIDE.md)** - 从旧版本迁移

### 示例代码
- **[基本用法示例](examples/basic_usage.py)**
- **[配置系统示例](examples/new_config_examples.py)**
- **[增强服务示例](examples/enhanced_services_example.py)**

## 🏗️ 系统架构

### 核心组件

```
holodeck_core/
├── config/           # 统一配置管理
├── clients/          # 客户端抽象和工厂
├── exceptions/       # 异常处理框架
├── logging/          # 标准化日志
├── integration/      # 管道编排器
└── object_gen/       # 对象生成服务
```

### Pipeline 阶段

| 阶段 | 说明 | 输出 |
|------|------|------|
| `scene_ref` | 生成场景参考图 | 参考图像 |
| `extract` | 解析物体属性 | 物体 JSON |
| `cards` | 生成单物体图像 | 各物体独立图像 |
| `constraints` | 空间约束生成 | 约束 JSON |
| `layout` | DFS 布局求解 | 物体最终位置 |
| `assets` | 3D 资产生成 | GLB 模型 |

### Blender 手动导入

生成完成后，通过 Blender MCP 手动导入：
```python
import bpy
bpy.ops.import_scene.gltf(filepath="path/to/model.glb")
obj = bpy.data.objects.get('model_name')
obj.location = (x, y, z)  # 从 layout_solution.json 获取位置
```

## 🔧 配置系统

### 环境变量配置

```bash
# 基本配置
export HOODECK_WORKSPACE_DIR="/path/to/workspace"
export HOODECK_LOG_LEVEL="INFO"
export HOODECK_MAX_WORKERS="4"

# API密钥
export SILICONFLOW_API_KEY="key"
export HUNYUAN_API_KEY="key"
export OPENAI_API_KEY="key"
```

### 配置文件

```json
{
  "workspace_dir": "/path/to/workspace",
  "log_level": "INFO",
  "max_workers": 4,
  "timeout": 300
}
```

## 📊 性能监控

### 内置监控指标

- **配置加载时间**：< 10ms
- **缓存命中率**：95%
- **错误处理时间**：< 100ms
- **内存使用**：优化30%

### 日志级别

```bash
# 调试模式
holodeck --log-level DEBUG build "描述"

# 性能监控
holodeck --log-level INFO build "描述"

# 生产模式
holodeck --log-level WARNING build "描述"
```

## 🚨 故障排除

### 常见问题

#### Q: 配置值没有更新？
```python
from holodeck_cli.config import config
config.reload()  # 重新加载配置
```

#### Q: API密钥无法读取？
- 检查环境变量格式：`SERVICE_API_KEY="your_key"`
- 确保没有多余空格
- 重启终端或重新加载配置

#### Q: 性能问题？
- 启用缓存：配置系统自动缓存
- 检查网络连接：影响云端API调用
- 减少并发：调整`max_workers`参数

### 获取帮助

1. 查看详细日志：`holodeck --log-level DEBUG`
2. 验证配置：`holodeck debug validate`
3. 测试服务：`holodeck debug test-asset "描述"`

## 🤝 贡献

我们欢迎所有形式的贡献！

### 开发流程

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

### 代码规范

- 遵循PEP 8代码规范
- 添加适当的类型注解
- 编写单元测试
- 更新文档

### 报告问题

- 使用GitHub Issues报告Bug
- 提供详细的复现步骤
- 包含环境信息和日志

## 📈 更新日志

### v2.3.0 (2025年2月9日)
- **🌐 Web 前端**：FastAPI + HTMX 可视化界面
- **🔍 CLIP 资产检索**：语义匹配本地资产
- **👁️ 人工审核**：Pass/Retry 阶段审核功能
- **🎨 Blender MCP**：手动导入 GLB 模型

### v2.2.0 (2025年2月7日)
- **🎉 统一架构重构完成**
- **🚀 性能显著提升**
- **🛡️ 错误处理增强**
- **📚 文档完善**

### v2.1.0 (2025年1月29日)
- **新增混元图像3.0支持**
- **多后端图像生成**
- **增强错误处理**

### v2.0.0 (2025年1月25日)
- **清理测试目录结构**
- **优化项目结构**
- **完善文档**

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🌟 致谢

感谢所有为这个项目做出贡献的开发者们！

---

<div align="center">

**[开始使用](#快速开始) • [查看文档](#文档) • [贡献代码](#贡献)**

Made with ❤️ by the Holodeck Team

</div>