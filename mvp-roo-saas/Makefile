.PHONY: up down logs clean status help

# Default target
help:
	@echo "🦘 Roo SaaS MVP - Available commands:"
	@echo ""
	@echo "  make cluster - Start kind cluster only"
	@echo "  make services- Start Docker services and show URLs"
	@echo "  make up      - Start kind cluster and services (cluster + services)"
	@echo "  make down    - Stop services and delete cluster"
	@echo "  make logs    - Show logs from backend and cluster"
	@echo "  make status  - Show cluster and service status"
	@echo "  make clean   - Clean up Docker images and volumes"
	@echo "  make help    - Show this help message"
	@echo ""

# Start kind cluster only
cluster:
	@echo "📦 Creating kind cluster..."
	@cd kind && ./bootstrap.sh

# Start Docker services and show success message
services:
	@echo "🐳 Starting Docker services..."
	@docker compose up --build -d
	@echo ""
	@echo "✅ Roo SaaS MVP is running!"
	@echo "🌐 Frontend: http://localhost:3000"
	@echo "🔧 Backend API: http://localhost:5001"
	@echo "☸️  Kubernetes: kubectl get pods -A"
	@echo ""

# Start everything (cluster + services)
up: cluster services

# Stop everything
down:
	@echo "🛑 Stopping Roo SaaS MVP..."
	@docker compose down
	@kind delete cluster --name roo 2>/dev/null || true
	@echo "✅ Everything stopped and cleaned up!"

# Show logs
logs:
	@echo "📋 Backend logs:"
	@docker compose logs -f backend &
	@echo ""
	@echo "📋 Cluster pods:"
	@KUBECONFIG=kind/kubeconfig-host kubectl get pods -A
	@echo ""
	@echo "📋 Recent cluster events:"
	@KUBECONFIG=kind/kubeconfig-host kubectl get events --sort-by='.lastTimestamp' | tail -10

# Show status
status:
	@echo "📊 System Status:"
	@echo ""
	@echo "🐳 Docker services:"
	@docker compose ps
	@echo ""
	@echo "☸️  kind cluster:"
	@kind get clusters
	@echo ""
	@echo "🏠 Kubernetes namespaces:"
	@KUBECONFIG=kind/kubeconfig-host kubectl get ns -l roo=true 2>/dev/null || echo "No Roo namespaces found"
	@echo ""
	@echo "🌐 Active workspaces:"
	@KUBECONFIG=kind/kubeconfig-host kubectl get pods -l app=vscode-server -A 2>/dev/null || echo "No workspaces running"

# Clean up Docker resources
clean:
	@echo "🧹 Cleaning up Docker resources..."
	@docker compose down -v
	@docker system prune -f
	@docker volume prune -f
	@echo "✅ Cleanup complete!"

# Development helpers
dev-backend:
	@echo "🔧 Starting backend in development mode..."
	@cd backend && python main.py

dev-frontend:
	@echo "🎨 Starting frontend in development mode..."
	@cd frontend && npm run dev

# Quick restart
restart: down up

# Show cluster info
cluster-info:
	@KUBECONFIG=kind/kubeconfig-host kubectl cluster-info
	@KUBECONFIG=kind/kubeconfig-host kubectl get nodes
	@KUBECONFIG=kind/kubeconfig-host kubectl get pods -A
