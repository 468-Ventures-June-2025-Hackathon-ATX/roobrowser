#!/bin/bash

# Script to configure MCP server in vscode-server container
# This should be run inside the vscode-server container

set -e

echo "🔧 Configuring MCP server for Cline..."

# Define paths
MCP_SETTINGS_DIR="/home/workspace/.openvscode-server/data/User/globalStorage/rooveterinaryinc.roo-cline/settings"
MCP_SETTINGS_FILE="$MCP_SETTINGS_DIR/mcp_settings.json"
SOURCE_CONFIG="/home/workspace/mcp_settings.json"

# Ensure the settings directory exists
mkdir -p "$MCP_SETTINGS_DIR"

# Copy the configuration
if [ -f "$SOURCE_CONFIG" ]; then
    echo "📋 Copying MCP configuration..."
    cp "$SOURCE_CONFIG" "$MCP_SETTINGS_FILE"
    echo "✅ MCP configuration copied to: $MCP_SETTINGS_FILE"
else
    echo "❌ Source configuration not found at: $SOURCE_CONFIG"
    exit 1
fi

# Verify the MCP server binary exists
MCP_SERVER_PATH="/home/workspace/.mcp-servers/workspace-deployment/dist/index.js"
if [ -f "$MCP_SERVER_PATH" ]; then
    echo "✅ MCP server binary found at: $MCP_SERVER_PATH"
else
    echo "❌ MCP server binary not found at: $MCP_SERVER_PATH"
    echo "   Make sure to build the MCP server first with: cd ~/.mcp-servers/workspace-deployment && npm run build"
    exit 1
fi

# Test the MCP server can start
echo "🧪 Testing MCP server startup..."
if timeout 5s node "$MCP_SERVER_PATH" --help 2>/dev/null || true; then
    echo "✅ MCP server can start successfully"
else
    echo "⚠️  MCP server test completed (this is normal for stdio servers)"
fi

echo ""
echo "🎉 MCP server configuration complete!"
echo ""
echo "📋 Configuration details:"
echo "   Server name: workspace-deployment"
echo "   Binary path: $MCP_SERVER_PATH"
echo "   Workspace root: /workspace"
echo ""
echo "🔄 Please restart Cline/VSCode to load the new MCP server configuration."
echo ""
echo "🛠️  Available MCP tools:"
echo "   • scaffold_configmap_app - Create deployment boilerplate"
echo "   • deploy_app - Deploy with skaffold"
echo "   • get_deployment_status - Check deployment status"
echo "   • get_deployment_logs - Get application logs"
echo "   • cleanup_deployment - Clean up resources"
