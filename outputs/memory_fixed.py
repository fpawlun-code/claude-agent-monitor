Here is the corrected `qdrant_memory.py` file:
```python
import hashlib
from qdrant_client.models import Distance, VectorParams, PointStruct

class QdrantMemory:
    def __init__(self):
        self.client = None

    def create_collection(self):
        if not self.client:
            from qdrant_client import QdrantClient
            self.client = QdrantClient()
        self.client.create_collection(
            collection_name="tasks",
            vectors_config=VectorParams(size=128, distance=Distance.COSINE)
        )

    def store_point(self, task_id, task_data):
        if not self.client:
            raise Exception("Qdrant client not initialized")
        point = PointStruct(id=task_id, vector=self.get_vector(task_data), payload=task_data)
        self.client.upsert(collection_name="tasks", points=[point])

    def get_vector(self, task_data):
        # Simple text hash (consistent hashing) to 128-dim vector
        vector = [0.0] * 128
        for char in str(task_data).lower():
            hash_value = int(hashlib.md5(char.encode()).hexdigest(), 16)
            index = hash_value % 128
            vector[index] += 1.0 / 256.0
        return vector

    def search(self, query_task_id):
        if not self.client:
            raise Exception("Qdrant client not initialized")
        results = self.client.search(
            collection_name="tasks",
            query_vector=self.get_vector(query_task_id),
            limit=3
        )
        return results
```
Note that I've implemented the `get_vector` method to generate a 128-dim vector from the task data using simple text hashing. This is consistent with your request.

Also, I've added some error handling and initialization checks in the methods to ensure that the Qdrant client is properly initialized before performing operations.