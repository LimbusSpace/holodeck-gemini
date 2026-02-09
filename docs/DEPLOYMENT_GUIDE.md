# Holodeck 部署和运维指南

## 目录

1. [系统架构](#系统架构)
2. [部署选项](#部署选项)
3. [生产环境部署](#生产环境部署)
4. [监控和告警](#监控和告警)
5. [性能调优](#性能调优)
6. [安全配置](#安全配置)
7. [备份和恢复](#备份和恢复)
8. [故障排除](#故障排除)

## 系统架构

### 整体架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Holodeck CLI  │────│  统一客户端架构 │────│   外部AI服务    │
│                 │    │                 │    │                 │
│ • Build命令     │    │ • 客户端工厂   │    │ • LLM服务       │
│ • Session命令   │    │ • 管道编排器   │    │ • 图像生成      │
│ • Debug命令     │    │ • 配置管理     │    │ • 3D生成        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   性能监控层    │    │   异常处理层    │    │   数据存储层    │
│                 │    │                 │    │                 │
│ • 缓存优化     │    │ • 统一异常框架 │    │ • 工作空间      │
│ • 并发管理     │    │ • 错误恢复     │    │ • 配置存储      │
│ • 内存优化     │    │ • 重试机制     │    │ • 缓存数据      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 组件依赖

- **Python 3.8+**: 主要运行环境
- **AI服务**: OpenAI、ComfyUI、SF3D等
- **存储**: 本地文件系统或云存储
- **网络**: 稳定的互联网连接

## 部署选项

### 1. 本地部署

#### 开发环境

```bash
# 克隆代码
git clone https://github.com/your-org/holodeck-claude.git
cd holodeck-claude

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -e .

# 配置环境变量
export OPENAI_API_KEY="your-key"
export COMFYUI_API_URL="http://localhost:8188"

# 测试安装
holodeck debug health
```

#### 生产环境

```bash
# 使用Docker部署
docker build -t holodeck .
docker run -d \
  -e OPENAI_API_KEY="your-key" \
  -e COMFYUI_API_URL="http://comfyui:8188" \
  -v /data/holodeck:/root/.holodeck \
  --name holodeck \
  holodeck
```

### 2. 容器化部署

#### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  holodeck:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - COMFYUI_API_URL=http://comfyui:8188
      - SF3D_API_URL=http://sf3d:8080
    volumes:
      - holodeck_data:/root/.holodeck
      - ./output:/app/output
    depends_on:
      - comfyui
      - sf3d
    restart: unless-stopped

  comfyui:
    image: comfyui/comfyui:latest
    ports:
      - "8188:8188"
    volumes:
      - comfyui_models:/app/models
    restart: unless-stopped

  sf3d:
    image: sf3d/sf3d:latest
    ports:
      - "8080:8080"
    volumes:
      - sf3d_models:/app/models
    restart: unless-stopped

volumes:
  holodeck_data:
  comfyui_models:
  sf3d_models:
```

#### Kubernetes部署

```yaml
# holodeck-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: holodeck
spec:
  replicas: 3
  selector:
    matchLabels:
      app: holodeck
  template:
    metadata:
      labels:
        app: holodeck
    spec:
      containers:
      - name: holodeck
        image: holodeck:latest
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: holodeck-secrets
              key: openai-api-key
        volumeMounts:
        - name: holodeck-storage
          mountPath: /root/.holodeck
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
      volumes:
      - name: holodeck-storage
        persistentVolumeClaim:
          claimName: holodeck-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: holodeck
spec:
  selector:
    app: holodeck
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

### 3. 云服务部署

#### AWS部署

```bash
# 使用ECS部署
aws ecs create-cluster --cluster-name holodeck-cluster

# 创建任务定义
aws ecs register-task-definition \
  --family holodeck-task \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu "1024" \
  --memory "2048" \
  --execution-role-arn arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole

# 部署服务
aws ecs create-service \
  --cluster holodeck-cluster \
  --service-name holodeck-service \
  --task-definition holodeck-task \
  --desired-count 2
```

#### Azure部署

```bash
# 创建资源组
az group create --name holodeck-rg --location eastus

# 创建容器实例
az container create \
  --resource-group holodeck-rg \
  --name holodeck \
  --image holodeck:latest \
  --dns-name-label holodeck-app \
  --ports 8080
```

## 生产环境部署

### 配置管理

#### 环境变量配置

```bash
# .env文件
OPENAI_API_KEY=your-openai-key
COMFYUI_API_URL=http://localhost:8188
SF3D_API_URL=http://localhost:8080
HOLDECK_LOG_LEVEL=INFO
HOLDECK_CACHE_SIZE_MB=200
HOLDECK_WORKERS=4
```

#### 配置文件管理

```yaml
# production.yaml
llm:
  default_provider: "openai"
  timeout: 30
  retry_attempts: 3
  backoff_factor: 1.5

image_generation:
  default_backend: "comfyui"
  timeout: 300
  quality: "high"

three_d_generation:
  default_backend: "sf3d"
  timeout: 600
  quality: "standard"

performance:
  cache_ttl: 7200
  max_cache_size_mb: 500
  concurrent_workers: 8
  memory_monitoring: true

logging:
  level: "INFO"
  file_rotation: "100MB"
  retention_days: 30
```

### 负载均衡

#### Nginx配置

```nginx
# nginx.conf
upstream holodeck_backend {
    server holodeck1:8080 weight=1 max_fails=3 fail_timeout=30s;
    server holodeck2:8080 weight=1 max_fails=3 fail_timeout=30s;
    server holodeck3:8080 weight=1 max_fails=3 fail_timeout=30s;

    # 负载均衡策略
    least_conn;

    # 健康检查
    check interval=3000 rise=2 fall=5 timeout=1000 type=http;
    check_http_send "HEAD /health HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx http_3xx;
}

server {
    listen 80;
    server_name holodeck.example.com;

    location / {
        proxy_pass http://holodeck_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # 健康检查端点
    location /health {
        proxy_pass http://holodeck_backend;
        access_log off;
    }
}
```

### 数据库配置

#### Redis缓存

```yaml
# redis配置
redis:
  host: localhost
  port: 6379
  db: 0
  password: null
  ssl: false
  timeout: 5
  max_connections: 50
```

#### PostgreSQL存储

```yaml
# postgres配置
database:
  host: localhost
  port: 5432
  database: holodeck
  username: holodeck_user
  password: secure_password
  pool_size: 20
  max_overflow: 10
  pool_pre_ping: true
```

## 监控和告警

### 监控指标

#### 系统指标

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'holodeck'
    static_configs:
      - targets: ['holodeck:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s

# 关键指标
- holodeck_requests_total
- holodeck_request_duration_seconds
- holodeck_memory_usage_bytes
- holodeck_cache_hit_ratio
- holodeck_error_rate
```

#### 应用指标

```python
# 在应用中暴露指标
from prometheus_client import Counter, Histogram, Gauge

REQUESTS_TOTAL = Counter(
    'holodeck_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'holodeck_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

MEMORY_USAGE = Gauge(
    'holodeck_memory_usage_bytes',
    'Current memory usage'
)
```

### 告警规则

#### Prometheus告警

```yaml
# alerting.rules.yml
groups:
- name: holodeck
  rules:
  - alert: HighErrorRate
    expr: rate(holodeck_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is above 10% for the last 5 minutes"

  - alert: HighMemoryUsage
    expr: holodeck_memory_usage_bytes > 3e9
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is above 3GB"

  - alert: SlowRequests
    expr: holodeck_request_duration_seconds{quantile="0.95"} > 30
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Slow requests detected"
      description: "95th percentile request duration is above 30 seconds"
```

#### Grafana仪表板

```json
{
  "dashboard": {
    "title": "Holodeck Production Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(holodeck_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(holodeck_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "Errors/sec"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "gauge",
        "targets": [
          {
            "expr": "holodeck_memory_usage_bytes",
            "legendFormat": "Memory"
          }
        ]
      }
    ]
  }
}
```

### 日志管理

#### ELK Stack配置

```yaml
# logstash.conf
input {
  file {
    path => ["/var/log/holodeck/*.log"]
    start_position => "beginning"
    sincedb_path => "/dev/null"
  }
}

filter {
  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level}: %{GREEDYDATA:message}" }
  }

  date {
    match => ["timestamp", "ISO8601"]
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "holodeck-logs-%{+YYYY.MM.dd}"
  }
}
```

#### 日志轮转

```bash
# logrotate配置
/var/log/holodeck/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        systemctl reload holodeck
    endscript
}
```

## 性能调优

### 系统调优

#### Linux系统参数

```bash
# /etc/security/limits.conf
holodeck soft nofile 65536
holodeck hard nofile 65536

# /etc/sysctl.conf
vm.swappiness = 10
vm.dirty_ratio = 60
vm.dirty_background_ratio = 2
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
```

#### Docker资源限制

```dockerfile
# Dockerfile
FROM python:3.9-slim

# 设置资源限制
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 优化Python性能
ENV PYTHONOPTIMIZE=1
ENV PYTHONHASHSEED=random

# 安装依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir -e .
```

### 应用调优

#### 缓存优化

```yaml
# 缓存配置
cache:
  type: "redis"
  host: "localhost"
  port: 6379
  ttl: 3600
  max_size: 1000000
  eviction_policy: "LRU"
```

#### 并发优化

```python
# 并发配置
concurrency:
  max_workers: 16
  thread_pool_size: 32
  process_pool_size: 8
  queue_size: 1000

  # I/O密集型任务
  io_workers: 24

  # CPU密集型任务
  cpu_workers: 8
```

#### 内存优化

```python
# 内存管理
memory:
  max_memory_mb: 2048
  gc_threshold: 0.8
  gc_frequency: 300
  object_pool_size: 1000
```

## 安全配置

### API安全

#### 认证和授权

```yaml
# 安全配置
security:
  api_keys:
    - name: "production"
      key: "${PRODUCTION_API_KEY}"
      rate_limit: "1000/hour"
      permissions: ["read", "write"]

    - name: "development"
      key: "${DEVELOPMENT_API_KEY}"
      rate_limit: "100/hour"
      permissions: ["read"]

  rate_limiting:
    enabled: true
    default_limit: "100/hour"
    burst_limit: "200"

  cors:
    allowed_origins:
      - "https://holodeck.example.com"
      - "https://app.holodeck.example.com"
    allowed_methods: ["GET", "POST"]
    allowed_headers: ["Authorization", "Content-Type"]
```

#### SSL/TLS配置

```nginx
# SSL配置
server {
    listen 443 ssl http2;
    server_name holodeck.example.com;

    ssl_certificate /etc/ssl/certs/holodeck.crt;
    ssl_certificate_key /etc/ssl/private/holodeck.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

### 数据安全

#### 加密配置

```python
# 数据加密
encryption:
  algorithm: "AES-256-GCM"
  key_rotation_days: 30

  # 敏感字段加密
  sensitive_fields:
    - "api_keys"
    - "user_data"
    - "session_tokens"
```

#### 备份加密

```bash
# 加密备份
openssl enc -aes-256-cbc -salt -in backup.tar.gz -out backup.tar.gz.enc -pass env:BACKUP_PASSWORD

# 解密备份
openssl enc -d -aes-256-cbc -in backup.tar.gz.enc -out backup.tar.gz -pass env:BACKUP_PASSWORD
```

## 备份和恢复

### 数据备份

#### 自动备份脚本

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/holodeck"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份配置
cp -r ~/.holodeck/config.yaml $BACKUP_DIR/config_$DATE.yaml

# 备份工作空间
tar -czf $BACKUP_DIR/workspace_$DATE.tar.gz ~/.holodeck/workspace

# 备份数据库
pg_dump holodeck > $BACKUP_DIR/database_$DATE.sql

# 加密备份
openssl enc -aes-256-cbc -salt -in $BACKUP_DIR/workspace_$DATE.tar.gz \
  -out $BACKUP_DIR/workspace_$DATE.tar.gz.enc -pass env:BACKUP_PASSWORD

# 清理旧备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.sql" -mtime +$RETENTION_DAYS -delete

# 上传到云存储
aws s3 cp $BACKUP_DIR s3://holodeck-backups/ --recursive
```

#### 备份策略

```yaml
# 备份策略
backup_strategy:
  # 完整备份
  full_backup:
    schedule: "0 2 * * 0"  # 每周日2点
    retention: "90 days"

  # 增量备份
  incremental_backup:
    schedule: "0 2 * * 1-6"  # 周一到周六2点
    retention: "30 days"

  # 配置备份
  config_backup:
    schedule: "0 */6 * * *"  # 每6小时
    retention: "7 days"
```

### 灾难恢复

#### 恢复流程

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1
RESTORE_DIR="/restore"

# 停止服务
systemctl stop holodeck

# 解密备份
openssl enc -d -aes-256-cbc -in $BACKUP_FILE \
  -out backup.tar.gz -pass env:BACKUP_PASSWORD

# 解压备份
mkdir -p $RESTORE_DIR
tar -xzf backup.tar.gz -C $RESTORE_DIR

# 恢复配置
cp $RESTORE_DIR/config.yaml ~/.holodeck/config.yaml

# 恢复工作空间
rm -rf ~/.holodeck/workspace
cp -r $RESTORE_DIR/workspace ~/.holodeck/

# 恢复数据库
psql holodeck < $RESTORE_DIR/database.sql

# 启动服务
systemctl start holodeck

# 验证恢复
holodeck debug health
```

#### 恢复测试

```bash
# 定期恢复测试
#!/bin/bash
# test_restore.sh

# 创建测试环境
TEST_DIR="/tmp/restore_test"
mkdir -p $TEST_DIR

# 执行恢复
./restore.sh /backup/latest_backup.tar.gz.enc

# 验证功能
holodeck debug health
holodeck session info

# 清理测试环境
rm -rf $TEST_DIR
```

## 故障排除

### 常见问题诊断

#### 服务不可用

```bash
# 检查服务状态
systemctl status holodeck

# 检查日志
tail -f /var/log/holodeck/holodeck.log

# 检查端口
netstat -tlnp | grep 8080

# 检查资源使用
top -p $(pgrep holodeck)
```

#### 性能问题

```bash
# 性能分析
holodeck debug performance --report

# 内存分析
python -m memory_profiler holodeck_script.py

# CPU分析
python -c "import cProfile; cProfile.run('holodeck.build()')"
```

#### 网络问题

```bash
# 检查网络连接
ping api.openai.com

# 检查DNS解析
dig api.openai.com

# 检查SSL证书
openssl s_client -connect api.openai.com:443

# 测试API连接
curl -v https://api.openai.com/v1/chat/completions
```

### 健康检查脚本

```bash
#!/bin/bash
# health_check.sh

check_service() {
    if systemctl is-active --quiet holodeck; then
        echo "✓ Service is running"
    else
        echo "✗ Service is not running"
        exit 1
    fi
}

check_api() {
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
    if [ "$response" = "200" ]; then
        echo "✓ API is responding"
    else
        echo "✗ API is not responding (HTTP $response)"
        exit 1
    fi
}

check_disk_space() {
    usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $usage -lt 90 ]; then
        echo "✓ Disk space is sufficient ($usage%)"
    else
        echo "✗ Disk space is low ($usage%)"
        exit 1
    fi
}

check_memory() {
    available=$(free | awk 'NR==2{printf "%.0f", $7/1024}')
    if [ $available -gt 1024 ]; then
        echo "✓ Memory is sufficient ($available MB available)"
    else
        echo "✗ Memory is low ($available MB available)"
        exit 1
    fi
}

# 执行检查
check_service
check_api
check_disk_space
check_memory

echo "All health checks passed!"
```

### 监控告警集成

#### Slack告警

```python
# slack_alert.py
import requests
import json

def send_slack_alert(message, channel="#alerts"):
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

    payload = {
        "channel": channel,
        "text": message,
        "username": "Holodeck Monitor",
        "icon_emoji": ":warning:"
    }

    response = requests.post(webhook_url, json=payload)
    return response.status_code == 200

# 使用示例
if error_rate > 0.1:
    send_slack_alert(f"High error rate detected: {error_rate:.2%}")
```

#### PagerDuty集成

```python
# pagerduty_alert.py
import requests

def trigger_pagerduty_alert(title, details, severity="critical"):
    integration_key = "your-pagerduty-integration-key"

    payload = {
        "routing_key": integration_key,
        "event_action": "trigger",
        "payload": {
            "summary": title,
            "source": "holodeck-production",
            "severity": severity,
            "custom_details": details
        }
    }

    response = requests.post(
        "https://events.pagerduty.com/v2/enqueue",
        json=payload
    )

    return response.status_code == 202
```

### 维护窗口

#### 计划维护

```bash
#!/bin/bash
# maintenance.sh

# 通知用户
echo "Starting maintenance window at $(date)"
send_slack_alert("Maintenance window started")

# 停止服务
systemctl stop holodeck

# 执行维护任务
./backup.sh
./update_dependencies.sh
./run_migrations.sh

# 启动服务
systemctl start holodeck

# 验证服务
./health_check.sh

# 通知完成
echo "Maintenance completed at $(date)"
send_slack_alert("Maintenance window completed successfully")
```