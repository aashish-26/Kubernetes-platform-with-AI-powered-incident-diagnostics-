# System Architecture

## Overview

This platform implements a layered architecture that separates concerns between infrastructure management, application services, observability, and intelligent diagnostics. The design emphasizes resilience, security, and operational visibility.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      User / Operator                        │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/HTTPS
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 Istio Ingress Gateway                       │
│              (mTLS, Traffic Management)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌──────────────┐        ┌──────────────────┐
│  Frontend    │        │   Backend API    │
│  (Web UI)    │        │  (Aggregation)   │
└──────────────┘        └────────┬─────────┘
                                 │
                  ┌──────────────┼──────────────┐
                  │              │              │
                  ▼              ▼              ▼
          ┌─────────────┐ ┌────────────┐ ┌────────────┐
          │   Users      │ │  Orders    │ │  Payments  │
          │  Service     │ │  Service   │ │  Service   │
          └─────────────┘ └────────────┘ └────────────┘

┌─────────────────────────────────────────────────────────────┐
│              AI Diagnostics Service                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐      │
│  │ Kubernetes   │  │ Prometheus   │  │  Analysis   │      │
│  │ API Client   │──┤ API Client   │──┤  Engine     │      │
│  │ (Read-Only)  │  │              │  │ (Rules)     │      │
│  └──────────────┘  └──────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────────┘
                     │              │
                     ▼              ▼
          ┌─────────────────────────────────────┐
          │    Observability Stack              │
          │  ┌──────────┐    ┌──────────┐      │
          │  │Prometheus│    │ Grafana  │      │
          │  │  Server  │────┤Dashboards│      │
          │  └──────────┘    └──────────┘      │
          └─────────────────────────────────────┘
```

## Technology Stack

### Infrastructure Layer

**Kubernetes v1.28.15 (kubeadm)**
- Multi-node cluster configuration (1 control-plane + 2 workers)
- Custom resource limits and quality-of-service policies
- RBAC for fine-grained access control

**Calico CNI v3.27.2**
- Network policy enforcement
- Pod-to-pod communication with IP-in-IP encapsulation
- Custom health check configuration for DNS reliability

**Helm 3**
- Templated deployments for consistency
- Version-controlled configuration management
- Rollback capabilities

### Service Mesh Layer

**Istio (Minimal Profile)**
- **Security**: Mutual TLS authentication for all service-to-service communication
- **Traffic Management**: Weighted routing for canary deployments (90/10 split)
- **Resilience**: Automatic retries (3 attempts), circuit breakers, and connection pooling
- **Observability**: Distributed tracing readiness and metrics collection

### Observability Layer

**Prometheus**
- 28 active scrape targets across cluster components
- Custom recording rules for common queries
- 6-hour retention with ephemeral storage optimization
- Integration with Kubernetes service discovery

**Grafana**
- 27 pre-configured dashboards for cluster visibility
- Direct ClusterIP datasource connectivity (avoiding DNS overhead)
- Resource usage tracking and alerting capabilities

**Kubernetes Events**
- Real-time event streaming for diagnostic correlation
- Field selectors for targeted event queries

### Intelligence Layer

**AI Diagnostics Service (Python/FastAPI)**
- **Analysis Engine**: Rule-based decision tree for incident classification
- **Data Collection**: Parallel queries to Kubernetes and Prometheus APIs
- **Confidence Scoring**: Evidence-weighted probability calculations
- **API Design**: RESTful endpoints with structured JSON responses

Local LLM (CPU-only)

Tool-based agent design (cluster introspection)

Application

Simple REST microservices

Metrics exposed via /metrics

Health checks via /health

PHASE 0 — Ground Rules

One change at a time: Apply and verify each modification before proceeding. Keep changes small and reversible.

No cloud services: Operate fully on local/cluster resources. No external managed services.

Every pod must have CPU & memory limits: All pods define resources.requests and resources.limits. Max memory: 300Mi per container.

Use Helm wherever possible: Prefer Helm charts over raw manifests for consistency and repeatability.

Document as you go (notes > perfection): Capture decisions, parameters, and deviations in repo docs and values.yaml comments.