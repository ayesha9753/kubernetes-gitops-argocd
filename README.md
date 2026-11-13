# Kubernetes GitOps with ArgoCD

A small sample web app deployed to Kubernetes using **Kustomize** (base + dev/prod overlays) and **ArgoCD GitOps**. Push code, CI builds the image, and ArgoCD keeps the cluster in sync with what is in Git — no manual `kubectl apply` in the normal flow.

This is a portfolio / lab project built to demonstrate a real GitOps workflow end to end on a local cluster. It is intentionally lightweight so it runs comfortably on a laptop (kind cluster, small resource requests).

## Architecture flow

```
Developer ──git push──▶ GitHub repo
                          │
                          ▼
                   GitHub Actions (CI)
                   • build Docker image
                   • Trivy vulnerability scan
                   • push image to GHCR
                          │
                          ▼
                   ArgoCD (in cluster)
                   • watches this repo (k8s/overlays/prod)
                   • automated sync: prune + self-heal
                          │
                          ▼
                   Kubernetes cluster (kind)
                   • Deployment → Pods (Flask + gunicorn)
                   • Service (ClusterIP) → Ingress (app.local)
                   • HPA scales 3–6 pods on CPU in prod
```

Git is the single source of truth: to change what runs in the cluster, you change the manifests in this repo and ArgoCD reconciles the cluster to match.

## Repo layout

```
.
├── app/
│   ├── app.py              # Tiny Flask app: / and /health
│   ├── requirements.txt    # flask, gunicorn
│   └── Dockerfile          # Multi-stage, non-root, gunicorn, healthcheck
├── k8s/
│   ├── base/
│   │   ├── deployment.yaml # 2 replicas, probes on /health, resource limits
│   │   ├── service.yaml    # ClusterIP service
│   │   ├── ingress.yaml    # nginx ingress, host app.local
│   │   └── kustomization.yaml
│   └── overlays/
│       ├── dev/            # namespace dev, 1 replica, image tag "dev"
│       └── prod/           # namespace prod, 3 replicas + HPA (3–6, 70% CPU)
├── argocd/
│   └── application.yaml    # ArgoCD Application → overlays/prod, auto-sync
└── .github/workflows/
    └── ci.yml              # Build + Trivy scan + push to GHCR
```

## Run it locally (kind + ArgoCD)

Prerequisites: Docker, `kubectl`, and `kind` installed.

**1. Create a local cluster and an ingress controller**

```bash
kind create cluster --name gitops-demo
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```

**2. Install ArgoCD**

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait -n argocd --for=condition=ready pod --all --timeout=300s
```

**3. Point the app at your fork**

Edit `argocd/application.yaml` and set `source.repoURL` to your fork of this
repo (the manifests reference the image
`ghcr.io/ayesha9753/kubernetes-gitops-argocd`; update the image name in
`k8s/base/kustomization.yaml` if your GHCR namespace differs).

**4. Register the application with ArgoCD**

```bash
kubectl apply -f argocd/application.yaml
```

ArgoCD will create the `prod` namespace, deploy the app from
`k8s/overlays/prod`, and keep it synced. Watch it converge:

```bash
kubectl get pods -n prod -w
```

**5. Open ArgoCD's UI and log in**

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Initial admin password:
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

Open https://localhost:8080 (user: `admin`) and find the
`kubernetes-gitops-argocd` application — it should show **Synced** and
**Healthy**.

**6. Visit the app**

Add the ingress host to your hosts file, then open http://app.local :

```bash
echo "127.0.0.1 app.local" | sudo tee -a /etc/hosts
curl http://app.local/health
# {"status":"ok", ...}
```

**7. Try the GitOps loop**

Change something in Git — for example the replica count or the message the
app returns — commit and push. CI rebuilds the image, and ArgoCD syncs the
change into the cluster automatically. To try the dev environment instead,
apply the dev overlay directly:

```bash
kubectl apply -k k8s/overlays/dev
curl http://app.local/health   # same ingress host, dev namespace
```

**Clean up**

```bash
kind delete cluster --name gitops-demo
```

## Skills demonstrated

- **Kubernetes** — Deployments, Services, Ingress, namespaces, resource requests/limits, readiness & liveness probes, HorizontalPodAutoscaler
- **Kustomize** — base + overlay pattern for environment promotion (dev/prod) without duplicating manifests
- **GitOps with ArgoCD** — declarative Application, automated sync with prune and self-heal, Git as the source of truth
- **Docker** — multi-stage builds, non-root containers, image healthchecks, minimal runtime images
- **CI/CD (GitHub Actions)** — image build on push, Trivy vulnerability scanning in the pipeline, publishing to GitHub Container Registry (GHCR)
- **Python** — small Flask service with a dedicated health endpoint for probes, served by gunicorn
