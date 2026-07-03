"""
Agent Registry — SHRRI AI OS v2 (Phase 5)

Central place that builds a ManagerAgent with every specialist agent
registered. Used by any entry point (Telegram, WhatsApp, CLI, etc.)
that wants the full multi-agent system, so registration logic lives
in exactly one place instead of being copy-pasted per channel.
"""

from runner.agents.manager_agent import ManagerAgent
from runner.agents.research_agent import ResearchAgent
from runner.agents.coding_agent import CodingAgent
from runner.agents.browser_agent import BrowserAgent
from runner.agents.vision_agent import VisionAgent
from runner.agents.memory_agent import MemoryAgent
from runner.agents.automation_agent import AutomationAgent
from runner.agents.security_agent import SecurityAgent
from runner.agents.testing_agent import TestingAgent
from runner.agents.documentation_agent import DocumentationAgent
from runner.agents.linux_agent import LinuxAgent
from runner.agents.android_agent import AndroidAgent
from runner.agents.github_agent import GitHubAgent
from runner.agents.calendar_agent import CalendarAgent
from runner.agents.email_agent import EmailAgent
from runner.agents.finance_agent import FinanceAgent
from runner.agents.iot_agent import IoTAgent
from runner.agents.consensus_agent import ConsensusAgent
from runner.agents.weather_agent import WeatherAgent
from runner.agents.maps_agent import MapsAgent
from runner.agents.files_agent import FilesAgent
from runner.agents.sqlite_agent import SQLiteAgent
from runner.agents.mcp_agent import MCPAgent


def build_manager(verbose: bool = False) -> ManagerAgent:
    manager = ManagerAgent(verbose=verbose)

    research = ResearchAgent(verbose=verbose)
    coding = CodingAgent(verbose=verbose)
    browser = BrowserAgent(verbose=verbose)
    vision = VisionAgent(verbose=verbose)
    memory = MemoryAgent(verbose=verbose)
    automation = AutomationAgent(verbose=verbose)
    security = SecurityAgent(verbose=verbose)
    testing = TestingAgent(verbose=verbose)
    documentation = DocumentationAgent(verbose=verbose)
    linux = LinuxAgent(verbose=verbose)
    android = AndroidAgent(verbose=verbose)
    github = GitHubAgent(verbose=verbose)
    calendar = CalendarAgent(verbose=verbose)
    email = EmailAgent(verbose=verbose)
    finance = FinanceAgent(verbose=verbose)
    iot = IoTAgent(verbose=verbose)
    consensus = ConsensusAgent(verbose=verbose)
    weather = WeatherAgent(verbose=verbose)
    maps = MapsAgent(verbose=verbose)
    files = FilesAgent(verbose=verbose)
    sqlite = SQLiteAgent(verbose=verbose)
    mcp = MCPAgent(verbose=verbose)

    manager.register_agent("research", research.run)
    manager.register_agent("code", coding.run)
    manager.register_agent("coding", coding.run)  # accept both names
    manager.register_agent("browse", browser.run)
    manager.register_agent("browser", browser.run)
    manager.register_agent("vision", vision.run)
    manager.register_agent("memory", memory.run)
    manager.register_agent("remember", memory.run)  # accept both names
    manager.register_agent("recall", memory.run)
    manager.register_agent("automation", automation.run)
    manager.register_agent("reminder", automation.run)  # accept both names
    manager.register_agent("schedule", automation.run)
    manager.register_agent("security", security.run)
    manager.register_agent("testing", testing.run)
    manager.register_agent("test", testing.run)  # accept both names
    manager.register_agent("documentation", documentation.run)
    manager.register_agent("docs", documentation.run)  # accept both names
    manager.register_agent("linux", linux.run)
    manager.register_agent("system", linux.run)  # accept both names
    manager.register_agent("android", android.run)
    manager.register_agent("github", github.run)
    manager.register_agent("calendar", calendar.run)
    manager.register_agent("email", email.run)
    manager.register_agent("gmail", email.run)  # accept both names
    manager.register_agent("finance", finance.run)
    manager.register_agent("iot", iot.run)
    manager.register_agent("consensus", consensus.run)
    manager.register_agent("weather", weather.run)
    manager.register_agent("maps", maps.run)
    manager.register_agent("files", files.run)
    manager.register_agent("file", files.run)
    manager.register_agent("sqlite", sqlite.run)
    manager.register_agent("db", sqlite.run)
    manager.register_agent("mcp", mcp.run)
    # "llm_call" (default, used by GoalPlanner for plain steps) already
    # has a built-in handler in ExecutionScheduler — no registration needed.

    from runner.dynamic_agent_factory import load_dynamic_agents
    loaded = load_dynamic_agents(manager)
    if loaded:
        print(f"[registry] auto-loaded {loaded} dynamic agent(s)")
    return manager
