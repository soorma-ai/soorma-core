"""Embedding generation service using OpenAI."""

from typing import List
from openai import AsyncOpenAI

from memory_service.core.config import settings


class EmbeddingService:
    """Service for generating embeddings."""

    def __init__(self):
        """Initialize the embedding service."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model
        self.dimensions = settings.embedding_dimensions

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.dimensions

        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dimensions,
        )
        return response.data[0].embedding

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Filter out empty texts and track indices
        non_empty_texts = []
        indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                non_empty_texts.append(text)
                indices.append(i)

        if not non_empty_texts:
            # All texts were empty, return zero vectors
            return [[0.0] * self.dimensions] * len(texts)

        # Generate embeddings for non-empty texts
        response = await self.client.embeddings.create(
            model=self.model,
            input=non_empty_texts,
            dimensions=self.dimensions,
        )

        # Build result array with zero vectors for empty texts
        result = [[0.0] * self.dimensions] * len(texts)
        for i, embedding_data in enumerate(response.data):
            original_index = indices[i]
            result[original_index] = embedding_data.embedding

        return result


# Global embedding service instance
embedding_service = EmbeddingService()
