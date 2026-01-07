#!/bin/bash
#
# Start script for 02-events-simple example
#
# Prerequisites: Platform services must be running
#   Terminal 1: soorma dev --build
#

set -e

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_NAME="02-events-simple"

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
echo "  Starting Subscriber Agent"
echo "======================================================================"
echo ""

# Start the subscriber
python "$EXAMPLE_DIR/subscriber.py" &
SUBSCRIBER_PID=$!

# Give the subscriber a moment to start and print its startup messages
sleep 2

echo ""
echo "======================================================================"
echo "  ✓ Subscriber Running (PID: $SUBSCRIBER_PID)"
echo "======================================================================"
echo ""
echo "📍 Next Step: Publish events"
echo ""
echo "   In another terminal, run:"
echo "   cd $EXAMPLE_DIR"
echo "   python publisher.py"
echo ""
echo "   Press Ctrl+C here to stop the subscriber"
echo "======================================================================"
echo ""

# Wait for subscriber or handle Ctrl+C
trap "echo ''; echo 'Stopping subscriber...'; kill $SUBSCRIBER_PID 2>/dev/null; exit 0" INT TERM

wait $SUBSCRIBER_PID
