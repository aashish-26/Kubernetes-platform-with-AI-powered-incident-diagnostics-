"""
AI Agent - rule-backed diagnostics with tool calls

This agent is deterministic and avoids hallucinations. It gathers facts
from Kubernetes (pods, events, logs) and Prometheus (CPU, memory, restarts)
then applies heuristics to explain likely causes and safe next steps.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import logging

from .k8s_client import K8sClient
from .prometheus_client import PrometheusClient

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
	summary: str
	root_cause: str
	recommendations: List[str]
	confidence: float
	evidence: Dict


class AIAgent:
	"""Diagnostic agent orchestrating K8s + Prometheus lookups."""

	def __init__(self, lookback_minutes: int = 15):
		self.k8s = K8sClient()
		self.prom = PrometheusClient()
		self.lookback_minutes = lookback_minutes

	def analyze_incident(
		self,
		namespace: str,
		pod_name: Optional[str] = None,
		service_name: Optional[str] = None,
		include_logs: bool = False,
	) -> AnalysisResult:
		"""Main diagnostic entry point."""

		evidence: Dict = {
			"pods": [],
			"pod_status": None,
			"events": [],
			"logs": None,
			"metrics": {},
		}

		# Step 1: list pods to validate targets
		pods = self.k8s.get_pods(namespace)
		evidence["pods"] = pods

		target_pod = self._pick_target_pod(pods, pod_name, service_name)
		if not target_pod:
			msg = "No matching pod found"
			logger.warning(msg)
			return AnalysisResult(
				summary=f"Namespace '{namespace}': {msg}.",
				root_cause="unknown",
				recommendations=["Confirm pod/service name and namespace"],
				confidence=0.3,
				evidence=evidence,
			)

		# Step 2: pod status
		pod_status = self.k8s.get_pod_status(namespace, target_pod)
		evidence["pod_status"] = pod_status

		# Step 3: events
		events = self.k8s.get_events(namespace, field_selector=f"involvedObject.name={target_pod}")
		evidence["events"] = events

		# Step 4: metrics (CPU, memory, restarts, OOM)
		metrics = self._collect_metrics(namespace, target_pod)
		evidence["metrics"] = metrics

		# Step 5: logs (optional, tail)
		if include_logs:
			evidence["logs"] = self.k8s.get_logs(namespace, target_pod, tail_lines=120)

		# Step 6: reason over facts
		summary, root_cause, recs, confidence = self._reason(pod_status, events, metrics)

		return AnalysisResult(
			summary=summary,
			root_cause=root_cause,
			recommendations=recs,
			confidence=confidence,
			evidence=evidence,
		)

	def _pick_target_pod(self, pods: List[Dict], pod_name: Optional[str], service_name: Optional[str]) -> Optional[str]:
		if pod_name:
			for p in pods:
				if p["name"] == pod_name:
					return pod_name
		if service_name:
			for p in pods:
				if p["name"].startswith(service_name):
					return p["name"]
		# fallback: newest pod in namespace
		if pods:
			return sorted(pods, key=lambda x: x.get("created", ""))[-1]["name"]
		return None

	def _collect_metrics(self, namespace: str, pod_name: str) -> Dict:
		return {
			"cpu_m": self.prom.get_pod_cpu_usage(namespace, pod_name),
			"mem_mb": self.prom.get_pod_memory_usage(namespace, pod_name),
			"restarts": self.prom.get_pod_restarts(namespace, pod_name),
			"ooms": self.prom.check_oom_kills(namespace),
		}

	def _reason(
		self,
		pod_status: Optional[Dict],
		events: List[Dict],
		metrics: Dict,
	) -> Tuple[str, str, List[str], float]:
		if not pod_status:
			return (
				"Pod not found or unreachable.",
				"unknown",
				["Verify pod exists and kubeconfig access"],
				0.3,
			)

		recs: List[str] = []
		root_cause = "unknown"
		confidence = 0.55

		phase = pod_status.get("phase")
		containers = pod_status.get("containers", [])
		warnings = [e for e in events if e.get("type") == "Warning"]
		restarts = metrics.get("restarts")
		ooms = metrics.get("ooms", [])

		# Phase-based reasoning
		if phase != "Running":
			root_cause = f"pod in phase {phase}"
			recs.append("Describe pod to inspect detailed status and conditions")
			confidence = 0.65

		# Container state checks
		for c in containers:
			state = c.get("state")
			if state == "waiting":
				reason = c.get("reason", "waiting")
				root_cause = f"container waiting: {reason}"
				recs.append("Check image pull/auth and recent deploy changes")
				confidence = 0.7
			if state == "terminated":
				reason = c.get("reason", "terminated")
				root_cause = f"container terminated: {reason}"
				recs.append("Inspect container logs around termination time")
				confidence = 0.7

		# Events
		if warnings:
			top = warnings[0]
			root_cause = f"event: {top.get('reason')} - {top.get('message')}"
			recs.append("Address the latest Warning event cause")
			confidence = 0.72

		# OOM
		if ooms:
			root_cause = "oom_killed"
			recs.append("Increase memory limit (within 300Mi cap) or reduce footprint")
			recs.append("Check memory leaks or traffic spikes")
			confidence = 0.78

		# Restarts
		if restarts is not None and restarts > 2:
			recs.append(f"High restarts detected ({restarts}); inspect logs and readiness probes")
			confidence = max(confidence, 0.7)

		# Metrics thresholds (heuristic, no limits known)
		cpu_m = metrics.get("cpu_m")
		mem_mb = metrics.get("mem_mb")
		if cpu_m and cpu_m > 400:
			recs.append("CPU >400m; consider throttling or scale out")
		if mem_mb and mem_mb > 220:
			recs.append("Memory >220Mi; nearing 256Mi cap; watch for OOM")

		summary_parts = [
			f"Phase: {phase}",
			f"Warnings: {len(warnings)}",
			f"Restarts: {restarts if restarts is not None else 'n/a'}",
			f"CPU(m): {cpu_m if cpu_m is not None else 'n/a'}",
			f"Mem(Mi): {mem_mb if mem_mb is not None else 'n/a'}",
		]

		summary = "; ".join(summary_parts)

		if not recs:
			recs.append("No critical signals found; continue monitoring and check recent deploys")
			confidence = 0.5

		return summary, root_cause, recs, round(confidence, 2)
