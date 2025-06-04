# Deployment Guide: Focused Workspace Deployment MCP Server

This guide explains how to deploy and use the Focused Workspace Deployment MCP Server within the existing MVP Roo SaaS infrastructure.

## 🎯 Quick Deployment

### 1. Start the MVP Roo SaaS System

```bash
cd mvp-roo-saas
make up
```

This will:
- Create a kind Kubernetes cluster
- Start the FastAPI backend and React frontend
- Install NGINX Ingress Controller
- Set up RBAC and cleanup jobs

### 2. Create a Workspace

Visit http://localhost:3000 and click "Create Project" to spin up a new workspace.

### 3. Access Your Workspace

Click "Open IDE" to access your VSCode workspace at `http://localhost/<namespace>/`

The workspace will automatically include:
- ✅ kubectl and skaffold installed
- ✅ Node.js runtime for MCP server
- ✅ Complete MCP server implementation (via volume mount)
- ✅ Sample static application
- ✅ Roo Code extension with MCP support
- ✅ Auto-built and configured MCP server

## 🔧 MCP Server Setup

### Automatic Setup (Default)

The MCP server is **automatically set up** when the workspace starts! No manual setup required.

**What happens automatically:**
- ✅ MCP server files copied from volume mount
- ✅ Dependencies installed via npm
- ✅ TypeScript compiled to JavaScript
- ✅ VSCode settings configured
- ✅ Sample static app ready to use

### Manual Setup (If Needed)

If for some reason the automatic setup fails, you can manually run:

```bash
# The setup script is already available in your workspace
./setup-mcp-server.sh
```

**Or manually:**
```bash
cd /home/workspace/.mcp-servers/workspace-deployment
npm install
npm run build
```

Then restart VSCode (refresh the browser page).

## 🚀 Using the MCP Server

### Basic Workflow

1. **Scaffold a deployment:**
   ```
   scaffold_configmap_app(
     project_path: "projects/my-static-app",
     app_name: "my-app",
     ingress_path: "/my-app"
   )
   ```

2. **Deploy with live reload:**
   ```
   deploy_app(
     project_path: "projects/my-static-app",
     mode: "dev"
   )
   ```

3. **Check deployment status:**
   ```
   get_deployment_status(app_name: "my-app")
   ```

4. **View your deployed app:**
   Visit `http://localhost/my-app/`

5. **Clean up when done:**
   ```
   cleanup_deployment(project_path: "projects/my-static-app")
   ```

### Natural Language Commands

You can also use natural language with Roo Code:

- "Deploy my static website in projects/portfolio as portfolio-app at /portfolio"
- "Check the status of my deployed apps"
- "Show me the logs for my-app"
- "Clean up the deployment in projects/my-static-app"

## 📁 Project Structure After Setup

```
/home/workspace/
├── .mcp-servers/
│   └── workspace-deployment/
│       ├── package.json
│       ├── tsconfig.json
│       ├── src/index.ts
│       ├── templates/
│       │   └── configmap-static/
│       └── dist/index.js
├── .vscode-server/
│   └── settings.json
├── projects/
│   └── my-static-app/
│       ├── index.html
│       ├── style.css
│       ├── script.js
│       └── .roobrowser/          # Created after scaffolding
│           └── skaffold/
└── setup-mcp-server.sh
```

## 🔍 Troubleshooting

### MCP Server Not Loading

1. **Check if built:**
   ```bash
   ls -la /home/workspace/.mcp-servers/workspace-deployment/dist/
   ```

2. **Rebuild if needed:**
   ```bash
   cd /home/workspace/.mcp-servers/workspace-deployment
   npm run build
   ```

3. **Check VSCode settings:**
   ```bash
   cat /home/workspace/.vscode-server/settings.json
   ```

4. **Restart VSCode** (refresh the browser page)

### Deployment Issues

1. **Check kubectl access:**
   ```bash
   kubectl get pods
   kubectl auth can-i create deployments
   ```

2. **Verify skaffold:**
   ```bash
   skaffold version
   ```

3. **Check project structure:**
   ```bash
   ls -la /home/workspace/projects/my-static-app/
   ```

### Common Errors

**"No .roobrowser/skaffold found"**
- Run `scaffold_configmap_app` first to create the deployment structure

**"kubectl access denied"**
- The workspace should have proper RBAC permissions automatically
- Check if you're in the correct namespace

**"Skaffold command not found"**
- Skaffold should be installed automatically in the workspace
- Try restarting the workspace if missing

## 🎯 Example: Deploying a Portfolio Site

1. **Create your portfolio files:**
   ```bash
   mkdir -p /home/workspace/projects/portfolio
   # Add your HTML, CSS, JS files
   ```

2. **Scaffold the deployment:**
   ```
   scaffold_configmap_app(
     project_path: "projects/portfolio",
     app_name: "portfolio",
     ingress_path: "/portfolio"
   )
   ```

3. **Deploy with live reload:**
   ```
   deploy_app(
     project_path: "projects/portfolio",
     mode: "dev"
   )
   ```

4. **Visit your site:**
   http://localhost/portfolio/

5. **Make changes and see live updates:**
   - Edit files in `projects/portfolio/`
   - Skaffold will automatically detect changes
   - Refresh browser to see updates

## 🔗 Integration Benefits

This MCP server integrates seamlessly with the existing MVP Roo SaaS infrastructure:

- **Same Kubernetes cluster** - Uses the existing kind setup
- **Same ingress controller** - Routes through NGINX
- **Same RBAC** - Leverages workspace permissions
- **Same monitoring** - Uses kubectl for status/logs
- **Same cleanup** - Auto-deleted with workspace after 2 hours

The MCP server extends workspace capabilities without replacing any core infrastructure.

## 📊 Performance

- **Scaffold time:** ~5 seconds
- **Deploy time:** ~15-30 seconds
- **Live reload:** ~3-5 seconds after file change
- **Resource usage:** ~64Mi memory, 250m CPU per app

Perfect for rapid prototyping and development of static sites!
