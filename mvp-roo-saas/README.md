# MVP Roo SaaS - Local Proof of Concept

A local SaaS that spins up on-demand OpenVSCode-Server workspaces with Roo Code pre-installed, orchestrated by k3d Kubernetes cluster.

## Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- k3d: `curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash`
- kubectl: `curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl" && chmod +x kubectl && sudo mv kubectl /usr/local/bin/`
- Helm: `curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash`
- k9s (optional): `brew install k9s` or download from releases

## Quick Start

```bash
# Spin up everything
make up

# Access the frontend
open http://localhost:3000

# Tear down everything
make down

# View logs
make logs
```

## How it works

1. **Frontend** (React + Vite) on port 3000 with "Create Project" button
2. **Backend** (FastAPI) on port 5000 handles project creation
3. **k3d cluster** runs workspaces as Kubernetes deployments
4. **Traefik ingress** exposes each workspace at `http://localhost/<namespace>/`
5. **CronJob** auto-deletes projects older than 2 hours

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React App     │───▶│   FastAPI       │───▶│   k3d Cluster   │
│   :3000         │    │   :5000         │    │   :80           │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                               ┌───────▼────────┐
                                               │  VSCode Server │
                                               │  + Roo Code    │
                                               └────────────────┘
```

## Testing

```bash
# Run smoke tests
bash tests/smoke.sh
