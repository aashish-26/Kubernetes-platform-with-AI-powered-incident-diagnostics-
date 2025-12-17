"""
Kubernetes API Client

This module provides a read-only wrapper around the Kubernetes Python client
for AI diagnostics and incident analysis.

Functions:
- get_pods(namespace) - List all pods in namespace
- get_pod_status(namespace, pod_name) - Get detailed pod status
- get_logs(namespace, pod_name, tail_lines) - Get pod logs
- get_events(namespace, field_selector) - Get events for resources
"""

from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class K8sClient:
    def __init__(self):
        """Initialize Kubernetes client (read-only)"""
        try:
            if os.getenv('K8S_IN_CLUSTER', 'false').lower() == 'true':
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes config")
            else:
                config.load_kube_config()
                logger.info("Loaded kubeconfig from filesystem")
            
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            logger.info("Kubernetes client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize K8s client: {e}")
            raise
    
#     def get_pod_status(self, namespace: str, pod_name: str):
#         """Get the status of a specific pod"""
#         try:
#             pod = self.core_v1.read_namespaced_pod(pod_name, namespace)
#             return {
#                 'name': pod.metadata.name,
#                 'namespace': pod.metadata.namespace,
#                 'phase': pod.status.phase,
#                 'conditions': [c.to_dict() for c in pod.status.conditions] if pod.status.conditions else [],

    def get_pods(self, namespace: str = "default") -> List[Dict]:
        """
        List all pods in a namespace
        
        Args:
            namespace: Kubernetes namespace
            
        Returns:
            List of pod information dictionaries
        """
        try:
            pods = self.core_v1.list_namespaced_pod(namespace)
            result = []
            for pod in pods.items:
                pod_info = {
                    'name': pod.metadata.name,
                    'namespace': pod.metadata.namespace,
                    'phase': pod.status.phase,
                    'ready': self._is_pod_ready(pod),
                    'restarts': self._get_restart_count(pod),
                    'node': pod.spec.node_name,
                    'created': pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
                }
                result.append(pod_info)
            
            logger.info(f"Listed {len(result)} pods in namespace {namespace}")
            return result
        except ApiException as e:
            logger.error(f"Error listing pods in namespace {namespace}: {e}")
            return []
    
    def get_pod_status(self, namespace: str, pod_name: str) -> Optional[Dict]:
        """
        Get detailed status of a specific pod
        
        Args:
            namespace: Kubernetes namespace
            pod_name: Name of the pod
            
        Returns:
            Detailed pod status dictionary or None
        """
        try:
            pod = self.core_v1.read_namespaced_pod(pod_name, namespace)
            
            container_statuses = []
            if pod.status.container_statuses:
                for c in pod.status.container_statuses:
                    state_info = {}
                    if c.state.running:
                        state_info = {'state': 'running', 'started_at': c.state.running.started_at.isoformat() if c.state.running.started_at else None}
                    elif c.state.waiting:
                        state_info = {'state': 'waiting', 'reason': c.state.waiting.reason, 'message': c.state.waiting.message}
                    elif c.state.terminated:
                        state_info = {
                            'state': 'terminated',
                            'reason': c.state.terminated.reason,
                            'exit_code': c.state.terminated.exit_code,
                            'message': c.state.terminated.message
                        }
                    
                    container_statuses.append({
                        'name': c.name,
                        'ready': c.ready,
                        'restart_count': c.restart_count,
                        **state_info
                    })
            
            pod_info = {
                'name': pod.metadata.name,
                'namespace': pod.metadata.namespace,
                'phase': pod.status.phase,
                'conditions': [{'type': c.type, 'status': c.status, 'reason': c.reason} for c in pod.status.conditions] if pod.status.conditions else [],
                'containers': container_statuses,
                'node': pod.spec.node_name,
                'qos_class': pod.status.qos_class,
                'created': pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
            }
            
            logger.info(f"Retrieved status for pod {pod_name} in namespace {namespace}")
            return pod_info
        except ApiException as e:
            logger.error(f"Error getting pod status for {pod_name}: {e}")
            return None
    
    def get_logs(self, namespace: str, pod_name: str, tail_lines: int = 100, container: Optional[str] = None) -> Optional[str]:
        """
        Get logs from a pod
        
        Args:
            namespace: Kubernetes namespace
            pod_name: Name of the pod
            tail_lines: Number of lines to retrieve from end
            container: Specific container name (if multi-container pod)
            
        Returns:
            Pod logs as string or None
        """
        try:
            kwargs = {
                'name': pod_name,
                'namespace': namespace,
                'tail_lines': tail_lines
            }
            if container:
                kwargs['container'] = container
                
            logs = self.core_v1.read_namespaced_pod_log(**kwargs)
            logger.info(f"Retrieved {tail_lines} lines of logs for pod {pod_name}")
            return logs
        except ApiException as e:
            logger.error(f"Error getting logs for pod {pod_name}: {e}")
            return None
    
    def get_events(self, namespace: str, field_selector: Optional[str] = None) -> List[Dict]:
        """
        Get events for a namespace or specific resource
        
        Args:
            namespace: Kubernetes namespace
            field_selector: Optional field selector (e.g., 'involvedObject.name=mypod')
            
        Returns:
            List of event dictionaries
        """
        try:
            kwargs = {'namespace': namespace}
            if field_selector:
                kwargs['field_selector'] = field_selector
                
            events = self.core_v1.list_namespaced_event(**kwargs)
            result = []
            
            for event in sorted(events.items, key=lambda e: e.last_timestamp or e.event_time, reverse=True):
                event_info = {
                    'type': event.type,
                    'reason': event.reason,
                    'message': event.message,
                    'object': f"{event.involved_object.kind}/{event.involved_object.name}",
                    'count': event.count,
                    'first_seen': event.first_timestamp.isoformat() if event.first_timestamp else None,
                    'last_seen': event.last_timestamp.isoformat() if event.last_timestamp else None
                }
                result.append(event_info)
            
            logger.info(f"Retrieved {len(result)} events from namespace {namespace}")
            return result[:50]  # Limit to 50 most recent events
        except ApiException as e:
            logger.error(f"Error getting events: {e}")
            return []
    
    def _is_pod_ready(self, pod) -> bool:
        """Check if pod is ready"""
        if not pod.status.conditions:
            return False
        for condition in pod.status.conditions:
            if condition.type == 'Ready':
                return condition.status == 'True'
        return False
    
    def _get_restart_count(self, pod) -> int:
        """Get total restart count for pod"""
        if not pod.status.container_statuses:
            return 0
        return sum(c.restart_count for c in pod.status.container_statuses)

