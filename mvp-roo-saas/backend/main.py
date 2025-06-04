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
rbac_v1 = client.RbacAuthorizationV1Api()

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

def load_manifest_template(template_name: str) -> str:
    """Load a manifest template YAML"""
    template_path = f"/app/manifests/{template_name}"
    if not os.path.exists(template_path):
        template_path = f"../manifests/{template_name}"

    try:
        with open(template_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Template file not found at {template_path}")
        raise HTTPException(status_code=500, detail=f"Template {template_name} not found")

def _create_volume(volume_spec: dict) -> client.V1Volume:
    """Create a Kubernetes volume from volume specification"""
    volume_name = volume_spec['name']
    logger.info(f"Creating volume {volume_name} with spec: {volume_spec}")

    if 'emptyDir' in volume_spec:
        logger.info(f"Creating emptyDir volume: {volume_name}")
        return client.V1Volume(
            name=volume_name,
            empty_dir=client.V1EmptyDirVolumeSource()
        )
    elif 'hostPath' in volume_spec:
        host_path_spec = volume_spec['hostPath']
        logger.info(f"Creating hostPath volume: {volume_name} -> {host_path_spec['path']}")
        return client.V1Volume(
            name=volume_name,
            host_path=client.V1HostPathVolumeSource(
                path=host_path_spec['path'],
                type=host_path_spec.get('type')
            )
        )
    elif 'configMap' in volume_spec:
        config_map_spec = volume_spec['configMap']
        logger.info(f"Creating configMap volume: {volume_name}")
        return client.V1Volume(
            name=volume_name,
            config_map=client.V1ConfigMapVolumeSource(
                name=config_map_spec['name']
            )
        )
    elif 'secret' in volume_spec:
        secret_spec = volume_spec['secret']
        logger.info(f"Creating secret volume: {volume_name}")
        return client.V1Volume(
            name=volume_name,
            secret=client.V1SecretVolumeSource(
                secret_name=secret_spec['secretName']
            )
        )
    else:
        # Default to emptyDir if no recognized volume type
        logger.warning(f"Unknown volume type for {volume_name}, defaulting to emptyDir. Volume spec: {volume_spec}")
        return client.V1Volume(
            name=volume_name,
            empty_dir=client.V1EmptyDirVolumeSource()
        )

def apply_manifest(namespace: str) -> None:
    """Apply Kubernetes manifests for a new workspace"""
    # First apply RBAC resources
    rbac_template = load_manifest_template("rbac-template.yaml")
    rbac_yaml = rbac_template.replace("${NAMESPACE}", namespace)

    # Then apply workspace resources
    workspace_template = load_manifest_template("workspace-template.yaml")
    workspace_yaml = workspace_template.replace("${NAMESPACE}", namespace)

    # Combine both templates
    manifest_yaml = rbac_yaml + "\n---\n" + workspace_yaml

    # Parse and apply each document in the YAML
    import yaml
    try:
        # Parse the YAML documents
        documents = list(yaml.safe_load_all(manifest_yaml))

        # First pass: Create namespaces
        for doc in documents:
            if not doc:  # Skip empty documents
                continue

            kind = doc.get('kind')
            if kind == 'Namespace':
                api_version = doc.get('apiVersion')
                metadata = doc.get('metadata', {})
                name = metadata.get('name')

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

        # Second pass: Create all other resources
        for doc in documents:
            if not doc:  # Skip empty documents
                continue

            kind = doc.get('kind')
            api_version = doc.get('apiVersion')
            metadata = doc.get('metadata', {})
            doc_namespace = metadata.get('namespace', 'default')
            name = metadata.get('name')

            if kind == 'Namespace':
                # Skip - already handled in first pass
                continue
            elif kind == 'Deployment':
                # Create deployment
                logger.info(f"Creating deployment with volumes: {doc['spec']['template']['spec'].get('volumes', [])}")
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
                                service_account_name=doc['spec']['template']['spec'].get('serviceAccountName'),
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
                                    _create_volume(volume) for volume in doc['spec']['template']['spec'].get('volumes', [])
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

            elif kind == 'ServiceAccount':
                # Create service account
                sa_obj = client.V1ServiceAccount(
                    api_version=api_version,
                    kind=kind,
                    metadata=client.V1ObjectMeta(
                        name=name,
                        namespace=doc_namespace,
                        labels=metadata.get('labels', {})
                    )
                )
                try:
                    v1.create_namespaced_service_account(namespace=doc_namespace, body=sa_obj)
                    logger.info(f"Created service account: {name} in namespace: {doc_namespace}")
                except ApiException as e:
                    if e.status == 409:  # Already exists
                        logger.info(f"Service account {name} already exists")
                    else:
                        raise

            elif kind == 'Role':
                # Create role
                role_obj = client.V1Role(
                    api_version=api_version,
                    kind=kind,
                    metadata=client.V1ObjectMeta(
                        name=name,
                        namespace=doc_namespace,
                        labels=metadata.get('labels', {})
                    ),
                    rules=[
                        client.V1PolicyRule(
                            api_groups=rule.get('apiGroups', []),
                            resources=rule.get('resources', []),
                            verbs=rule.get('verbs', [])
                        ) for rule in doc['rules']
                    ]
                )
                try:
                    rbac_v1.create_namespaced_role(namespace=doc_namespace, body=role_obj)
                    logger.info(f"Created role: {name} in namespace: {doc_namespace}")
                except ApiException as e:
                    if e.status == 409:  # Already exists
                        logger.info(f"Role {name} already exists")
                    else:
                        raise

            elif kind == 'RoleBinding':
                # Create role binding
                rb_obj = client.V1RoleBinding(
                    api_version=api_version,
                    kind=kind,
                    metadata=client.V1ObjectMeta(
                        name=name,
                        namespace=doc_namespace,
                        labels=metadata.get('labels', {})
                    ),
                    subjects=[
                        client.V1Subject(
                            kind=subject.get('kind'),
                            name=subject.get('name'),
                            namespace=subject.get('namespace')
                        ) for subject in doc['subjects']
                    ],
                    role_ref=client.V1RoleRef(
                        api_group=doc['roleRef']['apiGroup'],
                        kind=doc['roleRef']['kind'],
                        name=doc['roleRef']['name']
                    )
                )
                try:
                    rbac_v1.create_namespaced_role_binding(namespace=doc_namespace, body=rb_obj)
                    logger.info(f"Created role binding: {name} in namespace: {doc_namespace}")
                except ApiException as e:
                    if e.status == 409:  # Already exists
                        logger.info(f"Role binding {name} already exists")
                    else:
                        raise

            elif kind == 'ClusterRole':
                # Create cluster role
                cr_obj = client.V1ClusterRole(
                    api_version=api_version,
                    kind=kind,
                    metadata=client.V1ObjectMeta(
                        name=name,
                        labels=metadata.get('labels', {})
                    ),
                    rules=[
                        client.V1PolicyRule(
                            api_groups=rule.get('apiGroups', []),
                            resources=rule.get('resources', []),
                            verbs=rule.get('verbs', [])
                        ) for rule in doc['rules']
                    ]
                )
                try:
                    rbac_v1.create_cluster_role(body=cr_obj)
                    logger.info(f"Created cluster role: {name}")
                except ApiException as e:
                    if e.status == 409:  # Already exists
                        logger.info(f"Cluster role {name} already exists")
                    else:
                        raise

            elif kind == 'ClusterRoleBinding':
                # Create cluster role binding
                crb_obj = client.V1ClusterRoleBinding(
                    api_version=api_version,
                    kind=kind,
                    metadata=client.V1ObjectMeta(
                        name=name,
                        labels=metadata.get('labels', {})
                    ),
                    subjects=[
                        client.V1Subject(
                            kind=subject.get('kind'),
                            name=subject.get('name'),
                            namespace=subject.get('namespace')
                        ) for subject in doc['subjects']
                    ],
                    role_ref=client.V1RoleRef(
                        api_group=doc['roleRef']['apiGroup'],
                        kind=doc['roleRef']['kind'],
                        name=doc['roleRef']['name']
                    )
                )
                try:
                    rbac_v1.create_cluster_role_binding(body=crb_obj)
                    logger.info(f"Created cluster role binding: {name}")
                except ApiException as e:
                    if e.status == 409:  # Already exists
                        logger.info(f"Cluster role binding {name} already exists")
                    else:
                        raise

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
        # Delete cluster-wide RBAC resources first
        cluster_role_name = f"workspace-cluster-reader-{namespace}"
        cluster_role_binding_name = f"workspace-cluster-reader-{namespace}"

        try:
            rbac_v1.delete_cluster_role(name=cluster_role_name)
            logger.info(f"Deleted cluster role: {cluster_role_name}")
        except ApiException as e:
            if e.status != 404:  # Ignore if not found
                logger.warning(f"Failed to delete cluster role {cluster_role_name}: {e}")

        try:
            rbac_v1.delete_cluster_role_binding(name=cluster_role_binding_name)
            logger.info(f"Deleted cluster role binding: {cluster_role_binding_name}")
        except ApiException as e:
            if e.status != 404:  # Ignore if not found
                logger.warning(f"Failed to delete cluster role binding {cluster_role_binding_name}: {e}")

        # Delete the namespace (this will delete all namespaced resources in it)
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
