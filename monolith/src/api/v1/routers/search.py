from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.common.database import get_db
from src.common.auth import get_current_user
from src.modules.search.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])

# Request/Response Models
class SearchResultItem(BaseModel):
    """Search result item model."""
    id: UUID
    type: str
    title: str
    description: str
    thumbnail_url: Optional[str] = None
    metadata: Dict[str, Any] = {}
    relevance_score: float
    
    class Config:
        from_attributes = True

class SearchResponse(BaseModel):
    """Search response model."""
    query: str
    total_results: int
    results: List[SearchResultItem]
    filters_applied: Dict[str, Any]
    
class SearchSuggestion(BaseModel):
    """Search suggestion model."""
    text: str
    score: float

class SearchSuggestionResponse(BaseModel):
    """Search suggestion response model."""
    query: str
    suggestions: List[SearchSuggestion]

class PopularSearchesResponse(BaseModel):
    """Popular searches response model."""
    searches: List[Dict[str, Any]]

# Routes
@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    types: Optional[str] = Query(None, description="Comma-separated list of content types to include"),
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags to filter by"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search content.
    
    Performs a full-text search across courses, videos, assessments,
    learning paths, and other content types.
    """
    search_service = SearchService(db)
    
    # Parse filter parameters
    filter_types = types.split(",") if types else None
    filter_tags = tags.split(",") if tags else None
    
    # Build filters dictionary
    filters = {
        "types": filter_types,
        "category": category,
        "difficulty": difficulty,
        "tags": filter_tags
    }
    
    # If user is authenticated, include user ID for personalized results
    user_id = UUID(current_user["sub"]) if current_user else None
    
    search_results = await search_service.search(
        query=q,
        filters=filters,
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    # Log search query if authenticated user
    if user_id:
        await search_service.log_search_query(
            user_id=user_id,
            query=q,
            filters=filters,
            results_count=search_results["total_results"]
        )
    
    return SearchResponse(
        query=q,
        total_results=search_results["total_results"],
        results=[
            SearchResultItem(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                description=item["description"],
                thumbnail_url=item.get("thumbnail_url"),
                metadata=item.get("metadata", {}),
                relevance_score=item["relevance_score"]
            ) for item in search_results["results"]
        ],
        filters_applied=filters
    )

@router.get("/autocomplete", response_model=SearchSuggestionResponse)
async def autocomplete(
    q: str = Query(..., description="Partial search query"),
    limit: int = Query(5, ge=1, le=10),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get autocomplete suggestions.
    
    Returns search term suggestions based on a partial query.
    """
    search_service = SearchService(db)
    
    # If user is authenticated, include user ID for personalized suggestions
    user_id = UUID(current_user["sub"]) if current_user else None
    
    suggestions = await search_service.get_autocomplete_suggestions(
        query=q,
        user_id=user_id,
        limit=limit
    )
    
    return SearchSuggestionResponse(
        query=q,
        suggestions=[
            SearchSuggestion(
                text=suggestion["text"],
                score=suggestion["score"]
            ) for suggestion in suggestions
        ]
    )

@router.get("/popular", response_model=PopularSearchesResponse)
async def popular_searches(
    limit: int = Query(10, ge=1, le=20),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get popular searches.
    
    Returns the most popular search queries across all users.
    """
    search_service = SearchService(db)
    
    popular = await search_service.get_popular_searches(limit=limit)
    
    return PopularSearchesResponse(
        searches=popular
    )

@router.get("/related/{content_type}/{content_id}", response_model=List[SearchResultItem])
async def related_content(
    content_type: str = Path(..., description="Content type: 'course', 'video', 'assessment', 'learning_path'"),
    content_id: UUID = Path(..., description="Content ID"),
    limit: int = Query(5, ge=1, le=20),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get related content.
    
    Returns content related to the specified item.
    """
    search_service = SearchService(db)
    
    valid_types = ["course", "video", "assessment", "learning_path"]
    if content_type not in valid_types:
        return []
    
    # If user is authenticated, include user ID for personalized recommendations
    user_id = UUID(current_user["sub"]) if current_user else None
    
    related = await search_service.get_related_content(
        content_type=content_type,
        content_id=content_id,
        user_id=user_id,
        limit=limit
    )
    
    return [
        SearchResultItem(
            id=item["id"],
            type=item["type"],
            title=item["title"],
            description=item["description"],
            thumbnail_url=item.get("thumbnail_url"),
            metadata=item.get("metadata", {}),
            relevance_score=item["relevance_score"]
        ) for item in related
    ]
