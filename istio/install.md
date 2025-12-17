# TODO: Document Istio installation process
#
# What to include in this file:
# - Istio download and installation steps
# - Profile selection (demo, minimal, production)
# - Istioctl commands for installation
# - Namespace labeling for sidecar injection
# - Gateway configuration steps
# - Verification commands
# - Common troubleshooting steps

# Istio Service Mesh Installation Guide

## Prerequisites

- Kubernetes cluster (1.26+)
- kubectl configured
- Sufficient cluster resources

## Installation Steps

### 1. Download Istio (local, minimal footprint)

```bash
curl -L https://istio.io/downloadIstio | sh -
cd istio-*
export PATH=$PWD/bin:$PATH
```

### 2. Install Istio (minimal profile, no tracing)

```bash
istioctl install --set profile=minimal -y

# Or demo profile for testing (includes Grafana, Kiali, etc.)
# istioctl install --set profile=demo -y
```

### 3. Enable Sidecar Injection for apps namespace

```bash
kubectl label namespace apps istio-injection=enabled --overwrite
```

### 4. Verify Installation (one change at a time)

```bash
kubectl get pods -n istio-system
kubectl get namespace -L istio-injection
```

### 5. Apply mTLS STRICT (PeerAuthentication)

```bash
kubectl apply -f istio/peer-auth.yaml
```

### 6. Validate cluster stability

```bash
kubectl get pods -A
istioctl analyze || true
```

**Notes:**
- Minimal profile keeps add-ons off (no tracing, no kiali, no grafana).
- Keep resources modest; all pods must have CPU/memory limits.
- If injection causes issues, remove label and debug, then re-apply.

## Components Installed

- **Istiod**: Control plane (Pilot, Citadel, Galley merged)
- **Ingress Gateway**: Entry point for external traffic
- **Egress Gateway**: (Optional) Exit point for outbound traffic

## Configuration

See `peer-auth.yaml` for mTLS configuration
See `virtual-service.yaml` for traffic routing
See `destination-rule.yaml` for load balancing and TLS settings

## Troubleshooting

```bash
# Check Istio configuration
# istioctl analyze

# View proxy configuration
# istioctl proxy-config cluster <pod-name> -n <namespace>
```
