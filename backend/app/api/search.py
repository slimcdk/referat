from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sentence_transformers import SentenceTransformer
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.meeting import Meeting
from app.models.meeting_chunk import MeetingChunk
from app.schemas.search import SearchRequest, SearchResult

router = APIRouter(prefix="/search", tags=["search"])

MODEL_NAME = "all-MiniLM-L6-v2"

@router.post("", response_model=List[SearchResult])
async def semantic_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not request.query.strip():
        return []

    try:
        # Load local SentenceTransformer and generate query embedding
        model = SentenceTransformer(MODEL_NAME)
        query_vector = model.encode(request.query).tolist()

        # Execute cosine similarity vector search in PostgreSQL using pgvector
        # SQLAlchemy pgvector syntax: MeetingChunk.embedding.cosine_distance(query_vector)
        # Cosine similarity is 1 - Cosine Distance
        distance_expr = MeetingChunk.embedding.cosine_distance(query_vector)
        similarity_expr = 1.0 - distance_expr

        stmt = (
            select(
                MeetingChunk,
                Meeting.title.label("meeting_title"),
                similarity_expr.label("similarity")
            )
            .join(Meeting, Meeting.id == MeetingChunk.meeting_id)
            .order_by(distance_expr.asc())
            .limit(request.limit)
        )

        result = await db.execute(stmt)
        search_results = []

        for row in result.all():
            chunk = row[0]
            meeting_title = row[1]
            similarity = row[2]

            # Only return matches with a reasonable similarity score (threshold f.g. 0.3)
            if similarity >= 0.25:
                search_results.append({
                    "meeting_id": chunk.meeting_id,
                    "meeting_title": meeting_title,
                    "start_time": chunk.start_time,
                    "end_time": chunk.end_time,
                    "text": chunk.text,
                    "similarity": float(similarity)
                })

        return search_results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search execution failed: {str(e)}"
        )
