#!/bin/bash
# Helper script to generate Claude Desktop MCP configuration

set -e

# Get the absolute path to the virtual environment Python
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH="$SCRIPT_DIR/.venv/bin/python"

if [ ! -f "$PYTHON_PATH" ]; then
    echo "Error: Virtual environment not found at $PYTHON_PATH"
    echo "Please run 'uv venv && uv pip install -e .' first"
    exit 1
fi

# Detect OS and set config path
if [[ "$OSTYPE" == "darwin"* ]]; then
    CONFIG_DIR="$HOME/Library/Application Support/Claude"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    CONFIG_DIR="$APPDATA/Claude"
else
    CONFIG_DIR="$HOME/.config/Claude"
fi

CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

echo "Decomp.me MCP Server Configuration"
echo "===================================="
echo ""
echo "Python path: $PYTHON_PATH"
echo "Config file: $CONFIG_FILE"
echo ""

# Create the configuration snippet
cat > /tmp/decomp_mcp_config.json << EOF
{
  "mcpServers": {
    "decomp": {
      "command": "$PYTHON_PATH",
      "args": [
        "-m",
        "decomp_mcp.server"
      ]
    }
  }
}
EOF

echo "Configuration snippet saved to: /tmp/decomp_mcp_config.json"
echo ""
cat /tmp/decomp_mcp_config.json
echo ""
echo "To complete setup:"
echo "1. Copy the above JSON configuration"
echo "2. Open: $CONFIG_FILE"
echo "3. Add the 'decomp' server to your 'mcpServers' section"
echo "4. Restart Claude Desktop"
echo ""
echo "If the config file doesn't exist, you can create it with the entire JSON above."
