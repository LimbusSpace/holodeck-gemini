# Holodeck 故障排除指南

## 目录

1. [快速诊断](#快速诊断)
2. [常见问题](#常见问题)
3. [错误代码参考](#错误代码参考)
4. [日志分析](#日志分析)
5. [性能问题](#性能问题)
6. [网络问题](#网络问题)
7. [配置问题](#配置问题)
8. [高级调试](#高级调试)

## 快速诊断

### 系统健康检查

```bash
# 运行完整的健康检查
holodeck debug health --detailed

# 检查特定组件
holodeck debug health --service llm
holodeck debug health --service image
holodeck debug health --service 3d

# 快速状态检查
holodeck debug status
```

### 诊断脚本

```bash
#!/bin/bash
# quick_diagnostic.sh

echo "=== Holodeck 快速诊断 ==="
echo "时间: $(date)"
echo

# 系统信息
echo "--- 系统信息 ---"
uname -a
python --version
echo

# 服务状态
echo "--- 服务状态 ---"
holodeck debug health

echo "--- 客户端状态 ---"
holodeck debug clients

echo "--- 性能统计 ---"
holodeck debug performance

echo "--- 会话信息 ---"
holodeck session info

echo "=== 诊断完成 ==="
```

## 常见问题

### 1. 启动失败

#### 症状
- 命令无法执行
- 报错 "command not found"
- 导入错误

#### 诊断步骤

```bash
# 检查安装
which holodeck
holodeck --version

# 检查Python环境
python -c "import holodeck_cli; print('导入成功')"

# 检查依赖
pip list | grep holodeck

# 查看详细错误
holodeck debug --verbose
```

#### 解决方案

1. **重新安装**:
   ```bash
   pip uninstall holodeck-claude
   pip install -e .
   ```

2. **检查Python路径**:
   ```bash
   echo $PYTHONPATH
   export PYTHONPATH="/path/to/holodeck:$PYTHONPATH"
   ```

3. **虚拟环境问题**:
   ```bash
   # 重新创建虚拟环境
   rm -rf venv
   python -m venv venv
   source venv/bin/activate
   pip install -e .
   ```

### 2. API连接失败

#### 症状
- "API connection failed"
- "Authentication failed"
- "Timeout error"

#### 诊断步骤

```bash
# 检查网络连接
ping api.openai.com

# 检查API密钥
holodeck debug config --show-secrets

# 测试特定服务
holodeck debug clients --test --type llm

# 检查防火墙
curl -v https://api.openai.com/v1/chat/completions
```

#### 解决方案

1. **检查API密钥**:
   ```bash
   # 验证环境变量
   echo $OPENAI_API_KEY

   # 重新设置密钥
   export OPENAI_API_KEY="your-new-key"
   ```

2. **网络代理**:
   ```bash
   # 设置代理
   export HTTP_PROXY="http://proxy:port"
   export HTTPS_PROXY="http://proxy:port"
   ```

3. **超时设置**:
   ```yaml
   # config.yaml
   llm:
     timeout: 60
     retry_attempts: 3
   ```

### 3. 内存不足

#### 症状
- "Out of memory"
- 程序崩溃
- 运行缓慢

#### 诊断步骤

```bash
# 检查内存使用
free -h

# Holodeck内存使用
holodeck debug performance --memory

# 系统资源
top -p $(pgrep holodeck)

# 缓存大小
holodeck session cache-stats
```

#### 解决方案

1. **清理缓存**:
   ```bash
   holodeck session cache-clear
   ```

2. **调整内存限制**:
   ```yaml
   # config.yaml
   performance:
     max_cache_size_mb: 100
     memory_monitoring: true
     gc_frequency: 300
   ```

3. **减少并发**:
   ```yaml
   performance:
     concurrent_workers: 2
   ```

### 4. 生成质量不佳

#### 症状
- 输出不符合预期
- 缺少细节
- 风格不一致

#### 诊断步骤

```bash
# 检查提示词
holodeck debug prompt "your prompt"

# 测试不同后端
holodeck build "test" --backend comfyui
holodeck build "test" --backend hunyuan

# 查看详细日志
holodeck build "test" --verbose
```

#### 解决方案

1. **优化提示词**:
   ```
   # 不推荐
   "A room"

   # 推荐
   "A modern living room with large windows, comfortable gray sofa, wooden coffee table, and green plants"
   ```

2. **调整质量设置**:
   ```bash
   holodeck build "scene" --quality high
   holodeck build "scene" --detail-level maximum
   ```

3. **使用特定后端**:
   ```bash
   holodeck build "scene" --backend hunyuan
   ```

### 5. 性能问题

#### 症状
- 运行缓慢
- 高延迟
- 资源占用过高

#### 诊断步骤

```bash
# 性能分析
holodeck debug performance --report performance.json

# 实时监控
holodeck debug performance --live

# 瓶颈分析
python -m cProfile -s cumulative holodeck_script.py
```

#### 解决方案

1. **启用缓存**:
   ```yaml
   performance:
     cache_ttl: 3600
     max_cache_size_mb: 200
   ```

2. **优化并发**:
   ```yaml
   performance:
     concurrent_workers: 8
     thread_pool_size: 16
   ```

3. **调整超时**:
   ```yaml
   llm:
     timeout: 30
   image_generation:
     timeout: 300
   ```

## 错误代码参考

### 配置错误

| 代码 | 描述 | 解决方案 |
|------|------|----------|
| CONFIG_001 | 配置文件缺失 | 检查配置文件路径 |
| CONFIG_002 | 配置格式错误 | 验证YAML语法 |
| CONFIG_003 | 必填配置缺失 | 添加缺失的配置项 |
| CONFIG_004 | 配置值无效 | 检查配置值格式 |

### API错误

| 代码 | 描述 | 解决方案 |
|------|------|----------|
| API_001 | API密钥无效 | 验证API密钥 |
| API_002 | API配额超限 | 升级API计划或等待重置 |
| API_003 | 网络连接失败 | 检查网络连接 |
| API_004 | 服务不可用 | 稍后重试或联系服务商 |
| API_005 | 请求超时 | 增加超时时间 |

### 系统错误

| 代码 | 描述 | 解决方案 |
|------|------|----------|
| SYS_001 | 内存不足 | 清理缓存或增加内存 |
| SYS_002 | 磁盘空间不足 | 清理磁盘空间 |
| SYS_003 | 权限不足 | 检查文件权限 |
| SYS_004 | 依赖缺失 | 安装缺失的依赖 |

### 客户端错误

| 代码 | 描述 | 解决方案 |
|------|------|----------|
| CLIENT_001 | 客户端创建失败 | 检查配置和连接 |
| CLIENT_002 | 客户端连接失败 | 检查网络和服务状态 |
| CLIENT_003 | 客户端超时 | 增加超时设置 |
| CLIENT_004 | 客户端认证失败 | 检查认证信息 |

## 日志分析

### 日志位置

```bash
# 主日志文件
~/.holodeck/logs/holodeck.log

# 性能日志
~/.holodeck/logs/performance.log

# 错误日志
~/.holodeck/logs/error.log

# 调试日志
~/.holodeck/logs/debug.log
```

### 日志级别

```bash
# 设置日志级别
holodeck config set logging.level DEBUG

# 可用级别
# DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### 常见日志模式

#### 正常操作日志

```
INFO: 开始生成场景: modern living room
INFO: 使用后端: hunyuan
INFO: 场景生成完成，耗时: 45.2秒
INFO: 缓存命中: llm_response_abc123
```

#### 警告日志

```
WARNING: 缓存大小超过限制 (150MB > 100MB)，开始清理
WARNING: 网络延迟较高 (2.3s)，考虑优化连接
WARNING: API调用频率接近限制，启用节流
```

#### 错误日志

```
ERROR: API调用失败: 连接超时
ERROR: 内存不足，无法继续处理
ERROR: 配置文件解析失败: YAML格式错误
```

### 日志分析工具

```bash
# 实时日志监控
tail -f ~/.holodeck/logs/holodeck.log

# 过滤错误日志
grep ERROR ~/.holodeck/logs/holodeck.log

# 统计错误类型
grep ERROR ~/.holodeck/logs/holodeck.log | cut -d' ' -f4- | sort | uniq -c

# 时间范围过滤
grep "2024-01-15" ~/.holodeck/logs/holodeck.log

# 性能分析
grep "耗时" ~/.holodeck/logs/holodeck.log | awk '{print $NF}' | sort -n
```

### 日志轮转

```bash
# 手动轮转日志
logrotate /etc/logrotate.d/holodeck

# 查看轮转状态
ls -la ~/.holodeck/logs/

# 清理旧日志
find ~/.holodeck/logs/ -name "*.gz" -mtime +30 -delete
```

## 性能问题

### 性能监控

```bash
# 实时性能监控
holodeck debug performance --live

# 生成性能报告
holodeck debug performance --report perf_report.json

# 性能统计
holodeck debug performance --stats
```

### 性能分析工具

```python
# Python性能分析
import cProfile
import pstats

# 分析函数性能
cProfile.run('holodeck.build("test scene")', 'profile_stats')

# 查看分析结果
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative').print_stats(20)
```

```bash
# 内存分析
python -m memory_profiler holodeck_script.py

# I/O分析
strace -e trace=read,write,open,close holodeck build "test"

# 系统调用分析
perf record holodeck build "test"
perf report
```

### 性能优化建议

1. **缓存优化**:
   - 增加缓存大小
   - 优化缓存TTL
   - 使用分布式缓存

2. **并发优化**:
   - 调整工作进程数
   - 优化线程池大小
   - 使用异步IO

3. **内存优化**:
   - 启用内存监控
   - 定期垃圾回收
   - 优化数据结构

4. **网络优化**:
   - 启用连接池
   - 压缩数据传输
   - 使用CDN

## 网络问题

### 网络诊断

```bash
# 基本连接测试
ping api.openai.com

# DNS解析测试
dig api.openai.com
nslookup api.openai.com

# 端口连通性
telnet api.openai.com 443

# SSL证书检查
openssl s_client -connect api.openai.com:443
```

### 代理配置

```bash
# 设置HTTP代理
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"

# 设置no_proxy
export NO_PROXY="localhost,127.0.0.1,.company.com"

# 在配置文件中设置
network:
  proxy:
    http: "http://proxy:8080"
    https: "http://proxy:8080"
    no_proxy: ["localhost", "127.0.0.1"]
```

### 防火墙配置

```bash
# 检查防火墙状态
sudo ufw status
sudo iptables -L

# 开放必要端口
sudo ufw allow 8080/tcp
sudo ufw allow 8188/tcp  # ComfyUI
sudo ufw allow 8000/tcp  # SF3D

# 检查端口监听
netstat -tlnp | grep -E "(8080|8188|8000)"
```

## 配置问题

### 配置验证

```bash
# 验证配置文件
holodeck debug config --validate

# 显示当前配置
holodeck debug config --show

# 检查配置来源
holodeck debug config --sources
```

### 配置修复

```bash
# 重置为默认配置
holodeck config reset

# 重新加载配置
holodeck config reload

# 检查配置语法
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

### 环境变量

```bash
# 检查环境变量
env | grep -i holodeck
env | grep -i api

# 设置环境变量
export HOLDECK_LOG_LEVEL=DEBUG
export HOLDECK_CACHE_SIZE=200

# 验证设置
holodeck debug config --env
```

## 高级调试

### 调试模式

```bash
# 启用调试模式
holodeck --debug build "test scene"

# 详细日志
holodeck --verbose --log-level DEBUG build "test"

# 跟踪模式
holodeck --trace build "test scene"
```

### 远程调试

```python
# 启用远程调试
import pdb;pdb.set_trace()

# 使用ipdb
import ipdb;ipdb.set_trace()

# 远程调试服务器
import rpdb;rpdb.set_trace()
```

### 核心转储

```bash
# 启用核心转储
ulimit -c unlimited

# 设置核心转储路径
echo "/tmp/core.%p" > /proc/sys/kernel/core_pattern

# 分析核心转储
gdb python core.12345
```

### 性能剖析

```bash
# CPU剖析
perf record -g holodeck build "test"
perf report --call-graph

# 内存剖析
valgrind --tool=massif python holodeck_script.py
ms_print massif.out.<pid>

# I/O剖析
strace -c holodeck build "test"
```

### 网络抓包

```bash
# 抓取API调用
tcpdump -i any -w api_capture.pcap port 443

# 分析抓包文件
wireshark api_capture.pcap

# HTTP流量分析
tcpflow -c -i any port 443
```

### 自定义调试脚本

```python
#!/usr/bin/env python3
# debug_holodeck.py

import logging
import sys
from pathlib import Path

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

# 导入Holodeck模块
sys.path.insert(0, '/path/to/holodeck')

from holodeck_cli.debug import debug_system
from holodeck_core.config.base import ConfigManager

def main():
    print("=== Holodeck 高级调试 ===")

    # 检查配置
    config = ConfigManager()
    print(f"配置加载: {config.get('llm.default_provider')}")

    # 运行系统调试
    debug_system()

    # 自定义检查
    print("\n自定义检查:")
    # 添加自定义调试代码

if __name__ == "__main__":
    main()
```

### 问题报告模板

```markdown
## 问题描述
[详细描述遇到的问题]

## 重现步骤
1. [步骤1]
2. [步骤2]
3. [步骤3]

## 期望结果
[期望的行为]

## 实际结果
[实际的行为]

## 环境信息
- Holodeck版本: [版本号]
- Python版本: [版本号]
- 操作系统: [操作系统信息]
- 安装方式: [pip/docker/源码]

## 配置信息
```yaml
[相关的配置信息]
```

## 日志信息
```
[相关的日志输出]
```

## 已尝试的解决方案
- [尝试1]
- [尝试2]
- [尝试3]
```

### 联系支持

如果问题无法解决，请:

1. 收集诊断信息:
   ```bash
   holodeck debug health --detailed > diagnostic_info.txt
   ```

2. 保存相关日志:
   ```bash
   cp ~/.holodeck/logs/holodeck.log ./problem_logs/
   ```

3. 创建问题报告，包含:
   - 问题描述
   - 重现步骤
   - 环境信息
   - 诊断结果
   - 相关日志

4. 提交到项目issue跟踪器