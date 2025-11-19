# Decomp.me MCP Server

An MCP (Model Context Protocol) server that provides tools for interacting with the [decomp.me](https://decomp.me) API. This server allows AI assistants like Claude to help with video game decompilation projects by fetching scratches, compiling code, analyzing diffs, and iterating on improvements.

## Features

- **Fetch Scratches**: Load decompilation scratches with all context (source code, target assembly, compiler settings, headers)
- **Compile & Diff**: Compile modified source code and get detailed assembly diffs with match scores
- **Search**: Find scratches and presets by query, platform, or other criteria with advanced filtering
- **Context Search**: Search through massive header files (45k+ lines) to find type definitions and struct layouts
- **Compiler Info**: List available compilers and their configurations for different platforms

## Installation

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Install with uv (recommended)

```bash
# Clone or navigate to the repository
cd decomp-mcp-server

# Create a virtual environment and install
uv venv
uv pip install -e .
```

### Install with pip

```bash
cd decomp-mcp-server
pip install -e .
```

## Configuration

Add the MCP server to your Claude Desktop or other MCP client configuration.

### Claude Desktop Configuration

Edit your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the server configuration:

```json
{
  "mcpServers": {
    "decomp": {
      "command": "/Users/YOUR_USERNAME/decomp-mcp-server/.venv/bin/python",
      "args": [
        "-m",
        "decomp_mcp.server"
      ]
    }
  }
}
```

**Note**: Replace `/Users/YOUR_USERNAME/decomp-mcp-server/.venv/bin/python` with the actual path to your Python interpreter in the virtual environment.

To find the correct path, run:
```bash
cd ~/decomp-mcp-server
source .venv/bin/activate
which python
```

## Available Tools

### 1. `decomp_get_scratch`

Fetch a scratch from decomp.me by URL or slug.

**Parameters:**
- `url_or_slug` (string, required): The decomp.me scratch URL (e.g., `https://decomp.me/scratch/Jwtky`) or just the slug (e.g., `Jwtky`)

**Example:**
```
Get scratch Jwtky from decomp.me
```

**Returns:**
- Platform and compiler information
- Current match score
- Complete source code
- Compiler flags and settings

### 2. `decomp_compile`

Compile source code and get a diff showing how closely it matches the target assembly.

**Parameters:**
- `url_or_slug` (string, required): The decomp.me scratch URL or slug
- `source_code` (string, optional): Modified source code to compile. If not provided, compiles the existing code from the scratch.

**Example:**
```
Compile scratch Jwtky with this modified code: [paste code here]
```

**Returns:**
- Match score (current/max)
- Detailed assembly diff showing matched and mismatched instructions
- Compilation errors (if any)

### 3. `decomp_get_compilers`

List available compilers for a platform or all platforms.

**Parameters:**
- `platform` (string, optional): Platform ID (e.g., `gc_wii`, `n64`, `ps1`, `ps2`, `switch`)

**Example:**
```
Show me the available compilers for GameCube/Wii
```

**Returns:**
- List of compilers by platform
- Compiler IDs and default flags

### 4. `decomp_search`

Search for scratches and presets on decomp.me with advanced filtering.

**Parameters:**
- `query` (string, optional): Search query (searches function names, descriptions, etc.)
- `platform` (string, optional): Filter by platform (e.g., `gc_wii`, `n64`)
- `only_incomplete` (boolean, optional): Only show scratches that aren't perfectly matched
- `min_match_percent` (number, optional): Minimum match percentage (0-100)
- `max_match_percent` (number, optional): Maximum match percentage (0-100)
- `sort_by` (string, optional): Sort by `match_percent`, `last_updated`, or `creation_time`
- `limit` (integer, optional): Maximum results (default: 10)

**Examples:**
```
Search decomp.me for Melee item functions
```
```
Find scratches for Super Smash Bros that are between 70-90% matched
```
```
Show me the most recent incomplete GameCube scratches
```

**Returns:**
- Project presets (if matching the search query)
- List of matching scratches with URLs
- Match percentages and scores
- Platform, compiler, and owner information

### 5. `decomp_search_context`

Search through the context (header files) of a scratch for type definitions, struct definitions, function declarations, or other patterns. Essential for finding types in massive context files.

**Parameters:**
- `url_or_slug` (string, required): The decomp.me scratch URL or slug
- `pattern` (string, required): Regex pattern or text to search for
- `context_lines` (integer, optional): Number of context lines around each match (default: 3)
- `max_results` (integer, optional): Maximum number of matches (default: 20)

**Example:**
```
Search the context of scratch Jwtky for the Item struct definition
```

**Returns:**
- Matching lines with surrounding context
- Line numbers for easy reference
- Highlights of the matched pattern

## Usage Examples

Once configured with Claude Desktop or another MCP client, you can interact naturally:

### Basic Workflow

1. **Load a scratch:**
   ```
   Load scratch https://decomp.me/scratch/Jwtky
   ```

2. **Analyze the code:**
   ```
   What could be improved in this decompilation to get a better match?
   ```

3. **Test changes:**
   ```
   Try compiling this scratch with the temp variables consolidated
   ```

4. **Iterate:**
   ```
   The score improved! Now let's try adjusting the cast on line 8
   ```

### Advanced Examples

**Finding related work:**
```
Search for other Melee item-related scratches on GameCube
```

**Exploring compilers:**
```
What compilers are available for Nintendo 64?
```

**Analyzing diffs:**
```
Load scratch ABC123 and explain why the assembly doesn't match
```

## Development

### Running Tests

```bash
cd decomp-mcp-server
source .venv/bin/activate
python test_server.py
```

### Project Structure

```
decomp-mcp-server/
├── src/
│   └── decomp_mcp/
│       ├── __init__.py
│       └── server.py          # Main MCP server implementation
├── pyproject.toml             # Project dependencies and metadata
├── test_server.py            # API integration tests
└── README.md                 # This file
```

## Contributing

Contributions are welcome! Areas for improvement:

- Add support for creating new scratches via the API
- Implement caching for frequently accessed scratches
- Add more detailed diff analysis and suggestions
- Support for batch operations
- Integration with local decompilation projects

## Resources

- [decomp.me](https://decomp.me) - The decompilation collaboration platform
- [MCP Documentation](https://modelcontextprotocol.io) - Learn about the Model Context Protocol
- [decomp.me GitHub](https://github.com/decompme/decomp.me) - Source code for decomp.me

## License

MIT License - see LICENSE file for details

## Acknowledgments

- The decomp.me team for building an amazing decompilation platform
- The video game decompilation community
- Anthropic for creating the Model Context Protocol
