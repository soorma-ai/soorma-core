#!/bin/bash

# Start script for 01-hello-tool example
#
# Prerequisites: Platform services must be running
#   Terminal 1: soorma dev --build
#

set -e

EXAMPLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_NAME="01-hello-tool"

echo "======================================================================"
echo "  Starting Example: $EXAMPLE_NAME"
echo "======================================================================"
echo ""
echo "This example demonstrates:"
echo "  • Multiple @on_invoke() handlers"
echo "  • Stateless, synchronous operations"
echo "  • InvocationContext for requests"
echo "  • Auto-publishing to response_event"
echo ""
echo "The tool will listen for these events:"
echo "  • math.add.requested"
echo "  • math.subtract.requested"
echo "  • math.multiply.requested"
echo "  • math.divide.requested"
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
echo "  Starting Calculator Tool"
echo "======================================================================"
echo ""

echo "📍 Next Step: Send a calculation request"
echo ""
echo "   In another terminal, run:"
echo "   cd $EXAMPLE_DIR"
echo "   python client.py --operation add --a 10 --b 5"
echo ""
echo "   Press Ctrl+C here to stop the tool"
echo "======================================================================"
echo ""

# Start the tool (runs until Ctrl+C)
python "$EXAMPLE_DIR/calculator_tool.py"
