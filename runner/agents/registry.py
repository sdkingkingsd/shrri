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


def build_manager(verbose: bool = False) -> ManagerAgent:
    manager = ManagerAgent(verbose=verbose)

    research = ResearchAgent(verbose=verbose)
    coding = CodingAgent(verbose=verbose)
    browser = BrowserAgent(verbose=verbose)
    vision = VisionAgent(verbose=verbose)

    manager.register_agent("research", research.run)
    manager.register_agent("code", coding.run)
    manager.register_agent("coding", coding.run)  # accept both names
    manager.register_agent("browse", browser.run)
    manager.register_agent("browser", browser.run)
    manager.register_agent("vision", vision.run)
    # "llm_call" (default, used by GoalPlanner for plain steps) already
    # has a built-in handler in ExecutionScheduler — no registration needed.

    return manager
