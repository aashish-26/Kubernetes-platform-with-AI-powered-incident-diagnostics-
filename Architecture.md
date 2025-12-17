High-Level Architecture (Textual)
User
 |
 |  (HTTP)
 v
Istio Ingress Gateway
 |
 |---- frontend (UI / API client)
 |
 |---- backend-api
         |
         |---- users-service
         |---- orders-service
         |---- payments-service
         |
         |---- ai-diagnostics-service
                  |
                  |---- Kubernetes API (read-only)
                  |---- Prometheus API

Technology Stack
Core Platform

Kubernetes (kubeadm)

Calico CNI

Helm

Service Mesh

Istio (minimal profile)

mTLS enabled

Traffic retries and timeouts

Observability

Prometheus

Grafana

Kubernetes events

Istio telemetry

AI & Automation

Python-based AI service

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