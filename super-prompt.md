# Copy-and-Paste "Super-Prompt" for Roo Code / ChatGPT

**Feed this entire block to your AI agent; it will generate the complete local MVP for you.**

---

**SYSTEM CONTEXT**
You are an expert DevOps engineer.
Goal: spin up a LOCAL proof-of-concept SaaS that runs OpenVSCode-Server + Roo Code for each "project", using a single-node k3d cluster on my laptop.
No authentication, no billing, no TLS. Everything reachable at http://localhost.

**HARD REQUIREMENTS**
1. Use only free, local-install tools: Docker, k3d, kubectl, Helm, and k9s.
2. Provide copy-ready shell commands, Helm / YAML manifests, and minimal React frontend code.
3. One button ("Create Project") on the front page must:
   • call a tiny FastAPI backend on port 5000
   • backend generates a new Kubernetes namespace `proj-<random>`
   • backend applies a Deployment + Service + Ingress that runs
     `gitpod/openvscode-server:latest` **with Roo Code pre-installed**
   • Ingress exposes the IDE at `http://localhost/<namespace>/` via the built-in k3d Traefik.
4. Show how to pre-install the Roo Code `.vsix` during container start-up.
5. Auto-delete projects older than 2 hours with a simple CronJob.
6. Everything lives in a single Git repo with this structure:

```
mvp-roo-saas/
├── frontend/          # React Vite app
├── backend/           # FastAPI + kubernetes-python client
├── k3d/              # cluster-bootstrap scripts & Helm charts
├── manifests/        # base YAML templates (Namespace, Deployment, Service, Ingress, CronJob)
└── README.md         # quick-start
```

**STEP-BY-STEP DELIVERABLES**

1. **Quick-start instructions** (`README.md`)
   - prerequisites
   - `make up` → spins k3d, applies charts, starts backend & frontend in Docker Compose
   - `make down` → tears everything down

2. **k3d bootstrap script**
   - create cluster `k3d cluster create roo --agents 1 --port "80:80@loadbalancer"`
   - install Traefik (already bundled)
   - install metrics-server (Helm)

3. **Base workspace template (Helm or raw YAML)**
   Values to substitute: `namespace`, `subPath`.
   Deployment mounts an emptyDir at `/home/workspace`, sets env
   `ALLOWED_EXTENSIONS="roo-code"` and runs:
   ```bash
   openvscode-server --install-extension /roo-code.vsix --host 0.0.0.0 --port 3000
   ```
   Then a simple HTTP liveness probe on `/.`

4. **FastAPI backend**
   - endpoint `POST /api/projects` → creates namespace + applies manifests (use pydantic models).
   - endpoint `GET /api/projects` → list live namespaces for UI.

5. **React frontend**
   - Vite + Chakra UI (or plain CSS)
   - "Create Project" → fetch `/api/projects` (POST)
   - renders list: "Project abc123 ➜ Open IDE" → href `http://localhost/abc123/`

6. **CronJob cleanup**
   runs `kubectl delete ns $(kubectl get ns -l roo=true --no-headers | awk '$5 > 2 {print $1}')`
   where namespace label `roo=true` is set on each project and `$5` is AGE (hours) via `-o jsonpath`

7. **Docker Compose dev stack**
   ```yaml
   services:
     backend:
       build: ./backend
       ports: ["5000:5000"]
       env_file: .env
     frontend:
       build: ./frontend
       ports: ["3000:80"]
       depends_on: [backend]
   ```

8. **Makefile helpers**
   - `make up`: k3d cluster + compose up --build
   - `make down`: compose down && k3d cluster delete roo
   - `make logs`: tail backend & cluster pods

9. **Testing script** (`bash tests/smoke.sh`)
   curl POST to backend, wait for Deployment ready, curl `http://localhost/<ns>/` returns HTML.

**STYLE**
Write concise, well-commented code. Use placeholders `<namespace>` clearly indicated.
No superfluous boilerplate. Prefer Bash one-liners over lengthy prose where possible.

**OUTPUT FORMAT**
Return a single Markdown document containing:
- Quick-start section
- All code blocks grouped by folder path
- Any explanatory notes inline as HTML comments `<!-- note -->`

**START NOW. DO NOT OMIT ANY FILE CONTENTS.**

---

### How to use it

1. **Open your AI assistant** (ChatGPT, Roo Code "Plan Mode", etc.).
2. Paste everything above in one go.
3. Hit *Run / Ask / Execute*.
4. The AI will respond with an entire repo scaffold.
5. Copy the generated files into `mvp-roo-saas/`, run `make up`, and navigate to `http://localhost`.

You now have a local, self-contained MVP that demonstrates on-demand project workspaces running OpenVSCode-Server with Roo Code, all orchestrated by a k3d Kubernetes cluster—no auth, no billing, just proof of concept.
