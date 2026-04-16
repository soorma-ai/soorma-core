"""
Calculator Tool - Minimal Tool Pattern Example

This example demonstrates the Tool pattern with:
- Multiple @on_invoke() handlers for different operations
- Stateless, synchronous request/response
- InvocationContext for handling requests
- Auto-publishing results to caller-specified response_event
"""

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soorma import Tool, InvocationContext, PlatformContext

from examples.shared.auth import build_example_token_provider

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


EXAMPLE_NAME = "01-hello-tool"
EXAMPLE_TOKEN_PROVIDER = build_example_token_provider(EXAMPLE_NAME, __file__)


# Create the calculator tool
calculator = Tool(
    name="calculator-tool",
    description="Performs basic arithmetic operations (add, subtract, multiply, divide)",
    default_response_event="calculator.completed",  # Fallback if caller doesn't specify
    auth_token_provider=EXAMPLE_TOKEN_PROVIDER,
)


@calculator.on_invoke("math.add.requested")
async def handle_add(request: InvocationContext, context: PlatformContext):
    """Handle addition requests."""
    a = request.data.get("a", 0)
    b = request.data.get("b", 0)
    result = a + b
    
    logger.info(f"[ADD] {a} + {b} = {result}")
    
    return {
        "request_id": request.request_id,
        "operation": "add",
        "result": result,
        "inputs": {"a": a, "b": b}
    }


@calculator.on_invoke("math.subtract.requested")
async def handle_subtract(request: InvocationContext, context: PlatformContext):
    """Handle subtraction requests."""
    a = request.data.get("a", 0)
    b = request.data.get("b", 0)
    result = a - b
    
    logger.info(f"[SUBTRACT] {a} - {b} = {result}")
    
    return {
        "request_id": request.request_id,
        "operation": "subtract",
        "result": result,
        "inputs": {"a": a, "b": b}
    }


@calculator.on_invoke("math.multiply.requested")
async def handle_multiply(request: InvocationContext, context: PlatformContext):
    """Handle multiplication requests."""
    a = request.data.get("a", 0)
    b = request.data.get("b", 0)
    result = a * b
    
    logger.info(f"[MULTIPLY] {a} * {b} = {result}")
    
    return {
        "request_id": request.request_id,
        "operation": "multiply",
        "result": result,
        "inputs": {"a": a, "b": b}
    }


@calculator.on_invoke("math.divide.requested")
async def handle_divide(request: InvocationContext, context: PlatformContext):
    """Handle division requests with zero-division protection."""
    a = request.data.get("a", 0)
    b = request.data.get("b", 0)
    
    if b == 0:
        logger.warning(f"[DIVIDE] Division by zero attempted: {a} / {b}")
        return {
            "request_id": request.request_id,
            "operation": "divide",
            "error": "Division by zero",
            "inputs": {"a": a, "b": b}
        }
    
    result = a / b
    logger.info(f"[DIVIDE] {a} / {b} = {result}")
    
    return {
        "request_id": request.request_id,
        "operation": "divide",
        "result": result,
        "inputs": {"a": a, "b": b}
    }


if __name__ == "__main__":
    logger.info("Starting Calculator Tool...")
    logger.info(f"Listening for events: {calculator.config.events_consumed}")
    logger.info(f"Publishing to events: {calculator.config.events_produced}")
    calculator.run()
