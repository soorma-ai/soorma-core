#!/bin/bash
# Start script for 04-memory-working example

set -e

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_NAME="04-memory-working"
REPO_ROOT="$(cd "$EXAMPLE_DIR/../.." && pwd)"

echo "🚀 Starting 04-memory-working example..."
echo ""
echo "This example demonstrates working memory with request/response pattern."
echo ""

# Check if platform services are running
echo "Checking platform services..."
if ! curl -s http://localhost:8083/health > /dev/null 2>&1; then
    echo "❌ Memory Service not responding"
    echo ""
    echo "Please start platform services first:"
    echo "  cd ../../  # Go to soorma-core root"
    echo "  soorma dev --build"
    echo ""
    exit 1
fi

echo "✓ Memory Service is running"
echo ""
echo "🔐 Priming shared example token provider..."
(cd "$REPO_ROOT" && python -m examples.shared.auth "$EXAMPLE_NAME" "$EXAMPLE_DIR") > /dev/null
echo "✓ Example identity bootstrap and token cache ready"
echo ""

echo "This example requires 2 agents running simultaneously:"
echo "  1. Planner (orchestrates workflow, listens for responses)"
echo "  2. Worker (executes tasks, responds to planner)"
echo ""
echo "Starting all agents..."
echo ""

# Use trap to cleanup background processes
trap 'kill $(jobs -p) 2>/dev/null' EXIT

# Start agents in background
echo "Starting planner..."
python3 "$EXAMPLE_DIR/planner.py" &
PLANNER_PID=$!
sleep 2

echo "Starting worker..."
python3 "$EXAMPLE_DIR/worker.py" &
WORKER_PID=$!
sleep 2

echo ""
echo "✅ All agents running!"
echo ""
echo "Now start the workflow in another terminal:"
echo "  cd examples/04-memory-working"
echo "  python3 client.py"
echo ""
echo "Press Ctrl+C to stop all agents"
echo ""

# Wait for any process to exit
wait
