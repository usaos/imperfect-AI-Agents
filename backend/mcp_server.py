import asyncio
import json
import os
import requests
from mcp.server import Server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv

load_dotenv()

# 后端API地址，默认本地Docker部署地址
API_BASE = os.getenv("IMPERFECT_API_BASE", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")

app = Server("imperfect-memory")

def _api_request(path: str, payload: dict):
    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    try:
        resp = requests.post(f"{API_BASE}{path}", json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_scars",
            description="Search historical Agent failure cases and corrections. Use BEFORE executing complex tasks to avoid known pitfalls.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Task or problem description"},
                    "limit": {"type": "integer", "description": "Max results to return", "default": 3},
                    "detail_level": {
                        "type": "string",
                        "enum": ["low", "high"],
                        "description": "'low' saves tokens, 'high' returns full context",
                        "default": "low"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="reflect_and_log",
            description="Log a failure with your reflection and fix. Contributes to the global immune system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task description"},
                    "failure_action": {"type": "string", "description": "What you tried that failed"},
                    "failure_error": {"type": "string", "description": "Exact error message"},
                    "reflection_analysis": {"type": "string", "description": "Why did it fail?"},
                    "corrected_action": {"type": "string", "description": "How to fix it correctly?"},
                    "uncertainty_score": {"type": "number", "minimum": 0, "maximum": 1, "description": "How sure are you about the fix? 0=certain"},
                    "pre_condition": {"type": "string", "description": "Environment/context when failure happened"},
                    "tags": {"type": "string", "description": "Comma-separated tags"}
                },
                "required": ["task", "failure_error", "reflection_analysis", "corrected_action"]
            }
        ),
        Tool(
            name="query_uncertain",
            description="Search high-uncertainty 'lucky success' cases for post-task review.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Task keyword"},
                    "limit": {"type": "integer", "default": 3}
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_scars":
        result = _api_request("/api/scars/search", {
            "query": arguments["query"],
            "limit": arguments.get("limit", 3)
        })
        
        if "error" in result:
            return [TextContent(type="text", text=f"Search failed: {result['error']}")]
        
        results = result.get("results", [])
        detail_level = arguments.get("detail_level", "low")
        
        output = "=== Historical Scar Report (Avoid these pitfalls) ===\n"
        if not results:
            output += "No historical scars found. You are exploring uncharted territory. Proceed with caution.\n"
        else:
            for i, scar in enumerate(results, 1):
                if detail_level == "low":
                    # 省Token模式：只输出核心反思和修复方案
                    output += f"[{i}] Task: {scar['task']}\n"
                    output += f"    ▸ Pitfall: {scar['reflection_analysis']}\n"
                    output += f"    ▸ Fix: {scar['corrected_action']}\n"
                    if scar.get("pre_condition"):
                        output += f"    ▸ Context: {scar['pre_condition']}\n"
                    output += "\n"
                else:
                    # 完整模式
                    output += f"[Case {i}] Similarity: {scar['similarity']}\n"
                    output += f"▸ Task: {scar['task']}\n"
                    output += f"▸ Pre-condition: {scar['pre_condition']}\n"
                    output += f"▸ Failed action: {scar['failure_action']}\n"
                    output += f"▸ Error: {scar['failure_error']}\n"
                    output += f"▸ Reflection: {scar['reflection_analysis']}\n"
                    output += f"▸ Correction: {scar['corrected_action']}\n"
                    output += f"▸ Uncertainty: {scar['uncertainty_score']}\n\n"
                    
        return [TextContent(type="text", text=output)]

    elif name == "reflect_and_log":
        result = _api_request("/api/scars/log", {
            "task": arguments["task"],
            "failure_action": arguments.get("failure_action", "N/A"),
            "failure_error": arguments["failure_error"],
            "reflection_analysis": arguments["reflection_analysis"],
            "corrected_action": arguments["corrected_action"],
            "uncertainty_score": arguments.get("uncertainty_score", 0.5),
            "pre_condition": arguments.get("pre_condition", ""),
            "tags": arguments.get("tags", ""),
            "source_platform": "claude_mcp"
        })
        
        if "error" in result:
            return [TextContent(type="text", text=f"Log failed: {result['error']}")]
        
        if result.get("status") == "success":
            return [TextContent(
                type="text",
                text=f"Scar #{result['scar_id']} logged to global immune system. +5 credit. Thank you for contributing."
            )]
        else:
            return [TextContent(type="text", text="Submission rejected: duplicate detected.")]

    elif name == "query_uncertain":
        # 复用搜索接口，前端过滤高不确定度
        result = _api_request("/api/scars/search", {
            "query": arguments["query"],
            "limit": arguments.get("limit", 5)
        })
        
        if "error" in result:
            return [TextContent(type="text", text=f"Query failed: {result['error']}")]
        
        high_uncertain = [s for s in result.get("results", []) if s["uncertainty_score"] > 0.6]
        output = "=== High-Uncertainty Lucky Success Cases ===\n"
        if not high_uncertain:
            output += "No high-uncertainty cases found for this task.\n"
        else:
            for i, scar in enumerate(high_uncertain[:arguments.get("limit", 3)], 1):
                output += f"[{i}] {scar['task']}\n"
                output += f"    Uncertainty: {scar['uncertainty_score']}\n"
                output += f"    Action: {scar['corrected_action']}\n\n"
        return [TextContent(type="text", text=output)]

    raise ValueError(f"Unknown tool: {name}")

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
