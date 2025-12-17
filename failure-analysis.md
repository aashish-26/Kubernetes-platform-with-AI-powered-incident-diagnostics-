# Failure Analysis - Kubernetes Incident Scenarios

## Overview (Dec 17, 2025)

This document captures real incidents we hit, how we fixed them, and reusable playbooks for future failures.

**Quick Links:** [Real Incidents](#real-incidents-observed) • [OOM Playbook](#1-oom-out-of-memory-failure) • [Service Selector](#2-broken-service-selector) • [Latency](#3-high-latency--network-issues)

---

## Real Incidents Observed

### Incident 1: Calico Pods in CrashLoopBackOff (DNS Resolution Stall)

- **Symptoms**: `calico-node` pods restarting; health endpoint timing out on DNS; networking unavailable in cluster bring-up.
- **Detection**:
  - `kubectl -n kube-system get pods -l k8s-app=calico-node` showed CrashLoopBackOff
  - Logs indicated DNS lookup of `localhost` timing out (upstream nameserver slow)
- **Root Cause**: Calico health check resolves `localhost` via cluster DNS; upstream resolver was unreachable from the pod → health probe failure → CrashLoopBackOff.
- **Resolution**:
  - Force health check to bind directly: `kubectl -n kube-system set env daemonset/calico-node FELIX_HEALTHHOST=127.0.0.1`
  - Wait for rollout: `kubectl -n kube-system rollout status daemonset/calico-node --timeout=60s`
- **Outcome**: All Calico pods reached 1/1 Running; cluster networking healthy.
- **Prevention**: Prefer IP for health endpoints; keep DNS dependencies out of critical control-plane probes.

### Incident 2: OOM Test Pod CrashLoopBackOff (Intentional Failure)

- **Symptoms**: `oom-test-*` pod in `CrashLoopBackOff`, restarts > 3.
- **Detection**:
  - `kubectl -n default get pods -l app=oom-test` showing 0/1 Ready, CrashLoopBackOff
  - Events: BackOff, OOMKilled
  - Prometheus: memory spike vs limit, restart count > 0, OOM kill detected
  - AI `/ask` response: `root_cause="oom_killed"`, confidence 0.78
- **Root Cause**: Container memory request (256M in manifest) exceeded namespace LimitRange (300Mi cap) with load; OOM kill triggered by kernel.
- **Resolution**:
  - Increase memory request/limit to fit workload (e.g., request 256Mi, limit 512Mi within quota) and redeploy
  - Alternatively reduce workload footprint
- **Outcome**: Demonstrated AI correctly diagnosing OOM with accurate evidence and recommendations.
- **Prevention**: Right-size using metrics history, alert on memory >80% of limit, add VPA or profile memory leaks.

### Incident 3: kube-state-metrics Probe Flaps (CrashLoopBackOff)

- **Symptoms**: `prometheus-stack-kube-state-metrics-*` reported `CrashLoopBackOff`, 14 restarts; readiness/liveness probe failures (`connection refused`, `context deadline exceeded`).
- **Detection**:
  - `kubectl -n monitoring get pod prometheus-stack-kube-state-metrics-5cdc757b7-sv2fz -o wide`
  - `kubectl -n monitoring describe pod prometheus-stack-kube-state-metrics-5cdc757b7-sv2fz` (events show probe failures)
  - `kubectl -n monitoring logs prometheus-stack-kube-state-metrics-5cdc757b7-sv2fz --previous` (no fatal errors; exited with code 2)
- **Root Cause (likely)**: Probes hit before service fully bound or during CPU/memory contention on node, leading to transient connection refused and restarts. No persistent configuration error observed; pod eventually reached Ready.
- **Resolution**:
  - Allow kubelet to restart pod; it stabilized on subsequent restart (now 1/1 Running).
  - If flaps recur, increase probe initialDelaySeconds to 15s and timeoutSeconds to 10s; optionally bump CPU/memory requests for kube-state-metrics.
- **Outcome**: Pod currently Running; monitoring stack healthy.
- **Prevention**: Soften probe timing, ensure node not CPU-throttled, and keep kube-state-metrics requests/limits aligned with cluster size.

---

## Reference Playbooks (Reusable)

The sections below remain as reusable playbooks for common scenarios beyond the incidents already observed.

## 1. OOM (Out of Memory) Failure

### Scenario Description

A pod is killed because it exceeds its memory limit. This is one of the most common failures in Kubernetes.

### Symptoms

- Pod status: `OOMKilled`
- Pod phase: `CrashLoopBackOff`
- Events: "Container was OOMKilled"
- High memory usage in metrics before crash

### Detection Methods

**Manual Detection:**
```bash
kubectl get pods
kubectl describe pod <pod-name>
kubectl get events --field-selector involvedObject.name=<pod-name>
```

**Prometheus Query:**
```promql
# Memory usage approaching limit
container_memory_working_set_bytes / container_spec_memory_limit_bytes > 0.9
```

### Root Cause Analysis Process

1. **Check Pod Status**: Look for OOMKilled in container status
2. **Review Resource Limits**: Compare memory limit vs actual usage
3. **Analyze Memory Trends**: Query Prometheus for memory growth patterns
4. **Check Application Logs**: Look for memory leaks, large allocations
5. **Review Events**: Check for restart history

### AI Diagnostics Approach

The AI agent will:
1. Query pod status and identify OOMKilled
2. Retrieve memory metrics from Prometheus
3. Check memory requests vs limits
4. Analyze memory growth rate
5. Check for memory leaks in logs
6. Calculate appropriate memory limits

**Expected AI Output:**
```
Root Cause: Pod exceeds memory limit (128Mi) - OOMKilled

Evidence:
- Container memory usage reached 128Mi (100% of limit)
- Memory consumption grew at 2MB/min over last 30min
- No memory leaks detected in logs
- Application requires ~256Mi based on historical data

Analysis: The memory limit of 128Mi is insufficient for the 
workload. The application's normal operation requires 
approximately 256Mi, causing repeated OOM kills.

Immediate Actions:
1. Increase memory limit to 512Mi
2. Set memory request to 256Mi
3. Restart deployment

Long-term Recommendations:
1. Implement memory profiling
2. Add HPA based on memory metrics
3. Monitor memory trends for capacity planning

Confidence: High - Clear OOM pattern with consistent metrics
```

### Resolution Steps

```bash
# Increase memory limits
kubectl set resources deployment oom-test \
  --limits=memory=512Mi \
  --requests=memory=256Mi

# Verify fix
kubectl rollout status deployment oom-test
kubectl get pods -l app=oom-test
```

### Prevention Strategies

1. **Right-sizing**: Use VPA or historical metrics
2. **Memory Profiling**: Profile application memory usage
3. **Gradual Rollout**: Test with production-like load
4. **Monitoring**: Alert on memory > 80% of limit
5. **Resource Quotas**: Namespace-level limits

---

## 2. Broken Service Selector

### Scenario Description

A Service has a selector that doesn't match any pods, resulting in no endpoints and connection failures.

### Symptoms

- Service has no endpoints
- Connection refused errors
- `kubectl get endpoints <service>` shows no IPs
- DNS resolution works, but connections fail

### Detection Methods

**Manual Detection:**
```bash
kubectl get service broken-service-test
kubectl get endpoints broken-service-test
kubectl get pods -l app=backend
kubectl describe service broken-service-test
```

**Prometheus Query:**
```promql
# Service with no endpoints
kube_service_spec_type * on(service, namespace) group_left() 
  (kube_endpoint_address_available == 0)
```

### Root Cause Analysis Process

1. **Check Endpoints**: Verify service has endpoints
2. **Compare Labels**: Match service selector with pod labels
3. **Verify Pod Status**: Ensure matching pods are Running
4. **Check Readiness**: Confirm pods pass readiness probes
5. **Review Service Config**: Look for typos in selectors

### AI Diagnostics Approach

The AI agent will:
1. Query service configuration
2. List pods with selector labels
3. Compare service selector vs pod labels
4. Check endpoint availability
5. Identify the mismatch

**Expected AI Output:**
```
Root Cause: Service selector mismatch - no matching pods

Evidence:
- Service selector: app=backend-wrong
- Available pods have label: app=backend
- Endpoint count: 0
- Pod count with correct label: 3

Analysis: The service selector has a typo ("backend-wrong" 
instead of "backend"). This causes the service to not route 
traffic to any pods, resulting in connection failures.

Immediate Actions:
1. Update service selector to "app=backend"
2. Verify endpoints are populated
3. Test connectivity

Long-term Recommendations:
1. Implement label validation in CI/CD
2. Use Helm chart values to ensure consistency
3. Add monitoring for services without endpoints

Confidence: High - Clear label mismatch detected
```

### Resolution Steps

```bash
# Fix the service selector
kubectl patch service broken-service-test -p \
  '{"spec":{"selector":{"app":"backend"}}}'

# Verify endpoints
kubectl get endpoints broken-service-test

# Test connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never \
  -- curl http://broken-service-test
```

### Prevention Strategies

1. **Helm Templates**: Use consistent labeling
2. **Validation**: Add admission webhooks
3. **Testing**: E2E tests for service connectivity
4. **Monitoring**: Alert on zero-endpoint services
5. **Documentation**: Label naming conventions

---

## 3. High Latency / Network Issues

### Scenario Description

Application responses are slow due to network delays, slow dependencies, or resource contention.

### Symptoms

- Increased response times (p50, p95, p99)
- Timeout errors
- Readiness/liveness probe failures
- User complaints of slow performance

### Detection Methods

**Manual Detection:**
```bash
kubectl exec -it <pod-name> -- curl -w "@curl-format.txt" http://service
kubectl top pods
kubectl describe pod <pod-name>
```

**Prometheus Query:**
```promql
# High latency (p95 > 500ms)
histogram_quantile(0.95, 
  rate(request_duration_seconds_bucket[5m])) > 0.5
```

### Root Cause Analysis Process

1. **Measure Latency**: Check current response times
2. **Check Resource Usage**: CPU throttling, memory pressure
3. **Network Analysis**: Inter-service latency, DNS issues
4. **Dependency Check**: Slow downstream services
5. **Configuration Review**: Timeout settings, retries

### AI Diagnostics Approach

The AI agent will:
1. Query latency metrics from Prometheus
2. Check pod resource utilization
3. Review network metrics
4. Analyze probe configurations
5. Check for rate limiting or throttling

**Expected AI Output:**
```
Root Cause: Artificial network latency (500ms delay)

Evidence:
- p95 latency: 520ms (baseline: 50ms)
- Readiness probe failures: 15 in last 5min
- Probe timeout: 2s (insufficient for 500ms delay)
- CPU and memory usage: Normal
- No errors in application logs

Analysis: Network latency of ~500ms causes readiness probes 
to fail intermittently. The probe timeout of 2s is too 
aggressive for the current network conditions.

Immediate Actions:
1. Increase probe timeout to 5s
2. Increase probe periodSeconds to 10s
3. Investigate network latency source

Long-term Recommendations:
1. Implement retry logic with exponential backoff
2. Add request timeout monitoring
3. Use Istio timeout and retry policies
4. Consider caching for slow operations

Confidence: High - Consistent latency pattern in metrics
```

### Resolution Steps

```bash
# Update probe timeouts
kubectl patch deployment latency-test -p \
  '{"spec":{"template":{"spec":{"containers":[{
    "name":"slow-app",
    "readinessProbe":{"timeoutSeconds":5,"periodSeconds":10}
  }]}}}}'

# Check Istio configuration for retries
kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: latency-retry
spec:
  hosts:
  - latency-test
  http:
  - route:
    - destination:
        host: latency-test
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
EOF
```

### Prevention Strategies

1. **Timeouts**: Configure appropriate timeouts
2. **Retries**: Implement retry logic (with backoff)
3. **Circuit Breakers**: Use Istio circuit breakers
4. **Caching**: Cache expensive operations
5. **Load Testing**: Test under realistic latency conditions
6. **Monitoring**: Alert on p95/p99 latency spikes

---

## Common Incident Patterns

### Pattern 1: Cascading Failures

**Description**: One service failure triggers failures in dependent services

**Detection**: Multiple services reporting errors simultaneously

**AI Approach**: Trace dependency graph, identify initial failure point

### Pattern 2: Resource Exhaustion

**Description**: Node runs out of CPU/memory/disk

**Detection**: Multiple pods pending or evicted

**AI Approach**: Analyze node capacity, pod resource usage, scheduling constraints

### Pattern 3: Configuration Drift

**Description**: Manual changes cause unexpected behavior

**Detection**: Sudden behavior change without deployments

**AI Approach**: Compare current config vs previous versions, identify changes

---

## AI Diagnostics Workflow Summary

For each incident type, the AI follows this pattern:

1. **Initial Assessment**
   - Gather basic pod/service information
   - Check current status and recent events

2. **Data Collection**
   - Query relevant metrics (CPU, memory, network, latency)
   - Retrieve logs with error messages
   - Get resource configurations

3. **Pattern Recognition**
   - Compare against known failure patterns
   - Look for correlations in metrics and logs
   - Identify anomalies

4. **Root Cause Determination**
   - Synthesize evidence
   - Reason about probable causes
   - Calculate confidence level

5. **Recommendation Generation**
   - Immediate remediation steps
   - Configuration improvements
   - Long-term prevention strategies

---

## Testing the AI Diagnostics

### Test Case 1: OOM Detection
```bash
kubectl apply -f failures/oom.yaml
# Wait for OOMKilled
curl -X POST http://ai-diagnostics:8000/analyze \
  -d '{"namespace":"default","pod_name":"oom-test-*"}'
```

### Test Case 2: Service Mismatch
```bash
kubectl apply -f failures/bad-service.yaml
curl -X POST http://ai-diagnostics:8000/analyze \
  -d '{"namespace":"default","service_name":"broken-service-test"}'
```

### Test Case 3: Latency Issues
```bash
kubectl apply -f failures/latency.yaml
curl -X POST http://ai-diagnostics:8000/analyze \
  -d '{"namespace":"default","pod_name":"latency-test-*"}'
```

---

## Interview Discussion Points

1. **Problem-Solving**: Systematic approach to debugging
2. **Tools**: kubectl, Prometheus, Grafana, AI agents
3. **Patterns**: Recognition of common failure modes
4. **Prevention**: Proactive monitoring and alerting
5. **Automation**: AI-driven diagnostics and remediation
