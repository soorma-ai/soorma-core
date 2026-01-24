#!/bin/bash
#
# Start script for 03-events-structured example
#
# Prerequisites:
#   1. Platform services running: soorma dev --build
#   2. OPENAI_API_KEY environment variable set
#

set -e

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_NAME="03-events-structured"

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

# Check for OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set"
    echo ""
    echo "This example requires an OpenAI API key for LLM-based event selection."
    echo "Please set your API key:"
    echo "  export OPENAI_API_KEY='your-key-here'"
    echo ""
    exit 1
fi

echo "======================================================================"
echo "  Step 1: Registering Events with Registry"
echo "======================================================================"
echo ""

echo "✓ SDK will auto-register events when agent starts"
echo ""
echo "======================================================================"
echo "  Step 2: Starting Ticket Router Agent"
echo "======================================================================"
echo ""

# Start the router
python "$EXAMPLE_DIR/ticket_router.py" &
ROUTER_PID=$!

# Give the router a moment to start and print its startup messages
sleep 6

echo ""
echo "======================================================================"
echo "  ✓ Ticket Router Running (PID: $ROUTER_PID)"
echo "======================================================================"
echo ""
echo "📍 Next Step: Create test tickets"
echo ""
echo "   In another terminal, run:"
echo "   cd $EXAMPLE_DIR"
echo "   python client.py"
echo ""
echo "   Or create a custom ticket:"
echo "   python client.py \"My API integration is failing\""
echo ""
echo "   Press Ctrl+C here to stop the router"
echo "======================================================================"
echo ""
echo ""
echo "Press Ctrl+C to stop the router"
echo ""

# Wait for router or handle Ctrl+C
trap "echo ''; echo 'Stopping router...'; kill $ROUTER_PID 2>/dev/null; exit 0" INT TERM

wait $ROUTER_PID
