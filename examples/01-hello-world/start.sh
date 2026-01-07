#!/bin/bash
#
# Start script for 01-hello-world example
#
# Prerequisites: Platform services must be running
#   Terminal 1: soorma dev --build
#

set -e

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_NAME="01-hello-world"

echo "======================================================================"
echo "  Starting Example: $EXAMPLE_NAME"
echo "======================================================================"
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
echo "======================================================================"
echo "  Starting Worker Agent"
echo "======================================================================"
echo ""

# Start the worker
python "$EXAMPLE_DIR/worker.py" &
WORKER_PID=$!

# Give the worker a moment to start and print its startup messages
sleep 2

echo ""
echo "======================================================================"
echo "  ✓ Worker Running (PID: $WORKER_PID)"
echo "======================================================================"
echo ""
echo "📍 Next Step: Send a greeting request"
echo ""
echo "   In another terminal, run:"
echo "   cd $EXAMPLE_DIR"
echo "   python client.py Alice"
echo ""
echo "   Press Ctrl+C here to stop the worker"
echo "======================================================================"
echo ""

# Wait for worker or handle Ctrl+C
trap "echo ''; echo 'Stopping worker...'; kill $WORKER_PID 2>/dev/null; exit 0" INT TERM

wait $WORKER_PID
