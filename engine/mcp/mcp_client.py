"""
mcp_client.py - MCP client manager for SHRRI.
Connects to configured MCP servers (stdio-based), discovers their tools,
and lets SHRRI call them like any other tool.
"""
import asyncio
import json
import os
from contextlib import AsyncExitStack

MCP_CONFIG_FILE = os.path.expanduser("~/.shrri/mcp_servers.json")

FILESYSTEM_DEFAULT = {
    "name": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem",
              os.path.expanduser("~/shrri/mcp_sandbox")],
    "description": "SHRRI filesystem sandbox MCP server",
    "enabled": True
}


def _load_config():
    """Load existing ~/.shrri/mcp_servers.json (list format with 'name' key per
    server) and normalize it into a dict keyed by server name. Adds the
    filesystem sandbox server if it is not already present, without
    touching any existing entries (e.g. gmail)."""
    if not os.path.exists(MCP_CONFIG_FILE):
        os.makedirs(os.path.dirname(MCP_CONFIG_FILE), exist_ok=True)
        raw = {"servers": [FILESYSTEM_DEFAULT]}
        with open(MCP_CONFIG_FILE, "w") as f:
            json.dump(raw, f, indent=2)
    else:
        with open(MCP_CONFIG_FILE) as f:
            raw = json.load(f)

    servers_list = raw.get("servers", [])
    names = {s.get("name") for s in servers_list}
    if "filesystem" not in names:
        servers_list.append(FILESYSTEM_DEFAULT)
        raw["servers"] = servers_list
        with open(MCP_CONFIG_FILE, "w") as f:
            json.dump(raw, f, indent=2)

    servers_dict = {}
    for s in servers_list:
        name = s.get("name")
        if not name:
            continue
        servers_dict[name] = {
            "command": s.get("command"),
            "args": s.get("args", []),
            "env": s.get("env"),
            "enabled": s.get("enabled", True)
        }
    return {"servers": servers_dict}


class MCPManager:
    """Holds live connections to MCP servers and routes tool calls."""

    def __init__(self):
        self.config = _load_config()
        self.sessions = {}      # server_name -> ClientSession
        self.tools_by_server = {}  # server_name -> [tool_def, ...]
        self._stack = None
        self._connected = False

    async def connect_all(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        self._stack = AsyncExitStack()
        for name, cfg in self.config.get("servers", {}).items():
            if not cfg.get("enabled", True):
                continue
            try:
                params = StdioServerParameters(
                    command=cfg["command"],
                    args=cfg.get("args", []),
                    env=cfg.get("env")
                )
                read, write = await self._stack.enter_async_context(stdio_client(params))
                session = await self._stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                tools_result = await session.list_tools()
                self.sessions[name] = session
                self.tools_by_server[name] = tools_result.tools
                print(f"[mcp] Connected to '{name}' — {len(tools_result.tools)} tools")
            except Exception as e:
                print(f"[mcp] Failed to connect to '{name}': {e}")
        self._connected = True

    async def disconnect_all(self):
        if self._stack:
            await self._stack.aclose()
        self.sessions = {}
        self.tools_by_server = {}
        self._connected = False

    def list_all_tools(self):
        """Returns flat list of (server_name, tool_name, description) for all connected tools."""
        out = []
        for server, tools in self.tools_by_server.items():
            for t in tools:
                out.append({"server": server, "name": t.name, "description": t.description})
        return out

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict):
        session = self.sessions.get(server_name)
        if not session:
            return f"GAP: MCP server '{server_name}' not connected."
        try:
            result = await session.call_tool(tool_name, arguments=arguments)
            parts = []
            for c in result.content:
                if hasattr(c, "text"):
                    parts.append(c.text)
            return "\n".join(parts) if parts else "GAP: empty MCP tool result."
        except Exception as e:
            return f"GAP: MCP tool call failed — {e}"


def run_async(coro):
    """Run an async coroutine from sync code, handling existing event loops."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ── Singleton + thread-safe access for persistent background connection ──
_manager = None
_manager_loop = None


def get_manager():
    global _manager
    if _manager is None:
        _manager = MCPManager()
    return _manager


async def _startup_connect():
    """Called once from the bot's own event loop at startup."""
    global _manager_loop
    mgr = get_manager()
    await mgr.connect_all()
    _manager_loop = asyncio.get_event_loop()
    return mgr


def call_tool_sync(server_name: str, tool_name: str, arguments: dict, timeout: float = 15.0):
    """Call an MCP tool from sync code (e.g. the dispatcher), routing the
    actual call into the persistent connection's event loop safely."""
    global _manager_loop, _manager
    if _manager is None or _manager_loop is None:
        return "GAP: MCP not connected yet."
    try:
        fut = asyncio.run_coroutine_threadsafe(
            _manager.call_tool(server_name, tool_name, arguments), _manager_loop
        )
        return fut.result(timeout=timeout)
    except Exception as e:
        return f"GAP: MCP call failed — {e}"


def list_tools_sync():
    global _manager
    if _manager is None:
        return []
    return _manager.list_all_tools()
