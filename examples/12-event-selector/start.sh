#!/bin/bash
#
# Start script for 12-event-selector example
#
# Prerequisites: Platform services must be running
#   Terminal 1: soorma dev --build
#

set -e

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_NAME="12-event-selector"

echo "======================================================================"
echo "  Starting Example: $EXAMPLE_NAME"
echo "======================================================================"
echo ""
echo "This example demonstrates LLM-based intelligent event routing:"
echo "  - Three specialist workers register their event types at startup"
echo "  - EventSelector asks the LLM which worker should handle each ticket"
echo "  - Router never hard-codes event names — adapts as workers come and go"
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
echo "  Starting Specialist Workers"
echo "======================================================================"
echo ""

python "$EXAMPLE_DIR/technical_worker.py" &
TECH_PID=$!

python "$EXAMPLE_DIR/billing_worker.py" &
BILLING_PID=$!

python "$EXAMPLE_DIR/escalation_worker.py" &
ESCALATION_PID=$!

sleep 3  # Allow all workers to register with Registry before the router starts

echo ""
echo "======================================================================"
echo "  Starting Ticket Router"
echo "======================================================================"
echo ""

python "$EXAMPLE_DIR/router.py" &
ROUTER_PID=$!

sleep 2  # Allow router to start and subscribe to events before clients start sending tickets

echo ""
echo "======================================================================"
echo "  All Agents Running"
echo "======================================================================"
echo ""
echo "  Technical Worker PID:  $TECH_PID"
echo "  Billing Worker PID:    $BILLING_PID"
echo "  Escalation Worker PID: $ESCALATION_PID"
echo "  Router PID:            $ROUTER_PID"
echo ""
echo "Next Step: Submit a support ticket from another terminal"
echo "  cd $EXAMPLE_DIR"
echo "  python client.py technical   # routes to technical-worker"
echo "  python client.py billing     # routes to billing-worker"
echo "  python client.py escalation  # routes to escalation-worker"
echo ""

wait
