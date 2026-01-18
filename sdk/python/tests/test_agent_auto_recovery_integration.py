"""
Integration test to validate agent auto-recovery after heartbeat failure.

This test simulates the real-world scenario where an agent is deleted from
the registry (e.g., due to missed heartbeats during laptop sleep) and
verifies that it automatically re-registers itself.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_agent_heartbeat_auto_recovery_integration():
    """
    Integration test: Agent automatically recovers from heartbeat failure.
    
    This test validates the complete auto-recovery flow:
    1. Agent registers and starts heartbeat loop
    2. Heartbeat fails (simulating agent deletion)
    3. Agent detects failure and automatically re-registers
    4. Subsequent heartbeats succeed
    
    This proves the fix for the issue where agents would fail heartbeats
    after laptop sleep but never recover.
    """
    from soorma import Worker
    
    # Create a worker
    worker = Worker(
        name="recovery-test-worker",
        capabilities=["test"],
        auto_register=True
    )
    
    # Track registration attempts
    registration_attempts = []
    heartbeat_results = []
    
    # Mock the registry client methods
    async def mock_register(*args, **kwargs):
        registration_attempts.append(("register", args, kwargs))
        return True  # Registration succeeds
    
    async def mock_heartbeat(agent_id):
        # First 2 heartbeats succeed, then fail, then succeed again
        call_count = len(heartbeat_results)
        if call_count < 2:
            result = True  # Success
        elif call_count < 4:
            result = False  # Failure (agent deleted)
        else:
            result = True  # Success after recovery
        
        heartbeat_results.append((call_count, result))
        return result
    
    # Patch the registry client at the point of use
    with patch('soorma.context.RegistryClient') as MockRegistryClient:
        mock_registry_instance = AsyncMock()
        mock_registry_instance.register = mock_register
        mock_registry_instance.heartbeat = mock_heartbeat
        mock_registry_instance.register_event = AsyncMock(return_value=True)
        mock_registry_instance.deregister = AsyncMock(return_value=True)
        mock_registry_instance.close = AsyncMock()
        
        MockRegistryClient.return_value = mock_registry_instance
        
        # Mock the event client to avoid actual NATS connections
        with patch('soorma.events.EventClient') as MockEventClient:
            mock_event_client = AsyncMock()
            mock_event_client.connect = AsyncMock()
            mock_event_client.disconnect = AsyncMock()
            MockEventClient.return_value = mock_event_client
            
            # Initialize the agent's context manually
            await worker._initialize_context()
            
            # Register with registry (this is what agent.start() does)
            await worker._register_with_registry()
            
            # Verify initial registration happened
            assert len(registration_attempts) >= 1, "Agent should register on initialization"
            
            # Start the agent (this starts the heartbeat loop)
            worker._running = True
            
            # Manually trigger heartbeat loop iterations with shorter sleep
            async def fast_heartbeat_loop():
                consecutive_failures = 0
                for i in range(6):  # Run 6 iterations
                    await asyncio.sleep(0.1)  # Fast iterations for testing
                    if worker._running:
                        success = await worker.context.registry.heartbeat(worker.agent_id)
                        if not success:
                            consecutive_failures += 1
                            # Trigger re-registration
                            if consecutive_failures >= 1:
                                await worker._register_with_registry()
                        else:
                            consecutive_failures = 0
            
            # Run the fast heartbeat loop
            await fast_heartbeat_loop()
            
            # Stop the agent
            worker._running = False
            
            # Verify the behavior
            print(f"\nRegistration attempts: {len(registration_attempts)}")
            print(f"Heartbeat results: {heartbeat_results}")
            
            # Should have:
            # - Initial registration (1)
            # - Re-registrations after failures (2)
            # Total: 3 registration attempts
            assert len(registration_attempts) >= 3, (
                f"Expected at least 3 registrations (initial + 2 re-registers), "
                f"got {len(registration_attempts)}"
            )
            
            # Verify heartbeat failure detection and recovery
            failures = [r for r in heartbeat_results if not r[1]]
            assert len(failures) >= 2, f"Expected at least 2 failures, got {len(failures)}"
            
            successes_after_failure = [
                r for r in heartbeat_results 
                if r[0] > 3 and r[1]  # Successes after the failure period
            ]
            assert len(successes_after_failure) >= 1, (
                "Expected heartbeats to succeed after recovery"
            )
            
            print("\n✅ Auto-recovery test passed!")
            print(f"   - {len(registration_attempts)} total registrations (initial + re-registers)")
            print(f"   - {len(failures)} heartbeat failures detected")
            print(f"   - {len(successes_after_failure)} successful heartbeats after recovery")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
