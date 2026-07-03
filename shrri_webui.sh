#!/bin/bash
cd ~/shrri
echo "🚀 SHRRI Web UI starting on http://localhost:7788"
python3 -m uvicorn webui.api.main:app --host 0.0.0.0 --port 7788 --reload
