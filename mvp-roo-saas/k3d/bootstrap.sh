#!/bin/bash
set -e

echo "🚀 Creating k3d cluster 'roo'..."

# Delete existing cluster if it exists
k3d cluster delete roo 2>/dev/null || true

# Create cluster with port mapping for Traefik
k3d cluster create roo \
  --agents 1 \
  --port "80:80@loadbalancer" \
  --wait

echo "✅ k3d cluster 'roo' created"

# Fix kubeconfig to use localhost instead of host.docker.internal
echo "🔧 Fixing kubeconfig server address..."
K3D_PORT=$(docker port k3d-roo-serverlb 6443 | cut -d: -f2)
echo "Detected k3d API server port: $K3D_PORT"
kubectl config set-cluster k3d-roo --server=https://localhost:$K3D_PORT

# Wait for API server to be ready
echo "⏳ Waiting for API server to be ready..."
for i in {1..30}; do
  if kubectl get nodes >/dev/null 2>&1; then
    echo "✅ API server is ready!"
    break
  fi
  echo "Waiting for API server... (attempt $i/30)"
  sleep 2
done

# Wait for cluster to be ready
kubectl wait --for=condition=Ready nodes --all --timeout=60s

echo "📦 Metrics-server is already provided by k3d, skipping installation..."

echo "🎯 Applying cleanup CronJob..."
kubectl apply -f ../manifests/cleanup-cronjob.yaml

echo "🎉 k3d cluster ready! Traefik available at http://localhost"
echo "💡 Use 'kubectl get nodes' to verify cluster status"
