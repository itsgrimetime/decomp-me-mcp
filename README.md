# Decomp.me MCP Server

An MCP (Model Context Protocol) server that provides tools for interacting with the [decomp.me](https://decomp.me) API. This server allows AI assistants like Claude to help with video game decompilation projects by fetching scratches, compiling code, analyzing diffs, and iterating on improvements.

## Features

- **Fetch Scratches**: Load decompilation scratches with all context (source code, target assembly, compiler settings, headers)
- **Compile & Diff**: Compile modified source code and get detailed assembly diffs with match scores
- **Search**: Find scratches and presets by query, platform, or other criteria with advanced filtering
- **Context Search**: Search through massive header files (45k+ lines) to find type definitions and struct layouts
- **Compiler Info**: List available compilers and their configurations for different platforms
- **Create & Update Scratches**: Create new scratches and save improved source code back to decomp.me
- **Parallel Agent Coordination**: Claim functions and track completed work so multiple agents don't duplicate effort

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

### 6. `decomp_update_scratch`

Save new source code to an existing scratch on decomp.me. Use this to keep progress after improving the match score.

**Parameters:**
- `url_or_slug` (string, required): The decomp.me scratch URL or slug to update
- `source_code` (string, required): The new source code to save

**Example:**
```
Save this improved code to scratch Jwtky: [paste code here]
```

**Returns:**
- The scratch slug and URL
- The current match percentage, if decomp.me returns a score

**Note:** You can only update scratches you own. Scratches created with `decomp_create_scratch` are claimed automatically, and the session cookies are stored in `DECOMP_COOKIES_FILE` so later updates are recognized. Updating a scratch you don't own returns a 403 error suggesting you create a new scratch instead.

### 7. `decomp_create_scratch`

Create a new scratch on decomp.me for a function. Scratches are created with the Melee preset settings (`mwcc_233_163n` compiler and its flags).

**Parameters:**
- `name` (string, required): Name of the function (e.g., `fn_80393C14`). Also used as the diff label.
- `target_asm` (string, required): The target assembly to match against
- `source_code` (string, optional): Initial source code (defaults to a placeholder comment)
- `context` (string, optional): Context/headers for compilation. If omitted, the server reads `DECOMP_CONTEXT_FILE` when set, and otherwise copies the context from a reference scratch.

**Example:**
```
Create a scratch for fn_80393C14 with this target assembly: [paste asm here]
```

**Returns:**
- The new scratch slug and URL
- Whether the scratch was claimed (owned by you and updateable)

The claim token returned by decomp.me is saved to `DECOMP_SCRATCH_TOKENS_FILE`.

### 8. `decomp_claim_function`

Claim a function before working on it, so other agents running in parallel don't pick the same one. Claims are stored locally in `DECOMP_CLAIMS_FILE` and expire after `DECOMP_CLAIM_TIMEOUT` seconds (1 hour by default).

**Parameters:**
- `function_name` (string, required): Name of the function to claim
- `agent_id` (string, optional): Identifier for this agent, shown to other agents

**Returns:**
- Success if the function was claimed
- Failure if another agent already holds the claim, or if the function is already marked completed

### 9. `decomp_release_function`

Release a claimed function so other agents can work on it.

**Parameters:**
- `function_name` (string, required): Name of the function to release

### 10. `decomp_list_claims`

List all currently claimed functions, who claimed them, and how much time is left on each claim. Stale claims are dropped automatically.

**Parameters:** none

### 11. `decomp_complete_function`

Record a function as completed or attempted (whether it reached 100% or got stuck), so other agents skip it. Also releases any claim on the function. Records are stored in `DECOMP_COMPLETED_FILE`.

**Parameters:**
- `function_name` (string, required): Name of the function
- `match_percent` (number, required): Best match percentage achieved (0-100)
- `scratch_slug` (string, required): The scratch slug with the best code
- `committed` (boolean, optional): Whether the code was committed to the project repo (default: false)
- `notes` (string, optional): Notes such as `register diffs only` or `needs struct work`

### 12. `decomp_list_completed`

List completed/attempted functions, sorted by match percentage, with scratch links and commit status.

**Parameters:**
- `min_match` (number, optional): Only show functions with at least this match percentage (default: 0)

## Environment Variables

All settings are optional.

| Variable | Default | Description |
|----------|---------|-------------|
| `DECOMP_API_BASE` | `https://decomp.me/api` | Base URL of the decomp.me API (point it at a local instance if you run one) |
| `DECOMP_CONTEXT_FILE` | _(unset)_ | Path to a local context file (e.g. generated by `m2ctx.py`) used by `decomp_create_scratch` |
| `DECOMP_CLAIMS_FILE` | `/tmp/decomp_claims.json` | Where function claims are stored |
| `DECOMP_CLAIM_TIMEOUT` | `3600` | Seconds before a claim expires |
| `DECOMP_COMPLETED_FILE` | `/tmp/decomp_completed.json` | Where completed functions are recorded |
| `DECOMP_SCRATCH_TOKENS_FILE` | `/tmp/decomp_scratch_tokens.json` | Where claim tokens for created scratches are stored |
| `DECOMP_COOKIES_FILE` | `/tmp/decomp_cookies.json` | Where decomp.me session cookies are persisted |
| `CF_CLEARANCE` | _(unset)_ | Cloudflare `cf_clearance` cookie, if the public API requires it |

Environment variables can be set in the `env` block of your MCP client configuration:

```json
{
  "mcpServers": {
    "decomp": {
      "command": "/Users/YOUR_USERNAME/decomp-mcp-server/.venv/bin/python",
      "args": ["-m", "decomp_mcp.server"],
      "env": {
        "DECOMP_CONTEXT_FILE": "/path/to/ctx.c"
      }
    }
  }
}
```

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

- Implement caching for frequently accessed scratches
- Add more detailed diff analysis and suggestions
- Support for batch operations
- Integration with local decompilation projects

## Resources

- [decomp.me](https://decomp.me) - The decompilation collaboration platform
- [MCP Documentation](https://modelcontextprotocol.io) - Learn about the Model Context Protocol
- [decomp.me GitHub](https://github.com/decompme/decomp.me) - Source code for decomp.me

## License

GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details

## Acknowledgments

- The decomp.me team for building an amazing decompilation platform
- The video game decompilation community
- Anthropic for creating the Model Context Protocol
