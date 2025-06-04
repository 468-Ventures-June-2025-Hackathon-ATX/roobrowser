#!/bin/bash
set -e

echo "🚀 Creating kind cluster 'roo' from config..."

# Delete existing cluster if it exists
kind delete cluster --name roo 2>/dev/null || true

# Create cluster from kind-config.yaml
kind create cluster --config kind-config.yaml

echo "✅ kind cluster 'roo' created from config"

# Generate isolated kubeconfig for host
echo "📝 Creating isolated kubeconfig for host..."
kind get kubeconfig --name roo > kubeconfig-host
echo "✅ Host kubeconfig created at kind/kubeconfig-host"

# Generate Docker-compatible kubeconfig (replace 127.0.0.1 with container IP)
echo "📝 Creating Docker-compatible kubeconfig..."
CONTROL_PLANE_IP=$(docker inspect roo-control-plane | grep -A 15 '"Networks"' | grep '"IPAddress"' | cut -d'"' -f4)
sed "s/127.0.0.1:[0-9]*/${CONTROL_PLANE_IP}:6443/g" kubeconfig-host > kubeconfig-docker
echo "✅ Docker kubeconfig created at kind/kubeconfig-docker using IP: ${CONTROL_PLANE_IP}"

# Set KUBECONFIG to use the isolated config for this session
export KUBECONFIG="$(pwd)/kubeconfig-host"
echo "🔧 Using isolated kubeconfig: $KUBECONFIG"

# Wait for API server to be ready
echo "⏳ Waiting for API server to be ready..."
KUBECONFIG_PATH="$(pwd)/kubeconfig-host"
echo "🔍 Using kubeconfig: $KUBECONFIG_PATH"

for i in {1..30}; do
  if KUBECONFIG="$KUBECONFIG_PATH" kubectl get nodes >/dev/null 2>&1; then
    echo "✅ API server is ready!"
    break
  fi
  echo "Waiting for API server... (attempt $i/30)"
  sleep 2
done

# Wait for cluster to be ready
echo "⏳ Waiting for nodes to be ready..."
KUBECONFIG="$KUBECONFIG_PATH" kubectl wait --for=condition=Ready nodes --all --timeout=60s

# Install metrics-server for kind
echo "📦 Installing metrics-server..."
KUBECONFIG="$KUBECONFIG_PATH" kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Patch metrics-server for kind (disable TLS verification)
echo "🔧 Patching metrics-server for kind..."
KUBECONFIG="$KUBECONFIG_PATH" kubectl patch deployment metrics-server -n kube-system --type='json' -p='[
  {
    "op": "add",
    "path": "/spec/template/spec/containers/0/args/-",
    "value": "--kubelet-insecure-tls"
  }
]'

# Install NGINX Ingress Controller for kind
echo "📦 Installing NGINX Ingress Controller..."
KUBECONFIG="$KUBECONFIG_PATH" kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Wait for ingress controller to be ready
echo "⏳ Waiting for NGINX Ingress Controller to be ready..."
KUBECONFIG="$KUBECONFIG_PATH" kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

echo "🎯 Applying cleanup CronJob..."
KUBECONFIG="$KUBECONFIG_PATH" kubectl apply -f ../manifests/cleanup-cronjob.yaml

echo "✅ Cleanup CronJob applied successfully"

# Setup workspace template on kind nodes
echo ""
echo "📦 Setting up workspace template on kind nodes..."
if [ -f "../scripts/setup-workspace-template.sh" ]; then
    ../scripts/setup-workspace-template.sh
else
    echo "⚠️  Workspace template setup script not found"
    echo "💡 You can manually run: scripts/setup-workspace-template.sh"
fi

echo ""
echo "🎉 Kind cluster setup complete!"
echo "📋 Cluster info:"
KUBECONFIG="$KUBECONFIG_PATH" kubectl cluster-info --context kind-roo
echo ""
echo "🚀 Ready to deploy workspaces with MCP server!"
