"""MCP server for decomp.me API interactions."""

import asyncio
import json
import logging
from typing import Any
from urllib.parse import urlparse

import httpx
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("decomp-mcp")

# Base API URL
DECOMP_API_BASE = "https://decomp.me/api"

# Create server instance
app = Server("decomp-mcp-server")


def extract_slug_from_url(url_or_slug: str) -> str:
    """Extract slug from a decomp.me URL or return the slug if already provided."""
    if url_or_slug.startswith("http"):
        parsed = urlparse(url_or_slug)
        parts = parsed.path.strip("/").split("/")
        if "scratch" in parts:
            idx = parts.index("scratch")
            if idx + 1 < len(parts):
                return parts[idx + 1]
    return url_or_slug


def format_scratch_info(scratch: dict[str, Any]) -> str:
    """Format scratch information for display."""
    lines = [
        f"# Scratch: {scratch.get('name', 'Unnamed')} ({scratch['slug']})",
        f"",
        f"**Platform:** {scratch['platform']}",
        f"**Compiler:** {scratch['compiler']}",
        f"**Language:** {scratch.get('language', 'Unknown')}",
        f"**Score:** {scratch.get('score', 0)} / {scratch.get('max_score', 0)}",
    ]

    if scratch.get('description'):
        lines.extend([f"", f"**Description:** {scratch['description']}"])

    lines.extend([
        f"",
        f"**Compiler Flags:**",
        f"```",
        scratch.get('compiler_flags', ''),
        f"```",
        f"",
        f"**Source Code:**",
        f"```c",
        scratch.get('source_code', ''),
        f"```",
    ])

    return "\n".join(lines)


def format_diff_output(diff_data: dict[str, Any]) -> str:
    """Format diff output for display."""
    current_score = diff_data.get('current_score', 0)
    max_score = diff_data.get('max_score', 0)

    lines = [
        f"# Compilation Result",
        f"",
        f"**Diff Score:** {current_score} / {max_score}",
    ]

    if current_score == 0:
        lines.append(f"✅ **PERFECT MATCH!**")
    else:
        match_pct = ((max_score - current_score) / max_score * 100) if max_score > 0 else 0
        lines.append(f"📊 **Match:** {match_pct:.1f}%")

    lines.extend([f"", f"## Assembly Diff", f""])

    # Format the diff rows
    rows = diff_data.get('rows', [])
    if rows:
        lines.append("```diff")
        for row in rows[:50]:  # Limit to first 50 rows to avoid overwhelming output
            base = row.get('base', {})
            current = row.get('current', {})

            # Extract text from base
            base_text_parts = base.get('text', [])
            if isinstance(base_text_parts, list):
                base_text = ''.join(part.get('text', '') if isinstance(part, dict) else str(part) for part in base_text_parts)
            else:
                base_text = str(base_text_parts)

            # Extract text from current
            current_text_parts = current.get('text', [])
            if isinstance(current_text_parts, list):
                current_text = ''.join(part.get('text', '') if isinstance(part, dict) else str(part) for part in current_text_parts)
            else:
                current_text = str(current_text_parts)

            # Determine diff type
            if base_text and not current_text.strip():
                lines.append(f"- {base_text}")
            elif not base_text.strip() and current_text:
                lines.append(f"+ {current_text}")
            elif base_text == current_text:
                lines.append(f"  {base_text}")
            else:
                if base_text.strip():
                    lines.append(f"- {base_text}")
                if current_text.strip():
                    lines.append(f"+ {current_text}")

        if len(rows) > 50:
            lines.append(f"... ({len(rows) - 50} more rows)")

        lines.append("```")

    return "\n".join(lines)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="decomp_get_scratch",
            description=(
                "Fetch a scratch from decomp.me by URL or slug. "
                "Returns all information including source code, target assembly, "
                "compiler settings, context (headers), and current match score."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url_or_slug": {
                        "type": "string",
                        "description": "The decomp.me scratch URL (e.g., https://decomp.me/scratch/Jwtky) or just the slug (e.g., Jwtky)",
                    },
                },
                "required": ["url_or_slug"],
            },
        ),
        Tool(
            name="decomp_compile",
            description=(
                "Compile source code for a scratch and get the diff output showing "
                "how closely it matches the target assembly. Returns the score and "
                "a detailed assembly diff. You can either provide a slug to compile "
                "the existing source, or provide modified source_code to test changes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url_or_slug": {
                        "type": "string",
                        "description": "The decomp.me scratch URL or slug",
                    },
                    "source_code": {
                        "type": "string",
                        "description": "Optional: Modified source code to compile. If not provided, compiles the current source code from the scratch.",
                    },
                },
                "required": ["url_or_slug"],
            },
        ),
        Tool(
            name="decomp_get_compilers",
            description="List all available compilers and their configurations for a specific platform (e.g., gc_wii, n64, ps1).",
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "Platform ID (e.g., gc_wii, n64, ps1, ps2, switch). Leave empty to list all platforms and compilers.",
                    },
                },
            },
        ),
        Tool(
            name="decomp_search",
            description="Search for scratches and presets on decomp.me by query string, platform, compiler, or other criteria. Returns both project presets and individual scratches. Can filter scratches for incomplete/unmatched ones.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (searches in name, description, and other fields)",
                    },
                    "platform": {
                        "type": "string",
                        "description": "Filter by platform (e.g., gc_wii, n64)",
                    },
                    "only_incomplete": {
                        "type": "boolean",
                        "description": "Only show scratches that aren't perfectly matched (score > 0)",
                        "default": False,
                    },
                    "min_match_percent": {
                        "type": "number",
                        "description": "Minimum match percentage (0-100). E.g., 50 shows scratches that are at least 50% matched",
                    },
                    "max_match_percent": {
                        "type": "number",
                        "description": "Maximum match percentage (0-100). E.g., 90 shows scratches that are at most 90% matched",
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sort results by: 'match_percent' (closest to matching), 'last_updated' (most recent), 'creation_time' (newest)",
                        "enum": ["match_percent", "last_updated", "creation_time"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                },
            },
        ),
        Tool(
            name="decomp_search_context",
            description=(
                "Search through the context (header files) of a scratch for type definitions, "
                "struct definitions, function declarations, or other patterns. Useful for finding "
                "the correct types for variables in decompilation work."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url_or_slug": {
                        "type": "string",
                        "description": "The decomp.me scratch URL or slug",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern or text to search for (e.g., 'HSD_GObj', 'struct.*Item', 'typedef.*user_data')",
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Number of context lines to show around each match (default: 3)",
                        "default": 3,
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of matches to return (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["url_or_slug", "pattern"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if name == "decomp_get_scratch":
                return await handle_get_scratch(client, arguments)
            elif name == "decomp_compile":
                return await handle_compile(client, arguments)
            elif name == "decomp_get_compilers":
                return await handle_get_compilers(client, arguments)
            elif name == "decomp_search":
                return await handle_search(client, arguments)
            elif name == "decomp_search_context":
                return await handle_search_context(client, arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        logger.error(f"Error in {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_scratch(client: httpx.AsyncClient, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle decomp_get_scratch tool."""
    url_or_slug = arguments["url_or_slug"]
    slug = extract_slug_from_url(url_or_slug)

    logger.info(f"Fetching scratch: {slug}")

    response = await client.get(f"{DECOMP_API_BASE}/scratch/{slug}")
    response.raise_for_status()

    scratch = response.json()
    formatted = format_scratch_info(scratch)

    return [
        TextContent(
            type="text",
            text=formatted,
        )
    ]


async def handle_compile(client: httpx.AsyncClient, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle decomp_compile tool."""
    url_or_slug = arguments["url_or_slug"]
    slug = extract_slug_from_url(url_or_slug)

    # First, get the scratch to retrieve compilation settings
    logger.info(f"Fetching scratch for compilation: {slug}")
    scratch_response = await client.get(f"{DECOMP_API_BASE}/scratch/{slug}")
    scratch_response.raise_for_status()
    scratch = scratch_response.json()

    # Prepare compilation payload
    payload = {
        "compiler": scratch["compiler"],
        "compiler_flags": scratch["compiler_flags"],
        "diff_flags": scratch.get("diff_flags", []),
        "diff_label": scratch.get("diff_label", ""),
        "libraries": scratch.get("libraries", []),
        "source_code": arguments.get("source_code", scratch["source_code"]),
        "include_objects": False,
    }

    logger.info(f"Compiling scratch: {slug}")
    compile_response = await client.post(
        f"{DECOMP_API_BASE}/scratch/{slug}/compile",
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    compile_response.raise_for_status()

    result = compile_response.json()

    # Check for compilation errors
    if not result.get("success", True):
        compiler_output = result.get("compiler_output", "Unknown compilation error")
        return [
            TextContent(
                type="text",
                text=f"❌ **Compilation Failed**\n\n```\n{compiler_output}\n```",
            )
        ]

    # Format the diff output
    diff_output = result.get("diff_output", {})
    formatted = format_diff_output(diff_output)

    return [
        TextContent(
            type="text",
            text=formatted,
        )
    ]


async def handle_get_compilers(client: httpx.AsyncClient, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle decomp_get_compilers tool."""
    platform = arguments.get("platform")

    if platform:
        logger.info(f"Fetching compilers for platform: {platform}")
        response = await client.get(f"{DECOMP_API_BASE}/compiler/{platform}")
    else:
        logger.info("Fetching all compilers")
        response = await client.get(f"{DECOMP_API_BASE}/compiler")

    response.raise_for_status()
    data = response.json()

    # Format the output
    lines = ["# Available Compilers", ""]

    if isinstance(data, dict):
        for platform_id, compilers in data.items():
            lines.append(f"## {platform_id}")
            lines.append("")
            if isinstance(compilers, list):
                for compiler in compilers:
                    if isinstance(compiler, dict):
                        lines.append(f"- **{compiler.get('id', 'Unknown')}**")
                        if 'flags' in compiler:
                            lines.append(f"  - Flags: `{compiler['flags']}`")
                    else:
                        lines.append(f"- {compiler}")
                lines.append("")
    else:
        lines.append(json.dumps(data, indent=2))

    return [
        TextContent(
            type="text",
            text="\n".join(lines),
        )
    ]


async def handle_search(client: httpx.AsyncClient, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle decomp_search tool."""
    query = arguments.get("query", "")
    platform = arguments.get("platform", "")
    limit = arguments.get("limit", 10)
    only_incomplete = arguments.get("only_incomplete", False)
    min_match_percent = arguments.get("min_match_percent")
    max_match_percent = arguments.get("max_match_percent")
    sort_by = arguments.get("sort_by")

    params = {"page_size": 100}  # Fetch more to allow filtering
    if query:
        params["search"] = query
    if platform:
        params["platform"] = platform

    logger.info(f"Searching with params: {params}")
    response = await client.get(f"{DECOMP_API_BASE}/search", params=params)
    response.raise_for_status()

    results = response.json()

    # Separate results by type
    scratches = []
    presets = []
    users = []

    for result in results:
        result_type = result.get("type")
        item = result.get("item", {})

        if result_type == "scratch":
            scratches.append(item)
        elif result_type == "preset":
            presets.append(item)
        elif result_type == "user":
            users.append(item)

    # Calculate match percentages and filter scratches
    filtered_scratches = []
    for scratch in scratches:
        score = scratch.get("score", 0)
        max_score = scratch.get("max_score", 1)

        # Calculate correct match percentage (lower diff score = better match)
        match_pct = ((max_score - score) / max_score * 100) if max_score > 0 else 0
        scratch["_match_percent"] = match_pct

        # Apply filters
        if only_incomplete and score == 0:
            continue  # Skip perfect matches when only_incomplete is True

        if min_match_percent is not None and match_pct < min_match_percent:
            continue

        if max_match_percent is not None and match_pct > max_match_percent:
            continue

        filtered_scratches.append(scratch)

    # Sort scratches
    if sort_by == "match_percent":
        # Sort by closest to matching (highest match percent)
        filtered_scratches.sort(key=lambda x: x["_match_percent"], reverse=True)
    elif sort_by == "last_updated":
        filtered_scratches.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
    elif sort_by == "creation_time":
        filtered_scratches.sort(key=lambda x: x.get("creation_time", ""), reverse=True)

    # Limit scratches after filtering
    filtered_scratches = filtered_scratches[:limit]

    # Format results
    filter_desc = []
    if only_incomplete:
        filter_desc.append("incomplete only")
    if min_match_percent is not None:
        filter_desc.append(f"≥{min_match_percent}% match")
    if max_match_percent is not None:
        filter_desc.append(f"≤{max_match_percent}% match")

    lines = []

    # Show presets first if any
    if presets:
        lines.append(f"# Presets ({len(presets)} found)")
        lines.append("")
        for preset in presets[:limit]:  # Limit presets too
            lines.extend([
                f"## {preset.get('name', 'Unnamed')}",
                f"",
                f"- **Platform:** {preset.get('platform', 'Unknown')}",
                f"- **Compiler:** {preset.get('compiler', 'Unknown')}",
                f"- **Number of Scratches:** {preset.get('num_scratches', 0)}",
            ])
            if preset.get("id"):
                lines.append(f"- **Preset ID:** {preset['id']}")
            lines.append("")

    # Show scratches
    if filtered_scratches or not presets:
        title = f"# Scratches ({len(filtered_scratches)} found"
        if filter_desc:
            title += f", {', '.join(filter_desc)}"
        title += ")"
        lines.append(title)
        lines.append("")

        for scratch in filtered_scratches:
            score = scratch.get("score", 0)
            max_score = scratch.get("max_score", 1)
            match_pct = scratch["_match_percent"]

            lines.extend([
                f"## {scratch.get('name', 'Unnamed')} ({scratch['slug']})",
                f"",
                f"- **URL:** https://decomp.me/scratch/{scratch['slug']}",
                f"- **Platform:** {scratch.get('platform', 'Unknown')}",
                f"- **Compiler:** {scratch.get('compiler', 'Unknown')}",
                f"- **Match:** {match_pct:.1f}% (diff score: {score}/{max_score})",
            ])

            owner = scratch.get("owner")
            if owner and not owner.get("is_anonymous"):
                lines.append(f"- **Owner:** {owner.get('username', 'Unknown')}")

            lines.append("")

    if not presets and not filtered_scratches:
        lines.append("No results found matching your criteria.")

    return [
        TextContent(
            type="text",
            text="\n".join(lines),
        )
    ]


async def handle_search_context(client: httpx.AsyncClient, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle decomp_search_context tool."""
    import re

    url_or_slug = arguments["url_or_slug"]
    slug = extract_slug_from_url(url_or_slug)
    pattern = arguments["pattern"]
    context_lines = arguments.get("context_lines", 3)
    max_results = arguments.get("max_results", 20)

    logger.info(f"Searching context in scratch {slug} for pattern: {pattern}")

    # Fetch the scratch to get the context
    response = await client.get(f"{DECOMP_API_BASE}/scratch/{slug}")
    response.raise_for_status()
    scratch = response.json()

    context = scratch.get("context", "")
    if not context:
        return [
            TextContent(
                type="text",
                text="No context found for this scratch.",
            )
        ]

    # Split context into lines
    lines = context.splitlines()

    # Compile the regex pattern
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return [
            TextContent(
                type="text",
                text=f"Invalid regex pattern: {e}",
            )
        ]

    # Search for matches
    matches = []
    for i, line in enumerate(lines):
        if regex.search(line):
            # Get context lines around the match
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)

            context_block = {
                "line_num": i + 1,
                "matched_line": line,
                "context": lines[start:end],
                "context_start": start + 1,
            }
            matches.append(context_block)

            if len(matches) >= max_results:
                break

    # Format output
    if not matches:
        return [
            TextContent(
                type="text",
                text=f"No matches found for pattern: `{pattern}`",
            )
        ]

    output_lines = [
        f"# Context Search Results",
        f"",
        f"**Pattern:** `{pattern}`",
        f"**Matches:** {len(matches)} (showing up to {max_results})",
        f"",
    ]

    for idx, match in enumerate(matches, 1):
        output_lines.extend([
            f"## Match {idx} (line {match['line_num']})",
            f"",
            f"```c",
        ])

        # Show context with line numbers
        for line_idx, line_content in enumerate(match["context"]):
            line_num = match["context_start"] + line_idx
            marker = ">>> " if line_num == match["line_num"] else "    "
            output_lines.append(f"{marker}{line_num:5d}: {line_content}")

        output_lines.extend([
            f"```",
            f"",
        ])

    return [
        TextContent(
            type="text",
            text="\n".join(output_lines),
        )
    ]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
