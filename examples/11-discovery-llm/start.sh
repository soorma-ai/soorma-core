#!/bin/bash
#
# Start script for 11-discovery-llm example
#
# Prerequisites: Platform services must be running
#   Terminal 1: soorma dev --build
#

set -e

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_NAME="11-discovery-llm"

echo "======================================================================"
echo "  Starting Example: $EXAMPLE_NAME"
echo "======================================================================"
echo ""
echo "This example demonstrates LLM-based dynamic discovery:"
echo "  - Worker declares inline JSON Schema on AgentCapability"
echo "  - SDK auto-registers schema at startup (no explicit registration)"
echo "  - Planner discovers worker, fetches schema, uses LLM to build payload"
echo ""

if ! curl -s http://localhost:8081/health > /dev/null 2>&1; then
    echo "Platform services not running."
    echo ""
    echo "Start platform services first:"
    echo "  cd $(dirname $(dirname "$EXAMPLE_DIR"))"
    echo "  soorma dev --build"
    exit 1
fi

echo "Platform services detected"
echo ""

trap 'echo ""; echo "Stopping all agents..."; kill $(jobs -p) 2>/dev/null; exit 0' EXIT INT TERM

echo "======================================================================"
echo "  Starting Worker Agent"
echo "======================================================================"
echo ""

python "$EXAMPLE_DIR/worker.py" &
WORKER_PID=$!
sleep 2  # Give worker time to register agent + schema with Registry before planner runs

echo ""
echo "======================================================================"
echo "  Starting Planner Agent"
echo "======================================================================"
echo ""

python "$EXAMPLE_DIR/planner.py" &
PLANNER_PID=$!

echo ""
echo "======================================================================"
echo "  All Agents Running"
echo "======================================================================"
echo ""
echo "  Worker PID:  $WORKER_PID"
echo "  Planner PID: $PLANNER_PID"
echo ""
echo "Next Step: Send a research goal from another terminal"
echo "  cd $EXAMPLE_DIR"
echo "  See README.md for the publish snippet"
echo ""

wait

sleep 2 # give agents time to print final logs before exiting