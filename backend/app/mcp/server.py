"""MCP Server for LearnFlow.

Tools:
- add_card_draft: Add a card draft for user approval
- list_topics: List all topics with stats
- get_learning_status: Current learning state
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("learnflow")


@mcp.tool()
async def add_card_draft(
    topic_name: str,
    card_type: str,
    front_content: str,
    back_content: str,
    metadata: str | None = None,
) -> str:
    """Add a card draft to a topic for user approval.
    
    Args:
        topic_name: Name of the topic (will be created if doesn't exist)
        card_type: One of: term, command, procedure
        front_content: The question/term/task
        back_content: The answer/definition/solution
        metadata: Optional JSON metadata
    """
    # Implementation in MCP server handler
    return f"Card draft added to topic '{topic_name}'"


@mcp.tool()
async def list_topics() -> str:
    """List all learning topics with progress stats."""
    return "Topics list"


@mcp.tool()
async def get_learning_status() -> str:
    """Get current learning status: active card, progress, due reviews."""
    return "Learning status"
