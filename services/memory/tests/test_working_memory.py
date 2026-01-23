"""Tests for working memory with different value types."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from memory_service.services.working_memory_service import WorkingMemoryService
from memory_service.crud.working import set_working_memory, get_working_memory
from soorma_common.models import WorkingMemorySet


class TestWorkingMemoryValueTypes:
    """Test working memory handles all JSON-serializable value types."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return WorkingMemoryService()

    @pytest.fixture
    def test_ids(self):
        """Generate test IDs."""
        return {
            "tenant_id": uuid4(),
            "plan_id": uuid4(),
        }

    async def test_string_value(self, db_session: AsyncSession, service, test_ids):
        """Test storing and retrieving string values."""
        key = "goal"
        string_value = "buy 100 bitcoins"
        
        # Store string value
        result = await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=string_value),
        )
        
        assert result.value == string_value
        assert result.key == key
        
        # Retrieve and verify
        retrieved = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
        )
        
        assert retrieved is not None
        assert retrieved.value == string_value

    async def test_integer_value(self, db_session: AsyncSession, service, test_ids):
        """Test storing and retrieving integer values."""
        key = "current_task_index"
        int_value = 42
        
        # Store integer value
        result = await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=int_value),
        )
        
        assert result.value == int_value
        assert isinstance(result.value, int)
        
        # Retrieve and verify
        retrieved = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
        )
        
        assert retrieved is not None
        assert retrieved.value == int_value
        assert isinstance(retrieved.value, int)

    async def test_list_value(self, db_session: AsyncSession, service, test_ids):
        """Test storing and retrieving list values."""
        key = "tasks"
        list_value = ["research market", "place order", "monitor price"]
        
        # Store list value
        result = await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=list_value),
        )
        
        assert result.value == list_value
        assert isinstance(result.value, list)
        
        # Retrieve and verify
        retrieved = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
        )
        
        assert retrieved is not None
        assert retrieved.value == list_value
        assert isinstance(retrieved.value, list)

    async def test_dict_value(self, db_session: AsyncSession, service, test_ids):
        """Test storing and retrieving dict values."""
        key = "config"
        dict_value = {
            "max_retries": 3,
            "timeout": 30.5,
            "enabled": True,
            "options": ["verbose", "debug"],
        }
        
        # Store dict value
        result = await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=dict_value),
        )
        
        assert result.value == dict_value
        assert isinstance(result.value, dict)
        
        # Retrieve and verify
        retrieved = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
        )
        
        assert retrieved is not None
        assert retrieved.value == dict_value
        assert isinstance(retrieved.value, dict)

    async def test_boolean_value(self, db_session: AsyncSession, service, test_ids):
        """Test storing and retrieving boolean values."""
        key = "is_complete"
        bool_value = True
        
        # Store boolean value
        result = await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=bool_value),
        )
        
        assert result.value is True
        assert isinstance(result.value, bool)
        
        # Retrieve and verify
        retrieved = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
        )
        
        assert retrieved is not None
        assert retrieved.value is True
        assert isinstance(retrieved.value, bool)

    async def test_none_value(self, db_session: AsyncSession, service, test_ids):
        """Test storing and retrieving None values."""
        key = "optional_data"
        none_value = None
        
        # Store None value
        result = await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=none_value),
        )
        
        assert result.value is None
        
        # Retrieve and verify
        retrieved = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
        )
        
        assert retrieved is not None
        assert retrieved.value is None

    async def test_float_value(self, db_session: AsyncSession, service, test_ids):
        """Test storing and retrieving float values."""
        key = "progress"
        float_value = 75.5
        
        # Store float value
        result = await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=float_value),
        )
        
        assert result.value == float_value
        assert isinstance(result.value, float)
        
        # Retrieve and verify
        retrieved = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
        )
        
        assert retrieved is not None
        assert retrieved.value == float_value
        assert isinstance(retrieved.value, float)

    async def test_nested_structure(self, db_session: AsyncSession, service, test_ids):
        """Test storing and retrieving complex nested structures."""
        key = "complex_state"
        nested_value = {
            "goal": "buy 100 bitcoins",
            "tasks": ["research", "execute", "monitor"],
            "metadata": {
                "created": "2024-01-01",
                "priority": 1,
                "tags": ["crypto", "trading"],
            },
            "completed": False,
            "progress": 0.5,
            "notes": None,
        }
        
        # Store nested structure
        result = await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=nested_value),
        )
        
        assert result.value == nested_value
        
        # Retrieve and verify
        retrieved = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
        )
        
        assert retrieved is not None
        assert retrieved.value == nested_value
        assert retrieved.value["goal"] == "buy 100 bitcoins"
        assert len(retrieved.value["tasks"]) == 3
        assert retrieved.value["metadata"]["priority"] == 1

    async def test_empty_structures(self, db_session: AsyncSession, service, test_ids):
        """Test storing and retrieving empty collections."""
        # Empty list
        result = await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            "empty_list",
            WorkingMemorySet(value=[]),
        )
        assert result.value == []
        
        # Empty dict
        result = await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            "empty_dict",
            WorkingMemorySet(value={}),
        )
        assert result.value == {}
        
        # Empty string
        result = await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            "empty_string",
            WorkingMemorySet(value=""),
        )
        assert result.value == ""

    async def test_upsert_behavior(self, db_session: AsyncSession, service, test_ids):
        """Test that updating existing key works correctly."""
        key = "counter"
        
        # Store initial value
        await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=0),
        )
        
        # Update with new value
        result = await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=1),
        )
        
        assert result.value == 1
        
        # Verify only one record exists
        retrieved = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
        )
        assert retrieved.value == 1

    async def test_value_type_changes(self, db_session: AsyncSession, service, test_ids):
        """Test that value type can change for the same key."""
        key = "dynamic_value"
        
        # Store as string
        await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value="initial"),
        )
        
        # Update to integer
        await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=42),
        )
        
        result = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
        )
        assert result.value == 42
        assert isinstance(result.value, int)
        
        # Update to list
        await service.set(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=["a", "b", "c"]),
        )
        
        result = await service.get(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
        )
        assert result.value == ["a", "b", "c"]
        assert isinstance(result.value, list)


class TestWorkingMemoryCRUD:
    """Test CRUD operations directly."""

    @pytest.fixture
    def test_ids(self):
        """Generate test IDs."""
        return {
            "tenant_id": uuid4(),
            "plan_id": uuid4(),
        }

    async def test_crud_string_value(self, db_session: AsyncSession, test_ids):
        """Test CRUD layer handles string values."""
        key = "test_key"
        value = "test value"
        
        # Set value
        memory = await set_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=value),
        )
        
        assert memory.value == value
        
        # Get value
        retrieved = await get_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
        )
        
        assert retrieved is not None
        assert retrieved.value == value

    async def test_crud_integer_value(self, db_session: AsyncSession, test_ids):
        """Test CRUD layer handles integer values."""
        key = "counter"
        value = 123
        
        memory = await set_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=value),
        )
        
        assert memory.value == value
        assert isinstance(memory.value, int)

    async def test_crud_list_value(self, db_session: AsyncSession, test_ids):
        """Test CRUD layer handles list values."""
        key = "items"
        value = [1, 2, 3, "four", True]
        
        memory = await set_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=value),
        )
        
        assert memory.value == value
        assert isinstance(memory.value, list)

    async def test_crud_dict_value(self, db_session: AsyncSession, test_ids):
        """Test CRUD layer handles dict values."""
        key = "config"
        value = {"setting": "value", "count": 10}
        
        memory = await set_working_memory(
            db_session,
            test_ids["tenant_id"],
            test_ids["plan_id"],
            key,
            WorkingMemorySet(value=value),
        )
        
        assert memory.value == value
        assert isinstance(memory.value, dict)
