"""
MCP Agent — SHRRI Phase 7
Routes tool calls to connected MCP servers via the singleton MCPManager.
Supports: list tools, call a specific tool on a server.
"""
import logging, re
logger = logging.getLogger(__name__)

class MCPAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "").strip()
        if self.verbose:
            logger.info(f"[mcp_agent] prompt: {prompt!r}")

        from engine.mcp.mcp_client import list_tools_sync, call_tool_sync

        # List tools
        if re.search(r'\blist\b|\btools\b|\bwhat can\b|\bavailable\b', prompt, re.I):
            tools = list_tools_sync()
            if not tools:
                return "No MCP servers connected or no tools available."
            lines = [f"🔧 Available MCP tools ({len(tools)}):"]
            for t in tools:
                lines.append(f"  [{t['server']}] {t['name']} — {t['description']}")
            return "\n".join(lines)

        # Call a tool: expect "server:tool_name arg1=val1 arg2=val2"
        # e.g. "filesystem:read_file path=/home/shrridharshan/shrri/README.md"
        m = re.match(r'(\w+):(\w+)\s*(.*)', prompt, re.DOTALL)
        if m:
            server = m.group(1)
            tool = m.group(2)
            args_str = m.group(3).strip()
            # Parse key=value args
            arguments = {}
            for kv in re.findall(r'(\w+)=("[^"]*"|\S+)', args_str):
                arguments[kv[0]] = kv[1].strip('"')
            if self.verbose:
                logger.info(f"[mcp_agent] calling {server}:{tool} with {arguments}")
            return call_tool_sync(server, tool, arguments)

        return (
            "MCP Agent usage:\n"
            "  List tools: /goal mcp: list tools\n"
            "  Call tool:  /goal mcp: server:tool_name key=value"
        )
