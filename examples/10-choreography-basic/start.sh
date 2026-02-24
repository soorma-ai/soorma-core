#!/bin/bash
#
# Start script for 10-choreography-basic example
#
# Prerequisites: Platform services must be running
#   Terminal 1: soorma dev --build
#

set -e

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_NAME="10-choreography-basic"

echo "======================================================================"
echo "  Starting Example: $EXAMPLE_NAME"
echo "======================================================================"
echo ""
echo "This example demonstrates Stage 4 Phase 2 ChoreographyPlanner patterns:"
echo "  - LLM-driven event choreography"
echo "  - Planner + 3 workers (fetcher, analyzer, reporter)"
echo "  - Tracker progress queries"
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
echo "  Starting Worker Agents (must register events first)"
echo "======================================================================"
echo ""

python "$EXAMPLE_DIR/fetcher.py" &
FETCHER_PID=$!
sleep 1

python "$EXAMPLE_DIR/analyzer.py" &
ANALYZER_PID=$!
sleep 1

python "$EXAMPLE_DIR/reporter.py" &
REPORTER_PID=$!
sleep 2  # Give workers time to register their events

echo ""
echo "======================================================================"
echo "  Starting Planner Agent"
echo "======================================================================"
echo ""

python "$EXAMPLE_DIR/planner.py" &
PLANNER_PID=$!
sleep 2  # Give planner time to discover registered events

echo ""
echo "======================================================================"
echo "  All Agents Running"
echo "======================================================================"
echo ""
echo "  Planner PID:  $PLANNER_PID"
echo "  Fetcher PID:  $FETCHER_PID"
echo "  Analyzer PID: $ANALYZER_PID"
echo "  Reporter PID: $REPORTER_PID"
echo ""
echo "Next Step: Send a goal from another terminal"
echo "  cd $EXAMPLE_DIR"
echo "  See README.md for the publish snippet"
echo ""

wait
