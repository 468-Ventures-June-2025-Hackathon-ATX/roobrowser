#!/bin/bash

# Script to copy workspace template content to kind nodes
# This enables volume mounting of MCP server files in workspaces

set -e

echo "🚀 Setting up workspace template on kind nodes..."

# Get the absolute path to the workspace directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../../workspace" && pwd)"

if [ ! -d "$WORKSPACE_DIR" ]; then
    echo "❌ Workspace directory not found at $WORKSPACE_DIR"
    exit 1
fi

echo "📁 Workspace directory: $WORKSPACE_DIR"

# Get kind cluster name
CLUSTER_NAME="roo"

# Check if kind cluster exists
if ! kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "❌ Kind cluster '$CLUSTER_NAME' not found. Please create the cluster first."
    exit 1
fi

echo "✅ Found kind cluster: $CLUSTER_NAME"

# Get kind nodes
NODES=$(kind get nodes --name="$CLUSTER_NAME")

if [ -z "$NODES" ]; then
    echo "❌ No nodes found in kind cluster '$CLUSTER_NAME'"
    exit 1
fi

echo "📋 Found nodes:"
echo "$NODES"

# Copy workspace content to each node
for NODE in $NODES; do
    echo ""
    echo "📦 Setting up workspace template on node: $NODE"

    # Create the target directory on the node
    docker exec "$NODE" mkdir -p /opt/workspace-template

    # Copy workspace content to the node
    echo "📋 Copying workspace files..."

    # Copy .mcp-servers directory
    if [ -d "$WORKSPACE_DIR/.mcp-servers" ]; then
        docker cp "$WORKSPACE_DIR/.mcp-servers" "$NODE:/opt/workspace-template/"
        echo "✅ Copied .mcp-servers"
    fi

    # Copy .vscode-server directory
    if [ -d "$WORKSPACE_DIR/.vscode-server" ]; then
        docker cp "$WORKSPACE_DIR/.vscode-server" "$NODE:/opt/workspace-template/"
        echo "✅ Copied .vscode-server"
    fi

    # Copy projects directory
    if [ -d "$WORKSPACE_DIR/projects" ]; then
        docker cp "$WORKSPACE_DIR/projects" "$NODE:/opt/workspace-template/"
        echo "✅ Copied projects"
    fi

    # Copy setup script
    if [ -f "$WORKSPACE_DIR/setup-mcp-server.sh" ]; then
        docker cp "$WORKSPACE_DIR/setup-mcp-server.sh" "$NODE:/opt/workspace-template/"
        echo "✅ Copied setup-mcp-server.sh"
    fi

    # Copy mcp dev script
    if [ -f "$WORKSPACE_DIR/mcp-dev.sh" ]; then
        docker cp "$WORKSPACE_DIR/mcp-dev.sh" "$NODE:/opt/workspace-template/"
        echo "✅ Copied mcp-dev.sh"
    fi

    # Copy documentation files
    for DOC_FILE in README.md DEPLOYMENT.md; do
        if [ -f "$WORKSPACE_DIR/$DOC_FILE" ]; then
            docker cp "$WORKSPACE_DIR/$DOC_FILE" "$NODE:/opt/workspace-template/"
            echo "✅ Copied $DOC_FILE"
        fi
    done

    # Verify the copy
    echo "🔍 Verifying workspace template on $NODE..."
    docker exec "$NODE" ls -la /opt/workspace-template/

    echo "✅ Node $NODE setup complete"
done

echo ""
echo "🎉 Workspace template setup complete!"
echo ""
echo "📋 Summary:"
echo "- Workspace template copied to /opt/workspace-template/ on all kind nodes"
echo "- New workspaces will automatically receive MCP server files"
echo "- MCP server will be built and configured during workspace startup"
echo ""
echo "🚀 Next steps:"
echo "1. Create a new workspace via the frontend"
echo "2. The workspace will automatically include the full MCP server"
echo "3. Use the MCP tools to deploy static applications"
