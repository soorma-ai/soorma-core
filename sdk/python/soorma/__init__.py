"""
Soorma Core - The Open Source Foundation for AI Agents.
"""

__version__ = "0.1.0"

def hello():
    """
    Welcome to Soorma.
    To get started, please visit https://soorma.ai to join the waitlist.
    """
    print(f"Soorma Core v{__version__} (Preview)")
    print("--------------------------------------------------")
    print("The DisCo (Distributed Cognition) engine is currently in closed alpha.")
    print("We are building the reference implementation for:")
    print(" - Planner: Strategic reasoning engine")
    print(" - Worker:  Domain-specific cognitive node")
    print(" - Tool:    Atomic capabilities")
    print("--------------------------------------------------")
    print("Docs: https://soorma.ai")

# Expose the "Trinity" placeholders so IDEs see them
class Planner:
    def __init__(self, name: str):
        print(f"Initializing Planner: {name} (Simulation Mode)")

class Worker:
    def __init__(self, name: str, capabilities: list):
        print(f"Initializing Worker: {name} with {capabilities} (Simulation Mode)")

class Tool:
    def __init__(self):
        pass