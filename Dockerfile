FROM python:3.11-slim
WORKDIR /app
COPY ai /app/ai
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ENV K8S_IN_CLUSTER=true
ENV LOG_LEVEL=INFO
EXPOSE 8000
CMD ["uvicorn", "ai.app:app", "--host", "0.0.0.0", "--port", "8000"]
