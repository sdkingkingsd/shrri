import sys
import os

# So we can import tools/ from the main shrri folder
sys.path.insert(0, os.path.expanduser("~/shrri"))

from mcp.server.fastmcp import FastMCP
from tools.whatsapp_tool import (
    send_whatsapp_confirmed,
    reply_to_message,
    delete_last_message,
    forward_message,
    bridge_health,
)

mcp = FastMCP("shrri-whatsapp")

@mcp.tool()
def send_whatsapp(contact: str, text: str) -> str:
    """Send a WhatsApp message to a contact by name or saved number."""
    return send_whatsapp_confirmed(contact, text)

@mcp.tool()
def whatsapp_reply(contact: str, reply_text: str) -> str:
    """Reply to the most recent WhatsApp message from a contact."""
    return reply_to_message(contact, reply_text)

@mcp.tool()
def whatsapp_delete_last(contact: str) -> str:
    """Delete the last WhatsApp message sent to a contact."""
    return delete_last_message(contact)

@mcp.tool()
def whatsapp_forward(from_contact: str, to_contact: str) -> str:
    """Forward the last message from one WhatsApp contact to another."""
    return forward_message(from_contact, to_contact)

@mcp.tool()
def whatsapp_status() -> dict:
    """Check if the WhatsApp bridge/connection is alive and healthy."""
    return bridge_health()

if __name__ == "__main__":
    mcp.run(transport="stdio")
