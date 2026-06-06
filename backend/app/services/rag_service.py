from google import genai
from pinecone import Pinecone
from app.config import settings

class RAGService:
    def __init__(self):
        # Initialize Google GenAI and Pinecone via our clean configuration layer
        self.ai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index = self.pc.Index(settings.PINECONE_INDEX_NAME)

    def _get_query_embedding(self, query: str) -> list[float]:
        """Vectorizes user query matching the 3072-dimension space."""
        try:
            response = self.ai_client.models.embed_content(
                model="gemini-embedding-001",
                contents=query
            )
            return response.embeddings[0].values
        except Exception as e:
            print(f"RAG embedding generation error: {e}")
            return []

    def retrieve_context(self, query: str, top_k: int = 3) -> str:
        """Queries Pinecone index and returns a unified context block."""
        if not query.strip():
            return ""
            
        embedding = self._get_query_embedding(query)
        if not embedding:
            return ""

        try:
            results = self.index.query(
                vector=embedding, 
                top_k=top_k, 
                include_metadata=True
            )
            
            context_chunks = []
            for match in results.get("matches", []):
                if "metadata" in match and "page_content" in match["metadata"]:
                    context_chunks.append(match["metadata"]["page_content"])
                    
            return "\n\n---\n\n".join(context_chunks)
        except Exception as e:
            print(f"Pinecone retrieval query error: {e}")
            return ""

# Export a single reusable instance
rag_service = RAGService()