# TODO: Document your kubeadm cluster setup process
#
# What to include in this file:
# - kubeadm init commands and configuration
# - CNI plugin installation (Calico, Flannel, etc.)
# - Node joining process
# - Control plane tuning parameters
# - etcd backup and restore procedures
# - Cluster upgrade strategy
# - Networking configuration details
# - Security hardening steps
# - Certificate management notes

# Kubeadm Cluster Setup & Tuning Notes

## Initial Setup

### Control Plane Initialization

```bash
# Initialize control plane
# sudo kubeadm init --pod-network-cidr=10.244.0.0/16 --apiserver-advertise-address=<CONTROL_PLANE_IP>
```

### CNI Plugin Installation

```bash
# Install Calico CNI (recommended for this project)
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.2/manifests/calico.yaml

# If Calico node pods enter CrashLoopBackOff due to DNS resolving 'localhost',
# force felix health endpoint to bind 127.0.0.1 (bypass DNS):
kubectl -n kube-system set env daemonset/calico-node FELIX_HEALTHHOST=127.0.0.1
kubectl -n kube-system rollout status daemonset/calico-node
```

### Worker Node Join

```bash
# Join worker nodes
# sudo kubeadm join <CONTROL_PLANE_IP>:6443 --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH>
```

## Tuning & Optimization

### Resource Limits

### etcd Configuration

### API Server Tuning

## Backup & Recovery

## Upgrade Strategy
