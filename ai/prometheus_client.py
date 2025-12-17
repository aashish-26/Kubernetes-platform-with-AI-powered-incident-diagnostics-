"""
Prometheus API Client

This module provides a client for querying Prometheus metrics
to support AI-powered diagnostics.

Functions:
- query(promql) - Execute instant PromQL query
- get_pod_cpu_usage(namespace, pod_name) - Get CPU usage
- get_pod_memory_usage(namespace, pod_name) - Get memory usage
- get_pod_restarts(namespace, pod_name) - Get restart count
"""

import os
import requests
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class PrometheusClient:
    def __init__(self, base_url: str = "http://prometheus-stack-kube-prom-prometheus.monitoring:9090"):
        """
        Initialize Prometheus client
        
        Args:
            base_url: Prometheus server URL
        """
        # Allow override via environment for local runs
        env_url = os.getenv("PROMETHEUS_URL")
        self.base_url = (env_url or base_url).rstrip('/')
        self.api_url = f"{self.base_url}/api/v1"
        logger.info(f"Prometheus client initialized with URL: {self.base_url}")
    
    def query(self, promql: str) -> Optional[Dict]:
        """
        Execute an instant PromQL query
        
        Args:
            promql: PromQL query string
        
        Returns:
            Query results or None on error
        """
        try:
            response = requests.get(
                f"{self.api_url}/query",
                params={'query': promql},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'success':
                logger.info(f"Query successful: {promql[:50]}...")
                return data['data']
            else:
                logger.error(f"Query failed: {data.get('error', 'Unknown error')}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Prometheus: {e}")
            return None
    
    def query_range(self, promql: str, start: datetime, end: datetime, step: str = "30s") -> Optional[Dict]:
        """
        Execute a range PromQL query
        
        Args:
            promql: PromQL query string
            start: Start time
            end: End time
            step: Query resolution step
        
        Returns:
            Query results or None on error
        """
        try:
            response = requests.get(
                f"{self.api_url}/query_range",
                params={
                    'query': promql,
                    'start': start.isoformat(),
                    'end': end.isoformat(),
                    'step': step
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'success':
                logger.info(f"Range query successful")
                return data['data']
            else:
                logger.error(f"Range query failed: {data.get('error')}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Prometheus range: {e}")
            return None
    
    def get_pod_cpu_usage(self, namespace: str, pod_name: str) -> Optional[float]:
        """
        Get current CPU usage for a pod (in millicores)
        
        Args:
            namespace: Kubernetes namespace
            pod_name: Pod name
            
        Returns:
            CPU usage in millicores or None
        """
        promql = f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", pod=~"{pod_name}.*"}}[5m])) * 1000'
        result = self.query(promql)
        
        if result and result.get('result'):
            value = float(result['result'][0]['value'][1])
            logger.info(f"CPU usage for {pod_name}: {value:.2f}m")
            return value
        return None
    
    def get_pod_memory_usage(self, namespace: str, pod_name: str) -> Optional[float]:
        """
        Get current memory usage for a pod (in MB)
        
        Args:
            namespace: Kubernetes namespace
            pod_name: Pod name
            
        Returns:
            Memory usage in MB or None
        """
        promql = f'sum(container_memory_working_set_bytes{{namespace="{namespace}", pod=~"{pod_name}.*"}}) / 1024 / 1024'
        result = self.query(promql)
        
        if result and result.get('result'):
            value = float(result['result'][0]['value'][1])
            logger.info(f"Memory usage for {pod_name}: {value:.2f}Mi")
            return value
        return None
    
    def get_pod_restarts(self, namespace: str, pod_name: str) -> Optional[int]:
        """
        Get restart count for a pod
        
        Args:
            namespace: Kubernetes namespace
            pod_name: Pod name
            
        Returns:
            Restart count or None
        """
        promql = f'kube_pod_container_status_restarts_total{{namespace="{namespace}", pod=~"{pod_name}.*"}}'
        result = self.query(promql)
        
        if result and result.get('result'):
            value = int(float(result['result'][0]['value'][1]))
            logger.info(f"Restart count for {pod_name}: {value}")
            return value
        return None
    
    def get_namespace_metrics(self, namespace: str) -> Dict[str, Any]:
        """
        Get aggregated metrics for entire namespace
        
        Args:
            namespace: Kubernetes namespace
            
        Returns:
            Dictionary with CPU, memory, pod count
        """
        metrics = {}
        
        # Total CPU usage
        cpu_query = f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}"}}[5m])) * 1000'
        cpu_result = self.query(cpu_query)
        if cpu_result and cpu_result.get('result'):
            metrics['cpu_millicores'] = float(cpu_result['result'][0]['value'][1])
        
        # Total memory usage
        mem_query = f'sum(container_memory_working_set_bytes{{namespace="{namespace}"}}) / 1024 / 1024'
        mem_result = self.query(mem_query)
        if mem_result and mem_result.get('result'):
            metrics['memory_mb'] = float(mem_result['result'][0]['value'][1])
        
        # Pod count
        pod_query = f'count(kube_pod_info{{namespace="{namespace}"}})'
        pod_result = self.query(pod_query)
        if pod_result and pod_result.get('result'):
            metrics['pod_count'] = int(float(pod_result['result'][0]['value'][1]))
        
        logger.info(f"Namespace {namespace} metrics: {metrics}")
        return metrics
    
    def check_oom_kills(self, namespace: str, lookback_minutes: int = 15) -> List[Dict]:
        """
        Check for OOM kills in namespace
        
        Args:
            namespace: Kubernetes namespace
            lookback_minutes: How far back to look
            
        Returns:
            List of OOM killed containers
        """
        # Query for OOMKilled events
        promql = f'kube_pod_container_status_last_terminated_reason{{namespace="{namespace}", reason="OOMKilled"}} == 1'
        result = self.query(promql)
        
        oom_kills = []
        if result and result.get('result'):
            for item in result['result']:
                oom_kills.append({
                    'pod': item['metric'].get('pod'),
                    'container': item['metric'].get('container'),
                    'namespace': item['metric'].get('namespace')
                })
        
        logger.info(f"Found {len(oom_kills)} OOM kills in namespace {namespace}")
        return oom_kills

#                 f"{self.api_url}/query",
#                 params={'query': promql}
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.exceptions.RequestException as e:
#             logger.error(f"Error querying Prometheus: {e}")
#             return None
#     
#     def query_range(self, promql: str, start: str, end: str, step: str = "15s"):
#         """Execute a range PromQL query"""
#         # TODO: Implement range query
#         pass
#     
#     def get_pod_cpu_usage(self, namespace: str, pod_name: str):
#         """Get CPU usage for a pod"""
#         promql = f'rate(container_cpu_usage_seconds_total{{namespace="{namespace}", pod="{pod_name}"}}[5m])'
#         # TODO: Implement and parse query
#         pass
#     
#     def get_pod_memory_usage(self, namespace: str, pod_name: str):
#         """Get memory usage for a pod"""
#         promql = f'container_memory_working_set_bytes{{namespace="{namespace}", pod="{pod_name}"}}'
#         # TODO: Implement and parse query
#         pass
#     
#     def get_request_latency(self, service_name: str):
#         """Get request latency metrics for a service"""
#         # TODO: Implement latency query
#         pass
#     
#     def get_error_rate(self, service_name: str):
#         """Get error rate for a service"""
#         # TODO: Implement error rate query
#         pass
