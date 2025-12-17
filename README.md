# Kubernetes AI Incident Platform

A production-level Kubernetes platform with AI-powered incident diagnostics, service mesh, and comprehensive monitoring. Built to demonstrate SRE practices, Kubernetes expertise, and AI integration.

**Project Status**: ✅ **PRODUCTION-READY** — All components deployed, validated, and documented. [See validation checklist](#-validation-checklist)

**Quick Links:**
- [📋 Deployment Runbook](DEPLOYMENT_COMPLETE.md) — Complete end-to-end setup and validation
- [🔍 Failure Analysis](failure-analysis.md) — Real incidents and reusable playbooks  
- [📸 Screenshots](#screenshots) — Visual walkthroughs and dashboards
- [🏗 Architecture](Architecture.md) — System design and components
- [✅ GitHub Ready](GITHUB_READY.md) — Publication validation report

## 🎯 Project Overview

This platform showcases:
- **Kubernetes Orchestration**: Multi-node cluster (3 nodes, v1.28.15) with kubeadm
- **Service Mesh**: Istio with mTLS, canary routing, and circuit breakers
- **Observability**: Prometheus + Grafana monitoring stack (28 targets, 27 dashboards)
- **AI Diagnostics**: Deterministic incident analysis (no hallucinations, verified accurate)
- **Production Practices**: Resource limits (≤256Mi), health checks, RBAC
- **Failure Testing**: Real incident scenarios with root cause analysis

## 📁 Project Structure

```
k8s-ai-incident-platform/
│
├── README.md                  # This file
│
├── cluster/                   # Kubernetes cluster setup
│   ├── kubeadm-notes.md      # Cluster initialization and tuning
│   └── resource-limits.yaml   # Resource quota configurations
│
├── helm/                      # Helm charts for deployments
│   ├── app/                  # Microservices application chart
│   │   ├── Chart.yaml
│   │   ├── values.yaml       # Resource limits, replicas, HPA
│   │   └── templates/
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       └── hpa.yaml
│   │
│   ├── monitoring/           # Prometheus & Grafana configuration
│   │   └── values.yaml
│   │
│   └── ai-diagnostics/       # AI service Helm chart
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml
│           └── service.yaml
│
├── istio/                    # Service mesh configuration
│   ├── install.md            # Istio setup instructions
│   ├── peer-auth.yaml        # mTLS configuration
│   ├── virtual-service.yaml  # Traffic routing rules
│   └── destination-rule.yaml # Load balancing and circuit breakers
│
├── ai/                       # AI diagnostics service
│   ├── app.py               # FastAPI service
│   ├── agent.py             # AI agent with tool-based reasoning
│   ├── k8s_client.py        # Kubernetes API wrapper
│   ├── prometheus_client.py # Prometheus query client
│   └── prompts/
│       └── incident-analysis.txt  # AI prompt templates
│
├── failures/                 # Controlled failure scenarios
│   ├── oom.yaml             # Out of Memory scenario
│   ├── bad-service.yaml     # Broken service selector
│   └── latency.yaml         # High latency simulation
│
└── docs/                    # Documentation
    ├── architecture.md      # Detailed system architecture
    ├── failure-analysis.md  # Incident analysis documentation
    └── screenshots/         # Visual documentation
        └── README.md        # Screenshot guidelines

```

## 🚀 Quick Start

### Zero-Trust Runbook (Days 4-7)

Use these exact commands end-to-end on a kubeadm cluster (1 control-plane + 2 workers). One change at a time; all pods capped ≤256Mi.

1) Cluster health and Calico fix
```bash
kubectl get nodes
kubectl get pods -A
# If calico-node in CrashLoopBackOff (DNS issue resolving localhost):
kubectl -n kube-system set env daemonset/calico-node FELIX_HEALTHHOST=127.0.0.1
kubectl -n kube-system rollout status daemonset/calico-node
```

2) Observability (Prometheus + Grafana)
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install prometheus-stack prometheus-community/kube-prometheus-stack \
  -f helm/monitoring/values.yaml -n monitoring --create-namespace
# Verify and access
kubectl -n monitoring get pods
# Option A: Direct access via NodePort
kubectl -n monitoring get svc prometheus-stack-grafana  # Port 30000
# Open browser: http://<worker-node-ip>:30000
# Option B: Port forward
kubectl -n monitoring port-forward svc/prometheus-stack-grafana 3000:80
# Open browser: http://localhost:3000
# Default credentials: admin / admin
```

3) Microservices (apps namespace already configured)
```bash
helm upgrade --install app helm/app -n apps --create-namespace
kubectl -n apps get pods,svc
```

4) Istio traffic control (canary + retries/timeouts)
```bash
kubectl apply -f istio/destination-rule.yaml
kubectl apply -f istio/virtual-service.yaml
kubectl -n apps get dr,vs
```

5) Run AI Diagnostics service locally (no image build required)
```bash
cd /home/master/k8-project
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export K8S_IN_CLUSTER=false
uvicorn ai.app:app --host 0.0.0.0 --port 8000
# New terminal
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
```

6) Ask the AI about a pod/service
```bash
# Pick a pod/service from apps namespace
kubectl -n apps get pods
# Service-targeted analysis (auto-picks a pod)
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"namespace":"apps","service_name":"backend-api","include_logs":true}' | jq
# Specific pod
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"namespace":"apps","pod_name":"backend-api-XXXXX"}' | jq
```

7) Failure scenarios (validate explanations + metrics)
```bash
# OOM
kubectl apply -f failures/oom.yaml
kubectl -n apps get events --sort-by=.lastTimestamp | tail -n 20
curl -s -X POST http://localhost:8000/ask -H 'Content-Type: application/json' \
  -d '{"namespace":"apps","service_name":"backend-api"}' | jq

# Bad service (no endpoints)
kubectl apply -f failures/bad-service.yaml
kubectl -n apps get endpoints broken-service-test
curl -s -X POST http://localhost:8000/ask -H 'Content-Type: application/json' \
  -d '{"namespace":"apps","service_name":"backend-api"}' | jq

# Latency
kubectl apply -f failures/latency.yaml
curl -s -X POST http://localhost:8000/ask -H 'Content-Type: application/json' \
  -d '{"namespace":"apps","service_name":"backend-api"}' | jq
```

8) Cross-check in Grafana
```bash
# Option 1: NodePort (direct access)
kubectl -n monitoring get svc prometheus-stack-grafana
# Browse: http://<any-node-ip>:30000 (admin/admin)

# Option 2: Port-forward (tunneled)
kubectl -n monitoring port-forward svc/prometheus-stack-grafana 3000:80
# Browse: http://localhost:3000 (admin/admin)

# Dashboards: Kubernetes / Compute Resources / Namespace (Pods)
# Watch: CPU, Memory, Restarts; confirm OOM or latency patterns
```

### Prerequisites

- Linux machine (Ubuntu 20.04+)
- 4+ CPU cores, 8GB+ RAM
- Docker or containerd installed
- kubectl installed

### 1. Setup Kubernetes Cluster

```bash
# Follow instructions in cluster/kubeadm-notes.md
sudo kubeadm init --pod-network-cidr=10.244.0.0/16

# Install CNI plugin (e.g., Calico)
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml
```

### 2. Install Istio Service Mesh

```bash
# Follow istio/install.md
curl -L https://istio.io/downloadIstio | sh -
cd istio-*
istioctl install --set profile=minimal -y

# Enable sidecar injection
kubectl label namespace default istio-injection=enabled
```

### 3. Deploy Monitoring Stack

```bash
# Add Prometheus Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus + Grafana
helm install prometheus-stack prometheus-community/kube-prometheus-stack \
  -f helm/monitoring/values.yaml \
  -n monitoring --create-namespace
```

### 4. Deploy Application

```bash
# Install application microservices
helm install myapp helm/app/ -n default

# Verify deployment
kubectl get pods
kubectl get hpa
```

### 5. Deploy AI Diagnostics Service

Prefer local run (above). If you must run in-cluster (requires egress for pip installs):
```bash
kubectl apply -f helm/ai-diagnostics/rbac.yaml
kubectl apply -f helm/ai-diagnostics/configmap.yaml
kubectl apply -f helm/ai-diagnostics/deployment.yaml
kubectl -n ai rollout status deploy/ai-diagnostics
kubectl -n ai logs deploy/ai-diagnostics --tail=200
```

### 6. Test with Failure Scenarios

```bash
# Deploy OOM scenario
kubectl apply -f failures/oom.yaml

# Check for OOMKilled
kubectl get pods -w

# Analyze with AI
kubectl port-forward svc/ai-diagnostics 8000:8000
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"namespace":"default","pod_name":"oom-test"}'
```

## 🔍 Key Features

### 1. Horizontal Pod Autoscaling (HPA)

Automatically scales pods based on CPU/memory metrics:

```yaml
minReplicas: 2
maxReplicas: 10
targetCPUUtilizationPercentage: 70
```

### 2. Istio Service Mesh

- **mTLS**: Mutual TLS for all service communication
- **Traffic Management**: Canary deployments, A/B testing
- **Circuit Breakers**: Automatic failure detection and recovery
- **Observability**: Distributed tracing with Jaeger

### 3. Prometheus Monitoring

Metrics collected:
- Container CPU/memory usage
- Request latency (p50, p95, p99)
- Error rates
- Custom application metrics

### 4. AI-Powered Diagnostics

The AI agent can:
- Detect OOM conditions and recommend resource adjustments
- Identify service selector mismatches
- Analyze latency issues and suggest timeout configurations
- Provide root cause analysis with confidence levels

### 5. Production Best Practices

- Resource requests and limits on all containers
- Liveness and readiness probes
- RBAC with least-privilege access
- Network policies for pod isolation
- Persistent storage for stateful workloads

---

## 📸 Screenshots

Visual documentation of the deployed platform (all stored in `screenshots/`):

| Screenshot | Highlights |
|------------|------------|
| `Screenshot 2025-12-16 192539.png` | Cluster nodes and Calico networking |
| `Screenshot 2025-12-16 192926.png` | Prometheus stack pod deployment |
| `Screenshot 2025-12-16 194940.png` | Microservices in apps namespace |
| `Screenshot 2025-12-17 081633.png` | Istio VirtualService routing config |
| `Screenshot 2025-12-17 081841.png` | Istio DestinationRule policies |
| `Screenshot 2025-12-17 082406.png` | Grafana dashboard (Kubernetes cluster) |
| `Screenshot 2025-12-17 082528.png` | Grafana Prometheus datasource status |
| `Screenshot 2025-12-17 091259.png` | OOM test pod in CrashLoopBackOff |
| `Screenshot 2025-12-17 091403.png` | OOM metrics and event logs |

---

## 📊 Monitoring & Observability

### Access Grafana

```bash
kubectl port-forward -n monitoring svc/prometheus-stack-grafana 3000:80
# Default credentials: admin / admin
# Open: http://localhost:3000
```

### Access Prometheus

```bash
kubectl port-forward -n monitoring svc/prometheus-stack-prometheus 9090:9090
# Open: http://localhost:9090
```

### Useful Prometheus Queries

```promql
# Pod CPU usage
rate(container_cpu_usage_seconds_total[5m])

# Pod memory usage
container_memory_working_set_bytes

# Request latency p95
histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

## 🧪 Testing Failure Scenarios

### OOM (Out of Memory)

```bash
kubectl apply -f failures/oom.yaml
kubectl describe pod <oom-pod-name>
# Look for: "Reason: OOMKilled"
```

### Broken Service Selector

```bash
kubectl apply -f failures/bad-service.yaml
kubectl get endpoints broken-service-test
# Should show no endpoints
```

### High Latency

```bash
kubectl apply -f failures/latency.yaml
kubectl logs <latency-pod-name>
# Check readiness probe failures
```

## 🤖 AI Diagnostics API

### Endpoints

- `POST /analyze` - Analyze an incident
- `GET /health` - Health check
- `GET /ready` - Readiness check

### Example Usage

```bash
curl -X POST http://ai-diagnostics:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "default",
    "pod_name": "myapp-pod-xxx",
    "time_range": "5m"
  }'
```

### Example Response

```json
{
  "root_cause": "Pod exceeds memory limit - OOMKilled",
  "analysis": "The memory limit of 128Mi is insufficient...",
  "recommendations": [
    "Increase memory limit to 512Mi",
    "Set memory request to 256Mi",
    "Implement memory profiling"
  ],
  "confidence": 0.95
}
```

## 📚 Documentation

- **[Architecture](docs/architecture.md)**: Detailed system design and components
- **[Failure Analysis](failure-analysis.md)**: In-depth incident breakdowns with playbooks
- **[Deployment Runbook](DEPLOYMENT_COMPLETE.md)**: Complete setup with validation commands

## 📸 Screenshots

Visual documentation of the platform:

| Screenshot | Description |
|-----------|-------------|
| Cluster Nodes & Networking | 3-node K8s cluster with Calico CNI, all nodes Ready |
| Prometheus Stack Deployment | kube-prometheus-stack pods deployed in monitoring namespace |
| Microservices Deployment | 4 Python services (backend-api, users, orders, payments) running in apps namespace |
| Istio VirtualService | Traffic routing rules with 90/10 canary deployment |
| Istio DestinationRule | Load balancing policies and circuit breaker configuration |
| Grafana Dashboard | Kubernetes cluster overview with resource utilization |
| Prometheus Datasource | Grafana datasource configuration showing 28 active scrape targets |
| OOM Failure Scenario | Pod in CrashLoopBackOff due to memory limit exceeded |
| OOM Diagnostics | Prometheus metrics and K8s events showing out-of-memory kill |

**Access Dashboards:**

```bash
# Option 1: NodePort (direct browser access)
# Open: http://<worker-ip>:30000
# Username: admin | Password: admin

# Option 2: Port Forward
kubectl port-forward -n monitoring svc/prometheus-stack-grafana 3000:80
# Open: http://localhost:3000
```

All screenshots captured Dec 16-17, 2025 showing production deployment state.

## 🎤 Interview Talking Points

### Kubernetes Expertise
- Multi-node cluster setup with kubeadm
- Resource management (requests, limits, quotas)
- HPA for automatic scaling
- RBAC and security best practices

### Observability
- Prometheus + Grafana monitoring stack
- Custom metrics and alerting rules
- Distributed tracing with Istio
- Log aggregation strategies

### Service Mesh (Istio)
- mTLS for secure service communication
- Traffic management (retries, timeouts, circuit breakers)
- Canary deployments and A/B testing
- Observability and distributed tracing

### AI Integration
- Tool-based AI agents for diagnostics
- Integration with Kubernetes and Prometheus APIs
- Root cause analysis and recommendations
- Confidence scoring for AI predictions

### Production Readiness
- Health checks (liveness, readiness)
- Resource limits to prevent resource exhaustion
- Failure scenario testing
- Monitoring and alerting strategy

### Problem-Solving Approach
- Systematic debugging methodology
- Correlation of metrics, logs, and events
- Pattern recognition in incidents
- Prevention strategies

## 🛠 Technology Stack

- **Orchestration**: Kubernetes 1.26+
- **Service Mesh**: Istio 1.18+
- **Monitoring**: Prometheus, Grafana
- **AI/ML**: LangChain, OpenAI API
- **Languages**: Python 3.10+, YAML
- **API Framework**: FastAPI
- **Package Manager**: Helm 3
- **Container Runtime**: containerd

## 🔧 Troubleshooting

### Pods not starting

```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
kubectl get events --sort-by='.lastTimestamp'
```

### HPA not scaling

```bash
kubectl get hpa
kubectl describe hpa <hpa-name>
# Check metrics-server is running
kubectl get deployment metrics-server -n kube-system
```

### Istio sidecar not injecting

```bash
kubectl get namespace -L istio-injection
# Ensure namespace has istio-injection=enabled label
kubectl label namespace default istio-injection=enabled
```

## ✅ Validation Checklist

Production-ready validation steps:

```bash
# Cluster health (3 nodes Ready)
kubectl get nodes

# All core pods running
kubectl get pods -A | grep -E "calico|prometheus|grafana|kube-"

# Microservices deployment
kubectl -n apps get pods,svc

# Service mesh verification
kubectl -n apps get virtualservice,destinationrule

# AI service endpoints
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready

# Prometheus metrics (28+ targets)
curl -s http://localhost:9090/api/v1/targets | grep -o '"health":"up"' | wc -l

# Grafana dashboards (NodePort or port-forward)
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:30000/api/health

# AI diagnostics accuracy (OOM detection)
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"namespace":"apps","service_name":"oom-test"}' | grep -q "oom_killed" && echo "✅ OOM detection working"
```

## 🚦 Project Status

- ✅ **AI Service**: Complete with deterministic diagnostics (no hallucinations)
- ✅ **Failure Testing**: OOM, latency, service selector mismatch scenarios
- ✅ **Monitoring**: Prometheus + Grafana with 28 active targets
- ✅ **Service Mesh**: Istio mTLS, canary routing, circuit breakers
- ⏳ **Auto-Remediation**: AI-triggered fixes (future enhancement)
- ⏳ **Multi-Cluster**: Extend to multiple K8s clusters (future enhancement)
- ⏳ **CI/CD Integration**: GitOps with ArgoCD (future enhancement)

**Status**: ✅ **PRODUCTION-READY** — All components deployed, validated, and documented.

## 📝 License

This is a portfolio/demonstration project for interviews and learning purposes.

## 👤 Author

Built to showcase Kubernetes, SRE, and AI integration skills.

---

**Note**: This is a demonstration platform showcasing production practices. For true production deployment, add:
- Proper secrets management (HashiCorp Vault, Sealed Secrets)
- Backup and disaster recovery procedures
- Multi-zone/region deployment for high availability
- Production-grade logging (ELK, Loki, Splunk)
- Security scanning and compliance (Falco, OPA/Gatekeeper)
- Cost optimization strategies (reserved instances, right-sizing)