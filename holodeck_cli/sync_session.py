"""
同步Session包装器

为异步SessionManager提供同步接口。
"""

import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

from holodeck_cli.config import config
from holodeck_cli.utils import save_json, load_json

try:
    from holodeck_core.storage.session_manager import SessionManager
    from holodeck_core.schemas import Session, SessionRequest
except ImportError as e:
    print(f"错误: 无法导入holodeck_core模块: {e}")
    raise


class SyncSessionManager:
    """同步会话管理器"""

    def __init__(self, workspace_path: Optional[Path] = None):
        self.workspace_path = workspace_path or config.get_workspace_path()
        self.async_manager = SessionManager(str(self.workspace_path))

    def _run_async(self, coro):
        """运行异步函数"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

    def create_session(self, session_id: Optional[str], request_data: Dict[str, Any]) -> str:
        """创建会话"""

        # 如果没有提供session_id，生成一个新的
        if not session_id:
            timestamp = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
            unique_id = __import__('uuid').uuid4().hex[:8]
            session_id = f"{timestamp}_{unique_id}"

        # 创建SessionRequest对象
        request = SessionRequest(**request_data)

        # 异步创建会话
        session_id = self._run_async(self.async_manager.create_session(request))

        # 保存request.json文件
        session_dir = self.workspace_path / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        request_path = session_dir / "request.json"
        save_json(request_data, request_path)

        return session_id

    def load_session(self, session_id: str):
        """加载会话"""
        session_data = self._run_async(self.async_manager.load_session(session_id))
        if session_data:
            return SyncSession(session_id, session_data, self.workspace_path)
        return None


class SyncSession:
    """同步会话包装器"""

    def __init__(self, session_id: str, session_data: Dict[str, Any], workspace_path: Path):
        self.session_id = session_id
        self.session_data = session_data
        self.workspace_path = workspace_path
        self.session_dir = workspace_path / "sessions" / session_id

    def get_session_dir(self) -> Path:
        """获取会话目录"""
        return self.session_dir

    def get_request_path(self) -> Path:
        """获取请求文件路径"""
        return self.session_dir / "request.json"

    def get_scene_ref_path(self) -> Path:
        """获取场景参考图路径"""
        return self.session_dir / "scene_ref.png"

    def get_objects_path(self) -> Path:
        """获取对象文件路径"""
        return self.session_dir / "objects.json"

    def get_object_cards_dir(self) -> Path:
        """获取对象卡片目录"""
        return self.session_dir / "object_cards"

    def get_constraints_path(self, version: str = "v1") -> Path:
        """获取约束文件路径"""
        return self.session_dir / f"constraints_{version}.json"

    def get_layout_solution_path(self, version: str = "v1") -> Path:
        """获取布局解决方案路径"""
        return self.session_dir / f"layout_solution_{version}.json"

    def get_dfs_trace_path(self, version: str = "v1") -> Path:
        """获取DFS轨迹路径"""
        return self.session_dir / f"dfs_trace_{version}.json"

    def get_blend_path(self) -> Path:
        """获取Blender文件路径"""
        return self.session_dir / "blender_scene.blend"

    def get_renders_dir(self) -> Path:
        """获取渲染目录"""
        return self.session_dir / "renders"

    def load_request(self) -> Dict[str, Any]:
        """加载请求数据"""
        return load_json(self.get_request_path())

    def load_objects(self) -> Dict[str, Any]:
        """加载对象数据"""
        return load_json(self.get_objects_path())

    def load_layout_solution(self, version: str = "v1") -> Dict[str, Any]:
        """加载布局解决方案"""
        return load_json(self.get_layout_solution_path(version))