from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.common.database import get_db
from src.common.auth import get_current_user
from src.modules.learning_path.services.learning_path_service import LearningPathService
from src.modules.learning_path.services.enrollment_service import EnrollmentService

router = APIRouter(prefix="/learning-paths", tags=["Learning Paths"])

# Request/Response Models
class PathItemBase(BaseModel):
    """Base learning path item model."""
    order: int
    item_type: str = Field(..., description="Type of item: 'course', 'assessment', 'content'")
    item_id: UUID
    required: bool = True
    
class PathItemCreateRequest(PathItemBase):
    """Learning path item creation request model."""
    pass

class PathItemResponse(PathItemBase):
    """Learning path item response model."""
    id: UUID
    title: str
    description: str
    
    class Config:
        from_attributes = True

class LearningPathBase(BaseModel):
    """Base learning path model."""
    title: str
    description: str
    difficulty_level: str = Field(..., description="Difficulty level: 'beginner', 'intermediate', 'advanced'")
    estimated_hours: Optional[int] = None
    is_featured: bool = False
    category: Optional[str] = None
    is_published: bool = False

class LearningPathCreateRequest(LearningPathBase):
    """Learning path creation request model."""
    items: Optional[List[PathItemCreateRequest]] = None

class LearningPathUpdateRequest(BaseModel):
    """Learning path update request model."""
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty_level: Optional[str] = None
    estimated_hours: Optional[int] = None
    is_featured: Optional[bool] = None
    category: Optional[str] = None
    is_published: Optional[bool] = None
    items: Optional[List[PathItemCreateRequest]] = None

class LearningPathResponse(LearningPathBase):
    """Learning path response model."""
    id: UUID
    created_at: str
    updated_at: str
    total_items: int
    items: List[PathItemResponse]
    
    class Config:
        from_attributes = True

class EnrollmentRequest(BaseModel):
    """Learning path enrollment request model."""
    learning_path_id: UUID

class EnrollmentResponse(BaseModel):
    """Learning path enrollment response model."""
    id: UUID
    learning_path_id: UUID
    user_id: UUID
    enrolled_at: str
    status: str
    completion_percentage: int
    
    class Config:
        from_attributes = True

class ProgressUpdateRequest(BaseModel):
    """Learning path progress update request model."""
    item_id: UUID
    completed: bool

# Routes
@router.post("", response_model=LearningPathResponse, status_code=status.HTTP_201_CREATED)
async def create_learning_path(
    path_data: LearningPathCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new learning path.
    
    Creates a new learning path with optional items.
    """
    learning_path_service = LearningPathService(db)
    
    try:
        learning_path = await learning_path_service.create_learning_path(
            title=path_data.title,
            description=path_data.description,
            difficulty_level=path_data.difficulty_level,
            estimated_hours=path_data.estimated_hours,
            is_featured=path_data.is_featured,
            category=path_data.category,
            is_published=path_data.is_published,
            items=path_data.items,
            created_by=UUID(current_user["sub"])
        )
        
        items_response = [
            PathItemResponse(
                id=item.id,
                order=item.order,
                item_type=item.item_type,
                item_id=item.item_id,
                required=item.required,
                title=item.title,
                description=item.description
            ) for item in learning_path.items
        ]
        
        return LearningPathResponse(
            id=learning_path.id,
            title=learning_path.title,
            description=learning_path.description,
            difficulty_level=learning_path.difficulty_level,
            estimated_hours=learning_path.estimated_hours,
            is_featured=learning_path.is_featured,
            category=learning_path.category,
            is_published=learning_path.is_published,
            created_at=learning_path.created_at.isoformat(),
            updated_at=learning_path.updated_at.isoformat(),
            total_items=len(learning_path.items),
            items=items_response
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=List[LearningPathResponse])
async def list_learning_paths(
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty_level: Optional[str] = Query(None, description="Filter by difficulty level"),
    featured_only: bool = Query(False, description="Filter by featured status"),
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List learning paths.
    
    Returns a list of learning paths, optionally filtered by various criteria.
    """
    learning_path_service = LearningPathService(db)
    
    # Non-admins can only see published paths
    is_admin = False
    if current_user and "is_admin" in current_user and current_user["is_admin"]:
        is_admin = True
        
    learning_paths = await learning_path_service.list_learning_paths(
        category=category,
        difficulty_level=difficulty_level,
        featured_only=featured_only,
        published_only=not is_admin,
        limit=limit,
        offset=offset
    )
    
    result = []
    for path in learning_paths:
        items_response = [
            PathItemResponse(
                id=item.id,
                order=item.order,
                item_type=item.item_type,
                item_id=item.item_id,
                required=item.required,
                title=item.title,
                description=item.description
            ) for item in path.items
        ]
        
        result.append(LearningPathResponse(
            id=path.id,
            title=path.title,
            description=path.description,
            difficulty_level=path.difficulty_level,
            estimated_hours=path.estimated_hours,
            is_featured=path.is_featured,
            category=path.category,
            is_published=path.is_published,
            created_at=path.created_at.isoformat(),
            updated_at=path.updated_at.isoformat(),
            total_items=len(path.items),
            items=items_response
        ))
    
    return result

@router.get("/{path_id}", response_model=LearningPathResponse)
async def get_learning_path(
    path_id: UUID = Path(..., description="The ID of the learning path to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific learning path by ID.
    
    Returns the learning path data with its items.
    """
    learning_path_service = LearningPathService(db)
    learning_path = await learning_path_service.get_learning_path(path_id)
    
    if not learning_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning path not found"
        )
    
    # Non-admins can only see published paths
    is_admin = False
    if "is_admin" in current_user and current_user["is_admin"]:
        is_admin = True
        
    if not is_admin and not learning_path.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning path not found"
        )
    
    items_response = [
        PathItemResponse(
            id=item.id,
            order=item.order,
            item_type=item.item_type,
            item_id=item.item_id,
            required=item.required,
            title=item.title,
            description=item.description
        ) for item in learning_path.items
    ]
    
    return LearningPathResponse(
        id=learning_path.id,
        title=learning_path.title,
        description=learning_path.description,
        difficulty_level=learning_path.difficulty_level,
        estimated_hours=learning_path.estimated_hours,
        is_featured=learning_path.is_featured,
        category=learning_path.category,
        is_published=learning_path.is_published,
        created_at=learning_path.created_at.isoformat(),
        updated_at=learning_path.updated_at.isoformat(),
        total_items=len(learning_path.items),
        items=items_response
    )

@router.put("/{path_id}", response_model=LearningPathResponse)
async def update_learning_path(
    path_data: LearningPathUpdateRequest,
    path_id: UUID = Path(..., description="The ID of the learning path to update"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a learning path.
    
    Updates an existing learning path with new data.
    """
    # Check if user is an admin
    is_admin = False
    if "is_admin" in current_user and current_user["is_admin"]:
        is_admin = True
        
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update learning paths"
        )
    
    learning_path_service = LearningPathService(db)
    
    try:
        learning_path = await learning_path_service.update_learning_path(
            path_id=path_id,
            title=path_data.title,
            description=path_data.description,
            difficulty_level=path_data.difficulty_level,
            estimated_hours=path_data.estimated_hours,
            is_featured=path_data.is_featured,
            category=path_data.category,
            is_published=path_data.is_published,
            items=path_data.items,
            updated_by=UUID(current_user["sub"])
        )
        
        if not learning_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning path not found"
            )
        
        items_response = [
            PathItemResponse(
                id=item.id,
                order=item.order,
                item_type=item.item_type,
                item_id=item.item_id,
                required=item.required,
                title=item.title,
                description=item.description
            ) for item in learning_path.items
        ]
        
        return LearningPathResponse(
            id=learning_path.id,
            title=learning_path.title,
            description=learning_path.description,
            difficulty_level=learning_path.difficulty_level,
            estimated_hours=learning_path.estimated_hours,
            is_featured=learning_path.is_featured,
            category=learning_path.category,
            is_published=learning_path.is_published,
            created_at=learning_path.created_at.isoformat(),
            updated_at=learning_path.updated_at.isoformat(),
            total_items=len(learning_path.items),
            items=items_response
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{path_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_learning_path(
    path_id: UUID = Path(..., description="The ID of the learning path to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a learning path.
    
    Removes a learning path and its associated items.
    """
    # Check if user is an admin
    is_admin = False
    if "is_admin" in current_user and current_user["is_admin"]:
        is_admin = True
        
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete learning paths"
        )
    
    learning_path_service = LearningPathService(db)
    success = await learning_path_service.delete_learning_path(
        path_id=path_id,
        deleted_by=UUID(current_user["sub"])
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning path not found"
        )
    
    return None

@router.post("/enroll", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_in_learning_path(
    enrollment_data: EnrollmentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enroll in a learning path.
    
    Enrolls the current user in a learning path.
    """
    enrollment_service = EnrollmentService(db)
    learning_path_service = LearningPathService(db)
    
    # Check if learning path exists and is published
    learning_path = await learning_path_service.get_learning_path(enrollment_data.learning_path_id)
    if not learning_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning path not found"
        )
    
    if not learning_path.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enroll in unpublished learning path"
        )
    
    try:
        enrollment = await enrollment_service.enroll_user(
            user_id=UUID(current_user["sub"]),
            learning_path_id=enrollment_data.learning_path_id
        )
        
        return EnrollmentResponse(
            id=enrollment.id,
            learning_path_id=enrollment.learning_path_id,
            user_id=enrollment.user_id,
            enrolled_at=enrollment.enrolled_at.isoformat(),
            status=enrollment.status,
            completion_percentage=enrollment.completion_percentage
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/enrollments", response_model=List[EnrollmentResponse])
async def list_user_enrollments(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List user enrollments.
    
    Returns a list of learning paths that the current user is enrolled in.
    """
    enrollment_service = EnrollmentService(db)
    enrollments = await enrollment_service.list_user_enrollments(
        user_id=UUID(current_user["sub"])
    )
    
    return [
        EnrollmentResponse(
            id=enrollment.id,
            learning_path_id=enrollment.learning_path_id,
            user_id=enrollment.user_id,
            enrolled_at=enrollment.enrolled_at.isoformat(),
            status=enrollment.status,
            completion_percentage=enrollment.completion_percentage
        ) for enrollment in enrollments
    ]

@router.put("/progress", status_code=status.HTTP_204_NO_CONTENT)
async def update_learning_path_progress(
    progress_data: ProgressUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update learning path progress.
    
    Updates the current user's progress on a learning path item.
    """
    enrollment_service = EnrollmentService(db)
    
    try:
        await enrollment_service.update_progress(
            user_id=UUID(current_user["sub"]),
            item_id=progress_data.item_id,
            completed=progress_data.completed
        )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
