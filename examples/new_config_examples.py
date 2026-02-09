"""
新的配置系统示例

这些示例展示了如何使用新的统一配置管理系统。
"""

import os
from pathlib import Path

# 示例1: 基本配置使用
print("=== 示例1: 基本配置使用 ===")

from holodeck_core.config.base import get_config, get_api_credentials

# 获取基本配置
log_level = get_config('LOG_LEVEL', 'INFO')
max_workers = get_config('MAX_WORKERS', 4, value_type=int)
debug_mode = get_config('DEBUG_MODE', False, value_type=bool)

print(f"日志级别: {log_level}")
print(f"最大工作线程: {max_workers}")
print(f"调试模式: {debug_mode}")

# 示例2: API凭证管理
print("\n=== 示例2: API凭证管理 ===")

# 获取Hunyuan API凭证
hunyuan_creds = get_api_credentials('HUNYUAN')
print(f"Hunyuan凭证: {hunyuan_creds}")

# 获取SiliconFlow API凭证
siliconflow_creds = get_api_credentials('SILICONFLOW')
print(f"SiliconFlow凭证: {siliconflow_creds}")

# 示例3: 服务配置检查
print("\n=== 示例3: 服务配置检查 ===")

from holodeck_core.config.base import is_service_configured

services = ['HUNYUAN', 'SILICONFLOW', 'OPENAI', 'TESTBED']
for service in services:
    if is_service_configured(service):
        print(f"✅ {service} 已配置")
    else:
        print(f"❌ {service} 未配置")

# 示例4: 向后兼容的CLI配置
print("\n=== 示例4: 向后兼容的CLI配置 ===")

from holodeck_cli.config import config

# 使用现有的API（向后兼容）
workspace_path = config.get_workspace_path()
print(f"工作空间路径: {workspace_path}")

# 获取API密钥（向后兼容）
siliconflow_key = config.get_api_key('SILICONFLOW')
print(f"SiliconFlow密钥存在: {bool(siliconflow_key)}")

# 检查服务可用性
if config.is_siliconflow_available():
    print("✅ SiliconFlow服务可用")
else:
    print("❌ SiliconFlow服务不可用")

# 示例5: 配置设置和保存
print("\n=== 示例5: 配置设置和保存 ===")

# 设置新配置值
config.set('custom_setting', 'custom_value')
config.set('max_objects', 50)

print(f"自定义设置: {config.get('custom_setting')}")
print(f"最大对象数: {config.get('max_objects')}")

# 示例6: 配置重新加载
print("\n=== 示例6: 配置重新加载 ===")

# 模拟环境变量更改
os.environ['HOODECK_LOG_LEVEL'] = 'DEBUG'

# 重新加载配置
config.reload()

# 验证新值
new_log_level = config.get('log_level')
print(f"重新加载后的日志级别: {new_log_level}")

# 示例7: 高级类型转换
print("\n=== 示例7: 高级类型转换 ===")

# 设置一些测试环境变量
os.environ['HOODECK_SERVER_LIST'] = '["server1", "server2", "server3"]'
os.environ['HOODECK_FEATURE_FLAGS'] = 'feature1,feature2,feature3'

# 获取并转换类型
server_list = get_config('SERVER_LIST', [], value_type=list)
feature_flags = get_config('FEATURE_FLAGS', [], value_type=list)

print(f"服务器列表: {server_list}")
print(f"功能标志: {feature_flags}")

# 示例8: 配置管理器高级功能
print("\n=== 示例8: 配置管理器高级功能 ===")

from holodeck_core.config.base import ConfigManager

# 获取配置管理器实例
config_manager = ConfigManager()

# 确保环境变量已加载
loaded = config_manager.ensure_env_loaded()
print(f"环境变量加载状态: {loaded}")

# 清除缓存
config_manager.clear_cache()
print("配置缓存已清除")

# 获取统计信息
# 注意：这只是一个示例，实际统计信息可能需要额外实现
print("配置管理器功能演示完成")

print("\n=== 所有示例完成 ===")
print("新的配置系统提供了：")
print("✅ 自动类型转换")
print("✅ 配置缓存提升性能")
print("✅ 统一的API凭证管理")
print("✅ 完全向后兼容")
print("✅ 更好的错误处理")
print("✅ 配置重新加载功能")