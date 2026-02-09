"""
通用工具函数
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional


def ensure_dir(path: Path) -> Path:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(file_path: Path) -> Dict[str, Any]:
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"无法加载JSON文件 {file_path}: {e}")


def save_json(data: Dict[str, Any], file_path: Path) -> None:
    """保存JSON文件"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"无法保存JSON文件 {file_path}: {e}")

