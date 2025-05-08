from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl, Field

from src.common.database import get_db
from src.common.auth import get_current_user
from src.modules.video.services.video_service import VideoService
from src.modules.video.services.video_upload_service import VideoUploadService
from src.modules.video.services.video_streaming_service import VideoStreamingService

router = APIRouter(prefix="/videos", tags=["Videos"])

# Request/Response Models
class VideoBase(BaseModel):
    """Base video model."""
    title: str
    description: str
    duration_seconds: int
    thumbnail_url: Optional[HttpUrl] = None
    course_id: UUID

class VideoCreateRequest(VideoBase):
    """Video creation request model."""
    pass

class VideoUpdateRequest(BaseModel):
    """Video update request model."""
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[HttpUrl] = None

class VideoResponse(VideoBase):
    """Video response model."""
    id: UUID
    status: str
    created_at: str
    updated_at: str
    streaming_url: Optional[HttpUrl] = None
    
    class Config:
        from_attributes = True

class VideoPlaybackInfo(BaseModel):
    """Video playback information."""
    streaming_url: HttpUrl
    format: str
    quality_options: List[str]
    subtitle_tracks: List[Dict[str, Any]] = []
    last_position: Optional[int] = None  # Last position for user in seconds

# Routes
@router.post("", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def create_video(
    video_data: VideoCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new video.
    
    Creates metadata for a new video, which can later be populated with content
    via the upload endpoint.
    """
    video_service = VideoService(db)
    
    try:
        video = await video_service.create_video(
            title=video_data.title,
            description=video_data.description,
            duration_seconds=video_data.duration_seconds,
            thumbnail_url=video_data.thumbnail_url,
            course_id=video_data.course_id,
            created_by=UUID(current_user["sub"])
        )
        
        return VideoResponse(
            id=video.id,
            title=video.title,
            description=video.description,
            duration_seconds=video.duration_seconds,
            thumbnail_url=video.thumbnail_url,
            course_id=video.course_id,
            status=video.status,
            streaming_url=video.streaming_url,
            created_at=video.created_at.isoformat(),
            updated_at=video.updated_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=List[VideoResponse])
async def list_videos(
    course_id: Optional[UUID] = Query(None, description="Filter by course ID"),
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List videos.
    
    Returns a list of videos, optionally filtered by course.
    """
    video_service = VideoService(db)
    videos = await video_service.list_videos(
        course_id=course_id,
        limit=limit,
        offset=offset
    )
    
    return [
        VideoResponse(
            id=video.id,
            title=video.title,
            description=video.description,
            duration_seconds=video.duration_seconds,
            thumbnail_url=video.thumbnail_url,
            course_id=video.course_id,
            status=video.status,
            streaming_url=video.streaming_url,
            created_at=video.created_at.isoformat(),
            updated_at=video.updated_at.isoformat()
        ) for video in videos
    ]

@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: UUID = Path(..., description="The ID of the video to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific video by ID.
    
    Returns the video data for a single video.
    """
    video_service = VideoService(db)
    video = await video_service.get_video(video_id)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    return VideoResponse(
        id=video.id,
        title=video.title,
        description=video.description,
        duration_seconds=video.duration_seconds,
        thumbnail_url=video.thumbnail_url,
        course_id=video.course_id,
        status=video.status,
        streaming_url=video.streaming_url,
        created_at=video.created_at.isoformat(),
        updated_at=video.updated_at.isoformat()
    )

@router.put("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_data: VideoUpdateRequest,
    video_id: UUID = Path(..., description="The ID of the video to update"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a video.
    
    Updates the metadata for an existing video.
    """
    video_service = VideoService(db)
    
    try:
        video = await video_service.update_video(
            video_id=video_id,
            title=video_data.title,
            description=video_data.description,
            thumbnail_url=video_data.thumbnail_url,
            updated_by=UUID(current_user["sub"])
        )
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        return VideoResponse(
            id=video.id,
            title=video.title,
            description=video.description,
            duration_seconds=video.duration_seconds,
            thumbnail_url=video.thumbnail_url,
            course_id=video.course_id,
            status=video.status,
            streaming_url=video.streaming_url,
            created_at=video.created_at.isoformat(),
            updated_at=video.updated_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: UUID = Path(..., description="The ID of the video to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a video.
    
    Removes a video and its associated content.
    """
    video_service = VideoService(db)
    success = await video_service.delete_video(
        video_id=video_id,
        deleted_by=UUID(current_user["sub"])
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    return None

@router.post("/{video_id}/upload", response_model=VideoResponse)
async def upload_video_content(
    video_file: UploadFile = File(...),
    video_id: UUID = Path(..., description="The ID of the video to upload content for"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload video content.
    
    Uploads the actual video file content for a video that has already been created.
    """
    upload_service = VideoUploadService(db)
    
    try:
        video = await upload_service.upload_video(
            video_id=video_id,
            file=video_file,
            uploaded_by=UUID(current_user["sub"])
        )
        
        return VideoResponse(
            id=video.id,
            title=video.title,
            description=video.description,
            duration_seconds=video.duration_seconds,
            thumbnail_url=video.thumbnail_url,
            course_id=video.course_id,
            status=video.status,
            streaming_url=video.streaming_url,
            created_at=video.created_at.isoformat(),
            updated_at=video.updated_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{video_id}/playback", response_model=VideoPlaybackInfo)
async def get_video_playback_info(
    video_id: UUID = Path(..., description="The ID of the video to get playback info for"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get video playback information.
    
    Returns streaming URL and other playback-related information for a video.
    """
    streaming_service = VideoStreamingService(db)
    
    try:
        playback_info = await streaming_service.get_playback_info(
            video_id=video_id,
            user_id=UUID(current_user["sub"])
        )
        
        if not playback_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found or not ready for playback"
            )
        
        return VideoPlaybackInfo(
            streaming_url=playback_info["streaming_url"],
            format=playback_info["format"],
            quality_options=playback_info["quality_options"],
            subtitle_tracks=playback_info["subtitle_tracks"],
            last_position=playback_info.get("last_position")
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{video_id}/position", status_code=status.HTTP_204_NO_CONTENT)
async def update_video_position(
    position_seconds: int = Form(..., ge=0),
    video_id: UUID = Path(..., description="The ID of the video to update position for"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update video playback position.
    
    Saves the user's current position in the video for resuming later.
    """
    streaming_service = VideoStreamingService(db)
    
    try:
        await streaming_service.update_playback_position(
            video_id=video_id,
            user_id=UUID(current_user["sub"]),
            position_seconds=position_seconds
        )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
