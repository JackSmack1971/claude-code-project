#!/bin/bash
# Test script for AgentFactory

set -e

echo "🧪 Running AgentFactory Test Suite..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install test dependencies
echo "📦 Installing test dependencies..."
cd tests
pip install -r requirements.txt
cd ..

# Run pytest
echo ""
echo "🔬 Running tests..."
pytest tests/ -v --tb=short

echo ""
echo "✅ All tests completed!"
