"""
Client library for interacting with the Memory Service.

The Memory Service implements the CoALA (Cognitive Architectures for Language Agents)
framework with four types of memory:
- Semantic Memory: Knowledge base with RAG and vector search
- Episodic Memory: User/Agent interaction history with temporal recall
- Procedural Memory: Dynamic prompts, rules, and skills
- Working Memory: Plan-scoped shared state for multi-agent collaboration
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
import httpx

from soorma_common.models import (
    SemanticMemoryCreate,
    SemanticMemoryResponse,
    EpisodicMemoryCreate,
    EpisodicMemoryResponse,
    ProceduralMemoryResponse,
    WorkingMemorySet,
    WorkingMemoryResponse,
)


class MemoryClient:
    """
    Client for interacting with the Memory Service API.
    
    This client provides methods for all four CoALA memory types:
    - Semantic: Knowledge storage and semantic search
    - Episodic: Interaction history and temporal recall
    - Procedural: Dynamic prompts and skills retrieval
    - Working: Plan-scoped state management
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8083",
        timeout: float = 30.0,
    ):
        """
        Initialize the memory client.
        
        Args:
            base_url: Base URL of the memory service (e.g., "http://localhost:8083")
            timeout: HTTP request timeout in seconds
            
        Note:
            v0.5.0 operates in single-tenant, unauthenticated mode.
            user_id and agent_id must be provided as method parameters.
            Multi-tenant authentication will be added via Identity Service in future releases.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    # Semantic Memory Methods
    
    async def store_knowledge(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SemanticMemoryResponse:
        """
        Store knowledge in semantic memory.
        
        The service automatically generates embeddings for vector search.
        
        Args:
            content: Knowledge content to store
            metadata: Optional metadata (e.g., source, tags, etc.)
            
        Returns:
            SemanticMemoryResponse with the stored memory
        """
        data = SemanticMemoryCreate(
            content=content,
            metadata=metadata or {},
        )
        
        response = await self._client.post(
            f"{self.base_url}/v1/memory/semantic",
            json=data.model_dump(by_alias=True),
        )
        response.raise_for_status()
        return SemanticMemoryResponse.model_validate(response.json())
    
    async def search_knowledge(
        self,
        query: str,
        limit: int = 5,
    ) -> List[SemanticMemoryResponse]:
        """
        Search semantic memory using vector similarity.
        
        Args:
            query: Search query
            limit: Maximum number of results (1-50)
            
        Returns:
            List of SemanticMemoryResponse ordered by relevance
        """
        response = await self._client.get(
            f"{self.base_url}/v1/memory/semantic/search",
            params={"q": query, "limit": limit},
        )
        response.raise_for_status()
        return [SemanticMemoryResponse.model_validate(item) for item in response.json()]
    
    # Episodic Memory Methods
    
    async def log_interaction(
        self,
        agent_id: str,
        role: str,
        content: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EpisodicMemoryResponse:
        """
        Log an interaction to episodic memory.
        
        Args:
            agent_id: Agent identifier
            role: Role (user, assistant, system, tool)
            content: Interaction content
            user_id: User identifier (required in single-tenant mode)
            metadata: Optional metadata
            
        Returns:
            EpisodicMemoryResponse with the logged memory
        """
        data = EpisodicMemoryCreate(
            agent_id=agent_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        
        response = await self._client.post(
            f"{self.base_url}/v1/memory/episodic",
            json=data.model_dump(by_alias=True),
            params={"user_id": user_id},
        )
        response.raise_for_status()
        return EpisodicMemoryResponse.model_validate(response.json())
    
    async def get_recent_history(
        self,
        agent_id: str,
        user_id: str,
        limit: int = 10,
    ) -> List[EpisodicMemoryResponse]:
        """
        Get recent interaction history (context window).
        
        Args:
            agent_id: Agent identifier
            user_id: User identifier (required in single-tenant mode)
            limit: Maximum number of results (1-100)
            
        Returns:
            List of EpisodicMemoryResponse ordered by recency
        """
        response = await self._client.get(
            f"{self.base_url}/v1/memory/episodic/recent",
            params={"agent_id": agent_id, "user_id": user_id, "limit": limit},
        )
        response.raise_for_status()
        return [EpisodicMemoryResponse.model_validate(item) for item in response.json()]
    
    async def search_interactions(
        self,
        agent_id: str,
        query: str,
        user_id: str,
        limit: int = 5,
    ) -> List[EpisodicMemoryResponse]:
        """
        Search episodic memory using vector similarity (long-term recall).
        
        Args:
            agent_id: Agent identifier
            query: Search query
            user_id: User identifier (required in single-tenant mode)
            limit: Maximum number of results (1-50)
            
        Returns:
            List of EpisodicMemoryResponse ordered by relevance
        """
        response = await self._client.get(
            f"{self.base_url}/v1/memory/episodic/search",
            params={"agent_id": agent_id, "q": query, "user_id": user_id, "limit": limit},
        )
        response.raise_for_status()
        return [EpisodicMemoryResponse.model_validate(item) for item in response.json()]
    
    # Procedural Memory Methods
    
    async def get_relevant_skills(
        self,
        agent_id: str,
        context: str,
        user_id: str,
        limit: int = 3,
    ) -> List[ProceduralMemoryResponse]:
        """
        Get relevant procedural knowledge (skills, prompts, rules).
        
        Returns system prompts and few-shot examples matching the context.
        
        Args:
            agent_id: Agent identifier
            context: Task/query context
            user_id: User identifier (required in single-tenant mode)
            limit: Maximum number of results (1-20)
            
        Returns:
            List of ProceduralMemoryResponse ordered by relevance
        """
        response = await self._client.get(
            f"{self.base_url}/v1/memory/procedural/context",
            params={"agent_id": agent_id, "q": context, "user_id": user_id, "limit": limit},
        )
        response.raise_for_status()
        return [ProceduralMemoryResponse.model_validate(item) for item in response.json()]
    
    # Working Memory Methods
    
    async def set_plan_state(
        self,
        plan_id: str,
        key: str,
        value: Dict[str, Any],
    ) -> WorkingMemoryResponse:
        """
        Set or update working memory value for a plan.
        
        Args:
            plan_id: Plan identifier
            key: State key
            value: State value (JSON)
            
        Returns:
            WorkingMemoryResponse with the stored state
        """
        data = WorkingMemorySet(value=value)
        
        response = await self._client.put(
            f"{self.base_url}/v1/memory/working/{plan_id}/{key}",
            json=data.model_dump(by_alias=True),
        )
        response.raise_for_status()
        return WorkingMemoryResponse.model_validate(response.json())
    
    async def get_plan_state(
        self,
        plan_id: str,
        key: str,
    ) -> WorkingMemoryResponse:
        """
        Get working memory value for a plan.
        
        Args:
            plan_id: Plan identifier
            key: State key
            
        Returns:
            WorkingMemoryResponse with the state
            
        Raises:
            httpx.HTTPStatusError: If key not found (404)
        """
        response = await self._client.get(
            f"{self.base_url}/v1/memory/working/{plan_id}/{key}",
        )
        response.raise_for_status()
        return WorkingMemoryResponse.model_validate(response.json())
    
    # Health Check
    
    async def health(self) -> Dict[str, Any]:
        """
        Check if the Memory Service is healthy.
        
        Returns:
            Health status dictionary
        """
        response = await self._client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
