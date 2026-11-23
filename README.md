# Hello World project: Flask on Kubernetes with Jenkins, Helm and Argo CD
## Project overview
A minimal Flask application that returns **Hello World**, delivered through a complete CI/CD and GitOps ## workflow:
1. **CI (Jenkins)** – clones the repo, runs tests, builds the Docker image, scans it with Trivy, tags and pushes it to Docker Hub, and deploys to Kubernetes.
2. **Helm** – the Kubernetes manifests are packaged as a Helm chart.
3. **GitOps (Argo CD)** – Argo CD syncs the chart from GitHub automatically.
4. **Multi-environment** – `dev`, `stage` and `prod` differ in replica count, image tag and resource limits.
5. **App of Apps** – one parent Argo CD application manages all three environments.
### Repository layout:
.
├── app/                    
├── Dockerfile
├── Jenkinsfile
├── k8s/                    # Plain manifests (used by Jenkins)
│   ├── deployment.yaml
│   └── service.yaml
├── helm/hello-world/       # Helm chart
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
├── environments/           # Per-environment Helm values
│   ├── dev/values.yaml
│   ├── stage/values.yaml
│   └── prod/values.yaml
├── argocd/
│   ├── application.yaml    # Single Argo CD Application
│   ├── app-of-apps.yaml    # Parent application
│   └── apps/               # Child apps: dev, stage, prod
└── README.md
### Environments:
| Env   | Namespace | Replicas | Image tag | CPU req/limit | Memory req/limit | NodePort |
|-------|-----------|----------|-----------|---------------|------------------|----------|
| dev   | `dev`     | 2        | `v3`      | 50m / 100m    | 64Mi / 128Mi     | 30081    |
| stage | `stage`   | 3        | `v2`      | 100m / 250m   | 128Mi / 256Mi    | 30082    |
| prod  | `prod`    | 4        | `v1`      | 200m / 500m   | 256Mi / 512Mi    | 30083    |
NodePorts differ per environment so all three can run on the same single-node cluster.
## Prerequisites
Install the following:
| Tool | Purpose |
|------|---------|
| Docker | Build and push images |
| Jenkins (VM or container) | CI pipeline |
| k3s (or equivalent) | Kubernetes cluster |
| git | Source control |
| Trivy (binary or container) | Image vulnerability scanning |
| Helm | Chart install / templating |
| Argo CD | GitOps controller |
| Argo Rollouts | Progressive delivery controller (installed per the course prerequisites; the manifests in this repo use standard Deployments) |
```
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
```
> The Jenkins agent needs `docker`, `kubectl`, `trivy` and `python3` (with `venv`) available. If Jenkins runs in a container, build a custom image that includes them or install them into the container.
## Deployment instructions
Before anything else, replace the placeholders in the repo:
- `your-dockerhub-user` → your Docker Hub username (`Jenkinsfile`, `k8s/deployment.yaml`, `helm/hello-world/values.yaml`)
- `your-github-user` → your GitHub username (`Jenkinsfile`, everything under `argocd/`)
### 1. Run locally
```bash
cd app
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
python app.py            # http://localhost:5000
```
### 2. Build and push the image manually
```bash
docker build -t <dockerhub-user>/hello-world:v1 .
docker login
docker push <dockerhub-user>/hello-world:v1
```
Push `v2` and `v3` as well (or change the tags in `environments/*/values.yaml`) so every environment can pull its image.
### 3. Deploy with plain manifests
```bash
kubectl apply -f k8s/
kubectl get pods,svc
```
Open `http://<node-ip>:30080`.
### 4. Jenkins pipeline
1. In Jenkins, install the plugins: **Pipeline**, **Git**, **Credentials Binding**.
2. Add credentials:
   - `dockerhub-creds` – *Username with password* (Docker Hub user + access token)
   - `kubeconfig` – *Secret file* (your k3s kubeconfig; make sure `server:` points to an address reachable from Jenkins, not `127.0.0.1`)
3. Create a **Pipeline** job → *Pipeline script from SCM* → Git → your repo URL, branch `main`, script path `Jenkinsfile`.
4. Click **Build Now**.
Pipeline stages: Clone Repository → Build Application → Build Docker Image → Security Scan (Trivy) → Tag Image → Push to Docker Hub → Deploy to Kubernetes.
#### Jenkins screenshots
> Add a screenshot of a successful run here after your first green build:
```markdown
![Successful Jenkins pipeline](docs/screenshots/jenkins-success.png)
```
### 5. Helm
```bash
cd helm/hello-world
helm lint .
helm template hello-world .       # preview rendered manifests
helm install hello-world .
helm list
```
Upgrade / uninstall:

```bash
helm upgrade hello-world . --set replicaCount=3
helm uninstall hello-world
```
Install one environment manually:
```bash
helm install hello-world-dev ./helm/hello-world \
  -f environments/dev/values.yaml -n dev --create-namespace
```
### 6. Argo CD (single application)
```bash
# Get the admin password and open the UI
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
kubectl -n argocd port-forward svc/argocd-server 8443:443    # https://localhost:8443
# Create the application
kubectl apply -f argocd/application.yaml
```
The application has `automated` sync with `prune` and `selfHeal`, so any push to `main` is deployed automatically.
### 7. Argo CD App of Apps (dev, stage, prod)
Remove the single app first if you created it (both would try to use the same chart), then:
```bash
kubectl delete -f argocd/application.yaml --ignore-not-found
kubectl apply -f argocd/app-of-apps.yaml
```
Argo CD creates `hello-world-dev`, `hello-world-stage` and `hello-world-prod` from `argocd/apps/`, and each syncs automatically from Git.
```bash
kubectl get applications -n argocd
kubectl get pods -n dev; kubectl get pods -n stage; kubectl get pods -n prod
```
Access: `http://<node-ip>:30081` (dev), `:30082` (stage), `:30083` (prod).
To promote a release, edit `image.tag` in `environments/<env>/values.yaml`, commit and push; Argo CD rolls it out.