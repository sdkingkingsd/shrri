#!/usr/bin/env python3
"""
SHRRI Gmail MCP Server
Exposes Gmail as an MCP server so other agents/tools can call it
Run: python3 ~/shrri/tools/gmail_mcp.py
"""
import sys, os
sys.path.insert(0, '/home/shrridharshan/shrri')

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SHRRI Gmail")

@mcp.tool()
def read_emails(max_results: int = 5, query: str = "is:unread") -> str:
    """Read emails from Gmail inbox"""
    from tools.gmail import read_emails as _read
    return _read(max_results=max_results, query=query)

@mcp.tool()
def search_emails(query: str, max_results: int = 5) -> str:
    """Search Gmail for specific emails"""
    from tools.gmail import search_emails as _search
    return _search(query=query, max_results=max_results)

@mcp.tool()
def read_email_body(query: str) -> str:
    """Read full body of a specific email by subject/sender keyword"""
    from tools.gmail import read_email_body as _body
    return _body(query=query)

@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email"""
    from tools.gmail import send_email as _send
    return _send(to=to, subject=subject, body=body)

@mcp.tool()
def reply_email(message_id: str, reply_body: str) -> str:
    """Reply to an email by message ID"""
    from tools.gmail import reply_email as _reply
    return _reply(message_id=message_id, reply_body=reply_body)

@mcp.tool()
def archive_email(message_id: str) -> str:
    """Archive an email by message ID"""
    from tools.gmail import archive_email as _archive
    return _archive(message_id=message_id)

@mcp.tool()
def delete_email(message_id: str) -> str:
    """Move an email to trash"""
    from tools.gmail import delete_email as _delete
    return _delete(message_id=message_id)

@mcp.tool()
def mark_as_read(message_id: str) -> str:
    """Mark an email as read"""
    from tools.gmail import mark_as_read as _mark
    return _mark(message_id=message_id)

@mcp.tool()
def save_draft(to: str, subject: str, body: str) -> str:
    """Save an email as draft"""
    from tools.gmail import save_draft as _draft
    return _draft(to=to, subject=subject, body=body)

@mcp.tool()
def download_attachments(message_id: str, save_dir: str = "~/Downloads") -> str:
    """Download attachments from an email"""
    from tools.gmail import download_attachments as _att
    return _att(message_id=message_id, save_dir=save_dir)

@mcp.tool()
def list_recent_emails(max_results: int = 10) -> str:
    """List recent emails with IDs for use with other tools"""
    from tools.gmail import list_recent_subjects
    subjects = list_recent_subjects(max_results=max_results)
    if not subjects:
        return "No recent emails found."
    lines = [f"{i}. ID:{s['id']} | From:{s['sender']} | Subject:{s['subject']}" 
             for i, s in enumerate(subjects)]
    return "\n".join(lines)

if __name__ == "__main__":
    print("[gmail_mcp] Starting SHRRI Gmail MCP server...")
    mcp.run(transport="stdio")
