import os
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from qdrant_client.http.models import Distance, VectorParams, PointStruct

class SemanticCache:
    def __init__(self):
        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", "6333"))
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = "semantic_cache"
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        if not self.client.collection_exists(collection_name=self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )

    def get(self, query: str, threshold: float = 0.95):
        vector = self.embeddings.embed_query(query)
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=1
        )
        if results.points and results.points[0].score >= threshold:
            return results.points[0].payload
        return None

    def set(self, query: str, result: dict):
        vector = self.embeddings.embed_query(query)
        point_id = hash(query) % ((1<<63)-1) # simplistic hashing for ID
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=abs(point_id),
                    vector=vector,
                    payload={"query": query, "result": result}
                )
            ]
        )
