import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import * as fs from 'fs-extra';
import * as path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as yaml from 'yaml';
import * as mime from 'mime-types';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const execAsync = promisify(exec);

interface StaticContent {
  [filename: string]: string;
}

class WorkspaceDeploymentServer {
  private server: Server;
  private workspaceRoot: string = process.env.WORKSPACE_ROOT || '/workspace';
  private templatesPath: string = path.join(__dirname, '..', 'templates');

  constructor() {
    this.server = new Server({
      name: 'workspace-deployment-server',
      version: '1.0.0',
    }, {
      capabilities: { tools: {} }
    });
    this.setupTools();
  }

  private setupTools() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'scaffold_configmap_app',
          description: 'Create .roobrowser/skaffold/ with ConfigMap deployment boilerplate for static content',
          inputSchema: {
            type: 'object',
            properties: {
              project_path: {
                type: 'string',
                description: 'Path to project with static content (relative to workspace root)'
              },
              app_name: {
                type: 'string',
                description: 'Application name for deployment (lowercase, alphanumeric with hyphens)'
              },
              ingress_path: {
                type: 'string',
                description: 'URL path for ingress (e.g., /my-app)'
              }
            },
            required: ['project_path', 'app_name', 'ingress_path']
          }
        },
        {
          name: 'deploy_app',
          description: 'Deploy app using skaffold from .roobrowser/skaffold/ directory',
          inputSchema: {
            type: 'object',
            properties: {
              project_path: {
                type: 'string',
                description: 'Path to project containing .roobrowser/skaffold/'
              },
              mode: {
                type: 'string',
                enum: ['dev', 'run'],
                default: 'dev',
                description: 'Deployment mode: dev (with live reload) or run (one-time deployment)'
              }
            },
            required: ['project_path']
          }
        },
        {
          name: 'get_deployment_status',
          description: 'Check status of deployed applications',
          inputSchema: {
            type: 'object',
            properties: {
              app_name: {
                type: 'string',
                description: 'Specific app name to check (optional, shows all roobrowser apps if empty)'
              }
            }
          }
        },
        {
          name: 'get_deployment_logs',
          description: 'Get logs from deployed application',
          inputSchema: {
            type: 'object',
            properties: {
              app_name: {
                type: 'string',
                description: 'Application name to get logs from'
              },
              follow: {
                type: 'boolean',
                default: false,
                description: 'Whether to stream logs (true) or get snapshot (false)'
              }
            },
            required: ['app_name']
          }
        },
        {
          name: 'cleanup_deployment',
          description: 'Clean up deployed resources using skaffold delete',
          inputSchema: {
            type: 'object',
            properties: {
              project_path: {
                type: 'string',
                description: 'Path to project containing .roobrowser/skaffold/'
              }
            },
            required: ['project_path']
          }
        }
      ]
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'scaffold_configmap_app':
            return await this.scaffoldConfigMapApp(args);
          case 'deploy_app':
            return await this.deployApp(args);
          case 'get_deployment_status':
            return await this.getDeploymentStatus(args);
          case 'get_deployment_logs':
            return await this.getDeploymentLogs(args);
          case 'cleanup_deployment':
            return await this.cleanupDeployment(args);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [{
            type: 'text',
            text: `❌ Error: ${error instanceof Error ? error.message : String(error)}`
          }]
        };
      }
    });
  }

  private async scaffoldConfigMapApp(args: any) {
    const { project_path, app_name, ingress_path } = args;

    // Validate inputs
    if (!project_path || !app_name || !ingress_path) {
      throw new Error('Missing required parameters: project_path, app_name, ingress_path');
    }

    if (!/^[a-z0-9-]+$/.test(app_name)) {
      throw new Error('app_name must be lowercase alphanumeric with hyphens only');
    }

    if (!ingress_path.startsWith('/')) {
      throw new Error('ingress_path must start with /');
    }

    const fullProjectPath = path.join(this.workspaceRoot, project_path);
    const rooBrowserPath = path.join(fullProjectPath, '.roobrowser', 'skaffold');

    // Check if project directory exists
    if (!await fs.pathExists(fullProjectPath)) {
      throw new Error(`Project directory does not exist: ${project_path}`);
    }

    // Create .roobrowser/skaffold directory structure
    await fs.ensureDir(path.join(rooBrowserPath, 'k8s'));

    // Collect static content from project
    const staticContent = await this.collectStaticContent(fullProjectPath);

    if (Object.keys(staticContent).length === 0) {
      throw new Error('No static content found in project directory. Add some HTML, CSS, or JS files.');
    }

    // Copy and process templates
    const templatePath = path.join(this.templatesPath, 'configmap-static');
    await this.processTemplate(templatePath, rooBrowserPath, {
      APP_NAME: app_name,
      INGRESS_PATH: ingress_path,
      STATIC_CONTENT: this.formatStaticContent(staticContent)
    });

    const fileCount = Object.keys(staticContent).length;
    const fileList = Object.keys(staticContent).slice(0, 5).join(', ') +
                    (Object.keys(staticContent).length > 5 ? '...' : '');

    return {
      content: [{
        type: 'text',
        text: `✅ Scaffolded ConfigMap deployment for ${app_name}\n` +
              `📁 Created: ${project_path}/.roobrowser/skaffold/\n` +
              `📄 Processed ${fileCount} files: ${fileList}\n` +
              `🌐 Will be accessible at: http://localhost${ingress_path}/\n\n` +
              `Next: Use deploy_app to deploy with skaffold`
      }]
    };
  }

  private async deployApp(args: any) {
    const { project_path, mode = 'dev' } = args;
    const skaffoldPath = path.join(this.workspaceRoot, project_path, '.roobrowser', 'skaffold');

    if (!await fs.pathExists(skaffoldPath)) {
      throw new Error(`No .roobrowser/skaffold found in ${project_path}. Run scaffold_configmap_app first.`);
    }

    if (!await fs.pathExists(path.join(skaffoldPath, 'skaffold.yaml'))) {
      throw new Error(`No skaffold.yaml found in ${project_path}/.roobrowser/skaffold/`);
    }

    const command = `cd ${skaffoldPath} && skaffold ${mode}`;

    try {
      const { stdout, stderr } = await execAsync(command, { timeout: 60000 });

      return {
        content: [{
          type: 'text',
          text: `🚀 Deployment started with skaffold ${mode}\n\n` +
                `📍 Working directory: ${project_path}/.roobrowser/skaffold/\n` +
                `📋 Output:\n${stdout}\n\n` +
                `${stderr ? `⚠️  Warnings:\n${stderr}\n\n` : ''}` +
                `💡 Use get_deployment_status to check deployment progress`
        }]
      };
    } catch (error: any) {
      throw new Error(`Skaffold deployment failed: ${error.message}`);
    }
  }

  private async getDeploymentStatus(args: any) {
    const { app_name } = args;
    const selector = app_name ? `-l app=${app_name}` : '-l managed-by=roobrowser';

    try {
      const { stdout } = await execAsync(`kubectl get pods,services,ingress ${selector} -o wide`);

      return {
        content: [{
          type: 'text',
          text: `📊 Deployment Status:\n\n${stdout || 'No resources found'}`
        }]
      };
    } catch (error: any) {
      throw new Error(`Failed to get deployment status: ${error.message}`);
    }
  }

  private async getDeploymentLogs(args: any) {
    const { app_name, follow = false } = args;
    const followFlag = follow ? '-f' : '';
    const command = `kubectl logs -l app=${app_name} ${followFlag} --tail=100`;

    try {
      const { stdout } = await execAsync(command, { timeout: 30000 });

      return {
        content: [{
          type: 'text',
          text: `📋 Logs for ${app_name}:\n\n${stdout || 'No logs available'}`
        }]
      };
    } catch (error: any) {
      throw new Error(`Failed to get logs: ${error.message}`);
    }
  }

  private async cleanupDeployment(args: any) {
    const { project_path } = args;
    const skaffoldPath = path.join(this.workspaceRoot, project_path, '.roobrowser', 'skaffold');

    if (!await fs.pathExists(skaffoldPath)) {
      throw new Error(`No .roobrowser/skaffold found in ${project_path}`);
    }

    try {
      const command = `cd ${skaffoldPath} && skaffold delete`;
      const { stdout, stderr } = await execAsync(command, { timeout: 30000 });

      return {
        content: [{
          type: 'text',
          text: `🧹 Cleanup completed for ${project_path}\n\n` +
                `📋 Output:\n${stdout}\n\n` +
                `${stderr ? `⚠️  Warnings:\n${stderr}` : ''}`
        }]
      };
    } catch (error: any) {
      throw new Error(`Cleanup failed: ${error.message}`);
    }
  }

  // Helper methods for content processing
  private async collectStaticContent(projectPath: string): Promise<StaticContent> {
    const content: StaticContent = {};
    const allowedExtensions = ['.html', '.css', '.js', '.json', '.txt', '.md', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico'];

    const processDirectory = async (dirPath: string, relativePath: string = '') => {
      const items = await fs.readdir(dirPath);

      for (const item of items) {
        const fullPath = path.join(dirPath, item);
        const itemRelativePath = path.join(relativePath, item);
        const stat = await fs.stat(fullPath);

        if (stat.isDirectory()) {
          // Skip hidden directories and node_modules
          if (!item.startsWith('.') && item !== 'node_modules') {
            await processDirectory(fullPath, itemRelativePath);
          }
        } else if (stat.isFile()) {
          const ext = path.extname(item).toLowerCase();
          if (allowedExtensions.includes(ext)) {
            try {
              if (['.png', '.jpg', '.jpeg', '.gif', '.ico'].includes(ext)) {
                // Handle binary files as base64
                const buffer = await fs.readFile(fullPath);
                content[itemRelativePath] = buffer.toString('base64');
              } else {
                // Handle text files
                content[itemRelativePath] = await fs.readFile(fullPath, 'utf-8');
              }
            } catch (error) {
              console.warn(`Failed to read file ${fullPath}:`, error);
            }
          }
        }
      }
    };

    await processDirectory(projectPath);
    return content;
  }

  private formatStaticContent(content: StaticContent): string {
    const entries: string[] = [];

    for (const [filePath, fileContent] of Object.entries(content)) {
      const ext = path.extname(filePath).toLowerCase();
      const isBinary = ['.png', '.jpg', '.jpeg', '.gif', '.ico'].includes(ext);

      if (isBinary) {
        entries.push(`  ${JSON.stringify(filePath)}: ${JSON.stringify(fileContent)}`);
      } else {
        // Escape and format text content for YAML
        const escapedContent = fileContent
          .replace(/\\/g, '\\\\')
          .replace(/"/g, '\\"')
          .replace(/\n/g, '\\n')
          .replace(/\r/g, '\\r')
          .replace(/\t/g, '\\t');
        entries.push(`  ${JSON.stringify(filePath)}: ${JSON.stringify(escapedContent)}`);
      }
    }

    return entries.join('\n');
  }

  private async processTemplate(templatePath: string, outputPath: string, variables: any) {
    const processFile = async (filePath: string, outputFilePath: string) => {
      let content = await fs.readFile(filePath, 'utf-8');

      // Replace template variables
      for (const [key, value] of Object.entries(variables)) {
        const placeholder = `{{${key}}}`;
        content = content.replace(new RegExp(placeholder, 'g'), String(value));
      }

      await fs.writeFile(outputFilePath, content);
    };

    const processDirectory = async (dirPath: string, outputDirPath: string) => {
      const items = await fs.readdir(dirPath);

      for (const item of items) {
        const fullPath = path.join(dirPath, item);
        const outputFullPath = path.join(outputDirPath, item);
        const stat = await fs.stat(fullPath);

        if (stat.isDirectory()) {
          await fs.ensureDir(outputFullPath);
          await processDirectory(fullPath, outputFullPath);
        } else if (stat.isFile()) {
          await processFile(fullPath, outputFullPath);
        }
      }
    };

    await processDirectory(templatePath, outputPath);
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Workspace Deployment MCP Server running on stdio');
  }
}

const server = new WorkspaceDeploymentServer();
server.run().catch(console.error);
