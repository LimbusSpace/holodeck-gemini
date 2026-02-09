# Holodeck CLI 阶段化执行指南

## 概述

Holodeck CLI 现已支持阶段化执行，允许用户控制构建流程的各个阶段，实现灵活的断点续做和部分执行功能。

## 构建阶段

完整的构建流程包含以下9个阶段（按执行顺序）：

1. **session** - 创建会话和请求文件
2. **scene_ref** - 生成场景参考图
3. **objects** - 提取场景对象（生成 objects.json）
4. **cards** - 生成对象卡片（生成 object_cards/*）
5. **assets** - 生成3D资产
6. **constraints** - 生成布局约束（生成 constraints.json）
7. **layout** - 布局求解（生成 layout_solution.json）
8. **assemble** - 场景组装
9. **render** - 渲染场景

## 命令行参数

### 阶段控制参数

- `--only <stage>` - 只执行指定阶段
- `--until <stage>` - 执行从开始到指定阶段（包含）
- `--from <stage>` - 从指定阶段开始执行到结束
- `--from <stage> --until <stage>` - 执行指定范围内的阶段

### 会话参数

- `--session <id>` - 指定会话ID（用于断点续做）
- `"<text>"` - 文本描述（用于创建新会话）

### 执行控制参数

- `--skip-render` - 跳过渲染步骤
- `--skip-assets` - 跳过资产生成步骤
- `--no-blendermcp` - 跳过Blender MCP相关操作（assemble和render阶段）

## 使用示例

### 1. 创建新会话
```bash
holodeck build "现代客厅，包含沙发、茶几、电视" --only session
```

### 2. 执行到指定阶段
```bash
holodeck build --session <session_id> --until objects
```

### 3. 从指定阶段开始
```bash
holodeck build --session <session_id> --from layout
```

### 4. 执行指定范围内的阶段
```bash
holodeck build --session <session_id> --from assets --until layout
```

### 5. 只执行单个阶段
```bash
holodeck build --session <session_id> --only render
```

### 6. 跳过Blender操作
```bash
holodeck build --session <session_id> --from assemble --until render --no-blendermcp
```

## 断点续做功能

阶段化CLI支持智能的断点续做：

1. **自动跳过已完成阶段** - 系统会检查各阶段的输出文件，自动跳过已完成的阶段
2. **依赖检查** - 确保前置阶段都已完成（除非使用`--from`参数）
3. **状态查询** - 使用`holodeck session status <session_id>`查看进度

### 断点续做示例

```bash
# 查看会话状态
holodeck session status 2026-01-22T16-30-25Z_26c4af4c

# 从失败的阶段继续
holodeck build --session 2026-01-22T16-30-25Z_26c4af4c --from scene_ref
```

## 会话管理

### 列出所有会话
```bash
holodeck session list
```

### 查看会话详情
```bash
holodeck session show <session_id>
```

### 查看会话阶段状态
```bash
holodeck session status <session_id>
```

### 删除会话
```bash
holodeck session delete <session_id>
```

## 参数组合规则

1. **互斥参数**：
   - `--target` 和 `--only` 不能同时使用
   - `--target`/`--only` 与 `--from`/`--until` 不能同时使用

2. **优先级**：
   - `--from` 参数优先级高于 `--until`
   - 当同时指定 `--from` 和 `--until` 时，执行指定范围内的阶段

3. **依赖处理**：
   - 默认情况下会检查阶段依赖关系
   - 使用 `--from` 参数时会跳过依赖检查，实现真正的断点续做

## 输出文件

每个阶段都会生成相应的输出文件：

- `request.json` - 会话请求数据
- `scene_ref.png` - 场景参考图
- `objects.json` - 对象清单
- `object_cards/` - 对象卡片目录
- `assets/` - 3D资产目录
- `constraints_v1.json` - 布局约束
- `layout_solution_v1.json` - 布局解决方案
- `blender_scene.blend` - Blender场景文件
- `renders/` - 渲染输出目录

## 错误处理

- **阶段失败**：如果某个阶段失败，后续阶段将不会执行
- **依赖缺失**：如果前置阶段未完成，系统会提示缺失的依赖
- **会话不存在**：如果指定的会话ID不存在，会显示错误信息

## 最佳实践

1. **增量开发**：使用 `--until` 参数逐步验证每个阶段
2. **调试定位**：使用 `--only` 参数单独测试特定阶段
3. **断点续做**：使用 `--from` 参数从失败点继续执行
4. **状态监控**：定期使用 `session status` 命令监控进度

## 示例工作流

```bash
# 1. 创建会话
holodeck build "现代客厅设计" --only session

# 2. 生成到对象提取
holodeck build --session <id> --until objects

# 3. 检查对象结果，继续到布局
holodeck build --session <id> --from constraints --until layout

# 4. 如果布局失败，重新尝试
holodeck build --session <id> --only layout

# 5. 完成剩余阶段
holodeck build --session <id> --from assemble
```

这个阶段化CLI系统为用户提供了极大的灵活性，支持各种构建场景和调试需求。