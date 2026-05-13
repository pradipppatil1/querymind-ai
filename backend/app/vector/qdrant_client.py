import os
from qdrant_client import QdrantClient as BaseQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# Set HF Token for the environment to clean up warnings
hf_token = os.getenv("HF_TOKEN")
if hf_token:
    os.environ["HUGGINGFACEHUB_API_TOKEN"] = hf_token
    os.environ["HF_TOKEN"] = hf_token

class QdrantManager:
    def __init__(self):
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", 6333))
        self.client = BaseQdrantClient(host=self.host, port=self.port)
        self.encoder = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))

    def ensure_collection(self, collection_name, vector_size=384):
        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def upsert_points(self, collection_name, data_list, text_key="summary"):
        points = []
        for idx, item in enumerate(data_list):
            vector = self.encoder.encode(item[text_key]).tolist()
            points.append(PointStruct(
                id=idx,
                vector=vector,
                payload=item
            ))
        self.client.upsert(collection_name=collection_name, points=points)

    def search(self, collection_name, query, k=3):
        try:
            if not self.client.collection_exists(collection_name):
                return []
            vector = self.encoder.encode(query).tolist()
            results = self.client.query_points(
                collection_name=collection_name,
                query=vector,
                limit=k
            ).points
            return [hit.payload for hit in results]
        except Exception as e:
            print(f"Vector search error: {e}")
            return []
