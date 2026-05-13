import os
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from qdrant_client.http.models import PointStruct, VectorParams, Distance

class ExamplesRetriever:
    def __init__(self):
        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", "6333"))
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = "few_shot_examples"
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # Ensure collection exists
        if not self.client.collection_exists(collection_name=self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        vector = self.embeddings.embed_query(query)
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=top_k
        )
        return [hit.payload for hit in results.points]

    def add_example(self, question: str, sql: str):
        vector = self.embeddings.embed_query(question)
        # Use a simple hash of the question as the point ID
        point_id = hash(question) % ((1 << 63) - 1)
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=abs(point_id),
                    vector=vector,
                    payload={"question": question, "sql": sql}
                )
            ]
        )

    def get_all_examples(self, limit: int = 100) -> list[dict]:
        results = self.client.scroll(
            collection_name=self.collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        return [record.payload for record in results[0]]
