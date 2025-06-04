import os
import random
import string
import logging
import urllib3
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        # If we're using host.docker.internal, disable SSL verification
        configuration = client.Configuration.get_default_copy()
        if "host.docker.internal" in configuration.host:
            configuration.verify_ssl = False
            configuration.ssl_ca_cert = None
            configuration.assert_hostname = False
            client.Configuration.set_default(configuration)
            logger.info("Disabled SSL verification for host.docker.internal")
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
    import yaml
    try:
        # Parse the YAML documents
        documents = list(yaml.safe_load_all(manifest_yaml))

        for doc in documents:
            if not doc:  # Skip empty documents
                continue

            kind = doc.get('kind')
            api_version = doc.get('apiVersion')
            metadata = doc.get('metadata', {})
            doc_namespace = metadata.get('namespace', 'default')
            name = metadata.get('name')

            if kind == 'Namespace':
                # Create namespace
                namespace_obj = client.V1Namespace(
                    metadata=client.V1ObjectMeta(
                        name=name,
                        labels=metadata.get('labels', {})
                    )
                )
                try:
                    v1.create_namespace(namespace_obj)
                    logger.info(f"Created namespace: {name}")
                except ApiException as e:
                    if e.status == 409:  # Already exists
                        logger.info(f"Namespace {name} already exists")
                    else:
                        raise

            elif kind == 'Deployment':
                # Create deployment
                deployment_obj = client.V1Deployment(
                    api_version=api_version,
                    kind=kind,
                    metadata=client.V1ObjectMeta(
                        name=name,
                        namespace=doc_namespace,
                        labels=metadata.get('labels', {})
                    ),
                    spec=client.V1DeploymentSpec(
                        replicas=doc['spec']['replicas'],
                        selector=client.V1LabelSelector(
                            match_labels=doc['spec']['selector']['matchLabels']
                        ),
                        template=client.V1PodTemplateSpec(
                            metadata=client.V1ObjectMeta(
                                labels=doc['spec']['template']['metadata']['labels']
                            ),
                            spec=client.V1PodSpec(
                                containers=[
                                    client.V1Container(
                                        name=container['name'],
                                        image=container['image'],
                                        ports=[client.V1ContainerPort(container_port=port['containerPort'])
                                               for port in container.get('ports', [])],
                                        env=[client.V1EnvVar(name=env['name'], value=env['value'])
                                            for env in container.get('env', [])],
                                        command=container.get('command'),
                                        volume_mounts=[
                                            client.V1VolumeMount(
                                                name=vm['name'],
                                                mount_path=vm['mountPath']
                                            ) for vm in container.get('volumeMounts', [])
                                        ],
                                        liveness_probe=client.V1Probe(
                                            http_get=client.V1HTTPGetAction(
                                                path=container['livenessProbe']['httpGet']['path'],
                                                port=container['livenessProbe']['httpGet']['port']
                                            ),
                                            initial_delay_seconds=container['livenessProbe']['initialDelaySeconds'],
                                            period_seconds=container['livenessProbe']['periodSeconds']
                                        ) if 'livenessProbe' in container else None,
                                        readiness_probe=client.V1Probe(
                                            http_get=client.V1HTTPGetAction(
                                                path=container['readinessProbe']['httpGet']['path'],
                                                port=container['readinessProbe']['httpGet']['port']
                                            ),
                                            initial_delay_seconds=container['readinessProbe']['initialDelaySeconds'],
                                            period_seconds=container['readinessProbe']['periodSeconds']
                                        ) if 'readinessProbe' in container else None,
                                        resources=client.V1ResourceRequirements(
                                            requests=container['resources']['requests'],
                                            limits=container['resources']['limits']
                                        ) if 'resources' in container else None
                                    ) for container in doc['spec']['template']['spec']['containers']
                                ],
                                volumes=[
                                    client.V1Volume(
                                        name=volume['name'],
                                        empty_dir=client.V1EmptyDirVolumeSource()
                                    ) for volume in doc['spec']['template']['spec'].get('volumes', [])
                                ]
                            )
                        )
                    )
                )
                apps_v1.create_namespaced_deployment(namespace=doc_namespace, body=deployment_obj)
                logger.info(f"Created deployment: {name} in namespace: {doc_namespace}")

            elif kind == 'Service':
                # Create service
                service_obj = client.V1Service(
                    api_version=api_version,
                    kind=kind,
                    metadata=client.V1ObjectMeta(
                        name=name,
                        namespace=doc_namespace,
                        labels=metadata.get('labels', {})
                    ),
                    spec=client.V1ServiceSpec(
                        selector=doc['spec']['selector'],
                        ports=[
                            client.V1ServicePort(
                                port=port['port'],
                                target_port=port['targetPort'],
                                protocol=port['protocol']
                            ) for port in doc['spec']['ports']
                        ],
                        type=doc['spec']['type']
                    )
                )
                v1.create_namespaced_service(namespace=doc_namespace, body=service_obj)
                logger.info(f"Created service: {name} in namespace: {doc_namespace}")

            elif kind == 'Ingress':
                # Create ingress
                ingress_obj = client.V1Ingress(
                    api_version=api_version,
                    kind=kind,
                    metadata=client.V1ObjectMeta(
                        name=name,
                        namespace=doc_namespace,
                        labels=metadata.get('labels', {}),
                        annotations=metadata.get('annotations', {})
                    ),
                    spec=client.V1IngressSpec(
                        ingress_class_name=doc['spec'].get('ingressClassName'),
                        rules=[
                            client.V1IngressRule(
                                http=client.V1HTTPIngressRuleValue(
                                    paths=[
                                        client.V1HTTPIngressPath(
                                            path=path['path'],
                                            path_type=path['pathType'],
                                            backend=client.V1IngressBackend(
                                                service=client.V1IngressServiceBackend(
                                                    name=path['backend']['service']['name'],
                                                    port=client.V1ServiceBackendPort(
                                                        number=path['backend']['service']['port']['number']
                                                    )
                                                )
                                            )
                                        ) for path in rule['http']['paths']
                                    ]
                                )
                            ) for rule in doc['spec']['rules']
                        ]
                    )
                )
                networking_v1.create_namespaced_ingress(namespace=doc_namespace, body=ingress_obj)
                logger.info(f"Created ingress: {name} in namespace: {doc_namespace}")

        logger.info(f"Applied all manifests for namespace: {namespace}")
    except Exception as e:
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
