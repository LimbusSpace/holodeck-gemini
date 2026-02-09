"""MCP client for communicating with external MCP servers."""

import json
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class MCPToolClient:
    """Client for calling MCP tools from external servers."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._tool_registry = {}

    def register_tool(self, tool_name: str, tool_function: Callable) -> None:
        """Register a tool function for calling."""
        self._tool_registry[tool_name] = tool_function
        self.logger.info(f"Registered MCP tool: {tool_name}")

    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call a registered MCP tool."""
        if tool_name not in self._tool_registry:
            raise ValueError(f"MCP tool not registered: {tool_name}")

        try:
            tool_func = self._tool_registry[tool_name]
            result = tool_func(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            self.logger.error(f"MCP tool call failed: {tool_name} - {e}")
            return {"success": False, "error": str(e)}


# Global MCP client instance
_mcp_client = MCPToolClient()


def get_mcp_client() -> MCPToolClient:
    """Get the global MCP client instance."""
    return _mcp_client
