#!/bin/bash

# Script to fix workspace template volume mounting issues
# This script ensures the workspace template is properly deployed with hostPath volumes

set -e

echo "🔧 Fixing workspace template volume mounting..."

# Get the absolute path to the workspace directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../../workspace" && pwd)"
MANIFESTS_DIR="$(cd "$SCRIPT_DIR/../manifests" && pwd)"

if [ ! -d "$WORKSPACE_DIR" ]; then
    echo "❌ Workspace directory not found at $WORKSPACE_DIR"
    exit 1
fi

echo "📁 Workspace directory: $WORKSPACE_DIR"
echo "📁 Manifests directory: $MANIFESTS_DIR"

# Get kind cluster name
CLUSTER_NAME="roo"

# Check if kind cluster exists
if ! kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "❌ Kind cluster '$CLUSTER_NAME' not found. Please create the cluster first."
    exit 1
fi

echo "✅ Found kind cluster: $CLUSTER_NAME"

# Re-run workspace template setup to ensure files are on all nodes
echo ""
echo "📦 Re-running workspace template setup..."
../scripts/setup-workspace-template.sh

# Check if there are any existing workspace deployments with emptyDir volumes
echo ""
echo "🔍 Checking for existing workspace deployments with volume issues..."

export KUBECONFIG="$(pwd)/kubeconfig-host"

# Get all namespaces with roo label
NAMESPACES=$(kubectl get namespaces -l roo=true -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

if [ -n "$NAMESPACES" ]; then
    echo "📋 Found workspace namespaces: $NAMESPACES"

    for NAMESPACE in $NAMESPACES; do
        echo ""
        echo "🔧 Checking workspace in namespace: $NAMESPACE"

        # Check if deployment exists
        if kubectl get deployment -n "$NAMESPACE" vscode-server >/dev/null 2>&1; then
            # Check if it has emptyDir volume for workspace-template
            VOLUME_TYPE=$(kubectl get deployment -n "$NAMESPACE" vscode-server -o jsonpath='{.spec.template.spec.volumes[?(@.name=="workspace-template")].emptyDir}' 2>/dev/null || echo "")

            if [ -n "$VOLUME_TYPE" ]; then
                echo "⚠️  Found deployment with emptyDir volume - needs fixing"

                # Delete the deployment to force recreation with correct volume
                echo "🗑️  Deleting deployment to force recreation..."
                kubectl delete deployment -n "$NAMESPACE" vscode-server

                # Wait a moment for cleanup
                sleep 2

                # Recreate deployment with correct template
                echo "🚀 Recreating deployment with fixed volume mounting..."
                envsubst < "$MANIFESTS_DIR/workspace-template.yaml" | \
                    NAMESPACE="$NAMESPACE" envsubst | \
                    kubectl apply -f -

                echo "✅ Fixed deployment in namespace: $NAMESPACE"
            else
                echo "✅ Deployment already has correct volume configuration"
            fi
        else
            echo "ℹ️  No vscode-server deployment found in namespace: $NAMESPACE"
        fi
    done
else
    echo "ℹ️  No workspace namespaces found"
fi

echo ""
echo "🎉 Workspace template volume mounting fix complete!"
echo ""
echo "📋 Summary:"
echo "- Workspace template files updated on all kind nodes"
echo "- Existing deployments with volume issues have been fixed"
echo "- New workspaces will automatically have correct volume mounting"
echo ""
echo "🚀 Next steps:"
echo "1. Create a new workspace via the frontend"
echo "2. The workspace will automatically include the full MCP server"
echo "3. Use the MCP tools to deploy static applications"
