from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.common.database import get_db
from src.common.auth import get_current_user
from src.modules.recommendation.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

# Request/Response Models
class RecommendedItem(BaseModel):
    """Recommended item model."""
    id: UUID
    type: str
    title: str
    description: str
    thumbnail_url: Optional[str] = None
    metadata: Dict[str, Any] = {}
    relevance_score: float
    reason: str
    
    class Config:
        from_attributes = True

class RecommendationResponse(BaseModel):
    """Recommendation response model."""
    recommendations: List[RecommendedItem]
    category: str
    total: int
    
class AllRecommendationsResponse(BaseModel):
    """All recommendations response model."""
    personalized: List[RecommendedItem]
    trending: List[RecommendedItem]
    popular: List[RecommendedItem]
    new: List[RecommendedItem]
    continue_learning: List[RecommendedItem]

# Routes
@router.get("", response_model=AllRecommendationsResponse)
async def get_all_recommendations(
    limit_per_category: int = Query(5, ge=1, le=20),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all recommendations.
    
    Returns a set of recommendations across different categories.
    """
    recommendation_service = RecommendationService(db)
    
    recommendations = await recommendation_service.get_all_recommendations(
        user_id=UUID(current_user["sub"]),
        limit_per_category=limit_per_category
    )
    
    return AllRecommendationsResponse(
        personalized=[
            RecommendedItem(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                description=item["description"],
                thumbnail_url=item.get("thumbnail_url"),
                metadata=item.get("metadata", {}),
                relevance_score=item["relevance_score"],
                reason=item.get("reason", "Personalized for you")
            ) for item in recommendations["personalized"]
        ],
        trending=[
            RecommendedItem(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                description=item["description"],
                thumbnail_url=item.get("thumbnail_url"),
                metadata=item.get("metadata", {}),
                relevance_score=item["relevance_score"],
                reason=item.get("reason", "Trending")
            ) for item in recommendations["trending"]
        ],
        popular=[
            RecommendedItem(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                description=item["description"],
                thumbnail_url=item.get("thumbnail_url"),
                metadata=item.get("metadata", {}),
                relevance_score=item["relevance_score"],
                reason=item.get("reason", "Popular")
            ) for item in recommendations["popular"]
        ],
        new=[
            RecommendedItem(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                description=item["description"],
                thumbnail_url=item.get("thumbnail_url"),
                metadata=item.get("metadata", {}),
                relevance_score=item["relevance_score"],
                reason=item.get("reason", "New")
            ) for item in recommendations["new"]
        ],
        continue_learning=[
            RecommendedItem(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                description=item["description"],
                thumbnail_url=item.get("thumbnail_url"),
                metadata=item.get("metadata", {}),
                relevance_score=item["relevance_score"],
                reason=item.get("reason", "Continue learning")
            ) for item in recommendations["continue_learning"]
        ]
    )

@router.get("/personalized", response_model=RecommendationResponse)
async def get_personalized_recommendations(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized recommendations.
    
    Returns content recommendations tailored to the user based on their
    activity, preferences, and learning history.
    """
    recommendation_service = RecommendationService(db)
    
    recommendations = await recommendation_service.get_personalized_recommendations(
        user_id=UUID(current_user["sub"]),
        limit=limit,
        offset=offset
    )
    
    return RecommendationResponse(
        recommendations=[
            RecommendedItem(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                description=item["description"],
                thumbnail_url=item.get("thumbnail_url"),
                metadata=item.get("metadata", {}),
                relevance_score=item["relevance_score"],
                reason=item.get("reason", "Personalized for you")
            ) for item in recommendations["items"]
        ],
        category="personalized",
        total=recommendations["total"]
    )

@router.get("/trending", response_model=RecommendationResponse)
async def get_trending_content(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get trending content.
    
    Returns content that is currently popular or trending on the platform.
    """
    recommendation_service = RecommendationService(db)
    
    trending = await recommendation_service.get_trending_content(
        user_id=UUID(current_user["sub"]),
        limit=limit,
        offset=offset
    )
    
    return RecommendationResponse(
        recommendations=[
            RecommendedItem(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                description=item["description"],
                thumbnail_url=item.get("thumbnail_url"),
                metadata=item.get("metadata", {}),
                relevance_score=item["relevance_score"],
                reason=item.get("reason", "Trending")
            ) for item in trending["items"]
        ],
        category="trending",
        total=trending["total"]
    )

@router.get("/similar-users", response_model=RecommendationResponse)
async def get_similar_users_recommendations(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recommendations based on similar users.
    
    Returns content recommendations based on what similar users have engaged with.
    """
    recommendation_service = RecommendationService(db)
    
    recommendations = await recommendation_service.get_similar_users_recommendations(
        user_id=UUID(current_user["sub"]),
        limit=limit,
        offset=offset
    )
    
    return RecommendationResponse(
        recommendations=[
            RecommendedItem(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                description=item["description"],
                thumbnail_url=item.get("thumbnail_url"),
                metadata=item.get("metadata", {}),
                relevance_score=item["relevance_score"],
                reason=item.get("reason", "Users like you enjoyed this")
            ) for item in recommendations["items"]
        ],
        category="similar_users",
        total=recommendations["total"]
    )

@router.get("/continue-learning", response_model=RecommendationResponse)
async def get_continue_learning_recommendations(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recommendations for content to continue learning.
    
    Returns content that the user has started but not completed.
    """
    recommendation_service = RecommendationService(db)
    
    recommendations = await recommendation_service.get_continue_learning_recommendations(
        user_id=UUID(current_user["sub"]),
        limit=limit,
        offset=offset
    )
    
    return RecommendationResponse(
        recommendations=[
            RecommendedItem(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                description=item["description"],
                thumbnail_url=item.get("thumbnail_url"),
                metadata=item.get("metadata", {}),
                relevance_score=item["relevance_score"],
                reason=item.get("reason", "Continue learning")
            ) for item in recommendations["items"]
        ],
        category="continue_learning",
        total=recommendations["total"]
    )

@router.get("/new", response_model=RecommendationResponse)
async def get_new_content(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    days: int = Query(30, ge=1, le=90),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get new content recommendations.
    
    Returns content that has been recently added to the platform.
    """
    recommendation_service = RecommendationService(db)
    
    new_content = await recommendation_service.get_new_content(
        user_id=UUID(current_user["sub"]),
        days=days,
        limit=limit,
        offset=offset
    )
    
    return RecommendationResponse(
        recommendations=[
            RecommendedItem(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                description=item["description"],
                thumbnail_url=item.get("thumbnail_url"),
                metadata=item.get("metadata", {}),
                relevance_score=item["relevance_score"],
                reason=item.get("reason", f"Added in the last {days} days")
            ) for item in new_content["items"]
        ],
        category="new",
        total=new_content["total"]
    )
