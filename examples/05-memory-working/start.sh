#!/bin/bash
# Start script for 05-memory-working example

echo "🚀 Starting 05-memory-working example..."
echo ""
echo "This example demonstrates working memory and multi-agent workflows."
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

echo "This example requires 3 agents running simultaneously:"
echo "  1. Planner (initializes workflow)"
echo "  2. Worker (executes tasks)"
echo "  3. Coordinator (advances workflow)"
echo ""
echo "Starting all agents..."
echo ""

# Use trap to cleanup background processes
trap 'kill $(jobs -p) 2>/dev/null' EXIT

# Start agents in background
echo "Starting planner..."
python3 planner.py &
PLANNER_PID=$!
sleep 2

echo "Starting worker..."
python3 worker.py &
WORKER_PID=$!
sleep 2

echo "Starting coordinator..."
python3 coordinator.py &
COORDINATOR_PID=$!
sleep 2

echo ""
echo "✅ All agents running!"
echo ""
echo "Now submit a goal in another terminal:"
echo "  cd examples/05-memory-working"
echo "  python3 client.py 'Write a blog post about Docker'"
echo ""
echo "Or try the manual state demo:"
echo "  python3 manual_state.py"
echo ""
echo "Press Ctrl+C to stop all agents"
echo ""

# Wait for any process to exit
wait
