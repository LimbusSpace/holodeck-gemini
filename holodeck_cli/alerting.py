"""
告警管理系统

提供告警配置、通知和管理的功能。
"""

import json
import smtplib
import requests
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

from holodeck_cli.logging_config import get_logger
from holodeck_cli.monitoring import MonitoringSystem, AlertRule

logger = get_logger(__name__)


@dataclass
class NotificationChannel:
    """通知渠道"""
    name: str
    type: str  # email, webhook, slack, teams
    config: Dict[str, Any]
    enabled: bool = True


@dataclass
class AlertNotification:
    """告警通知"""
    alert_name: str
    severity: str
    message: str
    timestamp: float
    channels: List[str]
    resolved: bool = False
    resolved_at: Optional[float] = None


class AlertingManager:
    """告警管理器"""

    def __init__(self, monitoring_system: MonitoringSystem):
        """
        初始化告警管理器

        Args:
            monitoring_system: 监控系统实例
        """
        self.monitoring_system = monitoring_system
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self.active_alerts: Dict[str, AlertNotification] = {}
        self.alert_history: List[AlertNotification] = []
        self._lock = threading.RLock()

        # 加载配置
        self._load_config()

        # 设置默认通知渠道
        self._setup_default_channels()

    def _load_config(self):
        """加载告警配置"""
        config_path = Path.home() /".holodeck" / "alerting_config.json"

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 加载通知渠道
                for channel_config in config.get("channels", []):
                    channel = NotificationChannel(**channel_config)
                    self.notification_channels[channel.name] = channel

                logger.info(f"Loaded alerting configuration from {config_path}")

            except Exception as e:
                logger.error(f"Failed to load alerting configuration: {e}")

    def _save_config(self):
        """保存告警配置"""
        config_path = Path.home() / ".holodeck" / "alerting_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            config = {
                "channels": [asdict(channel) for channel in self.notification_channels.values()]
            }

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved alerting configuration to {config_path}")

        except Exception as e:
            logger.error(f"Failed to save alerting configuration: {e}")

    def _setup_default_channels(self):
        """设置默认通知渠道"""
        # 默认不设置任何渠道，需要用户配置
        pass

    def add_notification_channel(self, channel: NotificationChannel):
        """添加通知渠道"""
        with self._lock:
            self.notification_channels[channel.name] = channel

        # 保存配置
        self._save_config()

        logger.info(f"Added notification channel: {channel.name}")

    def remove_notification_channel(self, name: str):
        """移除通知渠道"""
        with self._lock:
            if name in self.notification_channels:
                del self.notification_channels[name]

        # 保存配置
        self._save_config()

        logger.info(f"Removed notification channel: {name}")

    def enable_channel(self, name: str):
        """启用通知渠道"""
        with self._lock:
            if name in self.notification_channels:
                self.notification_channels[name].enabled = True

        self._save_config()
        logger.info(f"Enabled notification channel: {name}")

    def disable_channel(self, name: str):
        """禁用通知渠道"""
        with self._lock:
            if name in self.notification_channels:
                self.notification_channels[name].enabled = False

        self._save_config()
        logger.info(f"Disabled notification channel: {name}")

    def process_alerts(self):
        """处理告警"""
        # 获取当前触发的告警
        current_alerts = self.monitoring_system.check_alerts()

        with self._lock:
            # 处理新告警
            for alert in current_alerts:
                alert_key = alert["name"]

                if alert_key not in self.active_alerts:
                    # 新告警
                    notification = AlertNotification(
                        alert_name=alert["name"],
                        severity=alert["severity"],
                        message=alert["description"],
                        timestamp=alert["timestamp"],
                        channels=list(self.notification_channels.keys())
                    )

                    self.active_alerts[alert_key] = notification

                    # 发送通知
                    self._send_notifications(notification)

                    logger.warning(f"New alert triggered: {alert['name']} - {alert['description']}")

            # 检查已解决的告警
            resolved_alerts = []
            for alert_key, notification in self.active_alerts.items():
                # 检查告警是否仍然存在
                alert_still_active = any(a["name"] == alert_key for a in current_alerts)

                if not alert_still_active and not notification.resolved:
                    # 告警已解决
                    notification.resolved = True
                    notification.resolved_at = time.time()

                    resolved_alerts.append(alert_key)

                    # 发送解决通知
                    self._send_resolved_notification(notification)

                    logger.info(f"Alert resolved: {alert_key}")

            # 将已解决的告警移到历史记录
            for alert_key in resolved_alerts:
                alert = self.active_alerts.pop(alert_key)
                self.alert_history.append(alert)

                # 保持历史记录大小限制
                if len(self.alert_history) > 1000:
                    self.alert_history = self.alert_history[-1000:]

    def _send_notifications(self, alert: AlertNotification):
        """发送告警通知"""
        for channel_name in alert.channels:
            if channel_name not in self.notification_channels:
                continue

            channel = self.notification_channels[channel_name]
            if not channel.enabled:
                continue

            try:
                if channel.type == "email":
                    self._send_email_notification(channel, alert)
                elif channel.type == "webhook":
                    self._send_webhook_notification(channel, alert)
                elif channel.type == "slack":
                    self._send_slack_notification(channel, alert)
                elif channel.type == "teams":
                    self._send_teams_notification(channel, alert)
                else:
                    logger.warning(f"Unknown notification channel type: {channel.type}")

            except Exception as e:
                logger.error(f"Failed to send notification via {channel_name}: {e}")

    def _send_resolved_notification(self, alert: AlertNotification):
        """发送告警解决通知"""
        resolved_alert = AlertNotification(
            alert_name=alert.alert_name,
            severity="info",
            message=f"Alert resolved: {alert.message}",
            timestamp=alert.resolved_at,
            channels=alert.channels
        )

        self._send_notifications(resolved_alert)

    def _send_email_notification(self, channel: NotificationChannel, alert: AlertNotification):
        """发送邮件通知"""
        config = channel.config

        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = config['from_email']
        msg['To'] = ', '.join(config['to_emails'])
        msg['Subject'] = f"[{alert.severity.upper()}] Holodeck Alert: {alert.alert_name}"

        # 邮件正文
        body = f"""
        Holodeck Alert Notification

        Alert: {alert.alert_name}
        Severity: {alert.severity}
        Message: {alert.message}
        Time: {datetime.fromtimestamp(alert.timestamp)}

        This is an automated notification from Holodeck monitoring system.
        """

        msg.attach(MIMEText(body, 'plain'))

        # 发送邮件
        server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
        server.starttls()
        server.login(config['username'], config['password'])
        server.send_message(msg)
        server.quit()

    def _send_webhook_notification(self, channel: NotificationChannel, alert: AlertNotification):
        """发送Webhook通知"""
        config = channel.config

        payload = {
            "alert": {
                "name": alert.alert_name,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "resolved": alert.resolved
            },
            "system": "holodeck"
        }

        headers = config.get('headers', {})
        headers['Content-Type'] = 'application/json'

        response = requests.post(
            config['url'],
            json=payload,
            headers=headers,
            timeout=10
        )

        if response.status_code not in [200, 201, 204]:
            raise Exception(f"Webhook request failed with status {response.status_code}")

    def _send_slack_notification(self, channel: NotificationChannel, alert: AlertNotification):
        """发送Slack通知"""
        config = channel.config

        # 根据严重程度选择颜色
        colors = {
            "critical": "#ff0000",
            "warning": "#ffaa00",
            "info": "#00aa00"
        }

        payload = {
            "text": f"Holodeck Alert: {alert.alert_name}",
            "attachments": [
                {
                    "color": colors.get(alert.severity, "#808080"),
                    "fields": [
                        {
                            "title": "Alert",
                            "value": alert.alert_name,
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": alert.severity.upper(),
                            "short": True
                        },
                        {
                            "title": "Message",
                            "value": alert.message,
                            "short": False
                        },
                        {
                            "title": "Time",
                            "value": datetime.fromtimestamp(alert.timestamp).isoformat(),
                            "short": True
                        }
                    ]
                }
            ]
        }

        response = requests.post(
            config['webhook_url'],
            json=payload,
            timeout=10
        )

        if response.status_code != 200:
            raise Exception(f"Slack webhook request failed with status {response.status_code}")

    def _send_teams_notification(self, channel: NotificationChannel, alert: AlertNotification):
        """发送Microsoft Teams通知"""
        config = channel.config

        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": self._get_teams_color(alert.severity),
            "summary": f"Holodeck Alert: {alert.alert_name}",
            "sections": [
                {
                    "activityTitle": f"Holodeck Alert: {alert.alert_name}",
                    "activitySubtitle": f"Severity: {alert.severity.upper()}",
                    "text": alert.message,
                    "facts": [
                        {
                            "name": "Alert",
                            "value": alert.alert_name
                        },
                        {
                            "name": "Severity",
                            "value": alert.severity.upper()
                        },
                        {
                            "name": "Time",
                            "value": datetime.fromtimestamp(alert.timestamp).isoformat()
                        }
                    ]
                }
            ]
        }

        response = requests.post(
            config['webhook_url'],
            json=payload,
            timeout=10
        )

        if response.status_code != 200:
            raise Exception(f"Teams webhook request failed with status {response.status_code}")

    def _get_teams_color(self, severity: str) -> str:
        """获取Teams消息颜色"""
        colors = {
            "critical": "ff0000",
            "warning": "ffaa00",
            "info": "00aa00"
        }
        return colors.get(severity, "808080")

    def get_alert_status(self) -> Dict[str, Any]:
        """获取告警状态"""
        with self._lock:
            return {
                "active_alerts": len(self.active_alerts),
                "total_channels": len(self.notification_channels),
                "enabled_channels": sum(1 for c in self.notification_channels.values() if c.enabled),
                "alert_history_count": len(self.alert_history),
                "active_alerts_list": [
                    {
                        "name": alert.alert_name,
                        "severity": alert.severity,
                        "message": alert.message,
                        "timestamp": alert.timestamp,
                        "resolved": alert.resolved
                    }
                    for alert in self.active_alerts.values()
                ]
            }

    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取告警历史"""
        with self._lock:
            return [
                {
                    "name": alert.alert_name,
                    "severity": alert.severity,
                    "message": alert.message,
                    "timestamp": alert.timestamp,
                    "resolved": alert.resolved,
                    "resolved_at": alert.resolved_at
                }
                for alert in self.alert_history[-limit:]
            ]

    def clear_alert_history(self):
        """清除告警历史"""
        with self._lock:
            self.alert_history.clear()

        logger.info("Cleared alert history")

    def test_notification_channel(self, channel_name: str) -> bool:
        """测试通知渠道"""
        if channel_name not in self.notification_channels:
            return False

        channel = self.notification_channels[channel_name]

        # 创建测试告警
        test_alert = AlertNotification(
            alert_name="test_alert",
            severity="info",
            message="This is a test notification from Holodeck monitoring system.",
            timestamp=time.time(),
            channels=[channel_name]
        )

        try:
            self._send_notifications(test_alert)
            logger.info(f"Test notification sent successfully via {channel_name}")
            return True
        except Exception as e:
            logger.error(f"Test notification failed via {channel_name}: {e}")
            return False


# 全局告警管理器实例
alerting_manager = None


def setup_alerting(monitoring_system: MonitoringSystem) -> AlertingManager:
    """设置告警系统"""
    global alerting_manager

    if alerting_manager is None:
        alerting_manager = AlertingManager(monitoring_system)

    return alerting_manager


def get_alerting_manager() -> Optional[AlertingManager]:
    """获取告警管理器实例"""
    return alerting_manager


# 后台告警处理线程
import time

def start_alert_processor(interval: int = 60):
    """启动后台告警处理器"""
    def alert_processor():
        while True:
            try:
                if alerting_manager:
                    alerting_manager.process_alerts()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Alert processor error: {e}")
                time.sleep(interval)

    thread = threading.Thread(target=alert_processor, daemon=True)
    thread.start()

    logger.info(f"Started alert processor with {interval}s interval")