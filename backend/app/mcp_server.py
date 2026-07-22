import sys
import os
import asyncio
import json
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from sqlalchemy.future import select
from sentence_transformers import SentenceTransformer

# Add app to path if executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker
from app.models.meeting import Meeting
from app.models.meeting_chunk import MeetingChunk
from app.models.action_item import ActionItem

server = Server("referat-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for the AI agent."""
    return [
        types.Tool(
            name="search_meetings",
            description="Semantically search across all recorded meetings using a natural language query. Best for answering questions about previous conversations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query, e.g., 'What did we decide about the Q3 budget?'"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of matched segments to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_meeting_summary",
            description="Retrieve the metadata, full Danish summary/minutes, and transcripts of a specific meeting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "meeting_id": {
                        "type": "integer",
                        "description": "The unique database ID of the meeting"
                    }
                },
                "required": ["meeting_id"]
            }
        ),
        types.Tool(
            name="get_action_items",
            description="Retrieve all extracted action items and tasks associated with a specific meeting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "meeting_id": {
                        "type": "integer",
                        "description": "The unique database ID of the meeting"
                    }
                },
                "required": ["meeting_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict
) -> list[types.TextContent]:
    """Execute the requested tool."""
    if name == "search_meetings":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)

        if not query.strip():
            return [types.TextContent(type="text", text="Empty query provided.")]

        try:
            # Load local model and embed the query
            model = SentenceTransformer("all-MiniLM-L6-v2")
            query_vector = model.encode(query).tolist()

            async with async_session_maker() as session:
                distance_expr = MeetingChunk.embedding.cosine_distance(query_vector)
                similarity_expr = 1.0 - distance_expr

                stmt = (
                    select(
                        MeetingChunk,
                        Meeting.title.label("meeting_title"),
                        similarity_expr.label("similarity")
                    )
                    .join(Meeting, Meeting.id == MeetingChunk.meeting_id)
                    .order_by(distance_expr.asc())
                    .limit(limit)
                )

                result = await session.execute(stmt)
                matches = []

                for row in result.all():
                    chunk = row[0]
                    meeting_title = row[1]
                    similarity = row[2]

                    if similarity >= 0.25:
                        matches.append({
                            "meeting_id": chunk.meeting_id,
                            "meeting_title": meeting_title,
                            "timestamp": f"{int(chunk.start_time // 60)}:{int(chunk.start_time % 60):02d}",
                            "text": chunk.text,
                            "similarity": f"{float(similarity)*100:.0f}%"
                        })

                if not matches:
                    return [types.TextContent(type="text", text="No relevant meeting segments found.")]

                return [types.TextContent(type="text", text=json.dumps(matches, indent=2, ensure_ascii=False))]

        except Exception as e:
            return [types.TextContent(type="text", text=f"Error executing search: {str(e)}")]

    elif name == "get_meeting_summary":
        meeting_id = arguments.get("meeting_id")
        try:
            async with async_session_maker() as session:
                result = await session.execute(select(Meeting).filter(Meeting.id == meeting_id))
                meeting = result.scalars().first()
                if not meeting:
                    return [types.TextContent(type="text", text=f"Meeting with ID {meeting_id} not found.")]

                meeting_data = {
                    "id": meeting.id,
                    "title": meeting.title,
                    "date": meeting.date.isoformat(),
                    "status": meeting.status,
                    "summary": meeting.summary,
                    "transcript_clean_snippet": meeting.transcript_clean[:2000] + "..." if meeting.transcript_clean else None
                }
                return [types.TextContent(type="text", text=json.dumps(meeting_data, indent=2, ensure_ascii=False))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    elif name == "get_action_items":
        meeting_id = arguments.get("meeting_id")
        try:
            async with async_session_maker() as session:
                result = await session.execute(select(ActionItem).filter(ActionItem.meeting_id == meeting_id))
                items = result.scalars().all()
                
                action_items = []
                for item in items:
                    action_items.append({
                        "id": item.id,
                        "task": item.task,
                        "assignee": item.assignee,
                        "deadline": item.deadline
                    })
                return [types.TextContent(type="text", text=json.dumps(action_items, indent=2, ensure_ascii=False))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_file_stream):
        await server.run(
            read_stream,
            write_file_stream,
            InitializationOptions(
                server_name="referat-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
