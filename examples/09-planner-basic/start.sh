#!/bin/bash
#
# Start script for 09-planner-basic example
#
# Prerequisites: Platform services must be running
#   Terminal 1: soorma dev --build
#

set -e

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_NAME="09-planner-basic"

echo "======================================================================"
echo "  Starting Example: $EXAMPLE_NAME"
echo "======================================================================"
echo ""
echo "This example demonstrates Stage 4 Phase 1 Planner patterns:"
echo "  • @on_goal() decorator for goal handling"
echo "  • @on_transition() for state transitions"
echo "  • PlanContext state machine orchestration"
echo "  • 3-state workflow: start → research → complete"
echo ""

# Check if platform services are running
if ! curl -s http://localhost:8081/health > /dev/null 2>&1; then
    echo "❌ Platform services not running!"
    echo ""
    echo "Please start platform services first:"
    echo ""
    echo "  Terminal 1:"
    echo "  cd $(dirname $(dirname "$EXAMPLE_DIR"))"
    echo "  soorma dev --build"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "✓ Platform services detected"
echo ""

# Use trap to cleanup background processes
trap 'echo ""; echo "Stopping all agents..."; kill $(jobs -p) 2>/dev/null; exit 0' EXIT INT TERM

echo "======================================================================"
echo "  Starting Planner Agent"
echo "======================================================================"
echo ""

python "$EXAMPLE_DIR/planner.py" &
PLANNER_PID=$!
sleep 2

echo ""
echo "======================================================================"
echo "  Starting Worker Agent"
echo "======================================================================"
echo ""

python "$EXAMPLE_DIR/worker.py" &
WORKER_PID=$!
sleep 2

echo ""
echo "======================================================================"
echo "  ✓ All Agents Running"
echo "======================================================================"
echo ""
echo "  Planner PID: $PLANNER_PID"
echo "  Worker PID:  $WORKER_PID"
echo ""
echo "📍 Next Step: Send a research goal"
echo ""
echo "   In another terminal, run:"
echo "   cd $EXAMPLE_DIR"
echo "   python client.py 'AI agents'"
echo ""
echo "   Press Ctrl+C here to stop all agents"
echo "======================================================================"
echo ""

# Wait for any process to exit
wait
