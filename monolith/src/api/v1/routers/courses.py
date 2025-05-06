from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_db
from src.common.auth import get_current_user, get_current_active_user, get_current_admin
from src.modules.courses.domain.course import CourseStatus, CourseLevel
from src.modules.courses.services.course_service import CourseService
from src.modules.courses.services.section_service import SectionService
from src.modules.courses.services.lesson_service import LessonService
from src.modules.courses.services.enrollment_service import EnrollmentService
from src.modules.courses.services.review_service import ReviewService
from src.modules.courses.services.category_service import CategoryService
from src.api.v1.schemas.courses import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseListResponse,
    CourseDetailResponse,
    SectionCreate,
    SectionUpdate,
    SectionResponse,
    LessonCreate,
    LessonUpdate,
    LessonResponse,
    EnrollmentResponse,
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    SubcategoryCreate,
    SubcategoryUpdate,
    SubcategoryResponse
)
from src.api.v1.schemas.common import PaginationParams

router = APIRouter(
    prefix="/courses",
    tags=["courses"],
    responses={404: {"description": "Not found"}},
)

# Dependency to get course service
def get_course_service(db: AsyncSession = Depends(get_db)) -> CourseService:
    return CourseService(db)

# Dependency to get section service
def get_section_service(db: AsyncSession = Depends(get_db)) -> SectionService:
    return SectionService(db)

# Dependency to get lesson service
def get_lesson_service(db: AsyncSession = Depends(get_db)) -> LessonService:
    return LessonService(db)

# Dependency to get enrollment service
def get_enrollment_service(db: AsyncSession = Depends(get_db)) -> EnrollmentService:
    return EnrollmentService(db)

# Dependency to get review service
def get_review_service(db: AsyncSession = Depends(get_db)) -> ReviewService:
    return ReviewService(db)

# Dependency to get category service
def get_category_service(db: AsyncSession = Depends(get_db)) -> CategoryService:
    return CategoryService(db)

# Course endpoints
@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_data: CourseCreate,
    course_service: CourseService = Depends(get_course_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Create a new course."""
    # Set the current user as instructor
    course_dict = course_data.dict()
    course_dict["instructor_id"] = current_user["id"]
    
    course = await course_service.create_course(course_dict)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create course"
        )
    
    return course

@router.get("/", response_model=CourseListResponse)
async def list_courses(
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(20, gt=0, le=100, description="Items per page"),
    status: Optional[CourseStatus] = Query(None, description="Filter by course status"),
    instructor_id: Optional[str] = Query(None, description="Filter by instructor ID"),
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    level: Optional[CourseLevel] = Query(None, description="Filter by course level"),
    featured: Optional[bool] = Query(None, description="Filter by featured status"),
    search: Optional[str] = Query(None, description="Search term"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    course_service: CourseService = Depends(get_course_service)
):
    """List courses with pagination and filtering."""
    courses, total = await course_service.list_courses(
        page=page,
        page_size=page_size,
        status=status,
        instructor_id=instructor_id,
        category_id=category_id,
        level=level,
        featured=featured,
        search_term=search,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return {
        "items": courses,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }

@router.get("/{course_id}", response_model=CourseDetailResponse)
async def get_course(
    course_id: str = Path(..., description="Course ID"),
    course_service: CourseService = Depends(get_course_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get course details."""
    course_data = await course_service.get_course_with_sections_and_lessons(course_id)
    if not course_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    course = course_data["course"]
    
    # If course is not published, only instructor or admin can view it
    if course.status != CourseStatus.PUBLISHED:
        if not current_user or (current_user["id"] != course.instructor_id and current_user.get("role") != "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Course is not published"
            )
    
    # Get statistics
    course_stats = await course_service.get_course_statistics(course_id)
    
    # Add enrollment info if user is logged in
    enrollment_info = None
    if current_user:
        enrollment_service = EnrollmentService(course_service.db)
        enrollment_info = await enrollment_service.check_user_enrollment(current_user["id"], course_id)
    
    return {
        "course": course,
        "sections": course_data["sections"],
        "statistics": course_stats,
        "enrollment": enrollment_info
    }

@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_data: CourseUpdate,
    course_id: str = Path(..., description="Course ID"),
    course_service: CourseService = Depends(get_course_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Update a course."""
    # Check if course exists and user is the instructor
    course = await course_service.get_course_by_id(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Only the instructor or admin can update the course
    if course.instructor_id != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this course"
        )
    
    updated_course = await course_service.update_course(course_id, course_data.dict(exclude_unset=True))
    if not updated_course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update course"
        )
    
    return updated_course

@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str = Path(..., description="Course ID"),
    course_service: CourseService = Depends(get_course_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Delete a course."""
    # Check if course exists and user is the instructor
    course = await course_service.get_course_by_id(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Only the instructor or admin can delete the course
    if course.instructor_id != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this course"
        )
    
    result = await course_service.delete_course(course_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete course"
        )
    
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{course_id}/publish", response_model=CourseResponse)
async def publish_course(
    course_id: str = Path(..., description="Course ID"),
    course_service: CourseService = Depends(get_course_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Publish a course."""
    # Check if course exists and user is the instructor
    course = await course_service.get_course_by_id(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Only the instructor or admin can publish the course
    if course.instructor_id != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to publish this course"
        )
    
    published_course = await course_service.publish_course(course_id)
    if not published_course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to publish course. Make sure the course has at least one section with content."
        )
    
    return published_course

@router.post("/{course_id}/unpublish", response_model=CourseResponse)
async def unpublish_course(
    course_id: str = Path(..., description="Course ID"),
    course_service: CourseService = Depends(get_course_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Unpublish a course (set to draft)."""
    # Check if course exists and user is the instructor
    course = await course_service.get_course_by_id(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Only the instructor or admin can unpublish the course
    if course.instructor_id != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to unpublish this course"
        )
    
    unpublished_course = await course_service.unpublish_course(course_id)
    if not unpublished_course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to unpublish course"
        )
    
    return unpublished_course

@router.get("/instructor/{instructor_id}", response_model=CourseListResponse)
async def get_instructor_courses(
    instructor_id: str = Path(..., description="Instructor ID"),
    include_drafts: bool = Query(False, description="Include draft courses"),
    course_service: CourseService = Depends(get_course_service),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get courses by instructor."""
    # Only the instructor or admin can see draft courses
    if include_drafts and (not current_user or (current_user["id"] != instructor_id and current_user.get("role") != "admin")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view draft courses"
        )
    
    courses = await course_service.get_instructor_courses(
        instructor_id=instructor_id,
        include_drafts=include_drafts
    )
    
    return {
        "items": courses,
        "total": len(courses),
        "page": 1,
        "page_size": len(courses),
        "pages": 1
    }

# Section endpoints
@router.post("/{course_id}/sections", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    section_data: SectionCreate,
    course_id: str = Path(..., description="Course ID"),
    section_service: SectionService = Depends(get_section_service),
    course_service: CourseService = Depends(get_course_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Create a new section in a course."""
    # Check if course exists and user is the instructor
    course = await course_service.get_course_by_id(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Only the instructor or admin can add sections
    if course.instructor_id != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to add sections to this course"
        )
    
    # Set the course ID in section data
    section_dict = section_data.dict()
    section_dict["course_id"] = course_id
    
    section = await section_service.create_section(section_dict)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create section"
        )
    
    return section

# Just define a few more key endpoints (there would be many more in a complete implementation)
@router.post("/{course_id}/enroll", response_model=EnrollmentResponse)
async def enroll_in_course(
    course_id: str = Path(..., description="Course ID"),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
    course_service: CourseService = Depends(get_course_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Enroll the current user in a course."""
    # Check if course exists and is published
    course = await course_service.get_course_by_id(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    if course.status != CourseStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course is not published"
        )
    
    # Enroll the user
    enrollment = await enrollment_service.enroll_user(
        user_id=current_user["id"],
        course_id=course_id
    )
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to enroll in course"
        )
    
    return enrollment

@router.post("/{course_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: ReviewCreate,
    course_id: str = Path(..., description="Course ID"),
    review_service: ReviewService = Depends(get_review_service),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """Create a review for a course."""
    # Check if the user is enrolled in the course
    enrollment_info = await enrollment_service.check_user_enrollment(current_user["id"], course_id)
    if not enrollment_info.get("is_enrolled") and not current_user.get("role") == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be enrolled in the course to leave a review"
        )
    
    # Set the user ID and course ID in review data
    review_dict = review_data.dict()
    review_dict["user_id"] = current_user["id"]
    review_dict["course_id"] = course_id
    
    review = await review_service.create_review(review_dict)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create review"
        )
    
    return review
