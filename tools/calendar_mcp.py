#!/usr/bin/env python3
"""SHRRI Google Calendar MCP Server"""
import sys
sys.path.insert(0, '/home/shrridharshan/shrri')
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SHRRI Calendar")

@mcp.tool()
def get_today_events() -> str:
    """Get today's calendar events"""
    from tools.calendar_tool import get_today_events as _f
    return _f()

@mcp.tool()
def get_upcoming_events(days: int = 7) -> str:
    """Get upcoming events for next N days"""
    from tools.calendar_tool import get_upcoming_events as _f
    return _f(days=days)

@mcp.tool()
def search_events(query: str) -> str:
    """Search calendar events by keyword"""
    from tools.calendar_tool import search_events as _f
    return _f(query)

@mcp.tool()
def create_event(title: str, date_str: str, time_str: str, duration_hours: float = 1.0, location: str = "", description: str = "") -> str:
    """Create a calendar event"""
    from tools.calendar_tool import create_event_full as _f
    return _f(title, date_str, time_str, duration_hours, location, description)

@mcp.tool()
def create_recurring_event(title: str, date_str: str, time_str: str, recurrence: str = "weekly", count: int = 4, location: str = "") -> str:
    """Create a recurring calendar event (daily/weekly/monthly)"""
    from tools.calendar_tool import create_recurring_event as _f
    return _f(title, date_str, time_str, recurrence, count, location)

@mcp.tool()
def delete_event(query: str) -> str:
    """Delete a calendar event by keyword"""
    from tools.calendar_tool import delete_event as _f
    return _f(query)

@mcp.tool()
def update_event(query: str, new_title: str = "", new_time: str = "", new_location: str = "") -> str:
    """Update an existing calendar event"""
    from tools.calendar_tool import update_event as _f
    return _f(query, new_title=new_title, new_time=new_time, new_location=new_location)

if __name__ == "__main__":
    print("[calendar_mcp] Starting SHRRI Calendar MCP server...")
    mcp.run(transport="stdio")
