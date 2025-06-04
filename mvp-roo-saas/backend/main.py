import os
import random
import string
import logging
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Roo SaaS Backend", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Kubernetes client
try:
    config.load_incluster_config()  # Try in-cluster config first
except:
    try:
        config.load_kube_config()  # Fall back to local kubeconfig
    except:
        logger.error("Could not load Kubernetes config")
        raise

k8s_client = client.ApiClient()
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
networking_v1 = client.NetworkingV1Api()

# Pydantic models
class ProjectRequest(BaseModel):
    name: str = None

class ProjectResponse(BaseModel):
    namespace: str
    url: str
    status: str

def generate_namespace() -> str:
    """Generate a random namespace name"""
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"proj-{suffix}"

def load_manifest_template() -> str:
    """Load the workspace template YAML"""
    template_path = "/app/manifests/workspace-template.yaml"
    if not os.path.exists(template_path):
        template_path = "../manifests/workspace-template.yaml"

    try:
        with open(template_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Template file not found at {template_path}")
        raise HTTPException(status_code=500, detail="Workspace template not found")

def apply_manifest(namespace: str) -> None:
    """Apply Kubernetes manifests for a new workspace"""
    template = load_manifest_template()
    manifest_yaml = template.replace("${NAMESPACE}", namespace)

    # Parse and apply each document in the YAML
    from kubernetes import utils
    try:
        utils.create_from_yaml_data(k8s_client, manifest_yaml)
        logger.info(f"Applied manifests for namespace: {namespace}")
    except ApiException as e:
        logger.error(f"Failed to apply manifests: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create workspace: {e}")

def get_workspace_status(namespace: str) -> str:
    """Get the status of a workspace deployment"""
    try:
        deployment = apps_v1.read_namespaced_deployment(
            name="vscode-server",
            namespace=namespace
        )

        if deployment.status.ready_replicas and deployment.status.ready_replicas > 0:
            return "ready"
        elif deployment.status.replicas and deployment.status.replicas > 0:
            return "starting"
        else:
            return "pending"
    except ApiException:
        return "unknown"

@app.get("/")
async def root():
    return {"message": "Roo SaaS Backend API", "version": "1.0.0"}

@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(request: ProjectRequest = None):
    """Create a new workspace project"""
    namespace = generate_namespace()

    try:
        # Apply Kubernetes manifests
        apply_manifest(namespace)

        # Return project info
        return ProjectResponse(
            namespace=namespace,
            url=f"http://localhost/{namespace}/",
            status="creating"
        )
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects", response_model=List[ProjectResponse])
async def list_projects():
    """List all active workspace projects"""
    try:
        # Get all namespaces with roo=true label
        namespaces = v1.list_namespace(label_selector="roo=true")

        projects = []
        for ns in namespaces.items:
            namespace = ns.metadata.name
            status = get_workspace_status(namespace)

            projects.append(ProjectResponse(
                namespace=namespace,
                url=f"http://localhost/{namespace}/",
                status=status
            ))

        return projects
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{namespace}")
async def delete_project(namespace: str):
    """Delete a workspace project"""
    try:
        # Delete the namespace (this will delete all resources in it)
        v1.delete_namespace(name=namespace)
        logger.info(f"Deleted namespace: {namespace}")
        return {"message": f"Project {namespace} deleted successfully"}
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Project not found")
        logger.error(f"Failed to delete project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Kubernetes connectivity
        v1.list_namespace(limit=1)
        return {"status": "healthy", "kubernetes": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
