# MCP Server Configuration for VSCode Server

This document explains how the MCP (Model Context Protocol) server is configured within the VSCode server environment to provide deployment tools for Cline.

## Overview

The workspace deployment MCP server provides tools for deploying static applications using Kubernetes and Skaffold. It's specifically designed to work within the containerized VSCode server environment.

## Configuration Files

### 1. `mcp_settings.json`

This is the main configuration file that tells Cline how to connect to the MCP server:

```json
{
  "mcpServers": {
    "workspace-deployment": {
      "command": "node",
      "args": ["/home/workspace/.mcp-servers/workspace-deployment/dist/index.js"],
      "env": {
        "WORKSPACE_ROOT": "/home/workspace"
      }
    }
  }
}
```

**Key components:**
- **Server name**: `workspace-deployment` - This is how you'll reference the server
- **Command**: `node` - The runtime to execute the server
- **Args**: Path to the compiled MCP server JavaScript file
- **Environment**: `WORKSPACE_ROOT` set to `/workspace` for proper path resolution

### 2. File Locations

Within the VSCode server container:

```
/home/openvscode-server/
├── .mcp-servers/
│   └── workspace-deployment/
│       ├── dist/
│       │   └── index.js          # Compiled MCP server
│       ├── src/
│       │   └── index.ts          # Source code
│       ├── package.json
│       └── tsconfig.json
└── .openvscode-server/
    └── data/User/globalStorage/rooveterinaryinc.roo-cline/settings/
        └── mcp_settings.json     # Cline MCP configuration
```

## Setup Process

The MCP server is now automatically configured when a new workspace is created using the workspace template. The setup process includes:

### 1. Automatic Installation (via workspace-template.yaml)

When a new workspace is deployed, the following happens automatically:
- Node.js is installed in the container
- MCP server files are copied from the workspace template
- Dependencies are installed with `npm install`
- MCP server is built with `npm run build`
- Cline MCP configuration is created at the correct location
- All necessary directories and permissions are set up

### 2. Manual Setup (if needed)

If you need to manually set up or rebuild the MCP server:

```bash
cd /home/workspace/.mcp-servers/workspace-deployment
npm install
npm run build
```

### 3. Configuration Location

The MCP configuration is automatically created at:
```
/home/workspace/.openvscode-server/data/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json
```

### 4. No Restart Required

The MCP server is configured during the initial workspace setup, so no additional restart is needed.

## Available Tools

Once configured, the following tools will be available in Cline:

### `scaffold_configmap_app`
Creates deployment boilerplate for static applications using ConfigMap pattern.

**Parameters:**
- `project_path`: Path to project with static content (relative to workspace root)
- `app_name`: Application name for deployment (lowercase, alphanumeric with hyphens)
- `ingress_path`: URL path for ingress (e.g., /my-app)

### `deploy_app`
Deploys application using Skaffold.

**Parameters:**
- `project_path`: Path to project containing .roobrowser/skaffold/
- `mode`: Deployment mode ('dev' for live reload, 'run' for one-time deployment)

### `get_deployment_status`
Checks status of deployed applications.

**Parameters:**
- `app_name`: Specific app name to check (optional)

### `get_deployment_logs`
Gets logs from deployed application.

**Parameters:**
- `app_name`: Application name to get logs from
- `follow`: Whether to stream logs (true) or get snapshot (false)

### `cleanup_deployment`
Cleans up deployed resources using skaffold delete.

**Parameters:**
- `project_path`: Path to project containing .roobrowser/skaffold/

## Usage Example

1. **Scaffold a new app:**
   ```
   Use the scaffold_configmap_app tool with:
   - project_path: "projects/my-static-app"
   - app_name: "my-app"
   - ingress_path: "/my-app"
   ```

2. **Deploy the app:**
   ```
   Use the deploy_app tool with:
   - project_path: "projects/my-static-app"
   - mode: "dev"
   ```

3. **Check status:**
   ```
   Use the get_deployment_status tool with:
   - app_name: "my-app"
   ```

## Troubleshooting

### MCP Server Not Found
- Ensure the MCP server is built: `cd ~/.mcp-servers/workspace-deployment && npm run build`
- Check that `dist/index.js` exists

### Configuration Not Loaded
- Verify `mcp_settings.json` is in the correct location
- Restart VSCode/Cline after configuration changes
- Check Cline logs for MCP connection errors

### Tools Not Available
- Confirm the MCP server is properly configured in `mcp_settings.json`
- Check that the server name matches exactly ("workspace-deployment")
- Verify environment variables are set correctly

### Permission Issues
- Ensure the openvscode-server user has read access to the MCP server files
- Check that the workspace directory is properly mounted

## Environment Variables

The MCP server uses the following environment variables:

- `WORKSPACE_ROOT`: Set to `/workspace` to define the root directory for projects
- Additional Kubernetes-related environment variables may be inherited from the container

## Security Considerations

- The MCP server runs with the same permissions as the VSCode server
- It has access to the workspace directory and can execute kubectl/skaffold commands
- Ensure proper RBAC is configured for the Kubernetes cluster
- The server only processes files within the workspace directory

## Integration with Kubernetes

The MCP server integrates with:
- **kubectl**: For managing Kubernetes resources
- **skaffold**: For deployment automation
- **ConfigMap pattern**: For serving static content
- **Ingress**: For external access to applications

Make sure these tools are available in the VSCode server container environment.
