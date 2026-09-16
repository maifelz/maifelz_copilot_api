#!/bin/bash
# mAifelZ AI Odoo Copilot — Backend Startup Script

echo "🚀 Starting mAifelZ AI Odoo Copilot Backend..."
cd "$(dirname "$0")"

# Create virtualenv if not exists
if [ ! -d "venv" ]; then
  echo "📦 Creating virtual environment..."
  python3 -m venv venv
fi

# Activate virtualenv
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet

# Copy env if not exists
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "⚠️  Created .env from template — please add your GEMINI_API_KEY!"
fi

# Start server
echo "✅ Backend starting at http://localhost:8000"
echo "📚 API Docs at http://localhost:8000/api/docs"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
