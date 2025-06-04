# RBAC Setup for Roo SaaS MVP

This document explains the Role-Based Access Control (RBAC) setup for the Roo SaaS MVP, which provides proper permissions for kubectl and skaffold to work within workspace namespaces.

## Overview

Each workspace gets its own namespace with a dedicated service account that has:
- Full permissions within its own namespace
- Read-only access to cluster-wide resources (nodes, storage classes, etc.)
- No permissions in other namespaces (proper isolation)

## RBAC Components

### 1. ServiceAccount (`workspace-deployer`)
- Created in each workspace namespace
- Used by the vscode-server pod
- Provides identity for RBAC bindings

### 2. Role (`workspace-deployer-role`)
- Namespace-scoped permissions
- Allows full CRUD operations on:
  - Pods, Services, Deployments, ConfigMaps, Secrets
  - Ingresses, Jobs, CronJobs
  - HorizontalPodAutoscalers, PodDisruptionBudgets
  - ServiceAccounts, Roles, RoleBindings (for skaffold)

### 3. RoleBinding (`workspace-deployer-binding`)
- Binds the `workspace-deployer-role` to the `workspace-deployer` service account
- Scoped to the workspace namespace only

### 4. ClusterRole (`workspace-cluster-reader-{namespace}`)
- Cluster-wide read-only permissions for:
  - Nodes, Namespaces, PersistentVolumes
  - StorageClasses, CustomResourceDefinitions
  - Metrics (for `kubectl top`)

### 5. ClusterRoleBinding (`workspace-cluster-reader-{namespace}`)
- Binds the cluster reader role to the workspace service account
- Allows read access to cluster-wide resources

## How It Works

### 1. Workspace Creation
When a new workspace is created via the backend API:
1. RBAC resources are applied first (ServiceAccount, Role, RoleBinding, ClusterRole, ClusterRoleBinding)
2. Workspace resources are applied (Namespace, Deployment, Service, Ingress)
3. The vscode-server pod uses the `workspace-deployer` service account

### 2. kubectl Configuration
The vscode-server pod automatically sets up kubectl with:
- Service account token authentication
- Namespace context set to the workspace namespace
- CA certificate from the service account

### 3. Permission Scope
- **Within namespace**: Full permissions to create/modify/delete resources
- **Cluster-wide**: Read-only access to nodes, storage classes, etc.
- **Other namespaces**: No access (proper isolation)

## Security Features

### Namespace Isolation
- Each workspace can only access resources in its own namespace
- Cannot view or modify resources in other workspaces
- Cannot access system namespaces (kube-system, etc.)

### Principle of Least Privilege
- Only the minimum required permissions are granted
- Cluster-wide permissions are read-only
- No access to sensitive cluster resources

### Automatic Cleanup
- When a workspace is deleted, all RBAC resources are cleaned up
- Cluster-wide resources are properly removed
- No orphaned permissions remain

## Supported Operations

### kubectl Commands
- `kubectl get pods` - List pods in workspace namespace
- `kubectl create deployment` - Create deployments
- `kubectl apply -f manifest.yaml` - Apply manifests
- `kubectl logs pod-name` - View pod logs
- `kubectl exec -it pod-name -- bash` - Execute into pods
- `kubectl top pods` - View resource usage
- `kubectl get nodes` - View cluster nodes (read-only)

### skaffold Operations
- `skaffold dev` - Development workflow
- `skaffold run` - Deploy applications
- `skaffold delete` - Clean up deployments
- Create temporary service accounts and roles as needed

## Testing Permissions

You can test the RBAC setup by accessing a workspace and running:

```bash
# Test namespace permissions (should work)
kubectl auth can-i create deployments
kubectl auth can-i create services
kubectl auth can-i get pods

# Test cluster permissions (should work - read only)
kubectl auth can-i get nodes
kubectl auth can-i list namespaces

# Test isolation (should fail)
kubectl auth can-i create deployments -n default
kubectl auth can-i create deployments -n kube-system
```

## Files

- `manifests/rbac-template.yaml` - RBAC resource template
- `manifests/workspace-template.yaml` - Workspace template (updated with serviceAccountName)
- `backend/main.py` - Backend with RBAC support

## Troubleshooting

### Permission Denied Errors
1. Check if the service account exists: `kubectl get sa workspace-deployer`
2. Verify role bindings: `kubectl get rolebinding workspace-deployer-binding`
3. Test permissions: `kubectl auth can-i <verb> <resource>`

### kubectl Not Working
1. Check if kubeconfig is properly set up in the pod
2. Verify service account token is mounted
3. Check if the pod is using the correct service account

### Cross-Namespace Access
This is intentionally blocked. Each workspace should only access its own namespace. If you need cross-namespace access, you'll need to modify the RBAC templates (not recommended for security reasons).
