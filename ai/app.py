"""
AI Diagnostics Service - FastAPI entrypoint

Exposes deterministic diagnostics over HTTP. No external cloud calls.

Endpoints:
- POST /ask  : analyze a pod/service
- GET  /health
- GET  /ready
"""

import logging
import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .agent import AIAgent


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("ai-diagnostics")

app = FastAPI(title="AI Diagnostics Service", version="1.0.0")

agent = AIAgent()


class AskRequest(BaseModel):
	namespace: str = Field(..., example="apps")
	pod_name: Optional[str] = Field(None, example="backend-api-abc123")
	service_name: Optional[str] = Field(None, example="backend-api")
	include_logs: bool = Field(False, description="Tail pod logs (120 lines)")


class AskResponse(BaseModel):
	summary: str
	root_cause: str
	recommendations: List[str]
	confidence: float
	evidence: dict


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
	try:
		result = agent.analyze_incident(
			namespace=req.namespace,
			pod_name=req.pod_name,
			service_name=req.service_name,
			include_logs=req.include_logs,
		)
		return AskResponse(
			summary=result.summary,
			root_cause=result.root_cause,
			recommendations=result.recommendations,
			confidence=result.confidence,
			evidence=result.evidence,
		)
	except Exception as e:
		logger.exception("Error analyzing incident")
		raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
	return {"status": "ok"}


@app.get("/ready")
async def ready():
	try:
		# Lightweight readiness: ensure k8s client can list namespaces
		_ = agent.k8s.get_pods(namespace="kube-system")
		return {"status": "ready"}
	except Exception as e:
		logger.error(f"Readiness check failed: {e}")
		raise HTTPException(status_code=503, detail="Dependencies not ready")


if __name__ == "__main__":
	import uvicorn

	uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
