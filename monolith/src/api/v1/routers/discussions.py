from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.common.database import get_db
from src.common.auth import get_current_user
from src.modules.discussion.services.discussion_service import DiscussionService
from src.modules.discussion.services.moderation_service import ModerationService

router = APIRouter(prefix="/discussions", tags=["Discussions"])

# Request/Response Models
class UserInfo(BaseModel):
    """User info model."""
    id: UUID
    name: str
    avatar_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class CommentBase(BaseModel):
    """Base comment model."""
    content: str = Field(..., min_length=1, max_length=5000)

class CommentCreateRequest(CommentBase):
    """Comment creation request model."""
    pass

class CommentUpdateRequest(CommentBase):
    """Comment update request model."""
    pass

class CommentResponse(CommentBase):
    """Comment response model."""
    id: UUID
    created_at: str
    updated_at: str
    author: UserInfo
    upvotes: int
    downvotes: int
    is_approved: bool
    user_vote: Optional[int] = None  # 1 for upvote, -1 for downvote, None for no vote
    
    class Config:
        from_attributes = True

class DiscussionBase(BaseModel):
    """Base discussion model."""
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=10, max_length=10000)
    tags: List[str] = Field(default_factory=list)

class DiscussionCreateRequest(DiscussionBase):
    """Discussion creation request model."""
    item_type: str = Field(..., description="Type of item: 'course', 'video', 'assessment', 'learning_path', 'general'")
    item_id: Optional[UUID] = None  # Optional for general discussions

class DiscussionUpdateRequest(BaseModel):
    """Discussion update request model."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    content: Optional[str] = Field(None, min_length=10, max_length=10000)
    tags: Optional[List[str]] = None

class DiscussionResponse(DiscussionBase):
    """Discussion response model."""
    id: UUID
    created_at: str
    updated_at: str
    author: UserInfo
    item_type: str
    item_id: Optional[UUID] = None
    upvotes: int
    downvotes: int
    comment_count: int
    is_pinned: bool
    is_approved: bool
    user_vote: Optional[int] = None  # 1 for upvote, -1 for downvote, None for no vote
    
    class Config:
        from_attributes = True

class VoteRequest(BaseModel):
    """Vote request model."""
    vote: int = Field(..., ge=-1, le=1)  # -1 for downvote, 0 for no vote, 1 for upvote

class ReportRequest(BaseModel):
    """Report request model."""
    reason: str = Field(..., min_length=10, max_length=1000)

# Routes
@router.post("", response_model=DiscussionResponse, status_code=status.HTTP_201_CREATED)
async def create_discussion(
    discussion_data: DiscussionCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new discussion.
    
    Creates a new discussion thread for a course, video, assessment, learning path, or general discussion.
    """
    discussion_service = DiscussionService(db)
    
    # Validate item_type and item_id combination
    valid_item_types = ["course", "video", "assessment", "learning_path", "general"]
    if discussion_data.item_type not in valid_item_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid item type. Must be one of: {', '.join(valid_item_types)}"
        )
    
    if discussion_data.item_type != "general" and discussion_data.item_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="item_id is required for non-general discussions"
        )
    
    # Apply content moderation
    moderation_service = ModerationService(db)
    is_content_allowed = await moderation_service.check_content(
        content=discussion_data.content,
        content_type="discussion"
    )
    
    if not is_content_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content violates community guidelines"
        )
    
    try:
        discussion = await discussion_service.create_discussion(
            title=discussion_data.title,
            content=discussion_data.content,
            tags=discussion_data.tags,
            item_type=discussion_data.item_type,
            item_id=discussion_data.item_id,
            author_id=UUID(current_user["sub"])
        )
        
        return DiscussionResponse(
            id=discussion.id,
            title=discussion.title,
            content=discussion.content,
            tags=discussion.tags,
            created_at=discussion.created_at.isoformat(),
            updated_at=discussion.updated_at.isoformat(),
            author=UserInfo(
                id=discussion.author.id,
                name=f"{discussion.author.first_name} {discussion.author.last_name}",
                avatar_url=discussion.author.avatar_url
            ),
            item_type=discussion.item_type,
            item_id=discussion.item_id,
            upvotes=discussion.upvotes,
            downvotes=discussion.downvotes,
            comment_count=discussion.comment_count,
            is_pinned=discussion.is_pinned,
            is_approved=discussion.is_approved,
            user_vote=discussion.user_vote
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=List[DiscussionResponse])
async def list_discussions(
    item_type: Optional[str] = Query(None, description="Filter by item type"),
    item_id: Optional[UUID] = Query(None, description="Filter by item ID"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search in title and content"),
    sort_by: str = Query("recent", description="Sort by: 'recent', 'popular', 'unanswered'"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List discussions.
    
    Returns a list of discussions, optionally filtered by various criteria.
    """
    discussion_service = DiscussionService(db)
    
    # Validate item_type
    if item_type is not None:
        valid_item_types = ["course", "video", "assessment", "learning_path", "general"]
        if item_type not in valid_item_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid item type. Must be one of: {', '.join(valid_item_types)}"
            )
    
    # Validate sort_by
    valid_sort_options = ["recent", "popular", "unanswered"]
    if sort_by not in valid_sort_options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort option. Must be one of: {', '.join(valid_sort_options)}"
        )
    
    # Get user ID if authenticated
    user_id = UUID(current_user["sub"]) if current_user else None
    
    discussions = await discussion_service.list_discussions(
        item_type=item_type,
        item_id=item_id,
        tag=tag,
        search=search,
        sort_by=sort_by,
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    return [
        DiscussionResponse(
            id=discussion.id,
            title=discussion.title,
            content=discussion.content,
            tags=discussion.tags,
            created_at=discussion.created_at.isoformat(),
            updated_at=discussion.updated_at.isoformat(),
            author=UserInfo(
                id=discussion.author.id,
                name=f"{discussion.author.first_name} {discussion.author.last_name}",
                avatar_url=discussion.author.avatar_url
            ),
            item_type=discussion.item_type,
            item_id=discussion.item_id,
            upvotes=discussion.upvotes,
            downvotes=discussion.downvotes,
            comment_count=discussion.comment_count,
            is_pinned=discussion.is_pinned,
            is_approved=discussion.is_approved,
            user_vote=discussion.user_vote
        ) for discussion in discussions
    ]

@router.get("/{discussion_id}", response_model=DiscussionResponse)
async def get_discussion(
    discussion_id: UUID = Path(..., description="The ID of the discussion to retrieve"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific discussion by ID.
    
    Returns the discussion data with its metadata.
    """
    discussion_service = DiscussionService(db)
    
    # Get user ID if authenticated
    user_id = UUID(current_user["sub"]) if current_user else None
    
    discussion = await discussion_service.get_discussion(
        discussion_id=discussion_id,
        user_id=user_id
    )
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    return DiscussionResponse(
        id=discussion.id,
        title=discussion.title,
        content=discussion.content,
        tags=discussion.tags,
        created_at=discussion.created_at.isoformat(),
        updated_at=discussion.updated_at.isoformat(),
        author=UserInfo(
            id=discussion.author.id,
            name=f"{discussion.author.first_name} {discussion.author.last_name}",
            avatar_url=discussion.author.avatar_url
        ),
        item_type=discussion.item_type,
        item_id=discussion.item_id,
        upvotes=discussion.upvotes,
        downvotes=discussion.downvotes,
        comment_count=discussion.comment_count,
        is_pinned=discussion.is_pinned,
        is_approved=discussion.is_approved,
        user_vote=discussion.user_vote
    )

@router.put("/{discussion_id}", response_model=DiscussionResponse)
async def update_discussion(
    discussion_data: DiscussionUpdateRequest,
    discussion_id: UUID = Path(..., description="The ID of the discussion to update"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a discussion.
    
    Updates the title, content, and/or tags of a discussion.
    """
    discussion_service = DiscussionService(db)
    
    # Check if user is the author or an admin
    discussion = await discussion_service.get_discussion(
        discussion_id=discussion_id,
        user_id=UUID(current_user["sub"])
    )
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    if str(discussion.author.id) != current_user["sub"] and not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this discussion"
        )
    
    # Apply content moderation if content is updated
    if discussion_data.content:
        moderation_service = ModerationService(db)
        is_content_allowed = await moderation_service.check_content(
            content=discussion_data.content,
            content_type="discussion"
        )
        
        if not is_content_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content violates community guidelines"
            )
    
    try:
        updated_discussion = await discussion_service.update_discussion(
            discussion_id=discussion_id,
            title=discussion_data.title,
            content=discussion_data.content,
            tags=discussion_data.tags,
            updated_by=UUID(current_user["sub"])
        )
        
        return DiscussionResponse(
            id=updated_discussion.id,
            title=updated_discussion.title,
            content=updated_discussion.content,
            tags=updated_discussion.tags,
            created_at=updated_discussion.created_at.isoformat(),
            updated_at=updated_discussion.updated_at.isoformat(),
            author=UserInfo(
                id=updated_discussion.author.id,
                name=f"{updated_discussion.author.first_name} {updated_discussion.author.last_name}",
                avatar_url=updated_discussion.author.avatar_url
            ),
            item_type=updated_discussion.item_type,
            item_id=updated_discussion.item_id,
            upvotes=updated_discussion.upvotes,
            downvotes=updated_discussion.downvotes,
            comment_count=updated_discussion.comment_count,
            is_pinned=updated_discussion.is_pinned,
            is_approved=updated_discussion.is_approved,
            user_vote=updated_discussion.user_vote
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{discussion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discussion(
    discussion_id: UUID = Path(..., description="The ID of the discussion to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a discussion.
    
    Removes a discussion and all its comments.
    """
    discussion_service = DiscussionService(db)
    
    # Check if user is the author or an admin
    discussion = await discussion_service.get_discussion(
        discussion_id=discussion_id,
        user_id=UUID(current_user["sub"])
    )
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    if str(discussion.author.id) != current_user["sub"] and not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this discussion"
        )
    
    success = await discussion_service.delete_discussion(
        discussion_id=discussion_id,
        deleted_by=UUID(current_user["sub"])
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    return None

@router.post("/{discussion_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment_data: CommentCreateRequest,
    discussion_id: UUID = Path(..., description="The ID of the discussion to comment on"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new comment.
    
    Adds a comment to a discussion.
    """
    discussion_service = DiscussionService(db)
    
    # Check if discussion exists
    discussion = await discussion_service.get_discussion(
        discussion_id=discussion_id,
        user_id=UUID(current_user["sub"])
    )
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    # Apply content moderation
    moderation_service = ModerationService(db)
    is_content_allowed = await moderation_service.check_content(
        content=comment_data.content,
        content_type="comment"
    )
    
    if not is_content_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content violates community guidelines"
        )
    
    try:
        comment = await discussion_service.create_comment(
            discussion_id=discussion_id,
            content=comment_data.content,
            author_id=UUID(current_user["sub"])
        )
        
        return CommentResponse(
            id=comment.id,
            content=comment.content,
            created_at=comment.created_at.isoformat(),
            updated_at=comment.updated_at.isoformat(),
            author=UserInfo(
                id=comment.author.id,
                name=f"{comment.author.first_name} {comment.author.last_name}",
                avatar_url=comment.author.avatar_url
            ),
            upvotes=comment.upvotes,
            downvotes=comment.downvotes,
            is_approved=comment.is_approved,
            user_vote=comment.user_vote
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{discussion_id}/comments", response_model=List[CommentResponse])
async def list_comments(
    discussion_id: UUID = Path(..., description="The ID of the discussion to get comments for"),
    sort_by: str = Query("recent", description="Sort by: 'recent', 'popular'"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List comments for a discussion.
    
    Returns comments for a specific discussion.
    """
    discussion_service = DiscussionService(db)
    
    # Check if discussion exists
    discussion = await discussion_service.get_discussion(
        discussion_id=discussion_id,
        user_id=UUID(current_user["sub"]) if current_user else None
    )
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    # Validate sort_by
    valid_sort_options = ["recent", "popular"]
    if sort_by not in valid_sort_options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort option. Must be one of: {', '.join(valid_sort_options)}"
        )
    
    # Get user ID if authenticated
    user_id = UUID(current_user["sub"]) if current_user else None
    
    comments = await discussion_service.list_comments(
        discussion_id=discussion_id,
        sort_by=sort_by,
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    return [
        CommentResponse(
            id=comment.id,
            content=comment.content,
            created_at=comment.created_at.isoformat(),
            updated_at=comment.updated_at.isoformat(),
            author=UserInfo(
                id=comment.author.id,
                name=f"{comment.author.first_name} {comment.author.last_name}",
                avatar_url=comment.author.avatar_url
            ),
            upvotes=comment.upvotes,
            downvotes=comment.downvotes,
            is_approved=comment.is_approved,
            user_vote=comment.user_vote
        ) for comment in comments
    ]

@router.put("/{discussion_id}/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_data: CommentUpdateRequest,
    discussion_id: UUID = Path(..., description="The ID of the discussion"),
    comment_id: UUID = Path(..., description="The ID of the comment to update"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a comment.
    
    Updates the content of a comment.
    """
    discussion_service = DiscussionService(db)
    
    # Check if comment exists and user is the author
    comment = await discussion_service.get_comment(
        comment_id=comment_id,
        user_id=UUID(current_user["sub"])
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    if str(comment.author.id) != current_user["sub"] and not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this comment"
        )
    
    # Apply content moderation
    moderation_service = ModerationService(db)
    is_content_allowed = await moderation_service.check_content(
        content=comment_data.content,
        content_type="comment"
    )
    
    if not is_content_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content violates community guidelines"
        )
    
    try:
        updated_comment = await discussion_service.update_comment(
            comment_id=comment_id,
            content=comment_data.content,
            updated_by=UUID(current_user["sub"])
        )
        
        return CommentResponse(
            id=updated_comment.id,
            content=updated_comment.content,
            created_at=updated_comment.created_at.isoformat(),
            updated_at=updated_comment.updated_at.isoformat(),
            author=UserInfo(
                id=updated_comment.author.id,
                name=f"{updated_comment.author.first_name} {updated_comment.author.last_name}",
                avatar_url=updated_comment.author.avatar_url
            ),
            upvotes=updated_comment.upvotes,
            downvotes=updated_comment.downvotes,
            is_approved=updated_comment.is_approved,
            user_vote=updated_comment.user_vote
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{discussion_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    discussion_id: UUID = Path(..., description="The ID of the discussion"),
    comment_id: UUID = Path(..., description="The ID of the comment to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a comment.
    
    Removes a comment from a discussion.
    """
    discussion_service = DiscussionService(db)
    
    # Check if comment exists and user is the author
    comment = await discussion_service.get_comment(
        comment_id=comment_id,
        user_id=UUID(current_user["sub"])
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    if str(comment.author.id) != current_user["sub"] and not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this comment"
        )
    
    success = await discussion_service.delete_comment(
        comment_id=comment_id,
        deleted_by=UUID(current_user["sub"])
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    return None

@router.post("/{discussion_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def vote_discussion(
    vote_data: VoteRequest,
    discussion_id: UUID = Path(..., description="The ID of the discussion to vote on"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Vote on a discussion.
    
    Adds an upvote, downvote, or removes a vote from a discussion.
    """
    discussion_service = DiscussionService(db)
    
    try:
        await discussion_service.vote_discussion(
            discussion_id=discussion_id,
            user_id=UUID(current_user["sub"]),
            vote=vote_data.vote
        )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{discussion_id}/comments/{comment_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def vote_comment(
    vote_data: VoteRequest,
    discussion_id: UUID = Path(..., description="The ID of the discussion"),
    comment_id: UUID = Path(..., description="The ID of the comment to vote on"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Vote on a comment.
    
    Adds an upvote, downvote, or removes a vote from a comment.
    """
    discussion_service = DiscussionService(db)
    
    try:
        await discussion_service.vote_comment(
            comment_id=comment_id,
            user_id=UUID(current_user["sub"]),
            vote=vote_data.vote
        )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{discussion_id}/report", status_code=status.HTTP_204_NO_CONTENT)
async def report_discussion(
    report_data: ReportRequest,
    discussion_id: UUID = Path(..., description="The ID of the discussion to report"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Report a discussion.
    
    Reports a discussion for violating community guidelines.
    """
    moderation_service = ModerationService(db)
    
    try:
        await moderation_service.report_content(
            content_type="discussion",
            content_id=discussion_id,
            reason=report_data.reason,
            reported_by=UUID(current_user["sub"])
        )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{discussion_id}/comments/{comment_id}/report", status_code=status.HTTP_204_NO_CONTENT)
async def report_comment(
    report_data: ReportRequest,
    discussion_id: UUID = Path(..., description="The ID of the discussion"),
    comment_id: UUID = Path(..., description="The ID of the comment to report"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Report a comment.
    
    Reports a comment for violating community guidelines.
    """
    moderation_service = ModerationService(db)
    
    try:
        await moderation_service.report_content(
            content_type="comment",
            content_id=comment_id,
            reason=report_data.reason,
            reported_by=UUID(current_user["sub"])
        )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
