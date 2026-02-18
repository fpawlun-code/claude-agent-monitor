"""
Qdrant-based memory system for rtx_agent.py
Uses in-memory Qdrant + local embeddings (no API costs)
"""

import time
import logging
from typing import Dict, List, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class QdrantMemory:
    """
    In-memory Qdrant-based memory system for rtx_agent.py.

    Stores task experiences as embeddings for semantic search.
    No external server needed - runs in-memory.
    """

    def __init__(self, collection_name: str = "agent_memories"):
        """
        Initialize the memory system.

        Args:
            collection_name: Name of the Qdrant collection
        """
        logger.info("[MEMORY] Initializing Qdrant memory system...")

        # In-memory Qdrant client
        self.client = QdrantClient(location=":memory:")

        # Load embedding model (384 dimensions)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.collection_name = collection_name

        # Create collection
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )

        self.memory_id = 0
        logger.info(f"[MEMORY] ✅ Ready (collection: {collection_name})")

    def add_memory(self, task: str, result: str, metadata: Dict[str, Any] = None) -> None:
        """
        Add a new memory to the system.

        Args:
            task: Task description
            result: Result/outcome of the task
            metadata: Additional metadata (optional)
        """
        try:
            # Generate embedding from task
            embedding = self.model.encode(task).tolist()

            # Create point
            point = PointStruct(
                id=self.memory_id,
                vector=embedding,
                payload={
                    "task": task,
                    "result": result,
                    "metadata": metadata or {},
                    "timestamp": time.time()
                }
            )

            # Store in Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )

            self.memory_id += 1
            logger.info(f"[MEMORY] ✅ Stored: {task[:50]}...")

        except Exception as e:
            logger.error(f"[MEMORY] ❌ Failed to add memory: {e}")

    def search_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for memories using semantic search.

        Args:
            query: Search query
            limit: Max number of results

        Returns:
            List of relevant memories with task, result, metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.model.encode(query).tolist()

            # Search in Qdrant
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=limit
            ).points

            # Format results
            memories = []
            for hit in results:
                memories.append({
                    "task": hit.payload["task"],
                    "result": hit.payload["result"],
                    "metadata": hit.payload.get("metadata", {}),
                    "score": hit.score,
                    "timestamp": hit.payload.get("timestamp")
                })

            logger.info(f"[MEMORY] 🔍 Found {len(memories)} memories for: {query[:50]}...")
            return memories

        except Exception as e:
            logger.error(f"[MEMORY] ❌ Search failed: {e}")
            return []

    def get_all_memories(self) -> List[Dict[str, Any]]:
        """Get all stored memories."""
        try:
            # Scroll through all points
            records, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000
            )

            return [
                {
                    "task": record.payload["task"],
                    "result": record.payload["result"],
                    "metadata": record.payload.get("metadata", {}),
                    "timestamp": record.payload.get("timestamp")
                }
                for record in records
            ]
        except Exception as e:
            logger.error(f"[MEMORY] ❌ Failed to get all memories: {e}")
            return []


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)

    memory = QdrantMemory()

    # Add test memories
    memory.add_memory(
        task="Calculate 2+2",
        result="4",
        metadata={"type": "math"}
    )

    memory.add_memory(
        task="Write Python function to validate email",
        result="def validate_email(email): ...",
        metadata={"type": "code"}
    )

    # Search
    results = memory.search_memories("math problem", limit=2)

    print("\n[SEARCH RESULTS]")
    for i, mem in enumerate(results, 1):
        print(f"{i}. {mem['task']} -> {mem['result'][:30]}... (score: {mem['score']:.2f})")

    print(f"\n[OK] Memory system working! Total memories: {len(memory.get_all_memories())}")
