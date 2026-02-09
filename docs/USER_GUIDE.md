# Holodeck 用户指南

## 目录

1. [快速开始](#快速开始)
2. [安装配置](#安装配置)
3. [基本使用](#基本使用)
4. [高级功能](#高级功能)
5. [故障排除](#故障排除)
6. [最佳实践](#最佳实践)

## 快速开始

### 基本场景生成

```bash
# 生成一个现代客厅场景
holodeck build "A modern living room with a sofa and coffee table"

# 生成高质量的3D场景
holodeck build "A futuristic kitchen" --quality high

# 指定输出目录
holodeck build "A cozy bedroom" --output ./my_scenes
```

### 查看系统状态

```bash
# 检查系统健康状态
holodeck debug health

# 查看所有客户端状态
holodeck debug clients

# 查看性能统计
holodeck debug performance
```

## 安装配置

### 前提条件

- Python 3.8+
- 足够的磁盘空间（建议至少10GB）
- 网络连接（用于访问AI服务）

### 基本配置

1. **配置文件位置**: `~/.holodeck/config.yaml`
2. **工作空间**: 默认在用户主目录下的`.holodeck/workspace`
3. **缓存目录**: `~/.holodeck/cache`

### 配置API密钥

编辑配置文件或设置环境变量：

```bash
# 设置OpenAI API密钥
export OPENAI_API_KEY="your-api-key"

# 设置其他服务密钥
export COMFYUI_API_URL="http://localhost:8188"
export SF3D_API_URL="http://localhost:8080"
```

### 配置文件示例

```yaml
# ~/.holodeck/config.yaml
llm:
  default_provider: "openai"
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
    base_url: "https://api.openai.com/v1"

image_generation:
  default_backend: "comfyui"
  comfyui:
    api_url: "${COMFYUI_API_URL}"
    timeout: 300

three_d_generation:
  default_backend: "sf3d"
  sf3d:
    api_url: "${SF3D_API_URL}"
    quality: "standard"

performance:
  cache_ttl: 3600
  max_cache_size_mb: 100
  concurrent_workers: 4
```

## 基本使用

### 场景生成

#### 简单场景

```bash
# 基本用法
holodeck build "A modern living room"

# 带详细描述
holodeck build "A spacious living room with large windows, a comfortable sofa, and a coffee table"
```

#### 高级选项

```bash
# 指定质量级别
holodeck build "A kitchen" --quality high

# 指定输出格式
holodeck build "A bedroom" --format glb

# 使用特定后端
holodeck build "A bathroom" --backend hunyuan

# 设置超时时间
holodeck build "A garden" --timeout 600
```

### 会话管理

#### 查看会话信息

```bash
# 显示当前会话信息
holodeck session info

# 显示详细会话状态
holodeck session info --verbose
```

#### 缓存管理

```bash
# 查看缓存统计
holodeck session cache-stats

# 清理所有缓存
holodeck session cache-clear

# 清理特定缓存
holodeck session cache-clear --type llm
```

#### 会话导出导入

```bash
# 导出会话
holodeck session export ./backup.json

# 导入会话
holodeck session import ./backup.json
```

### 调试工具

#### 系统健康检查

```bash
# 基本健康检查
holodeck debug health

# 详细健康检查
holodeck debug health --detailed

# 检查特定服务
holodeck debug health --service llm
```

#### 客户端状态

```bash
# 查看所有客户端
holodeck debug clients

# 检查特定客户端
holodeck debug clients --type image

# 测试客户端连接
holodeck debug clients --test
```

#### 性能监控

```bash
# 查看性能统计
holodeck debug performance

# 生成性能报告
holodeck debug performance --report ./perf_report.json

# 实时监控
holodeck debug performance --live
```

## 高级功能

### 批量处理

```bash
# 批量生成场景
holodeck build-batch scenes.txt --output ./batch_output

# 其中 scenes.txt 包含:
# A modern living room
# A futuristic kitchen
# A cozy bedroom
```

### 自定义工作流

```bash
# 使用自定义管道
holodeck build "A scene" --pipeline custom_pipeline.json

# 分阶段执行
holodeck build-staged "A scene" --stages layout,objects,textures
```

### 集成外部工具

#### 与Blender集成

```bash
# 生成Blender兼容的输出
holodeck build "A scene" --format blender

# 直接导入Blender
holodeck build "A scene" --import-blender
```

#### 与Unity集成

```bash
# 生成Unity兼容的输出
holodeck build "A scene" --format unity

# 生成预制件
holodeck build "A scene" --prefab
```

### 性能优化

#### 缓存优化

```bash
# 调整缓存大小
holodeck config set performance.max_cache_size_mb 200

# 调整缓存TTL
holodeck config set performance.cache_ttl 7200
```

#### 并发优化

```bash
# 调整并发工作进程数
holodeck config set performance.concurrent_workers 8

# 启用GPU加速
holodeck config set performance.gpu_acceleration true
```

#### 内存优化

```bash
# 启用内存监控
holodeck config set performance.memory_monitoring true

# 设置内存限制
holodeck config set performance.memory_limit_mb 1024
```

## 故障排除

### 常见问题

#### 1. API连接失败

**症状**: 无法连接到AI服务

**解决方案**:
```bash
# 检查网络连接
holodeck debug health --network

# 检查API密钥
holodeck debug config --show-secrets

# 测试特定服务
holodeck debug clients --test --type llm
```

#### 2. 内存不足

**症状**: 程序运行缓慢或崩溃

**解决方案**:
```bash
# 清理缓存
holodeck session cache-clear

# 减少并发数
holodeck config set performance.concurrent_workers 2

# 增加内存清理频率
holodeck config set performance.gc_frequency 300
```

#### 3. 生成质量不佳

**症状**: 生成的场景质量不符合预期

**解决方案**:
```bash
# 使用更详细的提示词
holodeck build "A modern living room with a large window, comfortable gray sofa, wooden coffee table, and plants"

# 提高质量设置
holodeck build "A scene" --quality high

# 使用特定后端
holodeck build "A scene" --backend hunyuan
```

#### 4. 性能问题

**症状**: 程序运行缓慢

**解决方案**:
```bash
# 查看性能报告
holodeck debug performance --report

# 优化缓存设置
holodeck session cache-clear
holodeck config set performance.max_cache_size_mb 200

# 检查系统资源
holodeck debug system-info
```

### 错误代码参考

| 错误代码 | 描述 | 解决方案 |
|---------|------|----------|
| CONFIG_001 | 配置文件缺失 | 检查配置文件路径 |
| API_001 | API密钥无效 | 验证API密钥 |
| NETWORK_001 | 网络连接失败 | 检查网络连接 |
| MEMORY_001 | 内存不足 | 清理缓存或增加内存 |
| TIMEOUT_001 | 请求超时 | 增加超时时间或检查网络 |

### 日志分析

#### 日志位置

- **主日志**: `~/.holodeck/logs/holodeck.log`
- **性能日志**: `~/.holodeck/logs/performance.log`
- **错误日志**: `~/.holodeck/logs/error.log`

#### 日志级别

```bash
# 设置日志级别
holodeck config set logging.level DEBUG

# 查看实时日志
tail -f ~/.holodeck/logs/holodeck.log

# 过滤错误日志
grep ERROR ~/.holodeck/logs/holodeck.log
```

#### 常见日志模式

```
# 正常操作
INFO: 开始生成场景: modern living room
INFO: 使用后端: hunyuan
INFO: 场景生成完成，耗时: 45.2秒

# 警告
WARNING: 缓存大小超过限制，开始清理
WARNING: 网络延迟较高，考虑优化连接

# 错误
ERROR: API调用失败: 连接超时
ERROR: 内存不足，无法继续处理
```

## 最佳实践

### 提示词工程

1. **具体描述**: 使用详细的描述而不是简单的关键词
   ```
   # 不推荐
   "A room"

   # 推荐
   "A modern living room with a large window, comfortable gray sofa, wooden coffee table, and green plants"
   ```

2. **风格指定**: 明确指定所需的风格
   ```
   "A steampunk style kitchen with brass fixtures and vintage appliances"
   ```

3. **材质描述**: 包含材质信息
   ```
   "A glass and steel coffee table with marble texture"
   ```

### 性能优化

1. **合理使用缓存**: 避免重复生成相同内容
2. **批量处理**: 对多个场景使用批量处理
3. **适当的质量设置**: 根据需要选择质量级别
4. **监控资源使用**: 定期查看性能报告

### 工作流程

1. **规划阶段**: 明确需求和预期结果
2. **测试阶段**: 使用简单场景测试配置
3. **优化阶段**: 调整参数获得最佳效果
4. **生产阶段**: 批量生成最终内容

### 备份和恢复

1. **定期备份配置**:
   ```bash
   cp ~/.holodeck/config.yaml ./backup_config.yaml
   ```

2. **备份工作空间**:
   ```bash
   tar -czf workspace_backup.tar.gz ~/.holodeck/workspace
   ```

3. **导出会话**:
   ```bash
   holodeck session export ./session_backup.json
   ```

### 安全注意事项

1. **API密钥保护**: 不要将API密钥提交到版本控制
2. **配置文件权限**: 设置适当的文件权限
3. **网络安全性**: 使用安全的网络连接
4. **数据隐私**: 注意处理敏感数据

## 获取帮助

### 内置帮助

```bash
# 查看命令帮助
holodeck --help
holodeck build --help
holodeck debug --help

# 查看配置帮助
holodeck config --help
```

### 在线资源

- **文档**: 查看详细的使用说明
- **示例**: 查看examples目录中的示例代码
- **测试**: 运行测试验证安装

### 社区支持

1. 查看项目文档和示例
2. 运行调试命令收集信息
3. 在issue中提供详细的错误信息
4. 包括日志文件和配置信息（去除敏感信息）