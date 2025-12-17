#!/bin/bash
set -e
cd /app
pip install --no-cache-dir -r requirements.txt
exec uvicorn ai.app:app --host 0.0.0.0 --port 8000
