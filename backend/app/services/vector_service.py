"""
Vector search for semantic memory lookup and YouTube content matching.
Uses Pinecone as the vector database with OpenAI embeddings.
"""
from typing import Optional
from openai import AsyncOpenAI
from app.config import settings

_pinecone_index = None


def _get_index():
    global _pinecone_index
    if _pinecone_index is None and settings.PINECONE_API_KEY:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
    return _pinecone_index


class VectorService:
    def __init__(self):
        self.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def embed_text(self, text: str) -> list[float]:
        response = await self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000],
        )
        return response.data[0].embedding

    async def upsert_memory(self, memory_id: str, content: str, user_id: str, memory_type: str):
        index = _get_index()
        if not index:
            return
        embedding = await self.embed_text(content)
        index.upsert(vectors=[{
            "id": memory_id,
            "values": embedding,
            "metadata": {
                "user_id": user_id,
                "memory_type": memory_type,
                "content": content[:500],
            },
        }])

    async def search_memories(self, query: str, user_id: str, top_k: int = 5) -> list[dict]:
        index = _get_index()
        if not index:
            return []
        embedding = await self.embed_text(query)
        results = index.query(
            vector=embedding,
            top_k=top_k,
            filter={"user_id": user_id},
            include_metadata=True,
        )
        return [
            {"score": match.score, "content": match.metadata.get("content", "")}
            for match in results.matches
            if match.score > 0.7
        ]

    async def upsert_youtube_video(self, video_id: str, title: str, transcript: str, topics: list[str]):
        index = _get_index()
        if not index:
            return
        text = f"{title}\n\n{transcript[:4000]}"
        embedding = await self.embed_text(text)
        index.upsert(vectors=[{
            "id": f"yt_{video_id}",
            "values": embedding,
            "metadata": {
                "type": "youtube",
                "video_id": video_id,
                "title": title,
                "topics": ",".join(topics),
            },
        }])

    async def find_relevant_videos(self, query: str, top_k: int = 3) -> list[dict]:
        index = _get_index()
        if not index:
            return []
        embedding = await self.embed_text(query)
        results = index.query(
            vector=embedding,
            top_k=top_k,
            filter={"type": "youtube"},
            include_metadata=True,
        )
        return [
            {
                "score": match.score,
                "title": match.metadata.get("title", ""),
                "video_id": match.metadata.get("video_id", ""),
            }
            for match in results.matches
            if match.score > 0.75
        ]


vector_service = VectorService()
