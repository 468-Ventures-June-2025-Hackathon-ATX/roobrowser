#!/bin/bash

# Setup script for Workspace Deployment MCP Server
# Run this inside a workspace to install and build the MCP server

set -e

echo "🚀 Setting up Workspace Deployment MCP Server..."

# Check if we're in a workspace
if [ ! -d "/home/workspace" ]; then
    echo "❌ This script must be run inside a workspace container"
    exit 1
fi

WORKSPACE_ROOT="/home/workspace"
MCP_DIR="$WORKSPACE_ROOT/.mcp-servers/workspace-deployment"

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p "$MCP_DIR/src"
mkdir -p "$MCP_DIR/templates/configmap-static/k8s"
mkdir -p "$WORKSPACE_ROOT/.vscode-server"
mkdir -p "$WORKSPACE_ROOT/projects"

# Copy MCP server files from the workspace directory structure
echo "📋 Copying MCP server files..."

# Check if files exist in the workspace directory and copy them
if [ -f "$WORKSPACE_ROOT/workspace/.mcp-servers/workspace-deployment/package.json" ]; then
    cp -r "$WORKSPACE_ROOT/workspace/.mcp-servers/workspace-deployment/"* "$MCP_DIR/"
    echo "✅ Copied MCP server files from workspace directory"
else
    echo "⚠️  MCP server files not found in workspace directory, creating basic structure..."

    # Create package.json with full dependencies
    cat > "$MCP_DIR/package.json" << 'EOF'
{
  "name": "workspace-deployment-mcp-server",
  "version": "1.0.0",
  "description": "Focused MCP server for deploying static applications using Skaffold and ConfigMap pattern",
  "main": "dist/index.js",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "tsc --watch"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^0.5.0",
    "fs-extra": "^11.2.0",
    "yaml": "^2.3.4",
    "mime-types": "^2.1.35"
  },
  "devDependencies": {
    "@types/node": "^20.10.0",
    "@types/fs-extra": "^11.0.4",
    "@types/mime-types": "^2.1.4",
    "typescript": "^5.3.0"
  }
}
EOF

    # Create tsconfig.json
    cat > "$MCP_DIR/tsconfig.json" << 'EOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "node",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "resolveJsonModule": true,
    "allowSyntheticDefaultImports": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
EOF

    echo "✅ Created basic MCP server configuration"
fi

# Copy VSCode settings
if [ -f "$WORKSPACE_ROOT/workspace/.vscode-server/settings.json" ]; then
    cp "$WORKSPACE_ROOT/workspace/.vscode-server/settings.json" "$WORKSPACE_ROOT/.vscode-server/"
    echo "✅ Copied VSCode settings"
fi

# Copy sample static app
if [ -d "$WORKSPACE_ROOT/workspace/projects/my-static-app" ]; then
    cp -r "$WORKSPACE_ROOT/workspace/projects/my-static-app" "$WORKSPACE_ROOT/projects/"
    echo "✅ Copied sample static app"
fi

# Install dependencies
echo "📦 Installing MCP server dependencies..."
cd "$MCP_DIR"
npm install

# Build the MCP server if source files exist
if [ -f "$MCP_DIR/src/index.ts" ]; then
    echo "🔨 Building MCP server..."
    npm run build
    echo "✅ MCP server built successfully"
else
    echo "⚠️  MCP server source files not found. You'll need to add the TypeScript source files and build manually."
fi

# Set permissions
echo "🔐 Setting permissions..."
chmod +x "$MCP_DIR/dist/index.js" 2>/dev/null || true

# Verify setup
echo "🔍 Verifying setup..."
echo "✅ MCP server directory: $MCP_DIR"
echo "✅ Node.js version: $(node --version)"
echo "✅ npm version: $(npm --version)"

if [ -f "$MCP_DIR/dist/index.js" ]; then
    echo "✅ MCP server compiled successfully"
else
    echo "⚠️  MCP server not compiled yet"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. If MCP server source files are missing, copy them from the workspace directory"
echo "2. Build the MCP server: cd $MCP_DIR && npm run build"
echo "3. Restart VSCode to load the MCP server"
echo "4. Test with the sample app in $WORKSPACE_ROOT/projects/my-static-app"
echo ""
echo "🔧 Usage:"
echo "- scaffold_configmap_app(project_path: 'projects/my-static-app', app_name: 'test-app', ingress_path: '/test')"
echo "- deploy_app(project_path: 'projects/my-static-app', mode: 'dev')"
echo "- get_deployment_status(app_name: 'test-app')"
echo "- cleanup_deployment(project_path: 'projects/my-static-app')"
